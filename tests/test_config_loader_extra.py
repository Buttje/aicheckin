import json
import tempfile
import unittest
from pathlib import Path

from vc_commit_helper.config.loader import ConfigError, load_config


class TestConfigLoaderExtra(unittest.TestCase):
    """Additional tests for load_config to cover optional type validation."""

    def _write_config(self, root: Path, data: dict) -> Path:
        path = root / ".ollama_config.json"
        path.write_text(json.dumps(data))
        return path

    def test_invalid_base_url_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"base_url": 123, "port": 1, "model": "m"})
            with self.assertRaises(ConfigError):
                load_config(root)

    def test_invalid_port_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"base_url": "http://", "port": "not_int", "model": "m"})
            with self.assertRaises(ConfigError):
                load_config(root)

    def test_invalid_model_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"base_url": "http://", "port": 1, "model": 123})
            with self.assertRaises(ConfigError):
                load_config(root)

    def test_invalid_request_timeout_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"base_url": "http://", "port": 1, "model": "m", "request_timeout": "not_number"})
            with self.assertRaises(ConfigError):
                load_config(root)

    def test_invalid_max_tokens_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, {"base_url": "http://", "port": 1, "model": "m", "max_tokens": 3.14})
            with self.assertRaises(ConfigError):
                load_config(root)


if __name__ == "__main__":
    unittest.main()