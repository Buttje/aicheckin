"""Tests for SVN ignore support."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vc_commit_helper.vcs.svn_client import SVNClient, FileChange


class TestSVNIgnore(unittest.TestCase):
    """Tests for SVN ignore handling in SVNClient."""

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_changes_excludes_unversioned_files(self, mock_run):
        """Test that unversioned files (?) are excluded."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "M       tracked.py\n?       unversioned.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        changes = client.get_changes()
        
        # Should only include tracked modified file
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].path, "tracked.py")
        self.assertEqual(changes[0].status, "M")

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_changes_with_multiple_statuses(self, mock_run):
        """Test that various SVN statuses are handled correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "M       modified.py\nA       added.py\nD       deleted.py\nR       replaced.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        changes = client.get_changes()
        
        # Should include all versioned files
        self.assertEqual(len(changes), 4)
        statuses = {c.path: c.status for c in changes}
        self.assertEqual(statuses, {
            "modified.py": "M",
            "added.py": "A",
            "deleted.py": "D",
            "replaced.py": "R"
        })

    @patch("vc_commit_helper.vcs.svn_client.subprocess.run")
    def test_get_changes_mixed_versioned_unversioned(self, mock_run):
        """Test that only versioned files are included."""
        mock_result = Mock()
        mock_result.returncode = 0
        # Mix of versioned and unversioned files
        mock_result.stdout = "M       file.py\n?       test.pyc\nA       new.py\n?       temp.txt\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = SVNClient(Path("/fake/repo"))
        changes = client.get_changes()
        
        # Should only include versioned files (M and A status)
        self.assertEqual(len(changes), 2)
        paths = {c.path for c in changes}
        self.assertEqual(paths, {"file.py", "new.py"})


if __name__ == "__main__":
    unittest.main()