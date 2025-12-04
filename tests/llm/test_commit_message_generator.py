"""Tests for commit message generator."""

import unittest
from unittest.mock import Mock

from vc_commit_helper.llm.commit_message_generator import CommitMessageGenerator
from vc_commit_helper.llm.ollama_client import LLMError


class TestCommitMessageGenerator(unittest.TestCase):
    """Tests for CommitMessageGenerator."""

    def test_generate_groups_basic(self):
        """Test basic group generation."""
        mock_client = Mock()
        mock_client.generate.return_value = "[feat]: add new feature\n\nDetailed description."
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "feature.py": "+def new_feature(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].type, "feat")
        self.assertIn("[feat]:", groups[0].message)

    def test_generate_groups_with_llm_error(self):
        """Test fallback when LLM fails."""
        mock_client = Mock()
        mock_client.generate.side_effect = LLMError("Connection failed")
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "tests/test_example.py": "+def test_something(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        self.assertIn("[test]:", groups[0].message)
        self.assertIn("Changes to 1 file", groups[0].message)


if __name__ == "__main__":
    unittest.main()