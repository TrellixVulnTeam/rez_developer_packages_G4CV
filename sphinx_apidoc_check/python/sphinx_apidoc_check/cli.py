#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from python_compatibility import wrapping
from sphinx.ext import apidoc

from .core import apidoc_patcher, check_exception


def check(text, directory=""):
    if not directory:
        directory = os.getcwd()

    if not os.path.isabs(directory):
        directory = os.path.normcase(os.path.join(os.getcwd(), directory))

    if not os.path.isdir(directory):
        # TODO : Add unittest for this
        raise check_exception.DirectoryDoesNotExist(
            'Path "{directory}" is not a directory. Check your spelling and try again.'.format(
                directory=directory
            ),
        )

    parser = apidoc.get_parser()

    try:
        with wrapping.capture_pipes() as output:
            arguments = parser.parse_args(text)
    except SystemExit as error:
        _, stderr = output

        if error.code != 2:
            print("Found issue:")
            print(stderr)

            raise

        stderr = stderr.replace("__main__.py", "sphinx-apidoc")
        stderr = stderr.splitlines()[-1]  # The first line shows the exact usage

        raise check_exception.InvalidSphinxArguments(
            'Command "{text}" is not a valid call to ``sphinx-apidoc``. '
            'Here\'s the full error message "{stderr}".'.format(
                text=" ".join(text), stderr=stderr.strip()
            )
        )

    if not arguments.dryrun:
        raise check_exception.NoDryRun(
            'Command "{text}" must have --dry-run in its arguments'.format(text=text)
        )

    with wrapping.keep_cwd(directory):
        os.chdir(directory)

        with wrapping.capture_pipes() as output:
            apidoc.main(text)

        stdout, stderr = output

    if stderr:
        raise RuntimeError(
            'Input "{text}" caused sphinx-apidoc to fail while running.'.format(
                text=text
            )
        )

    return apidoc_patcher.parse(stdout.strip())
