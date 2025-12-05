"""
Tests for dynamic version generation.
"""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vc_commit_helper._version import (
    generate_version,
    get_git_commit_sha,
    get_minor_version_from_tags,
)


class TestVersionGeneration(unittest.TestCase):
    """Test dynamic version generation functionality."""

    def test_get_git_commit_sha_returns_sha(self):
        """Test that get_git_commit_sha returns a valid SHA."""
        sha = get_git_commit_sha()
        # Should return either a valid SHA (7 chars) or 'unknown'
        self.assertTrue(len(sha) == 7 or sha == "unknown")

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_git_commit_sha_with_valid_repo(self, mock_run):
        """Test get_git_commit_sha with a mocked valid repository."""
        mock_result = MagicMock()
        mock_result.stdout = "abc1234\n"
        mock_run.return_value = mock_result

        sha = get_git_commit_sha()
        self.assertEqual(sha, "abc1234")

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_git_commit_sha_returns_unknown_on_error(self, mock_run):
        """Test that get_git_commit_sha returns 'unknown' on error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        sha = get_git_commit_sha()
        self.assertEqual(sha, "unknown")

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_minor_version_no_tags(self, mock_run):
        """Test that get_minor_version_from_tags returns 0 when no tags exist."""
        mock_result = MagicMock()
        mock_result.stdout = "\n"
        mock_run.return_value = mock_result

        minor = get_minor_version_from_tags()
        self.assertEqual(minor, 0)

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_minor_version_single_tag(self, mock_run):
        """Test get_minor_version_from_tags with a single tag."""
        mock_result = MagicMock()
        mock_result.stdout = "v0.1\n"
        mock_run.return_value = mock_result

        minor = get_minor_version_from_tags()
        self.assertEqual(minor, 1)

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_minor_version_multiple_tags(self, mock_run):
        """Test get_minor_version_from_tags with multiple tags."""
        mock_result = MagicMock()
        mock_result.stdout = "v0.1\nv0.5\nv0.3\n"
        mock_run.return_value = mock_result

        minor = get_minor_version_from_tags()
        self.assertEqual(minor, 5)

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_minor_version_invalid_tags_ignored(self, mock_run):
        """Test that invalid tags are ignored."""
        mock_result = MagicMock()
        mock_result.stdout = "v0.1\ninvalid\nv0.2\nv1.0\n"
        mock_run.return_value = mock_result

        minor = get_minor_version_from_tags()
        # Should return 2 (from v0.2), ignoring v1.0 which has different major version
        self.assertEqual(minor, 2)

    @patch("vc_commit_helper._version.subprocess.run")
    def test_get_minor_version_returns_zero_on_error(self, mock_run):
        """Test that get_minor_version_from_tags returns 0 on error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        minor = get_minor_version_from_tags()
        self.assertEqual(minor, 0)

    @patch("vc_commit_helper._version.get_git_commit_sha")
    @patch("vc_commit_helper._version.get_minor_version_from_tags")
    def test_generate_version_format(self, mock_minor, mock_sha):
        """Test that generate_version creates correct format."""
        mock_minor.return_value = 3
        mock_sha.return_value = "abc1234"

        version = generate_version("0")
        self.assertEqual(version, "0.3.dev0+gabc1234")

    @patch("vc_commit_helper._version.get_git_commit_sha")
    @patch("vc_commit_helper._version.get_minor_version_from_tags")
    def test_generate_version_with_no_tags(self, mock_minor, mock_sha):
        """Test generate_version when no tags exist."""
        mock_minor.return_value = 0
        mock_sha.return_value = "xyz9876"

        version = generate_version("0")
        self.assertEqual(version, "0.0.dev0+gxyz9876")

    @patch("vc_commit_helper._version.get_git_commit_sha")
    @patch("vc_commit_helper._version.get_minor_version_from_tags")
    def test_generate_version_with_different_major(self, mock_minor, mock_sha):
        """Test generate_version with a different major version."""
        mock_minor.return_value = 2
        mock_sha.return_value = "def5678"

        version = generate_version("1")
        self.assertEqual(version, "1.2.dev0+gdef5678")

    @patch("vc_commit_helper._version.get_git_commit_sha")
    @patch("vc_commit_helper._version.get_minor_version_from_tags")
    def test_generate_version_handles_unknown_sha(self, mock_minor, mock_sha):
        """Test generate_version when SHA is unknown."""
        mock_minor.return_value = 1
        mock_sha.return_value = "unknown"

        version = generate_version("0")
        self.assertEqual(version, "0.1.dev0")


class TestVersionImport(unittest.TestCase):
    """Test that version can be imported correctly."""

    def test_version_import(self):
        """Test that __version__ can be imported."""
        from vc_commit_helper import __version__

        # Version should be in PEP 440 format: major.minor.devN+gcommit_sha
        # or major.minor.devN (without commit info)
        self.assertIsInstance(__version__, str)
        parts = __version__.split(".")
        self.assertGreaterEqual(len(parts), 3)  # At least major.minor.devN
        self.assertTrue(parts[0].isdigit())  # major
        self.assertTrue(parts[1].isdigit())  # minor
        # Third part should start with 'dev'
        self.assertTrue(parts[2].startswith("dev"))

    def test_base_version_import(self):
        """Test that __base_version__ can be imported."""
        from vc_commit_helper import __base_version__

        self.assertIsInstance(__base_version__, str)
        self.assertEqual(__base_version__, "0")


if __name__ == "__main__":
    unittest.main()
