# Contributing to aicheckin

Thank you for your interest in contributing! We welcome bug reports, small
fixes, documentation improvements, tests, and new features. This file describes
how to get started and what we look for in contributions.

## Getting started

1. Fork the repository on GitHub and clone your fork locally.
2. Create a branch for your change: `git checkout -b feat/my-change`.
3. Make small, focused commits with clear messages. We follow
   Conventional Commits (e.g. `feat: add X`, `fix: correct Y`).
4. Run tests and linters before opening a pull request.

## Run tests

Install test requirements and run the test suite locally:

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate    # Windows (PowerShell)
pip install -r requirements.txt
pytest -q
```

If you prefer not to install, set `PYTHONPATH=src` and run `pytest`.

## Writing tests

- Add tests for any new behavior or bug fixes.
- Use `pytest` and the existing fixtures in `tests/`.
- Mock external programs and system effects (network, registry, package
  manager) so tests are deterministic and safe to run in CI.

## Coding style

- Follow the existing code style in the repository. Keep changes focused and
  avoid large unrelated refactors in the same PR.
- Use type hints where practical and keep function/variable names descriptive.

## Submitting a pull request

1. Push your branch to your fork and open a PR against `main`.
2. Provide a clear title and description. Explain the motivation and
   include before/after examples where applicable.
3. Add tests that demonstrate the behavior and ensure CI passes.
4. If your change is large, open an issue first to discuss scope and design.

## Review process

Maintainers will review PRs, request changes, or merge. Be responsive to
feedback and iterate on your PR. If you don't hear back after a week, a polite
reminder is fine.

## Security and sensitive issues

For security problems, do not open a public issue. Contact the maintainers
privately (email or the repository owner) and follow responsible disclosure.

## Code of conduct

We expect contributors to follow a respectful and collaborative code of
conduct. If the repository includes a `CODE_OF_CONDUCT.md`, please follow it.

## Contacts

Project maintainer: Buttje
Repository: https://github.com/Buttje/aicheckin
