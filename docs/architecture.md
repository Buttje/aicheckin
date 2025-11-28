# Architecture Overview

This document provides a high‑level overview of the `vc_commit_helper`
project. The goal of the project is to assist developers in creating
well‑structured commit histories by detecting local changes in a Git or
Subversion (SVN) repository, grouping them by purpose, and generating
high‑quality commit messages using a locally hosted Ollama LLM.

## Components

The codebase is organised around several key packages:

### `vc_commit_helper.vcs`

This package contains clients for interacting with version control
systems. The `GitClient` and `SVNClient` classes encapsulate
repository detection, change listing, diff retrieval, staging,
committing and (in the case of Git) pushing. The implementations are
thin wrappers around the respective command line tools. Importantly,
all subprocess invocations are captured so that they can be mocked in
tests.

### `vc_commit_helper.diff`

The diff module extracts unified diffs for changed files using the
VCS client. It returns a mapping from file paths to diff text. This
separation allows the grouping logic to remain agnostic of the
underlying VCS.

### `vc_commit_helper.grouping`

Grouping logic is responsible for deciding which Conventional Commit
type applies to each change and bundling related changes together into
`CommitGroup` objects. Classification currently uses simple
heuristics based on file extensions and keywords in the diff. Each
`CommitGroup` carries its commit type, list of files, diff snippets
and a message to be later confirmed or edited by the user.

### `vc_commit_helper.llm`

This package integrates with the Ollama LLM API. The
`OllamaClient` class handles HTTP communication and error reporting.
`CommitMessageGenerator` orchestrates classification, grouping and
message generation. For each group it constructs a prompt summarising
the diffs, sends it to the LLM and ensures the resulting message
conforms to the Conventional Commits format. If the LLM is
unreachable, a deterministic fallback message is used.

### `vc_commit_helper.config`

Configuration loading is centralised here. The tool expects a
`.ollama_config.json` in the repository root which defines the
server details (base URL, port, model) and optional parameters such
as timeouts and token limits. The loader validates this file and
raises a `ConfigError` on failure.

### `vc_commit_helper.cli`

The command line interface coordinates all other components. When
executed it:

1. Detects whether the current working directory is inside a Git or
   SVN repository and finds the repository root.
2. Loads the Ollama configuration.
3. Lists the local changes, respecting ignore rules and excluding
   untracked files by default.
4. Extracts diffs and passes them to the `CommitMessageGenerator` to
   obtain grouped commit messages.
5. Presents each group to the user, who can accept, edit or decline
   the group. In non‑interactive mode all groups are accepted.
6. Stages the corresponding files and creates a commit for each
   accepted group. For Git repositories the commits are immediately
   pushed to the `origin` remote.
7. Summarises the accepted and declined groups and exits with a
   meaningful exit code.

## Data Flow

The following sequence diagram illustrates the core flow of data and
responsibility:

```
CLI.main
   ├──> detect_vcs() ──┐
   │                  │
   ├──> load_config() │
   │                  │
   ├──> VCSClient.get_changes()
   │                  │
   ├──> extract_diffs()
   │                  │
   ├──> CommitMessageGenerator.generate_groups()
   │         ├─> classify_change()  # heuristic classification
   │         ├─> OllamaClient.generate()  # LLM call
   │         └─> construct CommitGroup objects
   ├──> prompt_user() for each group
   │         ├─> interactive input or accept all in CI mode
   │         └─> optional editing via $EDITOR
   ├──> VCSClient.stage_files()
   ├──> VCSClient.commit()
   └──> (Git only) VCSClient.push()
```

## Design Decisions and Trade‑offs

- **Simplicity vs. granularity**: The current implementation groups
  changes at the file level. A more sophisticated tool might group
  individual hunks, but this increases complexity in staging and
  classification.
- **Heuristic classification**: Without a language model the tool
  falls back to deterministic heuristics for classifying changes. This
  ensures robust behaviour even when the LLM is unavailable.
- **LLM call boundary**: Only the commit message generation relies on
  the LLM. Classification and grouping are kept local to minimise
  reliance on external services.
- **Error handling**: Clear exit codes and messages are provided for
  each failure mode, enabling callers to integrate the tool into
  scripts or CI pipelines.