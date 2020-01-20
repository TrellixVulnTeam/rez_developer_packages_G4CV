#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test all of the checkers in "dangers.py"."""

import os
import tempfile
import textwrap

from rez import packages_
from rez.config import config
from rez_lint import cli
from rez_utilities import creator, inspection

from .. import packaging


class ImproperRequirements(packaging.BasePackaging):
    """Add tests for Rez-requirement related checkers."""

    def test_no_impropers_001(self):
        """Check that a package with no "improper" requirements don't trigger any errors."""
        package = self._make_installed_package(
            "my_package",
            textwrap.dedent(
                """\
                name = "my_package"
                version = "1.0.0"
                build_command = "echo 'foo'"
                """
            ),
        )
        directory = inspection.get_package_root(package)

        results = cli.lint(directory)
        has_issue = any(
            description
            for description in results
            if description.get_summary()[0]
            == "Improper package requirements were found"
        )

        self.assertFalse(has_issue)

    def test_no_impropers_002(self):
        """Adding some dependency should not trigger the "improper" check."""
        dependency_package = self._make_installed_package(
            "some_dependency_that_is_okay",
            textwrap.dedent(
                """\
                name = "some_dependency_that_is_okay"
                version = "1.0.0"
                build_command = "echo 'foo'"
                """
            ),
        )
        dependency_path = inspection.get_packages_path_from_package(dependency_package)

        original = list(config.packages_path)  # pylint: disable=no-member
        config.packages_path[:] = [
            dependency_path
        ] + original  # pylint: disable=no-member

        try:
            installed_package = self._make_installed_package(
                "my_package",
                textwrap.dedent(
                    """\
                    name = "my_package"
                    version = "1.0.0"

                    requires = [
                        "some_dependency_that_is_okay",
                    ]

                    build_command = "echo 'foo'"
                    """
                ),
            )
        except Exception:
            raise
        finally:
            config.packages_path[:] = original  # pylint: disable=no-member

        directory = inspection.get_package_root(installed_package)
        original = list(config.packages_path)  # pylint: disable=no-member
        config.packages_path[:] = [
            directory,
            dependency_path,
        ] + original  # pylint: disable=no-member

        try:
            results = cli.lint(directory)
        except Exception:
            raise
        finally:
            config.packages_path[:] = original  # pylint: disable=no-member

        has_issue = any(
            description
            for description in results
            if description.get_summary()[0]
            == "Improper package requirements were found"
        )

        self.assertFalse(has_issue)

    # TODO : Do these
    # def test_one_improper(self):
    #     pass
    #
    # def test_multiple_impropers(self):
    #     pass
    #
    # def test_mixed_impropers(self):
    #     pass


