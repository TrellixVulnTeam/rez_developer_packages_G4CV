#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The main module that controls the command-line's interface."""

from __future__ import print_function

import argparse
import fnmatch
import logging
import operator
import os
import sys

import six
from rez.config import config
from rez_utilities import inspection

from .core import cli_constant, registry, worker

_LOGGER = logging.getLogger(__name__)


def __report(arguments, _):
    """Print out every package and its status information.

    This function prints out

    - Packages that need documentation
    - Packages that were found as "invalid"
    - Packages that were skipped automatically
    - Packages that were ignored explicitly (by the user)

    Args:
        arguments (:class:`argparse.Namespace`):
            The base user-provided arguments from command-line.
        _ (:class:`argparse.Namespace`):
            An un-used argument for this function.

    """
    ignore_patterns, packages_path, search_packages_path = _resolve_arguments(
        arguments.ignore_patterns,
        arguments.packages_path,
        arguments.search_packages_path,
    )
    rez_packages = set(arguments.rez_packages)
    latest_packages = inspection.iter_latest_packages(
        paths=packages_path, packages=rez_packages,
    )
    ignored_packages, other_packages = _split_the_ignored_packages(
        latest_packages, ignore_patterns
    )

    packages, invalids, skips = worker.report(
        other_packages,
        maximum_repositories=arguments.maximum_repositories,
        maximum_rez_packages=arguments.maximum_rez_packages,
        paths=packages_path + search_packages_path,
    )

    _print_ignored(ignored_packages)
    print("\n")
    _print_skips(skips, arguments.verbose)
    print("\n")
    _print_invalids(invalids, arguments.verbose)
    print("\n")
    _print_missing(packages, arguments.verbose)

    sys.exit(0)


def __fix(arguments, command_arguments):
    """Add documentation to any package that needs it.

    Args:
        arguments (:class:`argparse.Namespace`):
            The base user-provided arguments from command-line.
        command_arguments (:class:`argparse.Namespace`):
            The registered command's parsed arguments.

    """
    ignore_patterns, packages_path, search_packages_path = _resolve_arguments(
        arguments.ignore_patterns,
        arguments.packages_path,
        arguments.search_packages_path,
    )
    rez_packages = set(arguments.rez_packages)
    latest_packages = inspection.iter_latest_packages(
        paths=packages_path, packages=rez_packages,
    )
    ignored_packages, other_packages = _split_the_ignored_packages(
        latest_packages, ignore_patterns
    )
    print("TODO need to print the ignored packages")

    packages, unfixed, invalids, skips = worker.fix(
        other_packages,
        command_arguments,
        maximum_repositories=arguments.maximum_repositories,
        maximum_rez_packages=arguments.maximum_rez_packages,
        paths=packages_path + search_packages_path,
        keep_temporary_files=arguments.keep_temporary_files,
        temporary_directory=arguments.temporary_directory,
    )

    # TODO : Change `Skip` into a class and make it the same interface as an exception
    # so that I can easily print both types at the same time, here
    #
    bads = invalids + skips

    if bads:
        print("Some packages are invalid or had to be skipped.")
        print("\n")
        print(bads)

    if unfixed:
        print("These packages could not be given documentation:")

        for package, error in sorted(unfixed, key=_get_package_name):
            print(
                "{package.name}: {error}".format(
                    package=package, error=str(error) or "No found error message"
                )
            )

        sys.exit(cli_constant.UNFIXED_PACKAGES_FOUND)

    if packages:
        print("These packages were modified successfully:")

        for package in sorted(packages, key=operator.attrgetter("name")):
            print(package.name)


def _split_the_ignored_packages(packages, patterns):
    """Get the "user-ignored" Rez packages.

    Args:
        packages (iter[:class:`rez.packages_.Package`]):
            The Rez packages that may or may not need to be ignored.
        patterns (list[str]):
            All glob patterns that are used to find packages to ignore.
            If a Rez package's name matches even one of the strings in
            `patterns` then the package is ignored.

    Returns:
        tuple[set[:class:`rez.packages_.Package`], set[:class:`rez.packages_.Package`]]:
            The Rez packages to ignore, followed by the Rez packages to
            not ignore.

    """
    ignored = set()
    non_ignored = set()

    for package in packages:
        for pattern in patterns:
            if fnmatch.fnmatch(package.name, pattern):
                ignored.add((package, pattern))

                break
        else:
            non_ignored.add(package)

    return ignored, non_ignored


