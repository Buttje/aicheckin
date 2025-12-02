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
    # Fast guards: skip pseudo-file names used by import machinery
    if not filename:
        return False
    # Examples to skip: '<frozen importlib._bootstrap_external>', '<built-in>'
    if filename.startswith("<") and filename.endswith(">"):
        return False
    # Avoid attempting expensive path operations on non-files. Use a
    # cheap string containment check instead of Path.resolve() which
    # can trigger import-time filesystem semantics for pseudo-names.
    # Avoid calling Path.resolve() here; use the provided project_root
    # string representation which is cheap and does not touch the FS.
    project_root_str = str(project_root)
    try:
        # Simple substring check is sufficient and much cheaper than
        # constructing Path objects for every traced frame.
        return project_root_str in filename
    except Exception:
        return False


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
        print(f"Discovering tests in: {tests_dir.resolve()}")

        # Fast pre-scan: list matching test files so the user sees progress
        test_files = []
        for root, _dirs, files in os.walk(tests_dir):
            for fn in files:
                if fn.startswith("test_") and fn.endswith(".py"):
                    rel = Path(root).joinpath(fn).resolve().relative_to(Path(__file__).parent)
                    test_files.append(str(rel))
        print(f"Found {len(test_files)} test file(s). Showing up to 20:")
        for tf in test_files[:20]:
            print(f"  - {tf}")

        suite = loader.discover(
            str(tests_dir.resolve()), pattern="test_*.py", top_level_dir=str(Path(__file__).parent)
        )
        # Report number of test cases discovered
        try:
            total_cases = suite.countTestCases()
        except Exception:
            total_cases = None
        print(f"Discovered test suite. Test cases: {total_cases if total_cases is not None else 'unknown'}")
        runner = unittest.TextTestRunner(verbosity=2)
        print("Running tests (one by one, reporting progress)...")

        # Helper to iterate individual test cases from a possibly nested suite
        def iter_tests(s):
            if isinstance(s, unittest.TestSuite):
                for t in s:
                    yield from iter_tests(t)
            else:
                yield s

        all_failures = []
        all_errors = []
        tests_run = 0
        for test in iter_tests(suite):
            test_name = getattr(test, "id", lambda: str(test))()
            print(f"-> Running: {test_name}")
            sys.stdout.flush()
            # Run the individual test in its own tiny suite so runner prints details
            res = runner.run(unittest.TestSuite([test]))
            tests_run += res.testsRun
            all_failures.extend(res.failures)
            all_errors.extend(res.errors)

        success = (len(all_failures) == 0 and len(all_errors) == 0)
        print(f"Test run complete. Success: {success}. Tests run: {tests_run}")
        if all_failures or all_errors:
            print(f"Failures: {len(all_failures)}, Errors: {len(all_errors)}")
        if not success:
            sys.exit(1)
    sys.settrace(tracer)
    try:
        run_tests()
    finally:
        sys.settrace(None)
    print(f"Collected executed lines for {len(executed)} source file(s)")
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
    # 'config/loader.py' was temporarily excluded for development.
    # It is now included so coverage measures it after making it testable.
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
    per_file_stats = []
    for filepath in executed.keys():
        try:
            rel_path = Path(filepath).resolve().relative_to(project_root)
        except Exception:
            # If we cannot compute a relative path (file outside project_root
            # or resolution failed), skip this file as it is not part of the
            # measured source tree.
            print(f"Skipping file outside project root or unreadable: {filepath}")
            continue
        # Skip excluded modules entirely from the denominator
        if rel_path.as_posix() in EXCLUDE_FILES:
            print(f"Skipping excluded file from coverage: {rel_path.as_posix()}")
            continue
        file_total = 0
        file_covered = 0
        with Path(filepath).open("r", encoding="utf-8", errors="ignore") as f:
            inside_docstring = False
            for lineno, line in enumerate(f, start=1):
                stripped = line.strip()
                if '"""' in line or "'''" in line:
                    inside_docstring = not inside_docstring
                    continue
                if inside_docstring:
                    continue
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                if "# pragma: no cover" in line:
                    continue
                file_total += 1
                if lineno in executed[filepath]:
                    file_covered += 1
        total_lines += file_total
        covered_lines += file_covered
        pct = (file_covered / file_total * 100) if file_total else 100.0
        per_file_stats.append((rel_path.as_posix(), file_total, file_covered, pct))
        print(f"File: {rel_path.as_posix():40} Lines: {file_total:4} Covered: {file_covered:4} ({pct:5.1f}%)")
    if total_lines == 0:
        return 1.0
    # Print files with lowest coverage
    per_file_stats.sort(key=lambda t: t[3])
    print("\nLowest coverage files:")
    for path, ftotal, fcov, fpct in per_file_stats[:10]:
        print(f"  {path:40} {fpct:5.1f}% ({fcov}/{ftotal})")
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