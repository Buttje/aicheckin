"""
Client for interacting with an Ollama LLM server.

This client wraps HTTP requests to the Ollama REST API. It supports
making text generation requests via the `/api/generate` endpoint. On
error conditions (HTTP errors, timeouts), a :class:`LLMError` is
raised.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger(__name__)
# Attach a null handler to avoid errors when the root logger is missing a
# stream. Messages will still propagate to the root logger if configured.
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


class LLMError(Exception):
    """Raised when communication with the LLM server fails."""

    pass


@dataclass
class OllamaClient:
    """Client for interacting with an Ollama server.

    Parameters
    ----------
    base_url : str
        Base URL of the Ollama server, e.g. ``"http://localhost"``.
    port : int
        Port number of the Ollama server, e.g. ``11434``.
    model : str
        Name of the model to use for generation, e.g. ``"llama3"``.
    request_timeout : float, optional
        Timeout in seconds for HTTP requests. Defaults to 60 seconds.
    max_tokens : int, optional
        Maximum number of tokens to generate. If provided, passed via
        the ``options`` payload.
    """

    base_url: str
    port: int
    model: str
    request_timeout: float = 60.0
    max_tokens: Optional[int] = None

    def _endpoint(self) -> str:
        return f"{self.base_url}:{self.port}/api/generate"

    def generate(self, prompt: str, stream: bool = False) -> str:
        """Generate a completion from the model.

        Parameters
        ----------
        prompt : str
            The prompt to send to the model.
        stream : bool, optional
            Whether to request a streaming response. Streaming is not
            supported by this client, so ``stream=True`` is ignored.

        Returns
        -------
        str
            The generated response text.

        Raises
        ------
        LLMError
            If the request fails or the server returns an error.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        # Additional options
        options: Dict[str, Any] = {}
        if self.max_tokens is not None:
            options["num_predict"] = self.max_tokens
        if options:
            payload["options"] = options
        url = self._endpoint()
        logger.debug("Sending request to LLM at %s with payload: %s", url, payload)
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.request_timeout,
            )
        except (requests.RequestException, Exception) as exc:
            logger.error("Failed to connect to LLM: %s", exc)
            raise LLMError(str(exc)) from exc
        if response.status_code != 200:
            logger.error(
                "LLM returned non-200 status %s: %s", response.status_code, response.text
            )
            raise LLMError(f"LLM returned status {response.status_code}: {response.text}")
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM response: %s", exc)
            raise LLMError("Failed to parse LLM response") from exc
        # The generate endpoint returns a top-level 'response' field containing
        # the generated text when stream=False. If using /api/chat, 'message'
        # would contain the assistant content.
        if "response" in data:
            return data.get("response", "").strip()
        if "message" in data and isinstance(data["message"], dict):
            return data["message"].get("content", "").strip()
        # If none of the expected fields are present, raise an error
        raise LLMError("Unexpected response structure from LLM")