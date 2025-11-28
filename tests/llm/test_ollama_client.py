import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from vc_commit_helper.llm.ollama_client import LLMError, OllamaClient


class DummyResponse(SimpleNamespace):
    def json(self):
        return json.loads(self.text)


class TestOllamaClient(unittest.TestCase):
    def test_generate_success(self) -> None:
        # The patched function should accept keyword arguments matching the
        # requests.post signature. Avoid shadowing the json module name.
        def fake_post(url, *_args, **kwargs):
            # kwargs may include 'json' or 'data'; we don't inspect it here.
            return DummyResponse(status_code=200, text=json.dumps({"response": "Hello"}))

        with patch("requests.post", fake_post):
            client = OllamaClient("http://localhost", 11434, "model")
            resp = client.generate("prompt")
            self.assertEqual(resp, "Hello")

    def test_generate_error_status(self) -> None:
        def fake_post(url, *_args, **kwargs):
            return DummyResponse(status_code=500, text="Internal error")

        with patch("requests.post", fake_post):
            client = OllamaClient("http://localhost", 11434, "model")
            with self.assertRaises(LLMError):
                client.generate("prompt")

    def test_generate_invalid_json(self) -> None:
        def fake_post(url, *_args, **kwargs):
            return DummyResponse(status_code=200, text="not json")

        with patch("requests.post", fake_post):
            client = OllamaClient("http://localhost", 11434, "model")
            with self.assertRaises(LLMError):
                client.generate("prompt")


if __name__ == "__main__":
    unittest.main()