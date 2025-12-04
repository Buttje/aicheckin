"""Tests for _get_install_directory edge cases."""

import unittest
from pathlib import Path

from vc_commit_helper.config.loader import _get_install_directory


class TestGetInstallDirectory(unittest.TestCase):
    """Tests for _get_install_directory function."""

    def test_get_install_directory_returns_path(self):
        """Test that _get_install_directory returns a Path object."""
        result = _get_install_directory()
        self.assertIsInstance(result, Path)
        self.assertTrue(result.exists())
        
    def test_get_install_directory_has_init_file(self):
        """Test that the install directory has __init__.py (covers line 64-65)."""
        result = _get_install_directory()
        # This tests the check at line 64-65
        init_file = result / "__init__.py"
        # The directory should either have config or __init__.py
        config_file = result / ".ollama_config.json"
        self.assertTrue(
            config_file.exists() or init_file.exists(),
            "Install directory should have either config or __init__.py"
        )


if __name__ == "__main__":
    unittest.main()
