"""Connect `Sphinx`_ to :ref:`rez_sphinx`."""

import io
import logging
import os
import textwrap
import traceback
from datetime import date

import six
from rez_utilities import finder

from ..preferences import preference
from . import exception, generic, package_query, path_control

_LOGGER = logging.getLogger(__name__)
_REZ_SPHINX_BOOTSTRAP_LINES = textwrap.dedent(
    """
    # -- rez-sphinx start --
    # -- DO NOT TOUCH --
    #
    # These lines are needed for rez-sphinx to work
    #
    from rez_sphinx import api

    locals().update(api.bootstrap(locals()))
    #
    # If you want to add extra user customizations, please feel free to add any
    # of them BELOW this line.
    #
    # -- rez-sphinx end --
    """
)

_REZ_REQUIRES_KEY = "requires"

_AUTHOR = "author"
_COPYRIGHT = "copyright"
_EXTENSIONS = "extensions"
_INTERSPHINX_MAPPING_KEY = "intersphinx_mapping"
_LATEX_DOCUMENTS = "latex_documents"
_MAN_PAGES = "man_pages"
_MASTER_DOC = "master_doc"
_PROJECT = "project"
_PROJECT_COPYRIGHT = "project_copyright"
_RELEASE = "release"
_VERSION = "version"

_LATEX_FILE_EXTENSION = ".tex"
_LATEX_AUTHOR_SEPARATOR = " \\and "  # Reference: https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-latex_documents
_LATEX_THEME = "manual"


def _get_intersphinx_candidates(package):
    """Search dependencies of ``package`` for a `objects.inv`_.

    Args:
        package (rez.packages.Package):
            A Rez package which the user is attempting to build documentation for.

    Returns:
        set[str]:
            All Rez package family name requests which the user needs in
            order to build their documentation.

    """

    def _filter_generic_requests(requests):
        output = set()

        for request in requests:
            if request.ephemeral:
                _LOGGER.debug('Skipped loading "%s" ephemeral request.', request)

                continue

            if request.weak and not _in_resolve(request.name):
                _LOGGER.debug('Skipped loading "%s" weak request.', request)

                continue

            if not request.weak and request.conflict:
                _LOGGER.debug('Skipped loading "%s" excluded request.', request)

                continue

            if request.name in output:
                # If the user defines a package requirement in more than one
                # place, that's okay because a Rez resolve will only get one
                # single Package version. Just skip the duplicate requirement.
                #
                continue

            output.add(request.name)

        return output

    output = _filter_generic_requests(package_query.get_dependencies(package))

    test_name = _get_test_environment()

    if test_name:
        # If a test exists, we expect these to be in the resolve
        test_requires = _get_tests_requires_by_name(package, test_name)
    else:
        # If a test doesn't exist, we have to guess
        test_requires = {
            request
            for request in _get_tests_requires(package)
            if _in_resolve(request.name)
        }

    test_requires = _filter_generic_requests(test_requires)
    output.update(test_requires)

    return output


def _in_resolve(name):
    """Check if ``name`` is a Rez package family which is in the current resolve.

    Args:
        name (str): A Rez package name. e.g. "python", "Sphinx", etc.

    Returns:
        bool: If ``name`` has a root path.

    """
    try:
        return bool(path_control.get_installed_root(name))
    except EnvironmentError:
        return False


def _get_copyright(package):
    """Get a Sphinx-friendly copyright statement for some Rez ``package``.

    Args:
        package (rez.packages.Package): The source / install package to query from.

    Returns:
        str: The found year or year + author name, if there is any author.

    """
    authors = package.authors
    year = date.today().year

    if not authors:
        return str(year)

    primary = authors[0]

    return "{year}, {primary}".format(year=year, primary=primary)


