"""Tests for filtering thinking process from LLM responses."""

import unittest
from unittest.mock import Mock, patch

from vc_commit_helper.llm.ollama_client import OllamaClient


class TestThinkingFilter(unittest.TestCase):
    """Tests for filtering thinking process tags from LLM responses."""

    def test_filter_simple_thinking_tags(self):
        """Test that <think> tags are removed."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "<think>Let me analyze this code...</think>[feat]: Add new feature\n\nThis adds a new feature."
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        # Should not contain thinking tags or content
        self.assertNotIn("<think>", result)
        self.assertNotIn("</think>", result)
        self.assertNotIn("Let me analyze", result)
        # Should contain the actual commit message
        self.assertIn("[feat]: Add new feature", result)
        self.assertIn("This adds a new feature", result)

    def test_filter_thinking_tags(self):
        """Test that <thinking> tags are removed."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "<thinking>First, I need to understand what changed...\nThen I'll write the message.</thinking>\n\n[fix]: Fix bug in parser\n\nFixed an issue with the parser."
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        # Should not contain thinking tags or content
        self.assertNotIn("<thinking>", result)
        self.assertNotIn("</thinking>", result)
        self.assertNotIn("First, I need to understand", result)
        # Should contain the actual commit message
        self.assertIn("[fix]: Fix bug in parser", result)

    def test_filter_thought_tags(self):
        """Test that <thought> tags are removed."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "<thought>This looks like a documentation update</thought>[docs]: Update README\n\nUpdated the README file."
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        self.assertNotIn("<thought>", result)
        self.assertNotIn("</thought>", result)
        self.assertNotIn("This looks like a documentation", result)
        self.assertIn("[docs]: Update README", result)

    def test_filter_reasoning_tags(self):
        """Test that <reasoning> tags are removed."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "<reasoning>Based on the changes, this is a refactor</reasoning>[refactor]: Simplify code\n\nSimplified the code structure."
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        self.assertNotIn("<reasoning>", result)
        self.assertNotIn("</reasoning>", result)
        self.assertNotIn("Based on the changes", result)
        self.assertIn("[refactor]: Simplify code", result)

    def test_filter_multiple_thinking_blocks(self):
        """Test that multiple thinking blocks are removed."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "<think>First thought</think>[feat]: New feature<thinking>Second thought</thinking>\n\nDetails here.<thought>Third thought</thought>"
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        # Should not contain any thinking tags or content
        self.assertNotIn("<think>", result)
        self.assertNotIn("<thinking>", result)
        self.assertNotIn("<thought>", result)
        self.assertNotIn("First thought", result)
        self.assertNotIn("Second thought", result)
        self.assertNotIn("Third thought", result)
        # Should contain the actual commit message
        self.assertIn("[feat]: New feature", result)
        self.assertIn("Details here", result)

    def test_filter_multiline_thinking(self):
        """Test that multiline thinking blocks are removed."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": """<thinking>
Let me think about this step by step:
1. First, I see changes to the configuration
2. Then I see changes to the code
3. This looks like a feature addition
</thinking>

[feat]: Add configuration support

Added support for custom configuration files.

- config.py
- main.py"""
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        # Should not contain thinking tags or content
        self.assertNotIn("<thinking>", result)
        self.assertNotIn("</thinking>", result)
        self.assertNotIn("Let me think", result)
        self.assertNotIn("step by step", result)
        # Should contain the actual commit message
        self.assertIn("[feat]: Add configuration support", result)
        self.assertIn("Added support for custom", result)
        self.assertIn("- config.py", result)

    def test_no_thinking_tags(self):
        """Test that responses without thinking tags are unchanged."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        original_message = "[feat]: Add new feature\n\nThis adds a new feature to the system.\n\n- feature.py"
        mock_response.json.return_value = {
            "response": original_message
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        # Should be identical to the original (just stripped)
        self.assertEqual(result, original_message.strip())

    def test_filter_case_insensitive(self):
        """Test that filtering works regardless of tag case."""
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="test-model"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "<THINK>Uppercase tags</THINK>[feat]: Feature<Think>Mixed case</Think>"
        }
        
        with patch('requests.post', return_value=mock_response):
            result = client.generate("test prompt")
        
        # Should not contain thinking tags regardless of case
        self.assertNotIn("<THINK>", result)
        self.assertNotIn("Uppercase tags", result)
        self.assertNotIn("Mixed case", result)
        self.assertIn("[feat]: Feature", result)


if __name__ == "__main__":
    unittest.main()
