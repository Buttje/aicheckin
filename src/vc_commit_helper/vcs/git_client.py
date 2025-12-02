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
        try:
            result = subprocess.run(
                full_cmd,
                cwd=self.repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid characters instead of failing
            )
        except UnicodeDecodeError as e:
            logger.error("Unicode decode error in Git output: %s", e)
            raise GitError(f"Failed to decode Git output: {e}") from e
        
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
    # Status and change detection
    # ------------------------------------------------------------------
    def get_changes(self) -> List[FileChange]:
        """Get the list of changed files in the repository.
        
        Returns a list of FileChange objects representing modified, added,
        deleted, and renamed files. Untracked files (status '??') are excluded.
        
        Returns
        -------
        List[FileChange]
            List of file changes in the repository.
            
        Raises
        ------
        GitError
            If the git status command fails.
        """
        result = self._run(["status", "--porcelain"], check=True)
        changes = []
        
        for line in result.stdout.splitlines():
            # Skip empty lines
            if not line.strip():
                continue
            
            # Git porcelain format: XY filename
            # X = index status, Y = working tree status
            # We need at least 3 characters (XY + space + filename)
            if len(line) < 3:
                continue
            
            # Extract status code (first 2 characters)
            status_code = line[:2]
            # Extract filename (skip the status and space)
            filename = line[3:]
            
            # Skip untracked files
            if status_code == "??":
                continue
            
            # Determine the primary status
            # Status codes can be: ' M', 'M ', 'MM', 'A ', ' A', 'D ', ' D', 'R ', etc.
            status = status_code.strip()
            if not status:
                # Both characters are spaces - shouldn't happen in porcelain output
                continue
            
            # Take the first non-space character as the status
            primary_status = status[0] if status else 'M'
            
            # For renamed files, keep the full "old -> new" syntax in the path
            changes.append(FileChange(path=filename, status=primary_status))
        
        return changes

    # ------------------------------------------------------------------
    # Branch operations
    # ------------------------------------------------------------------
    def get_current_branch(self) -> str:
        """Get the name of the current branch.
        
        Returns
        -------
        str
            The name of the current branch.
            
        Raises
        ------
        GitError
            If unable to determine the current branch.
        """
        result = self._run(["rev-parse", "--abbrev-ref", "HEAD"], check=True)
        return result.stdout.strip()

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists.
        
        Parameters
        ----------
        branch_name : str
            The name of the branch to check.
            
        Returns
        -------
        bool
            True if the branch exists, False otherwise.
        """
        result = self._run(["branch", "--list", branch_name], check=False)
        return bool(result.stdout.strip())

    def _has_remote(self) -> bool:
        """Return True if the repository has at least one remote configured."""
        result = self._run(["remote"], check=False)
        return bool(result.stdout.strip())

    def remote_branch_exists(self, branch_name: str, remote: str = "origin") -> bool:
        """Check whether a branch exists on the given remote.

        Uses `git ls-remote --heads <remote> <branch>` which returns nothing
        (exit code 0) when the branch does not exist on the remote.
        """
        result = self._run(["ls-remote", "--heads", remote, branch_name], check=False)
        return bool(result.stdout.strip())

    def create_branch(self, branch_name: str) -> None:
        """Create and switch to a new branch.
        
        Parameters
        ----------
        branch_name : str
            The name of the branch to create.
            
        Raises
        ------
        GitError
            If branch creation fails.
        """
        # Create local branch and switch to it
        self._run(["checkout", "-b", branch_name], check=True)

        # If a remote exists and the branch is not present there, create it
        # on the remote by pushing and setting the upstream. This ensures
        # the branch exists on the remote before further operations.
        try:
            if self._has_remote() and not self.remote_branch_exists(branch_name):
                self._run(["push", "--set-upstream", "origin", branch_name], check=True)
        except GitError:
            # Bubble up the error if push fails; callers can decide how to
            # handle it. We don't silently ignore remote push failures.
            raise

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

    def push(self, set_upstream: bool = False) -> None:
        """Push the current branch to the default remote (origin).

        Parameters
        ----------
        set_upstream : bool, optional
            If True, set the upstream branch for the current branch.
            This is useful when pushing a newly created branch.

        Raises
        ------
        GitError
            If pushing fails.
        """
        if set_upstream:
            # Get current branch name
            branch = self.get_current_branch()
            self._run(["push", "--set-upstream", "origin", branch], check=True)
        else:
            self._run(["push"], check=True) 
