"""
Commit message generation using an LLM.

This module provides the :class:`CommitMessageGenerator` class, which
invokes the Ollama LLM (via :class:`OllamaClient`) to generate
high‑quality commit messages for grouped changes. It first classifies
individual changes into Conventional Commit types using the
``classify_change`` function, groups changes by type, and then
generates a message for each group. In the event of an LLM failure,
a deterministic fallback message is used.

All commit messages follow the format:
  [type]: Brief description (max 10 words)
  
  Detailed functional description (what, why, how the functionality changes).
  
  - file1
  - file2
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

        The prompt instructs the model to produce a commit message with:
        1. Title: [type]: brief description (max 10 words)
        2. Body: detailed functional description (what, why, how)
        3. File list: affected files with '-' prefix
        """
        # Gather full diffs for context; include more lines for better understanding
        diff_parts = []
        for file in files:
            diff_text = diffs.get(file, "")
            if diff_text:
                # Include more context lines (up to 20) to help LLM understand functionality
                lines = [line for line in diff_text.splitlines() if line.startswith(('+', '-')) and not line.startswith(('++', '--'))]
                context_lines = "\n".join(lines[:20]) if lines else "(no changes)"
                diff_parts.append(f"File: {file}\n{context_lines}")
            else:
                diff_parts.append(f"File: {file}\n(no diff available)")
        
        diff_context = "\n\n".join(diff_parts)
        
        prompt = dedent(
            f"""
            You are an expert software engineer writing commit messages.
            Analyze the following changes and generate a commit message.

            IMPORTANT: Output ONLY the commit message itself. Do NOT include:
            - Any thinking process or reasoning
            - Meta-commentary like "Here's the commit message" or "Let me analyze"
            - Explanations about how you arrived at the message
            - Any text before or after the commit message
            
            Start your response directly with the commit message in the format below.

            COMMIT MESSAGE FORMAT (strict):
            Line 1: [{group_type}]: <brief description max 10 words>
            Line 2: (blank)
            Lines 3-6: Detailed description of what changed, why it changed, and how the functionality is affected. 
                       Focus on the functional/behavioral impact, not just "files were updated".
                       Describe what the code now does, why this change was needed, and what users/system will experience.
            Line 7: (blank)
            Lines 8+: Affected files, one per line with "- " prefix

            CONTENT REQUIREMENTS:
            - The subject line (line 1) MUST be concise and max 10 words
            - The description (lines 3-6) MUST explain WHAT changed functionally, WHY it was needed, and HOW it affects behavior
            - Do NOT write generic messages like "update files" or "refactor code"
            - DO explain the actual functionality impact

            CHANGES TO ANALYZE:
            {diff_context}

            FILES AFFECTED:
            {chr(10).join(f"- {f}" for f in files)}

            Write the commit message now (no preamble, just the message):
            """
        ).strip()
        return prompt

    def _extract_commit_message(self, raw_response: str) -> str:
        """Extract the actual commit message from LLM response, removing thinking process.
        
        The LLM might include reasoning, thinking process, or meta-commentary before
        the actual commit message. This method extracts only the final commit message.
        
        Parameters
        ----------
        raw_response : str
            The raw response from the LLM, which may include thinking process.
            
        Returns
        -------
        str
            The extracted commit message without thinking process.
        """
        if not raw_response or not raw_response.strip():
            raise ValueError("Empty response")
        
        # Common patterns that indicate thinking process or meta-commentary
        thinking_markers = [
            "let me",
            "i will",
            "i'll",
            "first,",
            "based on",
            "looking at",
            "analyzing",
            "the changes show",
            "here's the",
            "here is the",
            "now write",
            "writing the",
            "i see that",
            "i can see",
        ]
        
        lines = raw_response.splitlines()
        
        # Look for the first line that looks like a commit message (starts with [type]: or type:)
        # Also accept lines that don't have type prefix but look like commit subjects
        commit_type_pattern = r'^\s*\[?(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)\]?:\s+'
        
        start_index = None
        
        # First pass: Look for explicit commit type patterns
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
                
            # Check if this line matches commit message pattern
            if re.match(commit_type_pattern, stripped, re.IGNORECASE):
                # Make sure this isn't part of meta-commentary
                lower_line = stripped.lower()
                is_meta = any(marker in lower_line[:40] for marker in thinking_markers)
                if not is_meta:
                    start_index = i
                    break
        
        # If we found a commit message start, extract from there
        if start_index is not None:
            message_lines = lines[start_index:]
            return "\n".join(message_lines).strip()
        
        # Second pass: Look for potential commit subject lines without type prefix
        # These should be short, action-oriented lines
        for i, line in enumerate(lines):
            stripped = line.strip()
            lower_line = stripped.lower()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Skip obvious thinking process lines
            if any(marker in lower_line for marker in thinking_markers):
                continue
            
            # Skip if it looks like a paragraph start (too long or starts with certain words)
            if len(stripped) > 72:  # Standard commit subject line limit
                continue
            
            # If we find a short, substantial line, it might be the commit subject
            if len(stripped) > 15 and not stripped.endswith(":"):
                # Check if the next few lines look like a commit message body
                # (blank line, then description, then file list)
                has_body_structure = False
                if i + 1 < len(lines):
                    # Check for blank line followed by content
                    next_lines = lines[i+1:i+10]
                    for j, next_line in enumerate(next_lines):
                        if next_line.strip() and j > 0:  # Found content after potential blank
                            has_body_structure = True
                            break
                
                if has_body_structure or i == len(lines) - 1:
                    # This looks like a commit message start
                    return "\n".join(lines[i:]).strip()
        
        # Last resort: return the whole response stripped
        return raw_response.strip()

    def _normalize_message(self, message: str, group_type: str) -> str:
        """Normalize the commit message to ensure it starts with [type]: format.
        
        Parameters
        ----------
        message : str
            The raw commit message from the LLM.
        group_type : str
            The commit type (feat, fix, docs, etc.) that was determined by classification.
            
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
        
        # Check if the message already starts with any commit type (not just the expected one)
        any_type_pattern = r'^\[?(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert|other)\]?:\s+'
        existing_type_match = re.match(any_type_pattern, subject_line, re.IGNORECASE)
        
        if existing_type_match:
            # Message already has a type prefix
            existing_type = existing_type_match.group(1).lower()
            
            # If it matches our expected type (or close enough), normalize the format
            if existing_type == group_type.lower():
                # Already has correct type, just ensure format is [type]:
                if re.match(rf'^\[{re.escape(group_type)}\]:\s+', subject_line, re.IGNORECASE):
                    # Already in correct format
                    return message
                # Fix the format
                rest_of_line = re.sub(any_type_pattern, '', subject_line, flags=re.IGNORECASE).strip()
                return f"[{group_type}]: {rest_of_line}\n" + "\n".join(lines[1:])
            else:
                # LLM suggested a different type than our classification
                # Replace with the classified type
                rest_of_line = re.sub(any_type_pattern, '', subject_line, flags=re.IGNORECASE).strip()
                return f"[{group_type}]: {rest_of_line}\n" + "\n".join(lines[1:])
        
        # No type prefix found, prepend the classified type
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
                raw_message = self.ollama_client.generate(prompt)
                # Extract the actual commit message, removing any thinking process
                message = self._extract_commit_message(raw_message)
                # Normalize the message to ensure correct format
                message = self._normalize_message(message, group_type)
            except (LLMError, Exception) as exc:
                logger.warning(
                    "LLM failed to generate commit message for group '%s': %s; using fallback.",
                    group_type,
                    exc,
                )
                # Fallback: concise message following the new format
                # Line 1: [type]: brief description
                # Line 2: blank
                # Lines 3-4: functional description
                # Line 5: blank
                # Lines 6+: file list
                subject = f"[{group_type}]: Changes to {len(files)} file{'s' if len(files) != 1 else ''}"
                description = (
                    "Updated the following files to address functionality improvements and "
                    "maintain code quality. Review the affected files for specific changes."
                )
                body_lines = [f"- {file}" for file in files]
                message = subject + "\n\n" + description + "\n\n" + "\n".join(body_lines)
            commit_groups.append(CommitGroup(type=group_type, files=files, message=message, diffs={file: diffs[file] for file in files}))
        return commit_groups