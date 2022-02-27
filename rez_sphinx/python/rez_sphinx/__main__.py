"""Run :mod:`rez_sphinx`'s main CLI."""

from __future__ import print_function

import logging
import sys

from . import cli
from ._core import exception


def _setup_logger():
    """Add stdout logging while the CLI is running."""
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def main(text):
    """Parse and run the users's given parameters.

    Args:
        text (list[str]):
            The user-provided arguments to run via :ref:`rez_sphinx`.
            This is usually space-separated CLI text like
            ``["init", "--directory", "/path/to/rez/package"]``.

    """
    try:
        cli.main(text)
    except exception.Base as error:
        print(str(error), file=sys.stderr)


if __name__ == "__main__":
    _setup_logger()
    main(text=sys.argv[1:])
