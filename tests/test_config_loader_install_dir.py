"""Tests for _get_config_directory edge cases."""

import unittest
from pathlib import Path

from vc_commit_helper.config.loader import _get_config_directory


class TestGetConfigDirectory(unittest.TestCase):
    """Tests for _get_config_directory function."""

    def test_get_config_directory_returns_path(self):
        """Test that _get_config_directory returns a Path object."""
        result = _get_config_directory()
        self.assertIsInstance(result, Path)
        # The directory should be ~/.ollama_server
        self.assertEqual(result, Path.home() / ".ollama_server")
        
    def test_get_config_directory_points_to_home(self):
        """Test that the config directory is in user's home directory."""
        result = _get_config_directory()
        # Verify that the path starts with user's home directory
        self.assertTrue(str(result).startswith(str(Path.home())))
        # Verify the directory name is .ollama_server
        self.assertEqual(result.name, ".ollama_server")


if __name__ == "__main__":
    unittest.main()