class MissingRequirements(packaging.BasePackaging):
    """Check that the :class:`rez_lint.plugins.checkers.dangers.MissingRequirements` class works."""

    def _make_nested_dependencies(self):
        """list[str]: A helper function to make some dependencies to test with."""
        code = textwrap.dedent(
            """\
            name = "another_dependency"
            version = "1.0.0"
            requires = []
            build_command = "python {root}/rezbuild.py {install}"

            def commands():
                import os

                env.PYTHONPATH.append(os.path.join("{root}", "python"))
            """
        )

        dependency1_directory = packaging.make_fake_source_package(
            "another_dependency", code
        )
        self.add_item(dependency1_directory)

        with open(os.path.join(dependency1_directory, "rezbuild.py"), "w") as handler:
            handler.write(_get_rezbuild_text())

        os.makedirs(os.path.join(dependency1_directory, "python"))

        with open(
            os.path.join(dependency1_directory, "python", "some_module.py"), "w"
        ) as handler:
            handler.write(
                textwrap.dedent(
                    """\
                    def get_foo():
                        return 8
                    """
                )
            )

        dependency1_build_path = tempfile.mkdtemp(suffix="_another_dependency")
        self.add_item(dependency1_build_path)

        creator.build(
            packages_.get_developer_package(dependency1_directory),
            dependency1_build_path,
        )

        code = textwrap.dedent(
            """\
            name = "direct_dependency"
            version = "1.0.0"
            requires = [
                "another_dependency-1",
            ]
            build_command = "python {root}/rezbuild.py {install}"

            def commands():
                import os

                env.PYTHONPATH.append(os.path.join("{root}", "python"))
            """
        )

        dependency2_directory = packaging.make_fake_source_package(
            "direct_dependency", code
        )
        self.add_item(dependency2_directory)
        os.makedirs(os.path.join(dependency2_directory, "python"))

        with open(os.path.join(dependency2_directory, "rezbuild.py"), "w") as handler:
            handler.write(_get_rezbuild_text())

        dependency2_build_path = tempfile.mkdtemp(suffix="_direct_dependency")
        self.add_item(dependency2_build_path)

        original = list(config.packages_path)
        config.packages_path = [dependency1_build_path] + config.packages_path

        try:
            creator.build(
                packages_.get_developer_package(dependency2_directory),
                dependency2_build_path,
            )
        finally:
            config.packages_path[:] = original

        return [dependency1_build_path, dependency2_build_path]

    def _create_test_environment(self, text, files=None):
        """Make a Rez source package, given some Rez definition text, for testing.

        Args:
            text (str):
                The text that will be used for a "package.py" file.
            files (iter[str], optional):
                File paths that will be used to create empty files in
                the source package. Default is empty.

        Returns:
            list[:class:`rez_lint.core.message_description.Description`]: Get the found issues.

        """
        if not files:
            files = set()

        directory = packaging.make_fake_source_package("some_package", text)
        self.add_item(directory)

        for path in files:
            full_path = os.path.join(directory, path)
            path_directory = os.path.dirname(full_path)

            if not os.path.isdir(path_directory):
                os.makedirs(path_directory)

            open(full_path, "a").close()

        return cli.lint(directory)

    def test_empty(self):
        """Don't error if there is not set of requirements listed."""
        code = textwrap.dedent(
            """\
            name = "some_package"
            version = "1.0.0"
            """
        )

        results = self._create_test_environment(code)

        issues = [
            description
            for description in results
            if description.get_summary()[0] == "Missing Package requirements"
        ]

        self.assertEqual([], issues)

    def test_none_001(self):
        """Don't error if there are requirements defined but the list is empty."""
        code = textwrap.dedent(
            """\
            name = "some_package"
            version = "1.0.0"
            requires = []
            """
        )

        results = self._create_test_environment(code)

        issues = [
            description
            for description in results
            if description.get_summary()[0] == "Missing Package requirements"
        ]

        self.assertEqual([], issues)

    def test_none_002(self):
        """Don't error if there are requirements defined but the list is empty and there's files."""
        code = textwrap.dedent(
            """\
            name = "some_package"
            version = "1.0.0"
            requires = []

            def commands():
                import os

                env.PYTHONPATH.append(os.path.join("{root}", "python"))
            """
        )

        results = self._create_test_environment(
            code, files={os.path.join("python", "some_module.py")}
        )

        issues = [
            description
            for description in results
            if description.get_summary()[0] == "Missing Package requirements"
        ]

        self.assertEqual([], issues)

    def test_one(self):
        """Error because there is a missing dependency.

        In this case, the Rez package includes "direct_dependency".
        But the import, "import some_module" actually comes from the
        dependency package of "direct_dependency". In other words,
        "some_package" should also depend on "another_dependency", but
        doesn't.

        """
        dependency_paths = self._make_nested_dependencies()

        code = textwrap.dedent(
            """\
            name = "some_package"
            version = "1.0.0"
            requires = [
                "direct_dependency",
            ]

            def commands():
                import os

                env.PYTHONPATH.append(os.path.join("{root}", "python"))
            """
        )

        root = os.path.join(
            tempfile.mkdtemp(suffix="_some_package_location"), "some_package"
        )
        os.makedirs(root)
        self.add_item(root)
        os.makedirs(os.path.join(root, "python"))

        with open(os.path.join(root, "package.py"), "w") as handler:
            handler.write(code)

        with open(
            os.path.join(root, "python", "a_module_with_dependency.py"), "w"
        ) as handler:
            handler.write("import some_module; print(some_module.get_foo())")

        original = list(config.packages_path)
        config.packages_path[:] = dependency_paths + config.packages_path

        try:
            results = cli.lint(root)
        finally:
            config.packages_path[:] = original

        issues = [
            description
            for description in results
            if description.get_summary()[0] == "Missing Package requirements"
        ]

        self.assertEqual(1, len(issues))
        self.assertEqual(
            "Full list \"['another_dependency']\".",
            issues[0].get_message(verbose=True)[-1].lstrip(),
        )

    def test_mixed(self):
        """Get the right missing dependencies even if a mix of dependencies are given."""
        dependency_paths = self._make_nested_dependencies()

        code = textwrap.dedent(
            """\
            name = "some_package"
            version = "1.0.0"
            requires = [
                "direct_dependency",
                "python",
            ]

            def commands():
                import os

                env.PYTHONPATH.append(os.path.join("{root}", "python"))
            """
        )

        root = os.path.join(
            tempfile.mkdtemp(suffix="_some_package_location"), "some_package"
        )
        os.makedirs(root)
        self.add_item(root)
        os.makedirs(os.path.join(root, "python"))

        with open(os.path.join(root, "package.py"), "w") as handler:
            handler.write(code)

        with open(
            os.path.join(root, "python", "a_module_with_dependency.py"), "w"
        ) as handler:
            handler.write("import some_module; print(some_module.get_foo())")

        original = list(config.packages_path)
        config.packages_path[:] = dependency_paths + config.packages_path

        try:
            results = cli.lint(root)
        finally:
            config.packages_path[:] = original

        issues = [
            description
            for description in results
            if description.get_summary()[0] == "Missing Package requirements"
        ]

        self.assertEqual(1, len(issues))
        self.assertEqual(
            "Full list \"['another_dependency']\".",
            issues[0].get_message(verbose=True)[-1].lstrip(),
        )


