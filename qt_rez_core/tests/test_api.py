"""Make sure :mod:`qt_rez_core.api` works."""

import atexit
import functools
import io
import os
import shutil
import tempfile
import unittest

from six.moves import mock

from qt_rez_core import api
from qt_rez_core._core import menu_magic


class GetCurrentMenu(unittest.TestCase):
    """Make sure :func:`qt_rez_core.api.get_current_help_menu` works."""

    def test_action_command(self):
        """Simulate an action running some command."""
        package_path = os.path.join(
            _make_temporary_directory("_test_action_command"),
            "package.py",
        )
        package = mock.MagicMock()
        package.help = "do something.sh"
        package.filepath = package_path

        menu = _test(package)

        with mock.patch("qt_rez_core._core.menu_magic._run_command") as patch:
            menu.actions()[0].triggered.emit()

        self.assertEqual(1, patch.call_count)

    def test_action_url(self):
        """Simulate an action opening some URL in a browser."""
        package = mock.MagicMock()
        package.help = "https://www.aol.com"

        menu = _test(package)

        with mock.patch("qt_rez_core._core.menu_magic._open_as_url") as patch:
            menu.actions()[0].triggered.emit()

        self.assertEqual(1, patch.call_count)

    def test_action_path_absolute(self):
        """Simulate an action opening an absolute file path."""
        package_path = os.path.join(
            _make_temporary_directory("_test_action_path_absolute"),
            "package.py",
        )
        path = _make_temporary_file("_test_find_from_str.py")
        package = mock.MagicMock()
        package.help = path
        package.filepath = package_path

        menu = _test(package)

        with mock.patch("qt_rez_core._core.menu_magic._open_generic") as patch:
            menu.actions()[0].triggered.emit()

        self.assertEqual(1, patch.call_count)

    def test_action_path_relative(self):
        """Simulate an action opening a file path which is relative to the package."""
        directory = _make_temporary_directory("_test_action_command")
        os.path.join(directory, "package.py")
        name = "something.py"
        package = mock.MagicMock()
        package.help = name
        package.filepath = name

        with io.open(os.path.join(directory, name), "a", encoding="utf-8"):
            pass

        menu = _test(package)

        with mock.patch(
            "qt_rez_core._core.menu_magic._open_generic",
        ) as patch, mock.patch(
            "rez_utilities.finder.get_package_root"
        ) as get_package_root:
            get_package_root.return_value = directory
            menu.actions()[0].triggered.emit()

        self.assertEqual(1, patch.call_count)

    def test_current_package(self):
        """Get this package's `help`_ attribute."""
        menu = api.get_current_help_menu()

        self.assertEqual(1, len(menu.actions()))

    def test_empty(self):
        """Fail if the Rez package has no `help`_ attribute."""
        package = mock.MagicMock()
        package.help = None

        with self.assertRaises(RuntimeError):
            _test(package)

    def test_find_from_caller(self):
        """Find a help option, using a callable function."""

        def _is_foo(entry):
            label, _ = entry

            return label == "FooBar"

        label = "FooBar"
        package = mock.MagicMock()
        package.help = [[label, "foo"], ["Foo Bar", "bar"]]

        menu = _test(package, matches=_is_foo)

        self.assertEqual(1, len(menu.actions()))
        self.assertEqual(label, menu.actions()[0].text())

    def test_find_from_str(self):
        """Find a help option, using a :obj:`str`."""
        path = _make_temporary_file("_test_find_from_str.py")
        package = mock.MagicMock()
        package.help = path

        menu = _test(package, matches="elp")

        expected_default_text = "Help"
        self.assertEqual(1, len(menu.actions()))
        self.assertEqual(expected_default_text, menu.actions()[0].text())

    def test_not_found(self):
        """Fail early if Rez package could be found."""
        with self.assertRaises(ValueError):
            api.get_current_help_menu(directory="/does/not/exist")

        directory = _make_temporary_directory("_test_not_found")

        with self.assertRaises(ValueError):
            api.get_current_help_menu(directory=directory)

    def test_help_str(self):
        """Find the help command, even if `help`_ is defined as a string."""
        path = _make_temporary_file("_test_find_from_str.py")
        package = mock.MagicMock()
        package.help = path

        menu = _test(package)

        expected_default_text = "Help"
        self.assertEqual(1, len(menu.actions()))
        self.assertEqual(expected_default_text, menu.actions()[0].text())


def _make_temporary_directory(suffix):
    """Make a folder on-disk and delete it later.

    Args:
        suffix (str): The ending + extension of the folder to create.

    Returns:
        str: The absolute path to a created folder.

    """
    directory = tempfile.mkdtemp(suffix=suffix)
    atexit.register(functools.partial(shutil.rmtree, directory))

    return directory


def _make_temporary_file(suffix):
    """Make a file on-disk and delete it later.

    Args:
        suffix (str): The ending + extension of the file to create.

    Returns:
        str: The absolute path to a created file.

    """
    _, path = tempfile.mkstemp(suffix=suffix)
    atexit.register(functools.partial(os.remove, path))

    return path


def _test(
    package,
    matches=menu_magic._get_anything,  # pylint: disable=protected-access
):
    """Get a Qt menu containing all `help`_ entries for the Rez ``package``.

    Args:
        package (rez.packages.Package):
            An **installed** Rez package to query `help`_ entries from.
        matches (callable[tuple[str, str]] or str, optional):
            Any entry which returns ``True`` from the given function will be
            returned as actions in the menu. If a string is given, it's
            retreated as a regular Python ``in`` partial match. If no
            ``matches`` is given, every `help`_ entry is returned.

    Returns:
        Qt.QtWidgets.QMenu: The generated menu.

    """
    return menu_magic._get_menu(  # pylint: disable=protected-access
        package,
        matches=matches,
    )
