"""A wrap for accessing data from `Sphinx conf.py`_, from `Sphinx`_."""

import importlib
import inspect
import logging
import os

from python_compatibility import imports
from six.moves import mock
from sphinx import config

_CONFIGURATION_FILE_NAME = "conf.py"
_LOGGER = logging.getLogger(__name__)


class ConfPy(object):
    """A wrap for accessing data from `Sphinx conf.py`_, from `Sphinx`_."""

    def __init__(self, module):
        """Keep track of a `Sphinx conf.py`_ module.

        Args:
            module (module): The Python `Sphinx conf.py`_ to keep.

        """
        super(ConfPy, self).__init__()

        self._module = module
        self._directory = os.path.dirname(inspect.getsourcefile(self._module))

    @classmethod
    def from_directory(cls, directory):
        """Find and convert a `Sphinx conf.py`_ located directly within ``directory``.

        Args:
            directory (str):
                The absolute path to the documentation source directory,
                within some source Rez package.
                e.g. ``"{rez_root}/documentaion/source"``.

        Returns:
            ConfPy: The created instance.

        """
        return cls.from_path(os.path.join(directory, _CONFIGURATION_FILE_NAME))

    @classmethod
    def from_path(cls, path):
        """Convert a file path into an instance.

        Args:
            path (str): The absolute path to a file or folder on-disk.

        Raises:
            IOError:

        Returns:
            ConfPy: The converted instance.

        """
        if not os.path.isfile(path):
            raise IOError(
                'Path "{path}" does not exist and cannot be imported.'.format(path=path)
            )

        module = imports.import_file("rez_sphinx_conf", path)

        return cls(module)

    @staticmethod
    def is_valid_directory(directory):
        """Check if ``directory`` has a configuration file that this class can load.

        Args:
            directory (str): The absolute or relative folder path on-disk.

        Returns:
            bool: If the configuration can be read, return True.

        """
        return os.path.isfile(os.path.join(directory, _CONFIGURATION_FILE_NAME))

    def _get_extensions(self):
        """list[str]: Get each Python importable module that `Sphinx`_ will load."""
        if not hasattr(self._module, "extensions"):
            return []

        return getattr(self._module, "extensions")

    def _get_master_doc(self):
        """str: Get the name of the documentation "front page" file."""
        try:
            return self._module.master_doc
        except AttributeError:
            return "index"  # A reasonable default

    def get_attributes(self, allow_extensions=True):
        """Get each found attribute and its values.

        Args:
            allow_extensions (bool, optional):
                If True, include `Sphinx`_ extension attributes, like
                `intersphinx_mapping`_. If False, only return the base
                `Sphinx`_ attributes and nothing else.

        Returns:
            dict[tuple[str], object]: The found attribute and its value.

        """
        names = self.get_known_attribute_names(allow_extensions=allow_extensions)

        return {
            name: getattr(self._module, name)
            for name in names
            if hasattr(self._module, name)
        }

    def get_extensions(self):
        """Get all registered `Sphinx`_ extensions. e.g. `sphinx.ext.viewcode`_.

        Returns:
            list[str]: The registered extensions.

        """
        return self._module.extensions or []

    def get_known_attribute_names(self, allow_extensions=True):
        """Find every `Sphinx`_-known `conf.py`_ attribute.

        Args:
            allow_extensions (bool, optional):
                If True, include `Sphinx`_ extension attributes, like
                `intersphinx_mapping`_. If False, only return the base
                `Sphinx`_ attributes and nothing else.

        Returns:
            set[str]: Each found attribute name.

        """
        output = set(config.Config.config_values.keys())

        if allow_extensions:
            extensions = self._get_extensions()
            output.update(_get_extension_attribute_names(extensions))

        return output

    def get_master_document_path(self):
        """str: Get the full path on-disk where this `Sphinx conf.py`_ lives."""
        name = self._get_master_doc() + self.get_source_extension()

        return os.path.join(self._directory, name)

    def get_source_extension(self):
        """str: Get the extension to search for ReST files."""
        try:
            return self._module.source_suffix
        except AttributeError:
            return ".rst"  # A reasonable default

    def get_module_path(self):
        """str: Get the full path to this `conf.py`_ file, on-disk."""
        return self._module.__file__


def _get_extension_attribute_names(extensions):
    """Find every attribute for each `Sphinx`_ extension in ``extensions``.

    Args:
        extensions (iter[str]):
            An importable Python namespace to try to get attribute contents
            from. e.g. ``["sphinx.ext.intersphinx", "sphinx.ext.viewcode"]``.

    Returns:
        set[str]: Every found attribute name across all extensions.

    """

    def _capture_value(appender):
        def _wrap(attribute_name, *args, **kwargs):
            appender(attribute_name)

            return None

        return _wrap

    modules = []

    for name in extensions:
        _LOGGER.debug('Now importing "%s" to query its attributes.', name)

        try:
            modules.append(importlib.import_module(name))
        except Exception as error:
            # We're importing arbitrary Python modules based on whatever the
            # user has set.  So we need to catch generalized errors.
            #
            _LOGGER.warning('Skipped loading "%s". Error, "%s".', name, str(error))

            continue

    # Since `Sphinx`_ requires a ``setup`` function on every extension module
    # which defines attributes, we take advantage of this convention by passing
    # a fake ``app`` variable and returning its accumulated results.
    #
    # Simple but effective.
    #
    container = set()
    mocker = mock.MagicMock()
    mocker.add_config_value = _capture_value(container.add)

    for module in modules:
        if hasattr(module, "setup"):
            module.setup(mocker)

    return container
