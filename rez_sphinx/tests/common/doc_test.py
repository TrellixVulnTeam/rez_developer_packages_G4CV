"""Miscellaneous documentation/unittest related functions."""

import os


def add_to_default_text(directory):
    """Quickly add some non-default text to the default files within ``directory``."""
    source = os.path.join(directory, "documentation", "source")

    for path in (
        os.path.join(source, "developer_documentation.rst"),
        os.path.join(source, "user_documentation.rst"),
    ):
        with open(path, "a") as handler:
            handler.write("Extra text here")
