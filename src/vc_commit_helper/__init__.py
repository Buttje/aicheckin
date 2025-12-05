"""
Top-level package for vc_commit_helper.

This package exposes the main CLI entry point via the
``vc_commit_helper.cli`` module.
"""

from pathlib import Path

__all__ = ["__version__", "__base_version__"]

# Major version - controlled manually by the programmer
__base_version__ = "0"

# Full version - dynamically generated from major.minor.commit_sha
# where minor is from git tags and commit_sha is the current commit
try:
    from vc_commit_helper._version import generate_version
    __version__ = generate_version(__base_version__, Path(__file__).parent.parent.parent)
except Exception:
    # Fallback if version generation fails (e.g., not in a git repo)
    __version__ = f"{__base_version__}.0.0"