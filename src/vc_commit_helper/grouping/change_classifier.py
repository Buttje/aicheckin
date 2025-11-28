"""
Heuristics for classifying file changes into Conventional Commit types.

The classifier attempts to infer the most appropriate commit type based
on the file name and diff content. It is intentionally simple and
deterministic so that it can be unit tested without requiring a
language model. If an LLM is desired for classification, it can be
integrated by replacing or augmenting this function.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def classify_change(file_path: str, diff: str) -> str:
    """Classify a change into a Conventional Commit type.

    Parameters
    ----------
    file_path : str
        Path to the changed file relative to the repository root.
    diff : str
        Unified diff of the file relative to HEAD/BASE.

    Returns
    -------
    str
        One of the Conventional Commit types: ``feat``, ``fix``,
        ``docs``, ``style``, ``refactor``, ``perf``, ``test``, ``build``,
        ``ci``, ``chore``, ``revert``, or ``other``.

    Notes
    -----
    The classification is heuristic. It uses the file extension and
    simple keyword detection in the diff. If no rule matches, the
    fallback ``other`` is returned.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    # Documentation files
    if ext in {".md", ".rst", ".txt", ".adoc"}:
        return "docs"
    # Test files (common patterns)
    if path.name.startswith("test_") or path.name.endswith("_test.py") or "tests" in path.parts:
        return "test"
    # Build/CI files
    if path.name in {"Dockerfile", "docker-compose.yml"} or path.suffix in {".yaml", ".yml"}:
        # Use CI for workflows under .github
        if ".github" in path.parts:
            return "ci"
        return "build"
    # Style changes: detect formatting-only changes by checking diff for changes
    # to whitespace only. If all changed lines only modify whitespace, classify as style.
    # Collect added and removed lines (ignoring the diff header prefixes)
    changed_lines = [line for line in diff.splitlines() if line.startswith(('+', '-')) and not line.startswith(('++', '--'))]
    if changed_lines:
        # Detect pure whitespace changes. If the non-whitespace content of added and
        # removed lines is identical, treat this as a formatting/style change.
        minus_lines = [line[1:] for line in changed_lines if line.startswith('-')]
        plus_lines = [line[1:] for line in changed_lines if line.startswith('+')]
        if minus_lines and plus_lines:
            # Normalize by stripping all whitespace characters
            norm_minus = "".join(re.sub(r"\s", "", ln) for ln in minus_lines)
            norm_plus = "".join(re.sub(r"\s", "", ln) for ln in plus_lines)
            if norm_minus == norm_plus:
                return "style"
        # Fallback: if every changed line becomes empty when whitespace is removed
        # classify as style (covers blank line additions/removals)
        stripped = [re.sub(r"\s", "", l[1:]) for l in changed_lines]
        if all(not s for s in stripped):
            return "style"
    # Fix detection based on keywords
    if re.search(r"\bfix(e[ds])?|bug|error|issue|patch|hotfix\b", diff, re.IGNORECASE):
        return "fix"
    # Refactor detection: look for keyword and absence of new features
    if re.search(r"\brefactor\b", diff, re.IGNORECASE):
        return "refactor"
    # Performance optimisation
    if re.search(r"\bperf(ormance)?\b", diff, re.IGNORECASE):
        return "perf"
    # Feature additions: presence of the word "feature" or addition of function definitions/classes
    if re.search(r"\bfeat(ure)?\b", diff, re.IGNORECASE):
        return "feat"
    if re.search(r"\bclass\b|\bdef\b|\bfunction\b", diff, re.IGNORECASE) and '+' in diff:
        # Added new code structures
        return "feat"
    # Default
    return "other"