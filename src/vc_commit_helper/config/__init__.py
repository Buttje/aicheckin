"""
Configuration loading for vc_commit_helper.

Provides a simple loader for the Ollama configuration file located in
the repository root. See :mod:`vc_commit_helper.config.loader` for
implementation details.
"""

from .loader import ConfigError, load_config  # noqa: F401