def _resolve_arguments(patterns, packages_path, search_packages_path):
    """Convert user-provided data into glob expressions.

    Args:
        patterns (iter[str]):
            The strings to resolve into glob patterns. These strings
            could be glob expressions by themselves or they could
            be paths to files on-disk that contain glob expressions
            (one-expression-by-line).
        packages_path (str or list[str]):
            The Rez package directories that "fix" or "report" will run
            on. It could be a path-separated string like "/foo:/bar" or
            a list of strings, like ["/foo", "/bar"].
        search_packages_path (str or list[str]):
            Extra Rez package directories that will be used to help
            resolve packages found in `packages_path`. The Rez packages
            found here will not be processed using "fix" or "report".

    Returns:
        tuple[set[str], list[str]]:
            The resolved glob expressions and the paths to search for
            Rez packages.

    """

    def _read_patterns(path):
        try:
            with open(path, "r") as handler:
                return set(handler.read().splitlines())
        except IOError:
            return set()

    ignore_patterns = set()

    for item in patterns:
        if os.path.isfile(item) or os.path.isabs(item):
            # This happens in 2 scenarios
            # 1. The user-given pattern is actually a path on-disk
            # 2. The user does bash process substitution (e.g.
            #    `rez-batch-process report --ignore-patterns <(cat patterns.txt)`)
            #
            ignore_patterns.update(_read_patterns(item))
        else:
            ignore_patterns.add(item)

    if isinstance(packages_path, six.string_types):
        packages_path = packages_path.split(os.pathsep)

    if isinstance(search_packages_path, six.string_types):
        search_packages_path = search_packages_path.split(os.pathsep)

    return ignore_patterns, packages_path, search_packages_path


def _get_package_name(item):
    """str: Sort a package / error pair by the name of each Rez package."""
    package = item[0]

    return package.name


def _print_ignored(packages):
    """Print every package as "ignored".

    Args:
        packages (iter[:class:`rez.packages_.Package`, str]):
            The Rez package and the glob pattern that it matched against.

    """
    if not packages:
        print("## No Rez package was set to be ignored")
        print("No data found")

        return

    print("## Every package in this list was explicitly set to ignored by the user")

    for package, pattern in sorted(packages, key=_get_package_name):
        print(
            'Package: {package.name} - Pattern: "{pattern}"'.format(
                package=package, pattern=pattern
            )
        )


def _print_invalids(invalids, verbose):
    """Print out the errors that were found.

    Args:
        invalids (iter[:class:`.CoreException`]): The exceptions that were
            raised while searching for packages. Each error contains the
            package, path on-disk to that package, and error message
            that was found.
        verbose (bool): If True, print out as much information as possible.
            If False, print out concise "one-liner" information.

    """
    if not invalids:
        print('## Every found Rez package was marked as "valid"!')
        print("No data found")

        return

    print("## Some packages were marked as invalid. Here's why:")

    template = "{package.name}: {message}"

    if verbose:
        template = "{package.name}: {path} {message}: {full}"

    for message in sorted(
        (
            template.format(
                package=error.get_package(),
                path=error.get_path(),
                message=str(error),
                full=error.get_full_message(),
            )
            for error in invalids
        )
    ):
        print(message)


def _print_missing(packages, verbose):
    """Print all Rez packages that have missing documentation.

    Args:
        packages (iter[:class:`rez.packages`]): The Rez packages that
            describe a Python module / package.
        verbose (bool): If True, print out as much information as possible.
            If False, print out concise "one-liner" information.

    """
    if not packages:
        print("## No Rez package is missing Sphinx documentation.")
        print("No data found")

        return

    print("## These Rez packages are missing Sphinx documentation.")

    template = "{package.name}"

    if verbose:
        template = "{package.name}: {path}"

    for line in sorted(
        template.format(package=package, path=inspection.get_package_root(package))
        for package in packages
    ):
        print(line)


