import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vc_commit_helper.config.loader import ConfigError, load_config


class TestConfigLoader(unittest.TestCase):
    """Tests for the configuration loader."""

    def test_load_config_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            config = {
                "base_url": "http://localhost",
                "port": 11434,
                "model": "llama3",
                "request_timeout": 30,
                "max_tokens": 512,
            }
            (config_dir / ".ollama_config.json").write_text(json.dumps(config))
            
            # Mock the _get_config_directory function to return our temp dir
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                result = load_config()
                self.assertEqual(result["base_url"], "http://localhost")
                self.assertEqual(result["port"], 11434)
                self.assertEqual(result["model"], "llama3")
                self.assertEqual(result["request_timeout"], 30)
                self.assertEqual(result["max_tokens"], 512)

    def test_load_config_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError):
                    load_config()

    def test_load_config_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / ".ollama_config.json").write_text("{invalid}")
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError):
                    load_config()

    def test_load_config_missing_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / ".ollama_config.json").write_text(json.dumps({"base_url": "http://", "port": 1}))
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError):
                    load_config()


if __name__ == "__main__":
    unittest.main()