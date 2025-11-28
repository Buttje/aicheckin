"""
Data models for commit grouping.

The :class:`CommitGroup` represents a collection of related changes that
should be committed together. Each group has an associated commit type,
a list of affected files, and a proposed commit message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CommitGroup:
    """Representation of a grouped commit.

    Attributes
    ----------
    type : str
        The Conventional Commit type (feat, fix, docs, etc.).
    files : List[str]
        List of files included in the group.
    message : str
        Proposed commit message.
    diffs : Dict[str, str]
        Mapping of file paths to their unified diffs.
    """

    type: str
    files: List[str]
    message: str
    diffs: Dict[str, str] = field(default_factory=dict)