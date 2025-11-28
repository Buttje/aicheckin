"""
Git client implementation for vc_commit_helper.

This module wraps basic Git operations required by the commit assistant.
It is intentionally minimal and only implements the subset of features
needed by the CLI. All subprocess calls are executed with proper error
handling so that unit tests can mock them easily.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)
# Attach a null handler to avoid logging errors when the root logger is not
# configured. Logs will propagate to the root when configured by the CLI.
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


@dataclass
class FileChange:
    """Representation of a single file change in the repository."""

    path: str
    status: str  # e.g. 'M' modified, 'A' added, 'D' deleted, 'R' renamed


class GitError(Exception):
    """Raised when a Git command fails."""

    pass


class GitClient:
    """Client for interacting with a Git repository."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------
    @staticmethod
    def is_repo(path: Path) -> bool:
        """Return True if the given path is inside a Git repository."""
        return (path / ".git").exists()

    @staticmethod
    def find_repo_root(start: Path) -> Optional[Path]:
        """Find the root of the Git repository starting from ``start``.

        Walk upwards until a ``.git`` directory is found or the filesystem
        root is reached.
        """
        current = start.resolve()
        while True:
            if (current / ".git").exists():
                return current
            if current.parent == current:
                # reached filesystem root
                return None
            current = current.parent

    # ------------------------------------------------------------------
    # Basic Git commands
    # ------------------------------------------------------------------
    def _run(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a Git command in the repository root.

        Raises
        ------
        GitError
            If the command exits with a non-zero status when ``check`` is True.
        """
        full_cmd = ["git"] + args
        logger.debug("Executing Git command: %s", " ".join(full_cmd))
        result = subprocess.run(
            full_cmd,
            cwd=self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if check and result.returncode != 0:
            logger.error(
                "Git command failed: %s\nSTDOUT: %s\nSTDERR: %s",
                " ".join(full_cmd),
                result.stdout,
                result.stderr,
            )
            raise GitError(result.stderr.strip() or result.stdout.strip())
        return result

    # ------------------------------------------------------------------
    # Detection and status
    # ------------------------------------------------------------------
    def get_changes(self) -> List[FileChange]:
        """Return a list of changes in the working tree relative to HEAD.

        Ignored files (according to ``.gitignore`` and other Git mechanisms)
        are not included. Untracked files are excluded by default. Only
        modifications, additions, deletions, and renames are considered.
        """
        # Use porcelain status for easy parsing. The format is two-letter
        # status codes followed by the filename. See `git status --help`.
        result = self._run(["status", "--porcelain"], check=True)
        changes: List[FileChange] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # Status is two columns: index and working tree. We are interested
            # in the working tree indicator, but treat both similarly.
            status_code = line[:2]
            path = line[3:].strip()
            # Skip untracked files (??) unless specifically included
            if status_code == "??":
                continue
            # Map to simplified status
            if status_code[0] == "R" or status_code[1] == "R":
                status = "R"
            elif status_code[0] == "A" or status_code[1] == "A":
                status = "A"
            elif status_code[0] == "D" or status_code[1] == "D":
                status = "D"
            else:
                status = "M"
            changes.append(FileChange(path=path, status=status))
        logger.debug("Detected Git changes: %s", changes)
        return changes

    def get_diff(self, file_path: str) -> str:
        """Return the unified diff for a specific file relative to HEAD."""
        result = self._run(["diff", "HEAD", "--", file_path], check=True)
        return result.stdout

    # ------------------------------------------------------------------
    # Staging, committing, pushing
    # ------------------------------------------------------------------
    def stage_files(self, files: List[str]) -> None:
        """Stage the given files for commit.

        For deleted files, ``git rm`` is used; otherwise ``git add``.
        """
        for file in files:
            abs_path = self.repo_root / file
            if abs_path.exists():
                # Modified or added file
                self._run(["add", "--", file], check=True)
            else:
                # Deleted file
                self._run(["rm", "--", file], check=True)

    def commit(self, message: str) -> None:
        """Create a commit with the given message.

        Multi-line commit messages are supported. If the commit fails,
        a GitError is raised.
        """
        self._run(["commit", "-m", message], check=True)

    def push(self) -> None:
        """Push the current branch to the default remote (origin).

        If pushing fails, a GitError is raised.
        """
        self._run(["push"], check=True)