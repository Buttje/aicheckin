"""Tests for Git branch operations."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vc_commit_helper.vcs.git_client import GitClient, GitError


class TestGitBranchOperations(unittest.TestCase):
    """Tests for Git branch operations."""

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_get_current_branch(self, mock_run):
        """Test getting current branch name."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        branch = client.get_current_branch()
        
        self.assertEqual(branch, "main")
        mock_run.assert_called_once()

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_get_current_branch_error(self, mock_run):
        """Test error when getting current branch."""
        mock_result = Mock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        
        with self.assertRaises(GitError):
            client.get_current_branch()

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_branch_exists_true(self, mock_run):
        """Test checking if branch exists (true case)."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "  feature-branch\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        exists = client.branch_exists("feature-branch")
        
        self.assertTrue(exists)

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_branch_exists_false(self, mock_run):
        """Test checking if branch exists (false case)."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        exists = client.branch_exists("nonexistent-branch")
        
        self.assertFalse(exists)

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_create_branch(self, mock_run):
        """Test creating a new branch."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Switched to a new branch 'feature-branch'\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        client.create_branch("feature-branch")
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("checkout", args)
        self.assertIn("-b", args)
        self.assertIn("feature-branch", args)

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_create_branch_error(self, mock_run):
        """Test error when creating branch."""
        mock_result = Mock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_result.stderr = "fatal: A branch named 'feature-branch' already exists."
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        
        with self.assertRaises(GitError):
            client.create_branch("feature-branch")

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_push_with_set_upstream(self, mock_run):
        """Test pushing with set-upstream flag."""
        # Mock two calls: get_current_branch and push
        mock_results = [
            Mock(returncode=0, stdout="feature-branch\n", stderr=""),  # get_current_branch
            Mock(returncode=0, stdout="", stderr=""),  # push with --set-upstream
        ]
        mock_run.side_effect = mock_results
        
        client = GitClient(Path("/fake/repo"))
        client.push(set_upstream=True)
        
        self.assertEqual(mock_run.call_count, 2)
        # Check that the push command includes --set-upstream
        push_args = mock_run.call_args_list[1][0][0]
        self.assertIn("--set-upstream", push_args)
        self.assertIn("origin", push_args)
        self.assertIn("feature-branch", push_args)

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_push_without_set_upstream(self, mock_run):
        """Test pushing without set-upstream flag."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        client.push(set_upstream=False)
        
        # Should be called exactly once
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertNotIn("--set-upstream", args)
        self.assertEqual(args, ["git", "push"])


if __name__ == "__main__":
    unittest.main()
    unittest.main()