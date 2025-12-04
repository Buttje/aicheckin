"""Tests for commit message extraction from LLM responses with thinking process."""

import unittest
from unittest.mock import Mock

from vc_commit_helper.llm.commit_message_generator import CommitMessageGenerator
from vc_commit_helper.llm.ollama_client import LLMError


class TestCommitMessageExtraction(unittest.TestCase):
    """Tests for extracting commit messages from LLM responses containing thinking process."""

    def test_extract_message_with_preamble(self):
        """Test extraction when LLM includes thinking process before the message."""
        mock_client = Mock()
        # LLM response with thinking process
        mock_client.generate.return_value = """Let me analyze the changes. Looking at the diff, I can see that a new feature was added.
Here's the commit message:

[feat]: add user authentication system

This change implements a complete user authentication system with login,
logout, and session management capabilities. It provides secure access
control to the application.

- src/auth/login.py
- src/auth/session.py"""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "src/auth/login.py": "+def login(): pass",
            "src/auth/session.py": "+def session(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].type, "feat")
        # Message should start with [feat]: without preamble
        self.assertTrue(groups[0].message.startswith("[feat]:"))
        # Should not contain thinking process
        self.assertNotIn("Let me analyze", groups[0].message)
        self.assertNotIn("Looking at", groups[0].message)
        self.assertNotIn("Here's the", groups[0].message)

    def test_extract_message_with_meta_commentary(self):
        """Test extraction when LLM includes meta-commentary."""
        mock_client = Mock()
        mock_client.generate.return_value = """Based on the changes, I will create a commit message.
The files show test additions, so this is a test commit.

[test]: add unit tests for database operations

Added comprehensive unit tests for database CRUD operations to ensure
data integrity and proper error handling. These tests cover edge cases
and validate the database layer functionality.

- tests/test_db.py"""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "tests/test_db.py": "+def test_crud(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        message = groups[0].message
        # Should not contain meta-commentary
        self.assertNotIn("Based on", message)
        self.assertNotIn("I will", message)
        # Should start with commit message
        self.assertTrue(message.startswith("[test]:"))

    def test_extract_message_clean_response(self):
        """Test that clean responses without thinking process work correctly."""
        mock_client = Mock()
        mock_client.generate.return_value = """[fix]: resolve memory leak in cache manager

Fixed a memory leak in the cache manager that was causing gradual
memory consumption increase over time. The cache now properly releases
unused entries and maintains a stable memory footprint.

- src/cache/manager.py"""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            # Include "fix" keyword in diff to get fix classification
            "src/cache/manager.py": "-old code\n+new code\n+# fix memory leak"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        message = groups[0].message
        self.assertTrue(message.startswith("[fix]:"))
        self.assertIn("memory leak", message.lower())

    def test_extract_message_with_multiple_paragraphs(self):
        """Test extraction with thinking process in multiple paragraphs."""
        mock_client = Mock()
        mock_client.generate.return_value = """First, let me examine the changes.

The changes indicate documentation updates.

I'll now write the commit message:

[docs]: update API documentation for v2.0

Updated the API documentation to reflect new endpoints and deprecations
in version 2.0. This includes detailed examples and migration guides
for developers upgrading from v1.x.

- docs/api.md
- docs/migration.md"""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "docs/api.md": "+# API v2",
            "docs/migration.md": "+# Migration guide"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        message = groups[0].message
        # Should start with commit message
        self.assertTrue(message.startswith("[docs]:"))
        # Should not contain thinking process
        self.assertNotIn("First,", message)
        self.assertNotIn("let me examine", message)
        self.assertNotIn("I'll now", message)

    def test_extract_message_without_type_prefix(self):
        """Test extraction when LLM forgets the type prefix."""
        mock_client = Mock()
        # LLM response without [type]: prefix
        mock_client.generate.return_value = """Looking at the refactoring changes:

improve code organization in utils module

Refactored the utils module to improve code organization and
maintainability. Functions are now grouped by functionality with
clearer naming conventions.

- src/utils/helpers.py
- src/utils/validators.py"""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            # Include "refactor" keyword in diff to get refactor classification
            "src/utils/helpers.py": "+def helper(): pass\n# refactor for better organization",
            "src/utils/validators.py": "+def validate(): pass\n# refactor code"
        }
        
        groups = generator.generate_groups(diffs)
        
        self.assertEqual(len(groups), 1)
        message = groups[0].message
        # Should be normalized to include [refactor]: prefix
        self.assertTrue(message.startswith("[refactor]:"))
        self.assertIn("code organization", message.lower())
    def test_extract_empty_response_uses_fallback(self):
        """Test that empty response triggers fallback."""
        mock_client = Mock()
        mock_client.generate.return_value = ""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "src/feature.py": "+def feature(): pass"
        }
        
        groups = generator.generate_groups(diffs)
        
        # Should use fallback message
        self.assertEqual(len(groups), 1)
        self.assertIn("[feat]:", groups[0].message)
        self.assertIn("1 file", groups[0].message)

    def test_extract_message_with_only_thinking(self):
        """Test extraction when response is mostly thinking process."""
        mock_client = Mock()
        mock_client.generate.return_value = """Let me analyze these changes carefully.
I see that this is a performance optimization.
I'll create an appropriate commit message now."""
        
        generator = CommitMessageGenerator(mock_client)
        diffs = {
            "src/optimizer.py": "+optimizations"
        }
        
        groups = generator.generate_groups(diffs)
        
        # Since the response has no valid commit message, extraction will
        # return the text, but it won't match any commit type pattern.
        # The file will be classified based on its path/content.
        # In this case, it gets classified as "other" since it's not a special file type.
        self.assertEqual(len(groups), 1)
        # The message should be normalized with the correct type prefix
        self.assertTrue(groups[0].message.startswith("["))
        self.assertIn("]:", groups[0].message)


if __name__ == "__main__":
    unittest.main()
