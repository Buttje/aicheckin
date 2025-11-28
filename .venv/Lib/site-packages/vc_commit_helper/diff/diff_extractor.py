"""
Diff extraction utilities.

This module defines functions for obtaining diffs for modified files in
Git and SVN repositories. The callers provide a VCS client that
implements ``get_diff`` on individual files and a list of file
changes. The extractor returns a mapping of file paths to their diff
text.
"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional

from vc_commit_helper.vcs.git_client import FileChange as GitFileChange
from vc_commit_helper.vcs.svn_client import FileChange as SVNFileChange


def extract_diffs(
    vcs_client: any,
    changes: Iterable[object],
) -> Dict[str, str]:
    """Extract unified diffs for a list of file changes.

    Parameters
    ----------
    vcs_client : object
        The VCS client instance. Must implement ``get_diff(file_path)``.
    changes : Iterable[object]
        Iterable of file change objects. Each object must have a
        ``path`` attribute.

    Returns
    -------
    Dict[str, str]
        Mapping from file path to the diff text.
    """
    diffs: Dict[str, str] = {}
    for change in changes:
        # Only compute diffs for files that still exist or that were
        # modified. Deleted files produce empty diffs.
        file_path = change.path  # type: ignore[attr-defined]
        try:
            diff = vcs_client.get_diff(file_path)
        except Exception:
            # In case diff cannot be obtained (e.g. file deleted),
            # store empty diff. The classification heuristics can
            # still operate based on the file name.
            diff = ""
        diffs[file_path] = diff
    return diffs