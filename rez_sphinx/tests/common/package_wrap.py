import atexit
import functools
import os
import shutil
import tempfile
import textwrap

from rez_utilities import finder


def _delete_later(directory):
    atexit.register(functools.partial(shutil.rmtree, directory))


def make_directory(name):
    """Make a directory with ``name`` and delete it later."""
    directory = tempfile.mkdtemp(suffix=name)
    _delete_later(directory)

    return directory


def make_simple_developer_package():
    """:class:`rez.developer_package.DeveloperPackage`: A simple Rez source package."""
    directory = make_directory("_make_simple_developer_package_source_package")

    with open(os.path.join(directory, "package.py"), "w") as handler:
        handler.write(
            textwrap.dedent(
                """\
                name = "some_package"

                version = "1.0.0"

                requires = ["python"]

                build_command = "python {root}/rezbuild.py"

                def commands():
                    import os

                    env.PYTHONPATH.append(os.path.join(root, "python"))
                """
            )
        )

    with open(os.path.join(directory, "rezbuild.py"), "w") as handler:
        handler.write(
            textwrap.dedent(
                """\
                #!/usr/bin/env python
                # -*- coding: utf-8 -*-

                import os
                import shutil


                def build(source, destination, items):
                    shutil.rmtree(destination)
                    os.makedirs(destination)

                    for item in items:
                        source_path = os.path.join(source, item)
                        destination_path = os.path.join(destination, item)

                        if os.path.isdir(source_path):
                            shutil.copytree(source_path, destination_path)
                        elif os.path.isfile(source_path):
                            shutil.copy2(source_path, destination_path)


                if __name__ == "__main__":
                    build(
                        os.environ["REZ_BUILD_SOURCE_PATH"],
                        os.environ["REZ_BUILD_INSTALL_PATH"],
                        {"python"},
                    )
                """
            )
        )

    python_directory = os.path.join(directory, "python")
    os.makedirs(python_directory)

    with open(os.path.join(python_directory, "file.py"), "w") as handler:
        handler.write(
            textwrap.dedent(
                '''\
                def some_function():
                    """Do a function."""
                '''
            )
        )

    return finder.get_nearest_rez_package(directory)
