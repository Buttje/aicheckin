#!/usr/bin/env python
"""
Thin wrapper script to invoke the vc_commit_helper CLI.

Running ``python aicheckin.py`` is equivalent to running the
``aicheckin`` console script installed via ``pyproject.toml``.
"""

from vc_commit_helper.cli import main


if __name__ == "__main__":
    main(prog_name="aicheckin")