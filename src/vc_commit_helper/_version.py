"""
Dynamic version generation for vc_commit_helper.

The version is composed of:
- Major version: Manually set in __init__.py (e.g., "0")
- Minor version: Derived from git tags (number of release tags)
- Build number: Git commit short SHA

Format: {major}.{minor}.dev0+g{commit_sha}
Example: 0.5.dev0+g1fbcb8c
"""

import subprocess
from pathlib import Path
from typing import Optional


def get_git_commit_sha(repo_path: Optional[Path] = None) -> str:
    """
    Get the short commit SHA of the current HEAD.
    
    Args:
        repo_path: Path to the repository root. If None, uses current directory.
    
    Returns:
        Short commit SHA (7 characters) or 'unknown' if not in a git repo.
    """
    try:
        if repo_path:
            cmd = ["git", "-C", str(repo_path), "rev-parse", "--short=7", "HEAD"]
        else:
            cmd = ["git", "rev-parse", "--short=7", "HEAD"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_minor_version_from_tags(repo_path: Optional[Path] = None, major_version: str = "0") -> int:
    """
    Get the minor version by counting release tags for the given major version.
    
    Tags should follow the pattern: v{major}.{minor} (e.g., v0.1, v0.2)
    The minor version is the highest minor number found in tags matching the major version.
    
    Args:
        repo_path: Path to the repository root. If None, uses current directory.
        major_version: The major version to filter tags by (default: "0").
    
    Returns:
        The minor version number (0 if no tags found).
    """
    try:
        if repo_path:
            cmd = ["git", "-C", str(repo_path), "tag", "-l", f"v{major_version}.*"]
        else:
            cmd = ["git", "tag", "-l", f"v{major_version}.*"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        tags = result.stdout.strip().split('\n')
        minor_versions = []
        
        for tag in tags:
            if not tag:
                continue
            # Parse tags like v0.1, v0.2, etc. matching the major version
            expected_prefix = f"v{major_version}."
            if tag.startswith(expected_prefix):
                minor_str = tag[len(expected_prefix):]
                try:
                    minor = int(minor_str)
                    minor_versions.append(minor)
                except ValueError:
                    continue
        
        return max(minor_versions) if minor_versions else 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0


def generate_version(base_version: str, repo_path: Optional[Path] = None) -> str:
    """
    Generate the full version string in PEP 440 compliant format.
    
    Args:
        base_version: The base/major version (e.g., "0")
        repo_path: Path to the repository root. If None, uses current directory.
    
    Returns:
        Full version string in format: {major}.{minor}.dev0+g{commit_sha}
        This is PEP 440 compliant as a development release.
    """
    minor = get_minor_version_from_tags(repo_path, base_version)
    commit_sha = get_git_commit_sha(repo_path)
    
    # PEP 440 compliant format using local version identifier
    if commit_sha == "unknown":
        return f"{base_version}.{minor}.dev0"
    else:
        # Use git commit SHA as local version identifier with 'g' prefix
        return f"{base_version}.{minor}.dev0+g{commit_sha}"
