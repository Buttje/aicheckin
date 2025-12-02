"""
Configuration loader for vc_commit_helper.

The tool expects a JSON configuration file named ``.ollama_config.json``
located in the installation directory of aicheckin. This loader validates the
structure of the configuration and returns a dictionary containing
settings for connecting to an Ollama server.

If the configuration file is missing, malformed, or missing required
keys, a :class:`ConfigError` is raised.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)
# Attach a null handler to avoid "No handler" warnings or logging errors in
# environments where the root logger may be closed. We do not disable
# propagation so that when the CLI configures logging, messages still
# appear. If no handlers are configured on the root, messages will be
# suppressed safely.
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    # Prevent logs from propagating to the root logger. This avoids
    # errors when the root logger's stream has been closed (e.g. during
    # unit tests) while still allowing explicit configuration in the CLI
    # to override this behaviour.
    logger.propagate = False


class ConfigError(Exception):
    """Raised when the Ollama configuration file is missing or invalid."""

    pass


def _get_install_directory(module_file: Optional[Path] = None) -> Path:
    """Get the installation directory of aicheckin.
    
    Returns the directory where the aicheckin package is installed.
    This works for both development installations and installed packages.
    
    For editable installs, this returns the source directory.
    For regular installs, this returns the site-packages directory.
    """
    # Determine the module file to use (allows tests to pass a fake path).
    module_file = Path(module_file) if module_file is not None else Path(__file__)
    # Get the directory of this module file (loader.py -> src/vc_commit_helper/config/loader.py)
    # We want: src/vc_commit_helper/
    module_dir = module_file.parent.parent
    
    # Check if we're in an editable install (source directory)
    # In editable mode, the config should be in the source tree
    config_in_source = module_dir / ".ollama_config.json"
    if config_in_source.exists():
        return module_dir
    
    # Check if we're in a regular install (site-packages)
    # The config should still be in the package directory
    if (module_dir / "__init__.py").exists():
        return module_dir
    
    # Fallback: return the module directory
    return module_dir


def load_config(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load the Ollama configuration from the installation directory and return it.

    The configuration is read from a file named ``.ollama_config.json``
    located in the aicheckin installation directory. If the file is missing, 
    malformed, missing required keys, or has fields of the wrong type, a
    :class:`ConfigError` is raised.
    
    Args:
        repo_root: Deprecated parameter, kept for backward compatibility.
                   The configuration is now loaded from the installation directory.
    
    Returns:
        A dictionary containing the validated configuration with keys:
        - base_url (str): The base URL of the Ollama server
        - port (int): The port number
        - model (str): The model name
        - request_timeout (int|float, optional): Request timeout in seconds
        - max_tokens (int, optional): Maximum tokens for generation
    
    Raises:
        ConfigError: If the configuration file is missing, malformed, or invalid.
    """
    # First, prefer a user-level configuration in the home folder
    # e.g. ~/.ollama_server/.ollama_config.json
    home_config_dir = Path.home() / ".ollama_server"
    home_config_path = home_config_dir / ".ollama_config.json"

    if home_config_path.exists():
        config_path = home_config_path
    else:
        install_dir = _get_install_directory()
        config_path = install_dir / ".ollama_config.json"
    
    if not config_path.exists():
        logger.error("Configuration file '%s' does not exist", config_path)
        raise ConfigError(
            f"Missing Ollama configuration file: {config_path}. "
            f"Expected location: {install_dir}\n"
            f"Please run the installer again or create the config file manually."
        )
    
    try:
        content = config_path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read or parse configuration file: %s", exc)
        raise ConfigError(
            f"Invalid JSON in {config_path.name}: {exc}"  # type: ignore[str-bytes-safe]
        ) from exc
    
    # Validate required keys
    required_keys = ["base_url", "port", "model"]
    missing = [key for key in required_keys if key not in data]
    if missing:
        logger.error("Configuration file missing required keys: %s", missing)
        raise ConfigError(
            f"Missing required configuration keys: {', '.join(missing)}"
        )
    
    # Validate required key types
    if not isinstance(data.get("base_url"), str):
        raise ConfigError("'base_url' must be a string")
    if not isinstance(data.get("port"), int):
        raise ConfigError("'port' must be an integer")
    if not isinstance(data.get("model"), str):
        raise ConfigError("'model' must be a string")
    
    # Validate optional keys if present
    if "request_timeout" in data and not isinstance(data["request_timeout"], (int, float)):
        raise ConfigError("'request_timeout' must be a number")
    if "max_tokens" in data and not isinstance(data["max_tokens"], int):
        raise ConfigError("'max_tokens' must be an integer")
    
    logger.debug("Loaded Ollama configuration from: %s", config_path)
    logger.debug("Configuration data: %s", data)
    return data