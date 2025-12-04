import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vc_commit_helper.config.loader import ConfigError, load_config


class TestConfigLoaderExtra(unittest.TestCase):
    """Additional tests for load_config to cover optional type validation."""

    def _write_config(self, config_dir: Path, data: dict) -> Path:
        path = config_dir / ".ollama_config.json"
        path.write_text(json.dumps(data))
        return path

    def test_invalid_base_url_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._write_config(config_dir, {"base_url": 123, "port": 1, "model": "m"})
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("'base_url' must be a string", str(cm.exception))

    def test_invalid_port_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._write_config(config_dir, {"base_url": "http://", "port": "not_int", "model": "m"})
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("'port' must be an integer", str(cm.exception))

    def test_invalid_model_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._write_config(config_dir, {"base_url": "http://", "port": 1, "model": 123})
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("'model' must be a string", str(cm.exception))

    def test_invalid_request_timeout_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._write_config(config_dir, {"base_url": "http://", "port": 1, "model": "m", "request_timeout": "not_number"})
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("'request_timeout' must be a number", str(cm.exception))

    def test_invalid_max_tokens_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._write_config(config_dir, {"base_url": "http://", "port": 1, "model": "m", "max_tokens": 3.14})
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                with self.assertRaises(ConfigError) as cm:
                    load_config()
                self.assertIn("'max_tokens' must be an integer", str(cm.exception))

    def test_valid_optional_fields(self) -> None:
        """Test that valid optional fields are accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            config = {
                "base_url": "http://localhost",
                "port": 11434,
                "model": "llama3",
                "request_timeout": 60.5,  # float is valid
                "max_tokens": 1024,
            }
            self._write_config(config_dir, config)
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                result = load_config()
                self.assertEqual(result["request_timeout"], 60.5)
                self.assertEqual(result["max_tokens"], 1024)

    def test_missing_optional_fields(self) -> None:
        """Test that missing optional fields don't cause errors."""
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            config = {
                "base_url": "http://localhost",
                "port": 11434,
                "model": "llama3",
            }
            self._write_config(config_dir, config)
            with patch('vc_commit_helper.config.loader._get_config_directory', return_value=config_dir):
                result = load_config()
                self.assertEqual(result["base_url"], "http://localhost")
                self.assertEqual(result["port"], 11434)
                self.assertEqual(result["model"], "llama3")
                self.assertNotIn("request_timeout", result)
                self.assertNotIn("max_tokens", result)


if __name__ == "__main__":
    unittest.main()