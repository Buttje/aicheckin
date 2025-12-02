"""Additional tests for commit message generator to improve coverage."""

import unittest
from unittest.mock import Mock

from vc_commit_helper.llm.commit_message_generator import CommitMessageGenerator
from vc_commit_helper.llm.ollama_client import LLMError


class TestCommitMessageGeneratorExtra(unittest.TestCase):
    """Extra tests for CommitMessageGenerator edge cases."""
    def test_generate_groups_with_empty_message(self):
        """Test handling when LLM returns empty message."""
        mock_client = Mock()
        mock_client.generate.return_value = ""
    
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "tests/test_example.py": "+def test_something(): pass"
        }
    
        groups = generator.generate_groups(diffs)
    
        # Should use fallback message with correct format
        self.assertEqual(len(groups), 1)
        self.assertIn("[test]:", groups[0].message)
        self.assertIn("Changes to 1 file", groups[0].message)
        self.assertIn("- tests/test_example.py", groups[0].message)
    def test_generate_groups_with_generic_exception(self):
        """Test handling when LLM raises generic exception."""
        mock_client = Mock()
        mock_client.generate.side_effect = ValueError("Unexpected error")
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "feature.py": "+def new_feature(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        # Should use fallback message with correct format
        self.assertEqual(len(groups), 1)
        self.assertIn("[feat]:", groups[0].message)
        self.assertIn("Changes to 1 file", groups[0].message)
        self.assertIn("- feature.py", groups[0].message)

    def test_normalize_message_without_brackets(self):
        """Test normalizing message that starts with type: instead of [type]:"""
        mock_client = Mock()
        mock_client.generate.return_value = "feat: add new feature\n\nDetailed description."
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "feature.py": "+def new_feature(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        # Should be normalized to [feat]:
        self.assertTrue(groups[0].message.startswith("[feat]:"))

    def test_normalize_message_with_brackets_no_colon(self):
        """Test normalizing message that starts with [type] instead of [type]:"""
        mock_client = Mock()
        mock_client.generate.return_value = "[feat] add new feature\n\nDetailed description."
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "feature.py": "+def new_feature(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        # Should be normalized to [feat]:
        self.assertTrue(groups[0].message.startswith("[feat]:"))

    def test_normalize_message_no_prefix(self):
        """Test normalizing message without any type prefix."""
        mock_client = Mock()
        mock_client.generate.return_value = "add new feature\n\nDetailed description."
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "feature.py": "+def new_feature(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        # Should be prepended with [feat]:
        self.assertTrue(groups[0].message.startswith("[feat]:"))

    def test_generate_groups_multiple_files(self):
        """Test generating groups with multiple files."""
        mock_client = Mock()
        mock_client.generate.return_value = "[fix]: fix multiple bugs\n\nFixed bugs in multiple files."
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "bug1.py": "-old bug\n+fixed",
            "bug2.py": "-another bug\n+fixed"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0].message.startswith("[fix]:"))
        self.assertEqual(len(groups[0].files), 2)