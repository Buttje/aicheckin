"""Comprehensive tests for Git client to improve coverage."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vc_commit_helper.vcs.git_client import GitClient, GitError, FileChange


class TestGitClientComprehensive(unittest.TestCase):
    """Comprehensive tests for GitClient."""

    def test_find_repo_root_at_filesystem_root(self):
        """Test find_repo_root when reaching filesystem root."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            # Simulate reaching filesystem root
            mock_path = MagicMock()
            mock_path.parent = mock_path  # Parent equals self at root
            mock_path.__truediv__.return_value.exists.return_value = False
            mock_resolve.return_value = mock_path
            
            result = GitClient.find_repo_root(Path("/nonexistent"))
            self.assertIsNone(result)

    @patch("subprocess.run")
    def test_get_changes_with_renamed_files(self, mock_run):
        """Test get_changes with renamed files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "R  old.py -> new.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "R")

    @patch("subprocess.run")
    def test_get_changes_with_added_files(self, mock_run):
        """Test get_changes with added files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "A  new_file.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "A")

    @patch("subprocess.run")
    def test_get_changes_with_deleted_files(self, mock_run):
        """Test get_changes with deleted files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "D  deleted.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "D")

    @patch("subprocess.run")
    def test_stage_files_with_deleted_file(self, mock_run):
        """Test staging a deleted file."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/repo"))
        
        with patch("pathlib.Path.exists", return_value=False):
            client.stage_files(["deleted.py"])
        
        # Should call git rm
        calls = mock_run.call_args_list
        self.assertTrue(any("rm" in str(call) for call in calls))

    @patch("subprocess.run")
    def test_run_with_failure(self, mock_run):
        """Test _run when command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/repo"))
        
        with self.assertRaises(GitError) as ctx:
            client._run(["status"], check=True)
        self.assertIn("not a git repository", str(ctx.exception))

    @patch("subprocess.run")
    def test_run_without_check(self, mock_run):
        """Test _run with check=False doesn't raise on failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/repo"))
        result = client._run(["status"], check=False)
        
        self.assertEqual(result.returncode, 1)