def _get_environment_package(name):
    """Find a Rez package describing ``name``.

    Important:
        This function assumes that ``name`` is in the current Rez resolve.

    Args:
        name (str):
            The Rez package family name to search for. e.g. "rez",
            "Sphinx", "python", etc.

    Raises:
        EnvironmentError:
            If ``name`` is not listed in your Rez environment.
        RuntimeError:
            If for some reason ``name`` exists but has no Rez valid Rez
            package. If this happens, it's almost 100% some kind of Rez
            build / release issue, caused by **user** error.

    Returns:
        rez.packages.Package: The found package.

    """
    directory = path_control.get_installed_root(name)
    package = finder.get_nearest_rez_package(directory)

    if package:
        return package

    raise RuntimeError(
        'Found directory "{directory}" for Rez package "{name}" but no Rez package. '
        "This should not happen.".format(directory=directory, name=name)
    )


def _get_intersphinx_mappings(package):
    """Find every :ref`:objects.inv` file for each dependency of ``package``.

    The found `objects.inv`_ will be used to populate a
    `intersphinx_mapping`_ for ``package``. This enables
    cross-linking between external Rez packages, as long as they were
    also built by Sphinx.

    Note:
        The searched Rez packages by default are

        - `requires`_
        - :ref:`build_documentation_key`

        If you want to search for other requests for your package, like
        `private_build_requires`_ or `build_requires`_, consider
        setting that using `rez-config`_.

    Args:
        package (rez.packages.Package):
            A Rez package which the user is attempting to build documentation for.

    Returns:
        dict[str, tuple[str] or str]: A suitable `intersphinx_mapping`_ for `Sphinx`_.

    """
    output = {}

    for request in _get_intersphinx_candidates(package):
        package = _get_environment_package(request)
        path = _get_package_objects_inv(package)

        if not path:
            continue

    return output


def _get_package_objects_inv(package):
    """Find the path to a Rez package's `objects.inv`_ file.

    The package may have a locally installed `objects.inv`_ or it
    may be pointing to an Internet URL.  Either way, return the string
    there.

    Args:
        package (rez.packages.Package):
            A Rez package which we assume may have built :ref:`rez_sphinx`
            documentation and thus also has a `objects.inv`_ file.

    Returns:
        str:
            The Internet URL or the absolute path for a directory
            containing the "objects.inv" file.

    """
    help_ = package.help or []
    help_label = preference.get_help_label()

    if not help_:
        _LOGGER.warning(
            'Package "%s" has no help. No "%s" help found.',
            package.name,
            help_label,
        )

        return ""

    if isinstance(help_, six.string_types):
        _LOGGER.warning(
            'Package "%s" has single-line help. No "%s" help found.',
            package.name,
            help_label,
        )

        return ""

    for label, path in help_:
        if label == help_label:
            _LOGGER.info(
                'Found: Package "%s" has "%s" defined.', package.name, help_label
            )

            return path

    _LOGGER.info(
        'Package "%s" has tests but no "%s" is defined.', package.name, help_label
    )

    return ""


def _get_test_environment():
    """str: Get the current Rez test which is executing, if any."""
    # TODO : Make sure this works
    #
    # Reference: https://github.com/nerdvegas/rez/issues/1261
    #
    return os.getenv("REZ_CURRENT_TEST_NAME", "")


def _get_tests_requires(package):
    """Find every requested requirement of ``package``.

    Args:
        package (rez.packages.Package):
            The Rez package which the user is trying to generate Sphinx
            documentation for.

    Returns:
        set[rez.utils.formatting.PackageRequest]:
            All requests which the user needs in order to build their
            documentation.

    """
    tests = package.tests or {}

    if not tests:
        return set()

    test = ""

    for key in preference.get_build_documentation_keys(package=package):
        test = tests.get(key)

        if test:
            break
    else:
        return set()

    if isinstance(test, six.string_types):
        # It's a rez-test like ``tests = {"build_documentation": "bar"}``.
        # It defines no extra requirements so we can skip it.
        #
        return set()

    return set(test.get(_REZ_REQUIRES_KEY) or [])


