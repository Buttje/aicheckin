import json
import os
import tempfile
import unittest
from pathlib import Path

from vc_commit_helper.config.loader import ConfigError, load_config


class TestConfigLoader(unittest.TestCase):
    def test_load_config_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {
                "base_url": "http://localhost",
                "port": 11434,
                "model": "llama3",
                "request_timeout": 30,
                "max_tokens": 512,
            }
            (root / ".ollama_config.json").write_text(json.dumps(config))
            result = load_config(root)
            self.assertEqual(result["base_url"], "http://localhost")
            self.assertEqual(result["port"], 11434)
            self.assertEqual(result["model"], "llama3")
            self.assertEqual(result["request_timeout"], 30)
            self.assertEqual(result["max_tokens"], 512)

    def test_load_config_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ConfigError):
                load_config(root)

    def test_load_config_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ollama_config.json").write_text("{invalid}")
            with self.assertRaises(ConfigError):
                load_config(root)

    def test_load_config_missing_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ollama_config.json").write_text(json.dumps({"base_url": "http://", "port": 1}))
            with self.assertRaises(ConfigError):
                load_config(root)


if __name__ == "__main__":
    unittest.main()