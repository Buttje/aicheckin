"""Tests for SVN branch operations."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vc_commit_helper.vcs.svn_client import SVNClient, SVNError


class TestSVNBranchOperations(unittest.TestCase):
    """Tests for SVN branch operations."""

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_current_branch_trunk(self, mock_run):
        """Test getting current branch when on trunk."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "https://svn.example.com/repo/trunk\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        branch = client.get_current_branch()
        
        self.assertEqual(branch, "trunk")

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_current_branch_feature(self, mock_run):
        """Test getting current branch when on a feature branch."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "https://svn.example.com/repo/branches/feature-x\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        branch = client.get_current_branch()
        
        self.assertEqual(branch, "feature-x")

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_current_branch_tag(self, mock_run):
        """Test getting current branch when on a tag."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "https://svn.example.com/repo/tags/v1.0\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        branch = client.get_current_branch()
        
        self.assertEqual(branch, "v1.0")

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_current_branch_other(self, mock_run):
        """Test getting current branch for non-standard layout."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "https://svn.example.com/repo/custom/path\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        branch = client.get_current_branch()
        
        self.assertEqual(branch, "path")

    def test_branch_exists_always_false(self):
        """Test that branch_exists always returns False for SVN."""
        client = SVNClient(Path("/fake/repo"))
        exists = client.branch_exists("any-branch")
        
        self.assertFalse(exists)

    def test_create_branch_not_supported(self):
        """Test that create_branch raises error for SVN."""
        client = SVNClient(Path("/fake/repo"))
        with self.assertRaises(SVNError):
            client.create_branch("new-branch")


if __name__ == "__main__":
    unittest.main()