def _get_tests_requires_by_name(package, test_name):
    """Find all `requires`_ from a given Rez test.

    Args:
        package (rez.packages.Package): The Rez package to query from.
        test_name (str): The `tests`_ key to get requires from.

    Raises:
        RuntimeError: If ``package`` has no defined `tests`_.

    Returns:
        set[rez.utils.formatting.PackageRequest]:
            All found `requires`_ for ``test_name``, if any.

    """
    if not package.tests:
        raise RuntimeError(
            'Package "{package}" has no defined tests.'.format(package=package)
        )

    try:
        test = package.tests[test_name]
    except KeyError:
        raise RuntimeError(
            'Package "{package}" has no defined "{test_name}" test.'.format(
                package=package,
                test_name=test_name,
            )
        )

    if isinstance(test, six.string_types):
        return set()

    try:
        return set(test[_REZ_REQUIRES_KEY])
    except TypeError:
        # This happens if ``test`` is like ``tests = {"foo": "bar"}``,
        # where no ``"requires"`` key is provided. Just ignore it, if that
        # is the case.
        #
        return set()


def _get_major_minor_version(version):
    """Convert ``version`` into a "major.minor" string.

    Args:
        version (:class:`rez.vendor.version.version.Version`): The object to convert.

    Returns:
        str: The major + minor.

    """
    # TODO : We need to handle non-semantic versions here
    return "{version.major}.{version.minor}".format(version=version)


def _get_nearest_caller_package():
    """Find the Rez package which called this function.

    Important:
        This function is fragile. Don't use it outside of the context of
        :func:`bootstrap`.

    Raises:
        NoPackageFound: If no Rez package could be found.

    Returns:
        rez.packages.Package: The found package.

    """
    stack = traceback.extract_stack(limit=3)
    frame = stack[0]

    if hasattr(frame, "filename"):
        caller_path = frame.filename  # In Python 3, ``frame`` is :class:`FrameSummary`
    else:
        caller_path = frame[0]  # In Python 2, ``frame`` is a tuple

    _LOGGER.debug('Found caller "%s" file path.', caller_path)

    directory = os.path.dirname(caller_path)

    package = finder.get_nearest_rez_package(directory)

    if package:
        return package

    raise exception.NoPackageFound(
        'Directory "{directory}" has no Rez package. '
        "This exception is almost certainly a bug. "
        "Please contact rez_sphinx maintainers.".format(directory=directory),
    )


def _merge_intersphinx_maps(data, package):
    """Find and combine all links found within ``data`` and ``package``.

    Note:
        - All documentation exported directly from Rez packages
          :ref:`rez_sphinx` will be preferred over what the user has previously set.
        - However if a resolved Rez package has no found documentation and
          there's an entry in
          :ref:`rez_sphinx.intersphinx_settings.package_link_map`, that will be
          used instead.

    Args:
        data (dict[str, object]):
            Incoming ``locals()`` data from an existing `Sphinx conf.py`_.
        package (rez.packages.Package):
            The package to query from and extend ``data`` with extra
            information. If no package is given, the package is
            determined automatically from the caller's site.

    Returns:
        dict[str, tuple[str] or str]: A suitable `intersphinx_mapping`_ for `Sphinx`_.

    """
    existing_mapping = data.get(_INTERSPHINX_MAPPING_KEY) or {}
    output = existing_mapping.copy()

    # Prefer intersphinx maps we've found using Rez packages
    output.update(_get_intersphinx_mappings(package))

    # Use any known package paths
    #
    # - If the package is in the current resolve
    # - There is no existing value
    #
    for fallback_key, fallback_link in preference.get_package_link_map(
        package=package
    ).items():
        if _in_resolve(fallback_key) and fallback_key not in output:
            output[fallback_key] = fallback_link

    return output


def append_bootstrap_lines(path):
    """Append :ref:`rez_sphinx` specific commands to a `Sphinx`_ conf.py file.

    Args:
        path (str):
            The absolute path to a conf.py which `Sphinx`_ uses to source
            and build the user's documentation.

    """
    with io.open(path, "a", encoding="utf-8") as handler:
        handler.write(generic.decode("\n\n" + _REZ_SPHINX_BOOTSTRAP_LINES))


