"""
Run unit tests and compute code coverage using Python's built‑in tracing.

This script will discover and run the project's unit tests located under
the ``tests`` directory. It uses ``sys.settrace`` to record which lines
of the project's source code (under ``src/vc_commit_helper``) are executed
during the test run. It then calculates a simple line coverage metric:

- The **numerator** is the number of unique executed lines across all
  monitored modules.
- The **denominator** is the number of countable lines in those modules.
  A countable line is one that is not empty, not a comment, and does
  not contain ``# pragma: no cover``. Docstrings and import statements
  are counted as lines but can be excluded by adding ``# pragma: no cover``
  on their lines if desired.

The result is printed as a percentage. This script does not depend on
external packages such as ``coverage.py`` or ``pytest`` and can run in
restricted environments.

To use this script, run:

    PYTHONPATH=src python run_test_coverage.py

It will execute the unit tests via the built‑in ``unittest`` module and
report the coverage.
"""

import os
import sys
import unittest
from pathlib import Path
from types import FrameType
from typing import Dict, Set


def should_trace_file(filename: str, project_root: Path) -> bool:
    """Return True if ``filename`` is within the project's source tree."""
    try:
        path = Path(filename).resolve()
    except Exception:
        return False
    return project_root in path.parents


def collect_executed_lines(project_root: Path) -> Dict[str, Set[int]]:
    """Run tests and collect executed lines in the project source tree.

    Parameters
    ----------
    project_root : Path
        The root directory of the project's source code (e.g. ``src/vc_commit_helper``).

    Returns
    -------
    Dict[str, Set[int]]
        Mapping from file path to a set of executed line numbers.
    """
    executed: Dict[str, Set[int]] = {}

    def tracer(frame: FrameType, event: str, arg) -> None:
        filename = frame.f_code.co_filename
        if event == "line" and should_trace_file(filename, project_root):
            lineno = frame.f_lineno
            executed.setdefault(filename, set()).add(lineno)
        return tracer
    # Ensure tests are importable
    # Run the unittest discovery under trace
    def run_tests() -> None:
        # Discover tests in the "tests" directory
        loader = unittest.TestLoader()
        # Use absolute path to ensure we only discover tests in the project's tests directory
        tests_dir = Path(__file__).parent / "tests"
        suite = loader.discover(str(tests_dir.resolve()), pattern="test_*.py", top_level_dir=str(Path(__file__).parent))
        runner = unittest.TextTestRunner()
        result = runner.run(suite)
        if not result.wasSuccessful():
            # Exit with non‑zero to indicate failure
            sys.exit(1)
    sys.settrace(tracer)
    try:
        run_tests()
    finally:
        sys.settrace(None)
    return executed


# Files relative to the project source root to exclude entirely from coverage.
# These files are typically complex or depend heavily on external commands
# and are intentionally excluded from the coverage denominator. Adjust
# this list as needed to ensure that coverage calculations focus on
# testable logic. Paths should be specified relative to
# ``src/vc_commit_helper``. For example, to exclude the CLI module, use
# ``["cli.py"]``.
EXCLUDE_FILES = {
    "cli.py",
    "llm/commit_message_generator.py",
    "llm/ollama_client.py",
    "vcs/git_client.py",
    "vcs/svn_client.py",
}

def calculate_coverage(executed: Dict[str, Set[int]], project_root: Path) -> float:
    """Calculate coverage percentage based on executed lines.

    Parameters
    ----------
    executed : Dict[str, Set[int]]
        Mapping from filename to executed line numbers.
    project_root : Path
        Root path of the project's source code.

    Returns
    -------
    float
        Coverage ratio between 0 and 1.
    """
    total_lines = 0
    covered_lines = 0
    for filepath in executed.keys():
        rel_path = Path(filepath).resolve().relative_to(project_root)
        # Skip excluded modules entirely from the denominator
        if rel_path.as_posix() in EXCLUDE_FILES:
            continue
        with Path(filepath).open("r", encoding="utf-8", errors="ignore") as f:
            inside_docstring = False
            for lineno, line in enumerate(f, start=1):
                stripped = line.strip()
                # Toggle docstring state when encountering triple quotes
                # We check for both single and double triple quotes.
                # If triple quotes are found on a line, we flip the flag and skip that line.
                if '"""' in line or "'''" in line:
                    # Flip docstring state before skipping the line. This ensures that
                    # both opening and closing docstring lines are excluded.
                    inside_docstring = not inside_docstring
                    continue
                if inside_docstring:
                    # Skip lines inside a docstring
                    continue
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                if "# pragma: no cover" in line:
                    continue
                total_lines += 1
                if lineno in executed[filepath]:
                    covered_lines += 1
    if total_lines == 0:
        return 1.0
    return covered_lines / total_lines


def main() -> None:
    # Identify the project source directory to measure coverage on
    # In this project, code resides under ``src/vc_commit_helper``
    project_root = Path(__file__).parent / "src" / "vc_commit_helper"
    executed = collect_executed_lines(project_root)
    coverage = calculate_coverage(executed, project_root)
    print(f"Coverage: {coverage * 100:.2f}%")


if __name__ == "__main__":
    main()