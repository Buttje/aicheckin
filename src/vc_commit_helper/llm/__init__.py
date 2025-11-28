"""
Language model integration for vc_commit_helper.

This package contains the :class:`OllamaClient` for communicating with
an Ollama LLM server and the :class:`CommitMessageGenerator` which
leverages the language model to produce commit messages and grouping
logic.
"""

from .ollama_client import OllamaClient, LLMError  # noqa: F401
from .commit_message_generator import CommitMessageGenerator  # noqa: F401