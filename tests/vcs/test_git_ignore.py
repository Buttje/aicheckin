"""Tests for Git .gitignore support."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from vc_commit_helper.vcs.git_client import GitClient, FileChange


class TestGitIgnore(unittest.TestCase):
    """Tests for .gitignore handling in GitClient."""

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_get_changes_excludes_untracked_files(self, mock_run):
        """Test that untracked files (??) are excluded."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "M  tracked.py\n?? untracked.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        changes = client.get_changes()
        
        # Should only include tracked modified file
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].path, "tracked.py")
        self.assertEqual(changes[0].status, "M")

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_get_changes_includes_staged_files(self, mock_run):
        """Test that staged files are included."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "A  new_file.py\nM  modified.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        changes = client.get_changes()
        
        # Should include both files
        self.assertEqual(len(changes), 2)
        paths = {c.path for c in changes}
        self.assertEqual(paths, {"new_file.py", "modified.py"})

    @patch("vc_commit_helper.vcs.git_client.subprocess.run")
    def test_get_changes_respects_gitignore(self, mock_run):
        """Test that Git automatically respects .gitignore patterns."""
        # Git status --porcelain automatically excludes .gitignore patterns
        mock_result = Mock()
        mock_result.returncode = 0
        # Only tracked changes are shown, ignored files don't appear
        mock_result.stdout = "M  src/main.py\nA  src/new.py\n"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        client = GitClient(Path("/fake/repo"))
        changes = client.get_changes()
        
        # Should include both tracked files
        self.assertEqual(len(changes), 2)
        paths = {c.path for c in changes}
        self.assertEqual(paths, {"src/main.py", "src/new.py"})


if __name__ == "__main__":
    unittest.main()
