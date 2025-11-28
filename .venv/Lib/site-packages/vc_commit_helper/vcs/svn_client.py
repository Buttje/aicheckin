"""
Subversion (SVN) client implementation for vc_commit_helper.

This module provides a thin wrapper around SVN command line operations
required for the commit assistant. Only a limited subset of SVN
functionality is implemented.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


logger = logging.getLogger(__name__)
# Attach a null handler to prevent logging errors when no root handlers are
# configured. Logs will still propagate to the root logger when available.
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


@dataclass
class FileChange:
    """Representation of a single file change in an SVN working copy."""

    path: str
    status: str  # e.g. 'M' modified, 'A' added, 'D' deleted, 'R' replaced


class SVNError(Exception):
    """Raised when an SVN command fails."""

    pass


class SVNClient:
    """Client for interacting with an SVN working copy."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    @staticmethod
    def is_repo(path: Path) -> bool:
        """Return True if the given path is inside an SVN working copy."""
        return (path / ".svn").exists()

    @staticmethod
    def find_repo_root(start: Path) -> Optional[Path]:
        """Find the root of an SVN working copy starting from ``start``.

        Walk upwards until a ``.svn`` directory is found or the filesystem
        root is reached.
        """
        current = start.resolve()
        while True:
            if (current / ".svn").exists():
                return current
            if current.parent == current:
                return None
            current = current.parent

    # Internal helper to run SVN commands
    def _run(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        full_cmd = ["svn"] + args
        logger.debug("Executing SVN command: %s", " ".join(full_cmd))
        result = subprocess.run(
            full_cmd,
            cwd=self.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if check and result.returncode != 0:
            logger.error(
                "SVN command failed: %s\nSTDOUT: %s\nSTDERR: %s",
                " ".join(full_cmd),
                result.stdout,
                result.stderr,
            )
            raise SVNError(result.stderr.strip() or result.stdout.strip())
        return result

    def get_changes(self) -> List[FileChange]:
        """Return a list of changes in the working copy relative to BASE.

        Unversioned ("?") files are ignored by default.
        """
        result = self._run(["status"], check=True)
        changes: List[FileChange] = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            status_code = line[0]
            path = line[8:].strip()
            # Ignore unversioned files
            if status_code == "?":
                continue
            # Map to simplified statuses
            if status_code == "A":
                status = "A"
            elif status_code == "D":
                status = "D"
            elif status_code == "R":
                status = "R"
            else:
                status = "M"
            changes.append(FileChange(path=path, status=status))
        logger.debug("Detected SVN changes: %s", changes)
        return changes

    def get_diff(self, file_path: str) -> str:
        """Return the unified diff for a specific file relative to BASE."""
        result = self._run(["diff", "--", file_path], check=True)
        return result.stdout

    def stage_files(self, files: List[str], statuses: Optional[dict[str, str]] = None) -> None:
        """Schedule changes for commit.

        In SVN there is no index; staging corresponds to scheduling
        additions or deletions. Modified files do not need explicit staging.

        Parameters
        ----------
        files : List[str]
            List of file paths to stage.
        statuses : dict[str, str], optional
            Mapping from file path to status ('A', 'D', etc.). If provided,
            determines whether to call 'svn add' or 'svn delete' for each
            file. If not provided, files are assumed to be modified.
        """
        statuses = statuses or {}
        for file in files:
            status = statuses.get(file, "M")
            if status == "A":
                self._run(["add", "--", file], check=True)
            elif status == "D":
                self._run(["delete", "--", file], check=True)
            # Modified files need no explicit staging

    def commit(self, message: str, files: List[str]) -> None:
        """Commit the specified files with the given message.

        Parameters
        ----------
        message : str
            The commit message.
        files : List[str]
            Files to include in the commit.
        """
        # Build commit command: specify files and message
        args = ["commit", "-m", message] + ["--"] + files
        self._run(args, check=True)