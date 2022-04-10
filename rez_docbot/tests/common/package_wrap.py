import atexit
import functools
import io
import os
import shutil
import tempfile
import textwrap

from rez import developer_package


def make_package_configuration(configuration):
    directory = tempfile.mkdtemp(suffix="_make_package_config")
    atexit.register(functools.partial(shutil.rmtree, directory))

    template = textwrap.dedent(
        """\
        name = "foo"

        version = "1.0.0"

        rez_docbot_configuration = {configuration!r}
        """
    )

    with io.open(
        os.path.join(directory, "package.py"),
        "w",
        encoding="utf-8",
    ) as handler:
        handler.write(template.format(configuration=configuration))

    return developer_package.DeveloperPackage.from_path(directory)
