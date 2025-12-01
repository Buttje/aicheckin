"""Comprehensive tests for diff extractor."""

import unittest
from unittest.mock import Mock

from vc_commit_helper.diff.diff_extractor import extract_diffs


class TestDiffExtractorComprehensive(unittest.TestCase):
    """Comprehensive tests for diff extraction."""

    def test_extract_diffs_with_exception(self):
        """Test that exceptions during diff extraction result in empty diff."""
        mock_client = Mock()
        mock_client.get_diff.side_effect = Exception("Diff failed")
        
        change1 = Mock()
        change1.path = "file1.py"
        
        changes = [change1]
        
        result = extract_diffs(mock_client, changes)
        
        self.assertEqual(result, {"file1.py": ""})
        mock_client.get_diff.assert_called_once_with("file1.py")

    def test_extract_diffs_mixed_success_and_failure(self):
        """Test extraction with some files succeeding and others failing."""
        mock_client = Mock()
        
        def get_diff_side_effect(path):
            if path == "success.py":
                return "diff content"
            else:
                raise Exception("Failed")
        
        mock_client.get_diff.side_effect = get_diff_side_effect
        
        change1 = Mock()
        change1.path = "success.py"
        change2 = Mock()
        change2.path = "failure.py"
        
        changes = [change1, change2]
        
        result = extract_diffs(mock_client, changes)
        
        self.assertEqual(result, {
            "success.py": "diff content",
            "failure.py": ""
        })

    def test_extract_diffs_empty_changes(self):
        """Test extraction with no changes."""
        mock_client = Mock()
        changes = []
        
        result = extract_diffs(mock_client, changes)
        
        self.assertEqual(result, {})
        mock_client.get_diff.assert_not_called()