# TODO : Finish these
# class RequirementLowerBoundsMissing(unittest.TestCase):
#     def test_empty(self):
#         pass
#
#     def test_none(self):
#         pass
#
#     def test_one(self):
#         pass
#
#     def test_mixed(self):
#         pass
#
#
# class RequirementsNotSorted(unittest.TestCase):
#     def test_empty(self):
#         pass
#
#     def test_none(self):
#         pass
#
#     def test_one(self):
#         pass
#
#     def test_mixed(self):
#         pass
#
#
# class NotPythonDefinition(unittest.TestCase):
#     def test_yaml(self):
#         pass
#
#     def test_python(self):
#         pass
#
#
# class NoRezTest(unittest.TestCase):
#     def test_undefined(self):
#         pass
#
#     def test_empty(self):
#         pass
#
#     def test_exists(self):
#         pass
#
#
# class TooManyDependencies(unittest.TestCase):
#     def test_undefined(self):
#         pass
#
#     def test_empty(self):
#         pass
#
#     def test_under(self):
#         pass
#
#     def test_over(self):
#         pass
#
#
# class UrlNotReachable(unittest.TestCase):
#     def test_undefined(self):
#         pass
#
#     def test_empty(self):
#         pass
#
#     def test_reachable(self):
#         pass
#
#     def test_unreachable(self):
#         pass


def _get_rezbuild_text():
    return textwrap.dedent(
        """\
        #!/usr/bin/env python
        # -*- coding: utf-8 -*-

        # IMPORT STANDARD LIBRARIES
        import os
        import shutil
        import sys


        def build(source_path, install_path):
            for folder in {"python", }:
                source = os.path.join(source_path, folder)
                destination = os.path.join(install_path, folder)
                shutil.copytree(source, destination)

        if __name__ == "__main__":
            build(
                source_path=os.environ["REZ_BUILD_SOURCE_PATH"],
                install_path=os.environ["REZ_BUILD_INSTALL_PATH"],
            )
        """
    )
