"""Edge case tests for SVN client."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vc_commit_helper.vcs.svn_client import SVNClient, SVNError


class TestSVNClientEdgeCases(unittest.TestCase):
    """Edge case tests for SVNClient."""

    @patch("subprocess.run")
    def test_get_changes_with_empty_lines(self, mock_run):
        """Test get_changes with empty lines in output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n\nM       file.py\n\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        changes = client.get_changes()
        
        self.assertEqual(len(changes), 1)

    @patch("subprocess.run")
    def test_run_with_stderr_only(self, mock_run):
        """Test _run when only stderr contains error message."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "svn: error"
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        
        with self.assertRaises(SVNError) as ctx:
            client._run(["status"], check=True)
        self.assertIn("svn: error", str(ctx.exception))

    @patch("subprocess.run")
    def test_run_with_stdout_fallback(self, mock_run):
        """Test _run when stderr is empty but stdout has error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "error message"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/repo"))
        
        with self.assertRaises(SVNError) as ctx:
            client._run(["status"], check=True)
        self.assertIn("error message", str(ctx.exception))