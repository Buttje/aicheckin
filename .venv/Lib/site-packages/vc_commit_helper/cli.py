"""
Command line interface for the vc_commit_helper tool.

This module defines the ``main`` function which is used as the entry
point when executing the ``aicheckin`` command. It orchestrates
repository detection, configuration loading, change detection, commit
grouping, interaction with the user, and the actual commit/push
operations. Exit codes are defined in accordance with the specification
in the project README.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from vc_commit_helper.config.loader import ConfigError, load_config
from vc_commit_helper.diff.diff_extractor import extract_diffs
from vc_commit_helper.grouping.group_model import CommitGroup
from vc_commit_helper.llm.commit_message_generator import CommitMessageGenerator
from vc_commit_helper.llm.ollama_client import LLMError, OllamaClient
from vc_commit_helper.vcs.git_client import GitClient, GitError
from vc_commit_helper.vcs.svn_client import SVNClient, SVNError

# Create a module-level logger. Attach a null handler and disable
# propagation to avoid logging errors when the root logger's stream is
# closed (such as during unit tests). When logging is configured by
# the CLI, root handlers will be added and messages will propagate.
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
EXIT_SUCCESS = 0
EXIT_GENERIC_ERROR = 1
EXIT_INVALID_USAGE = 2
EXIT_NO_REPO = 3
EXIT_NO_CHANGES = 4
EXIT_CONFIG_ERROR = 5
EXIT_VCS_FAILURE = 6
EXIT_LLM_FAILURE = 7
EXIT_ALL_DECLINED = 8


def detect_vcs(start_dir: Path) -> Tuple[str, Path]:
    """Detect the VCS type and repository root.

    Parameters
    ----------
    start_dir : Path
        The directory from which to start searching.

    Returns
    -------
    Tuple[str, Path]
        A tuple of (vcs_type, repo_root) where vcs_type is one of
        ``'git'`` or ``'svn'``.

    Raises
    ------
    SystemExit
        With code EXIT_NO_REPO if no repository is found or if both
        repositories are detected.
    """
    git_root = GitClient.find_repo_root(start_dir)
    svn_root = SVNClient.find_repo_root(start_dir)
    if git_root and svn_root:
        click.echo("Error: Both Git and SVN repository metadata found; ambiguous repository.", err=True)
        raise SystemExit(EXIT_NO_REPO)
    if git_root:
        return "git", git_root
    if svn_root:
        return "svn", svn_root
    click.echo("Error: No Git or SVN repository found.", err=True)
    raise SystemExit(EXIT_NO_REPO)


def prompt_user(group: CommitGroup) -> Optional[str]:
    """Interactively prompt the user about a commit group.

    Parameters
    ----------
    group : CommitGroup
        The commit group to prompt about.

    Returns
    -------
    Optional[str]
        The final commit message if the group is accepted or edited,
        ``None`` if the group is declined.
    """
    click.echo("")
    click.echo(f"Commit type: {group.type}")
    click.echo("Affected files:")
    for file in group.files:
        click.echo(f"  - {file}")
    click.echo("\nProposed commit message:")
    click.echo(group.message)
    click.echo("")
    while True:
        choice = click.prompt(
            "Accept (A), Edit (E), or Decline (D)?",
            type=str,
            default="A",
            show_default=True,
        ).strip().lower()
        if choice in {"a", "accept"}:
            return group.message
        if choice in {"d", "decline"}:
            return None
        if choice in {"e", "edit"}:
            # Open the user's editor if available
            editor = os.environ.get("EDITOR")
            if editor:
                import tempfile
                import subprocess
                with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
                    tmp.write(group.message)
                    tmp.flush()
                    subprocess.run([editor, tmp.name])
                    tmp.seek(0)
                    edited_message = tmp.read().strip()
                return edited_message
            else:
                click.echo(
                    "Enter the commit message. End the input with a single line containing only a period (.)"
                )
                lines: List[str] = []
                while True:
                    line = click.prompt("", default="", show_default=False)
                    if line.strip() == ".":
                        break
                    lines.append(line)
                edited = "\n".join(lines).strip()
                return edited if edited else group.message
        # Otherwise ask again
        click.echo("Invalid choice. Please enter A, E, or D.")


@click.command()
@click.option("--yes", "yes", is_flag=True, help="Accept all generated commit groups without prompting.")
@click.option("--vcs", type=click.Choice(["git", "svn"]), help="Force the VCS type (git or svn).")
@click.option("--verbose", is_flag=True, help="Enable verbose (debug) output.")
def main(yes: bool, vcs: Optional[str], verbose: bool) -> None:
    """Entry point for the aicheckin command.

    This function implements the complete workflow defined in the
    specification. It uses Click's context to exit with specific codes.
    """
    # Configure logging. Use force=True to ensure handlers are reconfigured
    # on subsequent invocations (important for tests).
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        force=True,
    )
    # Get Click context for proper exit handling
    ctx = click.get_current_context(silent=True)
    try:
        cwd = Path.cwd()
        # Detect repository type and root
        try:
            detected_vcs, repo_root = detect_vcs(cwd) if vcs is None else (vcs, None)
        except SystemExit:
            # detect_vcs already emitted an error message and raised
            raise click.exceptions.Exit(EXIT_NO_REPO)
        # If the user forced a VCS type, validate and find the repo root
        if vcs is not None:
            if vcs == "git":
                repo_root = GitClient.find_repo_root(cwd)
                if not repo_root:
                    click.echo("Error: Current directory is not inside a Git repository.", err=True)
                    raise click.exceptions.Exit(EXIT_NO_REPO)
            elif vcs == "svn":
                repo_root = SVNClient.find_repo_root(cwd)
                if not repo_root:
                    click.echo("Error: Current directory is not inside an SVN working copy.", err=True)
                    raise click.exceptions.Exit(EXIT_NO_REPO)
            detected_vcs = vcs
        assert repo_root is not None
        logger.debug("Detected VCS: %s, root: %s", detected_vcs, repo_root)
        # Load configuration
        try:
            config = load_config(repo_root)
        except ConfigError as exc:
            click.echo(f"Configuration error: {exc}", err=True)
            raise click.exceptions.Exit(EXIT_CONFIG_ERROR)
        # Instantiate the appropriate VCS client
        try:
            client: any
            if detected_vcs == "git":
                client = GitClient(repo_root)
            else:
                client = SVNClient(repo_root)
        except Exception as exc:
            click.echo(f"Failed to initialize VCS client: {exc}", err=True)
            raise click.exceptions.Exit(EXIT_GENERIC_ERROR)
        # Detect changes
        try:
            changes = client.get_changes()
        except (GitError, SVNError) as exc:
            click.echo(f"VCS error: {exc}", err=True)
            raise click.exceptions.Exit(EXIT_VCS_FAILURE)
        if not changes:
            click.echo("No changes detected to commit.")
            raise click.exceptions.Exit(EXIT_NO_CHANGES)
        # Extract diffs
        diffs = extract_diffs(client, changes)
        # Generate commit groups using LLM
        try:
            ollama_client = OllamaClient(
                base_url=config["base_url"],
                port=config["port"],
                model=config["model"],
                request_timeout=float(config.get("request_timeout", 60)),
                max_tokens=config.get("max_tokens"),
            )
            generator = CommitMessageGenerator(ollama_client)
            groups = generator.generate_groups(diffs)
        except LLMError as exc:
            click.echo(f"LLM error: {exc}", err=True)
            raise click.exceptions.Exit(EXIT_LLM_FAILURE)
        if not groups:
            click.echo("No commit groups were generated.")
            raise click.exceptions.Exit(EXIT_GENERIC_ERROR)
        # Handle interactive or non-interactive commit flow
        accepted_groups: List[Tuple[CommitGroup, str]] = []
        declined_groups: List[CommitGroup] = []
        if yes:
            # Non-interactive mode: accept all groups
            for group in groups:
                accepted_groups.append((group, group.message))
        else:
            click.echo(f"Found {len(groups)} commit group{'s' if len(groups) != 1 else ''}.")
            for idx, group in enumerate(groups, start=1):
                click.echo("\n" + "=" * 60)
                click.echo(f"Group {idx}/{len(groups)}")
                message = prompt_user(group)
                if message is None:
                    declined_groups.append(group)
                else:
                    accepted_groups.append((group, message))
        if not accepted_groups:
            click.echo("All commit groups were declined; no changes committed.")
            raise click.exceptions.Exit(EXIT_ALL_DECLINED)
        # Apply each accepted commit group
        for group, message in accepted_groups:
            try:
                if detected_vcs == "git":
                    # Stage, commit, and push for Git
                    client.stage_files(group.files)
                    client.commit(message)
                    client.push()
                else:
                    # For SVN, stage adds/deletes and commit
                    statuses = {change.path: change.status for change in changes if change.path in group.files}
                    client.stage_files(group.files, statuses=statuses)
                    client.commit(message, group.files)
            except (GitError, SVNError) as exc:
                click.echo(f"Failed to commit/push changes: {exc}", err=True)
                raise click.exceptions.Exit(EXIT_VCS_FAILURE)
        # Print summary
        click.echo("\nSummary:")
        click.echo(f"Committed {len(accepted_groups)} group{'s' if len(accepted_groups) != 1 else ''}.")
        if declined_groups:
            click.echo(f"Declined {len(declined_groups)} group{'s' if len(declined_groups) != 1 else ''}.")
        raise click.exceptions.Exit(EXIT_SUCCESS)
    except click.exceptions.Exit:
        # Click uses its own Exit exception; re-raise to let Click handle it
        raise
    except Exception as exc:
        # Catch any other unhandled errors
        logging.exception("Unhandled error: %s", exc)
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(EXIT_GENERIC_ERROR)