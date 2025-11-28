"""
Grouping logic for commit messages.

This package provides functionality to classify changes into commit
types and group them accordingly. See :mod:`vc_commit_helper.grouping.change_classifier`
and :mod:`vc_commit_helper.grouping.group_model` for details.
"""

from .change_classifier import classify_change  # noqa: F401
from .group_model import CommitGroup  # noqa: F401