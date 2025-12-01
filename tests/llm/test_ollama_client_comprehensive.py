"""Comprehensive tests for Ollama client to improve coverage."""

import json
import unittest
from unittest.mock import Mock, patch

from vc_commit_helper.llm.ollama_client import OllamaClient, LLMError


class TestOllamaClientComprehensive(unittest.TestCase):
    """Comprehensive tests for OllamaClient."""

    @patch("vc_commit_helper.llm.ollama_client.requests.post")
    def test_generate_with_message_field(self, mock_post):
        """Test generate when response contains 'message' field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Generated text from message field"}
        }
        mock_post.return_value = mock_response
        
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="llama3"
        )
        
        result = client.generate("test prompt")
        self.assertEqual(result, "Generated text from message field")

    @patch("vc_commit_helper.llm.ollama_client.requests.post")
    def test_generate_with_unexpected_structure(self, mock_post):
        """Test generate when response has unexpected structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "structure"}
        mock_post.return_value = mock_response
        
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="llama3"
        )
        
        with self.assertRaises(LLMError) as ctx:
            client.generate("test prompt")
        self.assertIn("Unexpected response structure", str(ctx.exception))

    @patch("vc_commit_helper.llm.ollama_client.requests.post")
    def test_generate_with_json_decode_error(self, mock_post):
        """Test generate when response cannot be parsed as JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_post.return_value = mock_response
        
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="llama3"
        )
        
        with self.assertRaises(LLMError) as ctx:
            client.generate("test prompt")
        self.assertIn("Failed to parse LLM response", str(ctx.exception))

    @patch("vc_commit_helper.llm.ollama_client.requests.post")
    def test_generate_with_non_200_status(self, mock_post):
        """Test generate when server returns non-200 status."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        client = OllamaClient(
            base_url="http://localhost",
            port=11434,
            model="llama3"
        )
        
        with self.assertRaises(LLMError) as ctx:
            client.generate("test prompt")
        self.assertIn("500", str(ctx.exception))