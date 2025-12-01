"""Comprehensive tests for SVN client to improve coverage."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vc_commit_helper.vcs.svn_client import SVNClient, SVNError, FileChange


class TestSVNClientComprehensive(unittest.TestCase):
    """Comprehensive tests for SVNClient."""

    def test_find_repo_root_at_filesystem_root(self):
        """Test find_repo_root when reaching filesystem root."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            # Simulate reaching filesystem root
            mock_path = MagicMock()
            mock_path.parent = mock_path  # Parent equals self at root
            mock_path.__truediv__.return_value.exists.return_value = False
            mock_resolve.return_value = mock_path
            
            result = SVNClient.find_repo_root(Path("/nonexistent"))
            self.assertIsNone(result)

    @patch("subprocess.run")
    def test_get_changes_with_added_files(self, mock_run):
        """Test get_changes with added files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "A       new_file.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "A")

    @patch("subprocess.run")
    def test_get_changes_with_deleted_files(self, mock_run):
        """Test get_changes with deleted files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "D       deleted.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "D")

    @patch("subprocess.run")
    def test_get_changes_with_replaced_files(self, mock_run):
        """Test get_changes with replaced files."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "R       replaced.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status, "R")

    @patch("subprocess.run")
    def test_stage_files_with_added_status(self, mock_run):
        """Test staging files with 'A' status."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        client.stage_files(["new.py"], statuses={"new.py": "A"})
        
        # Should call svn add
        calls = mock_run.call_args_list
        self.assertTrue(any("add" in str(call) for call in calls))

    @patch("subprocess.run")
    def test_stage_files_with_deleted_status(self, mock_run):
        """Test staging files with 'D' status."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        client.stage_files(["deleted.py"], statuses={"deleted.py": "D"})
        
        # Should call svn delete
        calls = mock_run.call_args_list
        self.assertTrue(any("delete" in str(call) for call in calls))

    @patch("subprocess.run")
    def test_run_with_failure(self, mock_run):
        """Test _run when command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "svn: E155007: not a working copy"
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        
        with self.assertRaises(SVNError) as ctx:
            client._run(["status"], check=True)
        self.assertIn("not a working copy", str(ctx.exception))

    @patch("subprocess.run")
    def test_run_without_check(self, mock_run):
        """Test _run with check=False doesn't raise on failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error"
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        result = client._run(["status"], check=False)
        
        self.assertEqual(result.returncode, 1)