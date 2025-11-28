import unittest
from unittest.mock import patch

from vc_commit_helper.llm.ollama_client import LLMError, OllamaClient


class DummyResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status
        self.text = ""

    def json(self):
        return self._json


class TestOllamaClientExtra(unittest.TestCase):
    """Additional tests for OllamaClient to cover alternate response structures."""

    def test_generate_message_key(self) -> None:
        client = OllamaClient(base_url="http://", port=1, model="m")
        resp_data = {"message": {"content": "hello world"}}
        with patch("requests.post", return_value=DummyResponse(resp_data, status=200)):
            result = client.generate("prompt")
            self.assertEqual(result, "hello world")

    def test_generate_stream_ignored(self) -> None:
        client = OllamaClient(base_url="http://", port=1, model="m")
        resp_data = {"response": "ok"}
        # Provide stream=True; our client ignores streaming and sets stream to False
        with patch("requests.post", return_value=DummyResponse(resp_data, status=200)):
            result = client.generate("prompt", stream=True)
            self.assertEqual(result, "ok")


if __name__ == "__main__":
    unittest.main()