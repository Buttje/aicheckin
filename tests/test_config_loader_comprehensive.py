"""Comprehensive tests for config loader."""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vc_commit_helper.config.loader import (
    ConfigError,
    load_config,
    _get_config_directory,
)


class TestConfigLoaderComprehensive(unittest.TestCase):
    """Comprehensive tests for configuration loading."""

    def test_get_config_directory(self):
        """Test that _get_config_directory returns correct path."""
        config_dir = _get_config_directory()
        self.assertIsInstance(config_dir, Path)
        # The directory should be ~/.ollama_server
        self.assertEqual(config_dir, Path.home() / ".ollama_server")

    @patch("vc_commit_helper.config.loader._get_config_directory")
    def test_load_config_file_not_found(self, mock_get_config_dir):
        """Test ConfigError when config file doesn't exist."""
        mock_config_dir = MagicMock()
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_config_dir.__truediv__.return_value = mock_config_path
        mock_get_config_dir.return_value = mock_config_dir
        
        with self.assertRaises(ConfigError) as ctx:
            load_config()
        self.assertIn("Missing Ollama configuration file", str(ctx.exception))

    @patch("vc_commit_helper.config.loader._get_config_directory")
    def test_load_config_invalid_json(self, mock_get_config_dir):
        """Test ConfigError on malformed JSON."""
        mock_config_dir = MagicMock()
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = "{ invalid json"
        mock_config_path.name = ".ollama_config.json"
        mock_config_dir.__truediv__.return_value = mock_config_path
        mock_get_config_dir.return_value = mock_config_dir
        
        with self.assertRaises(ConfigError) as ctx:
            load_config()
        self.assertIn("Invalid JSON", str(ctx.exception))

    @patch("vc_commit_helper.config.loader._get_config_directory")
    def test_load_config_missing_required_keys(self, mock_get_config_dir):
        """Test ConfigError when required keys are missing."""
        mock_config_dir = MagicMock()
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = json.dumps({"base_url": "http://localhost"})
        mock_config_path.name = ".ollama_config.json"
        mock_config_dir.__truediv__.return_value = mock_config_path
        mock_get_config_dir.return_value = mock_config_dir
        
        with self.assertRaises(ConfigError) as ctx:
            load_config()
        self.assertIn("Missing required configuration keys", str(ctx.exception))

    @patch("vc_commit_helper.config.loader._get_config_directory")
    def test_load_config_invalid_types(self, mock_get_config_dir):
        """Test ConfigError when field types are wrong."""
        test_cases = [
            ({"base_url": 123, "port": 11434, "model": "llama3"}, "'base_url' must be a string"),
            ({"base_url": "http://localhost", "port": "11434", "model": "llama3"}, "'port' must be an integer"),
            ({"base_url": "http://localhost", "port": 11434, "model": 123}, "'model' must be a string"),
            ({"base_url": "http://localhost", "port": 11434, "model": "llama3", "request_timeout": "60"}, "'request_timeout' must be a number"),
            ({"base_url": "http://localhost", "port": 11434, "model": "llama3", "max_tokens": "100"}, "'max_tokens' must be an integer"),
        ]
        
        for config_data, expected_error in test_cases:
            with self.subTest(config=config_data):
                mock_config_dir = MagicMock()
                mock_config_path = MagicMock()
                mock_config_path.exists.return_value = True
                mock_config_path.read_text.return_value = json.dumps(config_data)
                mock_config_path.name = ".ollama_config.json"
                mock_config_dir.__truediv__.return_value = mock_config_path
                mock_get_config_dir.return_value = mock_config_dir
                
                with self.assertRaises(ConfigError) as ctx:
                    load_config()
                self.assertIn(expected_error, str(ctx.exception))

    @patch("vc_commit_helper.config.loader._get_config_directory")
    def test_load_config_success_with_optional_fields(self, mock_get_config_dir):
        """Test successful config load with all optional fields."""
        config_data = {
            "base_url": "http://localhost",
            "port": 11434,
            "model": "llama3",
            "request_timeout": 120.5,
            "max_tokens": 2000,
        }
        
        mock_config_dir = MagicMock()
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.return_value = json.dumps(config_data)
        mock_config_path.name = ".ollama_config.json"
        mock_config_dir.__truediv__.return_value = mock_config_path
        mock_get_config_dir.return_value = mock_config_dir
        
        result = load_config()
        self.assertEqual(result, config_data)

    @patch("vc_commit_helper.config.loader._get_config_directory")
    def test_load_config_os_error(self, mock_get_config_dir):
        """Test ConfigError when file cannot be read."""
        mock_config_dir = MagicMock()
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_config_path.read_text.side_effect = OSError("Permission denied")
        mock_config_path.name = ".ollama_config.json"
        mock_config_dir.__truediv__.return_value = mock_config_path
        mock_get_config_dir.return_value = mock_config_dir
        
        with self.assertRaises(ConfigError) as ctx:
            load_config()
        self.assertIn("Invalid JSON", str(ctx.exception))