# aicheckin — AI-powered commit assistant

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-blue)](https://pytest.org)
[![GitHub Actions](https://github.com/Buttje/aicheckin/actions/workflows/python-package.yml/badge.svg)](https://github.com/Buttje/aicheckin/actions)
[![Codecov](https://codecov.io/gh/Buttje/aicheckin/branch/main/graph/badge.svg)](https://codecov.io/gh/Buttje/aicheckin)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)](https://github.com/Buttje/aicheckin)

Short, practical tool to create clear, incremental commit histories using an
LLM. It analyzes uncommitted changes in Git or SVN working copies, groups
related edits, and proposes Conventional-Commit‑style messages you can accept,
edit or decline.

--

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Installer](#installer)
- [Development & Tests](#development--tests)
- [Contributing](#contributing)
- [License](#license)

## Features

- Support for Git and Subversion (SVN) with automatic repository detection.
- AI-generated Conventional Commit messages (via a local Ollama LLM).
- Groups related changes into focused commit units.
- Interactive review: accept / edit / decline, or run non-interactively
  with `--yes`.
- Installer script can detect common package managers and attempt to
  install system dependencies (best-effort).

## Quick Start

Prerequisites:

- Python 3.10 or newer
- Git and/or Subversion installed (installer can help where supported)
- A running Ollama server and model (see [Configuration](#configuration))

Run from inside a repository (or a subdirectory):

```bash
# development (recommended)
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.venv\Scripts\activate     # Windows (PowerShell)
pip install -e .[test]

# run tool (normal use)
python -m vc_commit_helper.cli

# or with auto-accept
python -m vc_commit_helper.cli --yes
```

If you prefer not to install, tests and the CLI can be run by setting
`PYTHONPATH` to `src/`:

Windows (cmd.exe):

```cmd
set PYTHONPATH=src
pytest -q
```

Windows (PowerShell):

```powershell
$env:PYTHONPATH = 'src'
pytest -q
```

## Configuration

The tool expects an Ollama connection configuration JSON. Preferred location:

```
~/.ollama_server/.ollama_config.json
```

Minimum required keys:

```json
{
  "base_url": "http://localhost",
  "port": 11434,
  "model": "llama3"
}
```

Optional keys: `request_timeout`, `max_tokens`.

During installation, `install.py` will create `~/.ollama_server` and write an
example config if none exists. If a home-level config is present it will be
preferred over a package-adjacent config file.

## Usage

Basic invocation (interactive):

```bash
python -m vc_commit_helper.cli
```

Options:

```
--yes           Accept all generated commit groups without prompting
--vcs [git|svn] Force VCS type (auto-detected by default)
--verbose       Enable debug output
```

High-level flow:

1. Detect repository (Git or SVN)
2. Load Ollama config
3. Find and classify changes
4. Extract diffs and group related changes
5. Generate commit messages via the LLM
6. Review and commit (stage/commit/push for Git, commit for SVN)

Exit codes are documented in `README.md` and the CLI source; they indicate
success, no repo, no changes, config problems, VCS errors, LLM errors, or
all-declined outcomes.

## Installer

`install.py` attempts an editable install and can help install missing system
tools (git, svn) using a detected package manager (`apt`, `dnf`, `pacman`,
`zypper`, `brew`, `choco`, `winget`) on supported platforms. Ollama itself is
platform-specific and is not installed automatically — the installer prints
links and guidance.

Run installer (auto-confirm):

```cmd
python install.py --yes
```

If automatic installation is not possible the script prints manual steps.

## Development & Tests

Run the full test suite locally:

```bash
pip install -r requirements.txt
pytest -q
```

Generate coverage report:

```bash
pytest --cov=src --cov-report=term-missing
```

Notes:

- Tests mock external programs and system effects where appropriate to avoid
  changing the host system (registry edits, package installs).

## Contributing

Contributions are welcome. Good first steps:

- Open an issue to discuss major changes.
- Follow the repository coding style and include tests for new behaviour.
- Keep changes focused and open a PR with a clear description and tests.

See `CONTRIBUTING.md` (if present) for more guidance.

## License

This project is licensed under the MIT License — see the `LICENSE` file.

## Contact

Maintainer: Buttje
Project: https://github.com/Buttje/aicheckin
# aicheckin – AI‑powered VCS commit assistant

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Issues](https://img.shields.io/badge/issues-github-red)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)

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
   settings. Untracked files are detected and presented to the user
   (ignored files are skipped according to the VCS ignore rules).
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

Developer setup (editable install and tests)
-------------------------------------------

If you're developing or running the test suite locally, install the package in "editable" mode
so that changes in `src/` are immediately visible to Python. Also install test dependencies.

Windows (cmd.exe):

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -e .[test]
```

Windows (PowerShell):

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -e .[test]
```

Alternative (without installing): set `PYTHONPATH` so tests can import the package from `src/`:

Windows (cmd.exe):

```cmd
set PYTHONPATH=src
python -m pytest -q
```

Windows (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```

## Configuration

The preferred location for configuration is a user-level directory in
your home folder: `~/.ollama_server/.ollama_config.json`. The
installer will create `~/.ollama_server` and write an example
`.ollama_config.json` there during installation. The tool will use the
home-level configuration if present; otherwise it falls back to a
config file adjacent to the installed package.

The configuration file defines how to connect to your local
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

The tool will detect your VCS, load the Ollama configuration, find
uncommitted changes and propose commit groups with messages. You will
be prompted to accept, edit or decline each group. When accepted,
changes will be staged, committed and pushed (Git) or committed
(SVN).

To automatically accept all groups without prompting, use the
`--yes` flag:

```bash
python aicheckin.py --yes
```

To increase verbosity for debugging, use `--verbose`.

### Installer behavior

The provided `install.py` script detects the host operating system and
attempts to help you install system dependencies (Git and Subversion)
using a detected package manager when available (e.g. `apt`, `dnf`,
`pacman`, `brew`, `choco`, `winget`). Ollama is platform-specific and is
not installed automatically; the installer provides links and guidance.

To run the installer and auto-confirm prompts, use:

```cmd
python install.py --yes
```

If the installer cannot install a missing dependency automatically
it will print instructions for manual installation.

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
pytest --cov=vc_commit_helper --cov-report=term-missing
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