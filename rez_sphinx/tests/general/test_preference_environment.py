"""Make sure setting environment variables from the terminal works."""

import os
import unittest

from python_compatibility import wrapping
from rez_sphinx.preferences import preference

from ..common import run_test


class Environment(unittest.TestCase):
    """Set preferences using environment variables."""

    def test_bool(self):
        """Set a bool preference."""
        run_test.clear_caches()
        self.assertTrue(preference.allow_apidoc_templates())

        run_test.clear_caches()

        with wrapping.keep_os_environment():
            os.environ["REZ_SPHINX_SPHINX_APIDOC_ALLOW_APIDOC_TEMPLATES"] = "0"
            self.assertFalse(preference.allow_apidoc_templates())

    def test_dict(self):
        """Set a dict preference."""
        raise ValueError()

    def test_list(self):
        """Set a list preference."""
        run_test.clear_caches()
        self.assertEqual(
            ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode'],
            preference.get_sphinx_extensions(),
        )

        run_test.clear_caches()

        with wrapping.keep_os_environment():
            os.environ["REZ_SPHINX_SPHINX_CONF_OVERRIDES_EXTENSIONS"] = "['foo', 'bar', 'thing']"
            self.assertEqual(
                ["foo", "bar", "thing"],
                preference.get_sphinx_extensions(),
            )

    def test_str(self):
        """Set a str preference."""
        run_test.clear_caches()
        self.assertEqual(
            "API Documentation <api/modules>",
            preference.get_master_api_documentation_line(),
        )

        expected = "blah"

        run_test.clear_caches()

        with wrapping.keep_os_environment():
            os.environ["REZ_SPHINX_API_TOCTREE_LINE"] = expected
            self.assertFalse(preference.allow_apidoc_templates())

    def test_use(self):
        """Set a preference which has dynamic evaluation configured."""
        raise ValueError()
        # 'auto_help': {   'filter_by': Use(<function filter_generated at 0x7f084a6a7048>),
        #                  'sort_order': Use(<function alphabetical at 0x7f084a6a1f28>)},
