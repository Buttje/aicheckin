"""Edge case tests for Ollama client."""

import unittest
from unittest.mock import Mock, patch
import requests

from vc_commit_helper.llm.ollama_client import OllamaClient, LLMError


class TestOllamaClientEdgeCases(unittest.TestCase):
    """Edge case tests for OllamaClient."""

    @patch("vc_commit_helper.llm.ollama_client.requests.post")
    def test_generate_with_request_exception(self, mock_post):
        """Test generate when requests raises an exception."""
        mock_post.side_effect = requests.RequestException("Connection error")
        
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="llama3"
        )
        
        with self.assertRaises(LLMError) as ctx:
            client.generate("test prompt")
        self.assertIn("Connection error", str(ctx.exception))

    @patch("vc_commit_helper.llm.ollama_client.requests.post")
    def test_generate_with_generic_exception(self, mock_post):
        """Test generate when a generic exception occurs."""
        mock_post.side_effect = Exception("Unexpected error")
        
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="llama3"
        )
        
        with self.assertRaises(LLMError) as ctx:
            client.generate("test prompt")
        self.assertIn("Unexpected error", str(ctx.exception))