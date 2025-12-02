# aicheckin – AI‑powered VCS commit assistant

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Issues](https://img.shields.io/badge/issues-github-red)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)
![CodeQL Advanced](https://github.com/Buttje/aicheckin/actions/workflows/codeql.yml/badge.svg)](https://github.com/Buttje/aicheckin/actions/workflows/codeql.yml)

## Short description

`aicheckin` is a command‑line tool that helps you create clear,
incremental commit histories from uncommitted changes in your Git or
Subversion (SVN) repository. It leverages a local Ollama LLM to
analyse your changes, classify them into Conventional Commit types
(feat, fix, docs, etc.), group related changes and propose high‑quality
commit messages. You can accept, edit or decline each group
interactively or run in a non‑interactive mode for automation.

## Features

- **Git and SVN support**: Works with both Git and Subversion
  repositories. Automatically detects the VCS type and repository root.
- **AI‑powered messages**: Uses an Ollama LLM to generate commit
  messages that follow the Conventional Commits specification.
- **Grouped commits**: Analyses diffs to group related changes so
  that each commit is focused and descriptive.
- **Interactive flow**: Review each proposed commit, edit the message
  or decline the group. A `--yes` flag allows fully automated
  operation.
- **Robust ignore handling**: Respects `.gitignore` and SVN ignore
  settings. Untracked files are excluded by default.
- **Clear exit codes**: Distinct exit codes for success, no changes,
  configuration errors, VCS errors, LLM/network errors and cases
  where all groups are declined.

## Requirements

- Python **3.10** or newer.
- A working installation of **Git** and/or **Subversion** on your
  system.
- A running **Ollama** server with the desired model installed.

## Installation

1. Create and activate a virtual environment (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows PowerShell
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install the tool system‑wide using `pipx` or `pip`:

   ```bash
   pip install .
   ```

## Configuration

The tool expects a file named `.ollama_config.json` in the root of
your repository. This file defines how to connect to your local
Ollama server. The required keys are:

```json
{
  "base_url": "http://localhost",
  "port": 11434,
  "model": "llama3",
  "request_timeout": 60,
  "max_tokens": 1024
}
```

Only `base_url`, `port` and `model` are required. `request_timeout`
and `max_tokens` are optional. See the sample in `examples/` for a
complete example.

## Quick start

Run the tool from within your repository (or any subdirectory of it):

```bash
python aicheckin.py
```

You can run the tool interactively to review and confirm generated
commit groups, or use `--yes` to accept all proposed groups
non-interactively (useful for automation).

To automatically accept all groups without prompting, use the
`--yes` flag:
```bash
python aicheckin.py --yes
```

To increase verbosity for debugging, use `--verbose`.

## Usage

The following CLI options are supported:

```
Usage: aicheckin [OPTIONS]

Options:
  --yes           Accept all generated commit groups without prompting.
  --vcs [git|svn] Force the VCS type (auto‑detected by default).
  --verbose       Enable verbose (debug) output.
  --help          Show this message and exit.
```

### How it works

1. **Detection** – Starting from the current directory, the tool
   walks up the directory tree to find a `.git` or `.svn` folder. It
   stops when it finds one or reaches the filesystem root. If both
   are present at the same level, it exits with an error. If neither
   is found, it exits with code 3.
2. **Configuration** – The tool looks for `.ollama_config.json` in
   the repository root. If the file is missing or malformed, it
   prints an error and exits with code 5.
3. **Change detection** – It computes the status of your working
   copy against `HEAD` (Git) or `BASE` (SVN). Untracked/unversioned
   files are ignored unless you extend the tool yourself. If no
   changes are found, it exits with code 4.
4. **Diff extraction** – For each changed file, a unified diff is
   obtained via `git diff` or `svn diff`.
5. **Grouping** – The diffs are classified into Conventional Commit
   types using heuristics (file extensions and keywords) and grouped
   accordingly.
6. **LLM message generation** – For each group the tool
   constructs a prompt summarising the changes and calls your
   Ollama server to generate a commit message. If the LLM is
   unreachable or errors, a fallback message is used.
7. **Interactive confirmation** – In interactive mode you are
   shown each group with its proposed message. You may accept the
   message, edit it (either via your `$EDITOR` or inline) or decline
   the group entirely. Declined groups remain uncommitted.
8. **Commit and push** – For each accepted group, files are staged
   (`git add`/`svn add`), a commit is created and (for Git) pushed
   immediately to the `origin` remote.
9. **Summary and exit** – A summary of committed and declined groups
   is printed. Distinct exit codes indicate success or the type of
   failure. See below.

## Exit codes

The tool exits with one of the following codes:

| Code | Meaning                                    |
|----:|---------------------------------------------|
| 0   | Success – commits were created or there were no changes |
| 1   | Generic error (unexpected/unhandled)         |
| 2   | Invalid usage / CLI argument error           |
| 3   | No repository found                          |
| 4   | No changes found to commit                   |
| 5   | Configuration error                          |
| 6   | VCS command failure                          |
| 7   | LLM / network error                          |
| 8   | User declined all commit groups              |

## Architecture overview

The project uses a **src layout** with modular components. See
`docs/architecture.md` for details on how the VCS, diff, grouping,
LLM and CLI modules interact.

## Testing

Install the test dependencies and run pytest:

```bash
pip install -r requirements.txt
pytest -q
```

Optionally generate a coverage report:

```bash
pytest --cov=src --cov-report=term-missing
```

## Limitations and known issues

- The grouping is currently file‑based. If a single file contains
  multiple unrelated changes (e.g. bug fix and new feature), it will
  be classified by the dominant type and committed together.
- The commit type classification uses simple heuristics; it may
  occasionally misclassify changes. You can always edit the proposed
  message.
- The tool relies on a running Ollama server. Network failures or
  misconfiguration will result in fallback messages or aborts.

## Contributing

Contributions are welcome! Please open an issue or a pull request on
GitHub. Ensure your code is well‑tested and adheres to the existing
coding style. For major changes, please discuss them in an issue
first.

## License

This project is licensed under the MIT License. See the `LICENSE`
file for details.

## Changelog

All notable changes are documented in `CHANGELOG.md`.
