"""
Version control system (VCS) integrations.

This package contains abstractions and concrete clients for interacting
with Git and Subversion (SVN) repositories. Each client exposes
methods for detecting repository roots, listing local changes, staging
changes, committing, and pushing.
"""

from .git_client import GitClient  # noqa: F401
from .svn_client import SVNClient  # noqa: F401