def bootstrap(data, package=None, skip=frozenset()):
    """Gather Rez package information for `Sphinx`_.

    This data is returned and used to auto-fill-out the values for
    `Sphinx conf.py`_.

    Args:
        data (dict[str, object]):
            Incoming ``locals()`` data from an existing `Sphinx conf.py`_.
        package (rez.packages.Package, optional):
            The package to query from and extend ``data`` with extra
            information. If no package is given, the package is
            determined automatically from the caller's site.
        skip (set[str], optional):
            Any variable which you do not want :ref:`rez_sphinx build run` to
            set.  This includes both the built-in variables, such as
            ``"intersphinx_mapping"`` and even dynamic variables set using
            :ref:`rez_sphinx.sphinx_conf_overrides`

    Returns:
        dict[str, object]: All Rez data to send to the `Sphinx conf.py`_.

    """
    package = package or _get_nearest_caller_package()
    authors = package.authors or []
    master_document = preference.get_master_document_name(package=package) or "index"
    title = "{package.name} Documentation".format(package=package)
    description = package.description or "{package.name} Documentation".format(
        package=package
    )

    if _AUTHOR not in skip:
        # Note: Not sure if ", " separation is expected. I couldn't find
        # documentation about Sphinx on what the expected format is.
        #
        data[_AUTHOR] = ", ".join(authors)

    if _COPYRIGHT not in skip:
        data[_COPYRIGHT] = _get_copyright(package)

    if _EXTENSIONS not in skip:
        extensions = set(data.get(_EXTENSIONS) or set())
        extensions.update(preference.get_sphinx_extensions())
        data[_EXTENSIONS] = sorted(extensions)

    if _INTERSPHINX_MAPPING_KEY not in skip:
        data[_INTERSPHINX_MAPPING_KEY] = _merge_intersphinx_maps(data, package)

    if _LATEX_DOCUMENTS not in skip:
        data[_LATEX_DOCUMENTS] = [
            (
                master_document,
                package.name + _LATEX_FILE_EXTENSION,
                title,
                _LATEX_AUTHOR_SEPARATOR.join(authors),
                _LATEX_THEME,
                False,
            ),
        ]

    if _MAN_PAGES not in skip:
        section_index = 1
        data[_MAN_PAGES] = [
            (master_document, package.name, description, authors, section_index)
        ]

    if _MASTER_DOC not in skip:
        # Reference:
        # https://github.com/readthedocs/readthedocs.org/issues/2569#issuecomment-485117471
        #
        data[_MASTER_DOC] = master_document

    if _PROJECT not in skip:
        data[_PROJECT] = package.name

    if _PROJECT_COPYRIGHT not in skip:
        # An alias for "copyright". It's only Sphinx 3.5+ but it's harmless in
        # older Sphinx versions so we leave it in, regardless.
        #
        # Reference:
        # https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-project_copyright
        #
        data[_PROJECT_COPYRIGHT] = _get_copyright(package)

    if _RELEASE not in skip:
        # Confusingly, `Sphinx`_ treats `version`_ as a major.minor release.
        # And `release`_ is the full version name.
        #
        # So a Rez version -> Sphinx release
        # So a Sphinx version -> Nothing in Rez
        #
        data[_RELEASE] = str(package.version)

    if _VERSION not in skip:
        # Confusingly, `Sphinx`_ treats `version`_ as a major.minor release.
        # And `release`_ is the full version name.
        #
        # So a Rez version -> Sphinx release
        # So a Sphinx version -> Nothing in Rez
        #
        data[_VERSION] = _get_major_minor_version(package.version)

    overrides = {
        key: value
        for key, value in preference.get_sphinx_configuration_overrides(
            package=package
        ).items()
        if key not in skip
    }
    _LOGGER.info('Got extra conf.py overrides "%s".', overrides)
    data.update(overrides)

    return data
