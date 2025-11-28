"""
Configuration loader for vc_commit_helper.

The tool expects a JSON configuration file named ``.ollama_config.json``
located in the root of the repository. This loader validates the
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


def load_config(repo_root: Path) -> Dict[str, Any]:
    """Load the Ollama configuration from ``repo_root`` and return it.

    The configuration is read from a file named ``.ollama_config.json``
    located in the repository root. If the file is missing, malformed,
    missing required keys, or has fields of the wrong type, a
    :class:`ConfigError` is raised.
    """
    config_path = repo_root / ".ollama_config.json"
    if not config_path.exists():
        logger.error("Configuration file '%s' does not exist", config_path)
        raise ConfigError(
            f"Missing Ollama configuration file: {config_path.name}."
        )
    try:
        content = config_path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read or parse configuration file: %s", exc)
        raise ConfigError(
            f"Invalid JSON in {config_path.name}: {exc}"  # type: ignore[str-bytes-safe]
        )
    # Validate required keys
    required_keys = ["base_url", "port", "model"]
    missing = [key for key in required_keys if key not in data]
    if missing:
        logger.error("Configuration file missing required keys: %s", missing)
        raise ConfigError(
            f"Missing required configuration keys: {', '.join(missing)}"
        )
    # Optional keys: request_timeout, max_tokens. Validate types.
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
    logger.debug("Loaded Ollama configuration: %s", data)
    return data