def _print_skips(skips, verbose):
    """Print the Rez packages that were skipped automatically by this tool.

    Skipped packages differ from "invalid" packages in that they are
    "valid Rez packages but just not the kind of Rez packages that
    are missing documentation." Ignored packages are Rez packages
    that the user explicitly said to not process. Skipped packages
    are packages that the user may have meant to process but this
    tool could not (for some reason or another).

    Args:
        skips (:attr:`.Skip`): A collection of Rez package, path on-disk, and a
            message the explains a reason for the skip.
        verbose (bool): If True, print out as much information as possible.
            If False, print out concise "one-liner" information.

    """
    if not skips:
        print("## No packages were skipped")
        print("No data found")

        return

    print("## Packages were skipped. Here's the full list:")

    template = "{issue.package.name}: {issue.reason}"

    if verbose:
        template = "{issue.package.name}: {issue.path}: {issue.reason}"

    for issue in skips:
        print(template.format(issue=issue))


def _add_arguments(parser):
    """Add common arguments to the given command-line `parser`.

    Args:
        parser (:class:`argparse.ArgumentParser`):
            The user-provided parser that will get options appended to it.

    """
    parser.add_argument(
        "-x",
        "--maximum-repositories",
        default=sys.maxint,
        type=int,
        help='If this a value of `2` is used, it means "Only search 2 repositories '
        'for missing documentation, at most".',
    )

    parser.add_argument(
        "-z",
        "--maximum-rez-packages",
        default=sys.maxint,
        type=int,
        help='If this a value of `2` is used, it means "Only search 2 Rez packages '
        'for missing documentation, at most".',
    )

    parser.add_argument(
        "-p",
        "--packages-path",
        default=[config.release_packages_path],  # pylint: disable=no-member
        help="A `{os.pathsep}` separated list of paths that report/fix will be run on. "
        "If not defined, `rez.config.config.release_packages_path` is used, instead.".format(
            os=os
        ),
    )

    parser.add_argument(
        "-s",
        "--search-packages-path",
        default=[config.release_packages_path],  # pylint: disable=no-member
        help="A `{os.pathsep}` separated list of paths to search for Rez package dependencies. "
        "If not defined, `rez.config.config.release_packages_path` is used, instead.".format(
            os=os
        ),
    )

    parser.add_argument(
        "-i",
        "--ignore-patterns",
        default=[],
        nargs="*",
        help="A set of glob expressions or a file to a set of glob expressions. "
        "If a Rez package name matches one of "
        "these, it will not be checked for documentation.",
    )

    parser.add_argument(
        "-k",
        "--keep-temporary-files",
        action="store_true",
        help="If added, do not delete any temporary files that are generated during this run.",
    )

    parser.add_argument(
        "-r",
        "--rez-packages",
        default=set(),
        nargs="+",
        help="The names of Rez packages to process. If no names are given, "
        "every Rez package that is found will be processed.",
    )

    parser.add_argument(
        "-t",
        "--temporary-directory",
        help="A folder on-disk that will be used to clone git repositories.",
    )


def _parse_arguments(text):
    """Add commands such as "check" and "fix" which can detect / add documentation.

    Returns:
        tuple[:class:`argparse.Namespace`, :class:`argparse.Namespace`]:
            The base user-provided arguments from command-line followed
            by the registered command's parsed arguments.

    """
    parser = argparse.ArgumentParser(
        description="Find Rez packages that are missing Sphinx documentation."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print debug messages when this flag is included.",
    )

    sub_parsers = parser.add_subparsers(
        title="commands", description="The available command that can be run."
    )

    reporter = sub_parsers.add_parser("report")
    reporter.set_defaults(execute=__report)
    _add_arguments(reporter)

    fixer = sub_parsers.add_parser("fix")
    fixer.set_defaults(execute=__fix)
    _add_arguments(fixer)

    arguments, unknown_arguments = parser.parse_known_args(text)
    command_parser = registry.get_command(arguments.command)

    if not command_parser:
        print('Command "{arguments.command}" was not found. Options were "{options}".'
              ''.format(arguments=arguments, options=sorted(registry.get_command_keys())))

        sys.exit(cli_constant.NO_COMMAND_FOUND)

    command_arguments = command_parser.parse_arguments(unknown_arguments)

    return arguments, command_arguments


def main(text):
    """Run the main execution of the current script."""
    arguments, command_arguments = _parse_arguments(text)

    if arguments.verbose:
        _LOGGER.setLevel(logging.DEBUG)

    arguments.execute(arguments, command_arguments)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    main(sys.argv[1:])
