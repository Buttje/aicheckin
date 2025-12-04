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
            logger.error("Unicode decode error in SVN output: %s", e)
            raise SVNError(f"Failed to decode SVN output: {e}") from e
        except FileNotFoundError as e:
            # SVN executable not found on PATH
            logger.error("SVN executable not found: %s", e)
            raise SVNError("svn executable not found") from e
        
        if check and result.returncode != 0:
            logger.error(
                "SVN command failed: %s\nSTDOUT: %s\nSTDERR: %s",
                " ".join(full_cmd),
                result.stdout,
                result.stderr,
            )
            raise SVNError(result.stderr.strip() or result.stdout.strip())
        return result

    # ------------------------------------------------------------------
    # Branch operations (SVN branches are directories)
    # ------------------------------------------------------------------
    def get_current_branch(self) -> str:
        """Get the name of the current branch.
        
        For SVN, this returns the last component of the current URL path.
        
        Returns
        -------
        str
            The name of the current branch (e.g., "trunk", "branches/feature").
            
        Raises
        ------
        SVNError
            If unable to determine the current branch.
        """
        result = self._run(["info", "--show-item", "url"], check=True)
        url = result.stdout.strip()
        # Extract branch name from URL (e.g., .../trunk or .../branches/feature)
        if "/trunk" in url:
            return "trunk"
        elif "/branches/" in url:
            return url.split("/branches/")[-1]
        elif "/tags/" in url:
            return url.split("/tags/")[-1]
        else:
            # Return the last component of the URL
            return url.rstrip("/").split("/")[-1]

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists.
        
        For SVN, this is a simplified check that always returns False
        since SVN branch creation is more complex and typically done
        on the server.
        
        Parameters
        ----------
        branch_name : str
            The name of the branch to check.
            
        Returns
        -------
        bool
            Always returns False for SVN.
        """
        # Attempt to detect repository root URL and check if the branch
        # directory exists under the conventional /branches/ path.
        try:
            repos_root = self._get_repository_root_url()
        except SVNError:
            return False

        if not repos_root:
            return False

        branch_url = f"{repos_root.rstrip('/')}/branches/{branch_name}"
        result = self._run(["ls", branch_url], check=False)
        return result.returncode == 0 and bool(result.stdout.strip())

    def create_branch(self, branch_name: str) -> None:
        """Create a new branch.
        
        For SVN, branch creation is not supported in this simple client.
        This method raises an error.
        
        Parameters
        ----------
        branch_name : str
            The name of the branch to create.
            
        Raises
        ------
        SVNError
            Always raised as SVN branch creation is not supported.
        """
        # Create a branch on the SVN server by copying the current URL to
        # the branches/<branch_name> location. This requires server access
        # and write permissions.
        try:
            repos_root = self._get_repository_root_url()
        except SVNError as e:
            raise SVNError("Unable to determine repository root for branch creation") from e

        if not repos_root:
            raise SVNError("Repository root not found; cannot create branch")

        # Construct target branch URL
        branch_url = f"{repos_root.rstrip('/')}/branches/{branch_name}"

        # Get the current working copy URL to copy from
        result = self._run(["info", "--show-item", "url"], check=True)
        current_url = result.stdout.strip()
        if not current_url:
            raise SVNError("Current URL could not be determined for branch creation")

        # Perform server-side copy to create the branch with a message
        self._run(["copy", current_url, branch_url, "-m", f"Create branch {branch_name}"], check=True)

    def _get_repository_root_url(self) -> str:
        """Return the repository root URL (e.g. https://.../svn/project).

        Tries the portable `--show-item repos-root-url` first and falls
        back to parsing `svn info` output.
        """
        # First try the succinct option
        result = self._run(["info", "--show-item", "repos-root-url"], check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

        # Fallback: parse the verbose `svn info` output
        result = self._run(["info"], check=True)
        for line in result.stdout.splitlines():
            if line.lower().startswith("repository root:"):
                return line.split(":", 1)[1].strip()

        raise SVNError("Repository root URL not found in svn info")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def get_changes(self) -> List[FileChange]:
        """Return a list of changes in the working copy relative to BASE.

        Unversioned ("?") and ignored ("I") files are excluded by default.
        """
        result = self._run(["status"], check=True)
        changes: List[FileChange] = []
        for line in result.stdout.splitlines():
            if not line:
                continue
            status_code = line[0]
            path = line[8:].strip()
            # Ignore unversioned and ignored files
            if status_code in ("?", "I"):
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
                # Use --force to skip files that are already versioned
                # This prevents errors when parent directories are already under version control
                self._run(["add", "--force", "--", file], check=True)
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
        
        Raises
        ------
        SVNError
            If files list is empty or commit fails.
        """
        # Validate that we have files to commit
        if not files:
            raise SVNError("Cannot commit: files list is empty")
        
        # Build commit command: specify files and message
        # Note: -- separates options from file paths
        args = ["commit", "-m", message, "--"] + files
        self._run(args, check=True)