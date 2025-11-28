"""
Commit message generation using an LLM.

This module provides the :class:`CommitMessageGenerator` class, which
invokes the Ollama LLM (via :class:`OllamaClient`) to generate
high‑quality commit messages for grouped changes. It first classifies
individual changes into Conventional Commit types using the
``classify_change`` function, groups changes by type, and then
generates a message for each group. In the event of an LLM failure,
a deterministic fallback message is used.
"""

from __future__ import annotations

import logging
from textwrap import dedent
from typing import Dict, Iterable, List

from vc_commit_helper.grouping.change_classifier import classify_change
from vc_commit_helper.grouping.group_model import CommitGroup
from vc_commit_helper.llm.ollama_client import LLMError, OllamaClient


logger = logging.getLogger(__name__)
# Attach a null handler to prevent logging errors when no handlers are
# configured on the root logger. Logs will propagate when configured.
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


class CommitMessageGenerator:
    """Generate commit groups and messages using heuristic classification and an LLM."""

    def __init__(
        self,
        ollama_client: OllamaClient,
    ) -> None:
        self.ollama_client = ollama_client

    def _build_prompt(self, group_type: str, files: List[str], diffs: Dict[str, str]) -> str:
        """Construct a prompt for the LLM to generate a commit message.

        The prompt instructs the model to produce a Conventional Commit
        message of a specific type with a short summary and body listing
        changes.
        """
        diff_summary_parts = []
        for file in files:
            diff_text = diffs.get(file, "")
            # Summarize diff by including first few changed lines for context
            lines = [line for line in diff_text.splitlines() if line.startswith(('+', '-')) and not line.startswith(('++', '--'))]
            summary = "\n".join(lines[:6]) if lines else ""
            diff_summary_parts.append(f"File: {file}\n{summary}")
        diff_summary = "\n\n".join(diff_summary_parts)
        prompt = dedent(
            f"""
            You are an expert software engineer tasked with writing commit messages.
            Generate a Conventional Commit message of type '{group_type}' for the following changes.
            Provide a short subject line and a detailed body summarising what changed.
            The message should be clear and concise.

            {diff_summary}
            """
        ).strip()
        return prompt

    def generate_groups(
        self,
        diffs: Dict[str, str],
    ) -> List[CommitGroup]:
        """Classify changes, group them, and generate commit messages.

        Parameters
        ----------
        diffs : Dict[str, str]
            Mapping from file paths to their unified diffs.

        Returns
        -------
        List[CommitGroup]
            A list of commit groups with generated commit messages.
        """
        # Classify each file
        groups: Dict[str, List[str]] = {}
        for file_path, diff in diffs.items():
            commit_type = classify_change(file_path, diff)
            groups.setdefault(commit_type, []).append(file_path)
        commit_groups: List[CommitGroup] = []
        for group_type, files in groups.items():
            try:
                prompt = self._build_prompt(group_type, files, diffs)
                message = self.ollama_client.generate(prompt)
                # Ensure the subject line starts with the type prefix
                if not message.splitlines():
                    raise ValueError
                subject_line = message.splitlines()[0]
                if not subject_line.lower().startswith(group_type):
                    # Prepend type if missing
                    message = f"{group_type}: {subject_line}\n" + "\n".join(message.splitlines()[1:])
            except (LLMError, Exception) as exc:
                logger.warning(
                    "LLM failed to generate commit message for group '%s': %s; using fallback.",
                    group_type,
                    exc,
                )
                # Fallback: simple message
                subject = f"{group_type}: update {len(files)} file{'s' if len(files) != 1 else ''}"
                body_lines = [f"- {file}" for file in files]
                message = subject + "\n\n" + "\n".join(body_lines)
            commit_groups.append(CommitGroup(type=group_type, files=files, message=message, diffs={file: diffs[file] for file in files}))
        return commit_groups