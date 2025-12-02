"""
Commit message generation using an LLM.

This module provides the :class:`CommitMessageGenerator` class, which
invokes the Ollama LLM (via :class:`OllamaClient`) to generate
high‑quality commit messages for grouped changes. It first classifies
individual changes into Conventional Commit types using the
``classify_change`` function, groups changes by type, and then
generates a message for each group. In the event of an LLM failure,
a deterministic fallback message is used.

All commit messages follow the format: [type]: description
"""

from __future__ import annotations

import logging
import re
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

        The prompt instructs the model to produce a commit message
        with the format [type]: description, followed by a detailed body.
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
            Generate a commit message for the following changes.
            The message MUST start with [{group_type}]: followed by a short description.
            Then provide a brief 1-2 sentence "Functional impact" summary that explains
            the runtime/behavioural impact of the change (what will happen when this
            change is applied). Place this functional impact summary before the
            detailed file list or body.
            Finally, provide a detailed body summarising what changed.
            The message should be clear and concise.

            Example format:
            [{group_type}]: short description of the change

            Functional impact: One- or two-sentence summary of behavioural impact.

            Detailed explanation of what was changed and why.

            {diff_summary}
            """
        ).strip()
        return prompt

    def _normalize_message(self, message: str, group_type: str) -> str:
        """Normalize the commit message to ensure it starts with [type]: format.
        
        Parameters
        ----------
        message : str
            The raw commit message from the LLM.
        group_type : str
            The commit type (feat, fix, docs, etc.).
            
        Returns
        -------
        str
            Normalized message starting with [type]: description
        """
        if not message or not message.strip():
            raise ValueError("Empty message")
        
        lines = message.splitlines()
        if not lines:
            raise ValueError("No lines in message")
        
        subject_line = lines[0].strip()
        
        # Check if already in correct format [type]:
        if re.match(rf'^\[{re.escape(group_type)}\]:\s+', subject_line, re.IGNORECASE):
            return message
        
        # Check if it starts with type: (without brackets)
        if re.match(rf'^{re.escape(group_type)}:\s+', subject_line, re.IGNORECASE):
            # Replace with [type]:
            subject_line = re.sub(rf'^{re.escape(group_type)}:\s+', f'[{group_type}]: ', subject_line, flags=re.IGNORECASE)
            return subject_line + "\n" + "\n".join(lines[1:])
        
        # Check if it starts with [type] (without colon)
        if re.match(rf'^\[{re.escape(group_type)}\]\s+', subject_line, re.IGNORECASE):
            # Add colon after bracket
            subject_line = re.sub(rf'^\[{re.escape(group_type)}\]\s+', f'[{group_type}]: ', subject_line, flags=re.IGNORECASE)
            return subject_line + "\n" + "\n".join(lines[1:])
        
        # Otherwise, prepend [type]:
        return f"[{group_type}]: {subject_line}\n" + "\n".join(lines[1:])

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
            All messages follow the format: [type]: description
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
                # Normalize the message to ensure correct format
                message = self._normalize_message(message, group_type)
            except (LLMError, Exception) as exc:
                logger.warning(
                    "LLM failed to generate commit message for group '%s': %s; using fallback.",
                    group_type,
                    exc,
                )
                # Fallback: simple message with correct format and a short
                # deterministic functional impact summary placed before the file list.
                subject = f"[{group_type}]: update {len(files)} file{'s' if len(files) != 1 else ''}"
                impact = (
                    f"Functional impact: Changes {len(files)} file{'s' if len(files) != 1 else ''}. "
                    "Review the file list for affected areas and potential behaviour changes."
                )
                body_lines = [f"- {file}" for file in files]
                message = subject + "\n\n" + impact + "\n\n" + "\n".join(body_lines)
            commit_groups.append(CommitGroup(type=group_type, files=files, message=message, diffs={file: diffs[file] for file in files}))
        return commit_groups