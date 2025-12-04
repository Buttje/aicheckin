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
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from vc_commit_helper import __version__
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


# ---------------------------------------------------------------------------
# Progress and status display utilities
# ---------------------------------------------------------------------------

class ProgressIndicator:
    """Simple progress indicator for user feedback."""
    
    def __init__(self, message: str, show_spinner: bool = True):
        self.message = message
        self.show_spinner = show_spinner
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        if self.show_spinner:
            click.echo(f"{self.spinner_chars[0]} {self.message}...", nl=False)
        else:
            click.echo(f"→ {self.message}...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if self.show_spinner:
            click.echo(f"\r✓ {self.message} (took {elapsed:.1f}s)")
        else:
            click.echo(f"  ✓ Done ({elapsed:.1f}s)")
        return False
    
    def update(self, message: str):
        """Update the progress message."""
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
        if self.show_spinner:
            click.echo(f"\r{self.spinner_chars[self.spinner_index]} {message}...", nl=False)


def print_step(step_num: int, total_steps: int, message: str):
    """Print a step indicator."""
    click.echo(f"\n{'='*60}")
    click.echo(f"Step {step_num}/{total_steps}: {message}")
    click.echo(f"{'='*60}")


def print_info(message: str, indent: int = 0):
    """Print an info message."""
    prefix = "  " * indent
    click.echo(f"{prefix}ℹ {message}", err=False)


def print_success(message: str, indent: int = 0):
    """Print a success message."""
    prefix = "  " * indent
    click.echo(f"{prefix}✓ {message}", err=False)


def print_warning(message: str, indent: int = 0):
    """Print a warning message."""
    prefix = "  " * indent
    click.echo(f"{prefix}⚠ {message}", err=False)


def print_error(message: str, indent: int = 0):
    """Print an error message."""
    prefix = "  " * indent
    click.echo(f"{prefix}✗ {message}", err=True)


def print_summary_box(title: str, items: List[str]):
    """Print a formatted summary box."""
    max_width = max(len(title), max(len(item) for item in items) if items else 0)
    box_width = min(max_width + 4, 60)
    
    click.echo(f"\n┌{'─' * box_width}┐")
    click.echo(f"│ {title.ljust(box_width - 2)}│")
    click.echo(f"├{'─' * box_width}┤")
    for item in items:
        click.echo(f"│ {item.ljust(box_width - 2)}│")
    click.echo(f"└{'─' * box_width}┘")


# ---------------------------------------------------------------------------
# Core functionality
# ---------------------------------------------------------------------------

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
    with ProgressIndicator("Detecting version control system"):
        git_root = GitClient.find_repo_root(start_dir)
        svn_root = SVNClient.find_repo_root(start_dir)
    
    if git_root and svn_root:
        print_error("Both Git and SVN repository metadata found; ambiguous repository.")
        raise SystemExit(EXIT_NO_REPO)
    if git_root:
        print_success(f"Found Git repository at: {git_root}")
        return "git", git_root
    if svn_root:
        print_success(f"Found SVN repository at: {svn_root}")
        return "svn", svn_root
    
    print_error("No Git or SVN repository found in current directory or parent directories.")
    raise SystemExit(EXIT_NO_REPO)


def prompt_for_branch_creation(client: any, vcs_type: str, yes_mode: bool = False) -> Tuple[bool, str]:
    """Prompt user to create a new branch.
    
    Parameters
    ----------
    client : GitClient or SVNClient
        The VCS client instance.
    vcs_type : str
        The VCS type ('git' or 'svn').
    yes_mode : bool
        If True, skip prompts and use current branch.
        
    Returns
    -------
    Tuple[bool, str]
        (branch_created, branch_name) where branch_created indicates if a new
        branch was created, and branch_name is the name of the branch.
    """
    if yes_mode:
        # In auto-accept mode, don't create a new branch
        current_branch = client.get_current_branch()
        print_info(f"Using current branch: {current_branch}")
        return False, current_branch
    
    try:
        current_branch = client.get_current_branch()
        print_info(f"Current branch: {click.style(current_branch, fg='cyan', bold=True)}")
        
        click.echo("")
        create_branch = click.confirm(
            "   Do you want to create a new branch for these changes?",
            default=False
        )
        
        if not create_branch:
            print_info("Continuing with current branch")
            return False, current_branch
        
        # Prompt for branch name
        while True:
            branch_name = click.prompt(
                "   Enter the name for the new branch",
                type=str
            ).strip()
            
            if not branch_name:
                print_warning("Branch name cannot be empty")
                continue
            
            # Check if branch already exists
            if client.branch_exists(branch_name):
                print_error(f"Branch '{branch_name}' already exists")
                retry = click.confirm("   Try a different name?", default=True)
                if not retry:
                    print_info("Continuing with current branch")
                    return False, current_branch
                continue
            
            # Create the branch
            try:
                with ProgressIndicator(f"Creating branch '{branch_name}'"):
                    client.create_branch(branch_name)
                print_success(f"Created and switched to branch: {branch_name}")
                return True, branch_name
            except (GitError, SVNError) as e:
                print_error(f"Failed to create branch: {e}")
                retry = click.confirm("   Try a different name?", default=True)
                if not retry:
                    print_info("Continuing with current branch")
                    return False, current_branch
                continue
                
    except (GitError, SVNError) as e:
        print_warning(f"Could not determine current branch: {e}")
        print_info("Continuing without branch creation")
        return False, "unknown"


def prompt_user(group: CommitGroup, group_num: int, total_groups: int) -> Optional[str]:
    """Interactively prompt the user about a commit group.

    Parameters
    ----------
    group : CommitGroup
        The commit group to prompt about.
    group_num : int
        Current group number (1-indexed).
    total_groups : int
        Total number of groups.

    Returns
    -------
    Optional[str]
        The final commit message if the group is accepted or edited,
        ``None`` if the group is declined.
    """
    click.echo(f"\n{'─'*60}")
    click.echo(f"📦 Commit Group {group_num}/{total_groups}")
    click.echo(f"{'─'*60}")
    
    click.echo(f"\n🏷️  Type: {click.style(group.type, fg='cyan', bold=True)}")
    
    click.echo(f"\n📄 Affected files ({len(group.files)}):")
    for file in group.files:
        click.echo(f"   • {file}")
    
    click.echo(f"\n💬 Proposed commit message:")
    click.echo("   ┌" + "─" * 56 + "┐")
    for line in group.message.splitlines():
        # Ensure line fits in box (truncate if needed)
        display_line = line[:54] if len(line) > 54 else line
        click.echo(f"   │ {display_line.ljust(54)} │")
    click.echo("   └" + "─" * 56 + "┘")
    
    click.echo("")
    while True:
        choice = click.prompt(
            "   Choose action",
            type=click.Choice(['A', 'E', 'D', 'a', 'e', 'd'], case_sensitive=False),
            default='A',
            show_choices=True,
            show_default=True,
        ).strip().lower()
        
        if choice in {'a', 'accept'}:
            print_success("Accepted commit group")
            return group.message
        
        if choice in {'d', 'decline'}:
            print_warning("Declined commit group")
            return None
        
        if choice in {'e', 'edit'}:
            # Open the user's editor if available
            editor = os.environ.get("EDITOR")
            if editor:
                import tempfile
                import subprocess
                
                print_info("Opening editor...")
                with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt", encoding='utf-8') as tmp:
                    tmp.write(group.message)
                    tmp.flush()
                    tmp_path = tmp.name
                
                try:
                    subprocess.run([editor, tmp_path], check=True)
                    with open(tmp_path, 'r', encoding='utf-8') as f:
                        edited_message = f.read().strip()
                    os.unlink(tmp_path)
                    
                    if edited_message:
                        print_success("Message edited successfully")
                        return edited_message
                    else:
                        print_warning("Empty message, using original")
                        return group.message
                except Exception as e:
                    print_error(f"Editor failed: {e}")
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    continue
            else:
                click.echo("\n   💡 No EDITOR environment variable set.")
                click.echo("   Enter your commit message below.")
                click.echo("   End with a line containing only a period (.)")
                click.echo("")
                
                lines: List[str] = []
                while True:
                    line = click.prompt("   ", default="", show_default=False)
                    if line.strip() == ".":
                        break
                    lines.append(line)
                
                edited = "\n".join(lines).strip()
                if edited:
                    print_success("Message edited successfully")
                    return edited
                else:
                    print_warning("Empty message, using original")
                    return group.message


@click.command()
@click.option("--yes", "yes", is_flag=True, help="Accept all generated commit groups without prompting.")
@click.option("--vcs", type=click.Choice(["git", "svn"]), help="Force the VCS type (git or svn).")
@click.option("--verbose", is_flag=True, help="Enable verbose (debug) output.")
@click.version_option(version=__version__, prog_name="aicheckin")
def main(yes: bool, vcs: Optional[str], verbose: bool) -> None:
    """🚀 AI-powered commit assistant for Git and SVN repositories.
    
    This tool analyzes your changes, groups them logically, and generates
    meaningful commit messages using AI.
    """
    # Configure logging. Use force=True to ensure handlers are reconfigured
    # on subsequent invocations (important for tests).
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
        force=True,
    )
    
    # Print welcome banner
    click.echo("\n" + "="*60)
    click.echo("🤖 AI Commit Assistant".center(60))
    click.echo("="*60)
    
    # Get Click context for proper exit handling
    ctx = click.get_current_context(silent=True)
    
    total_steps = 8  # Increased from 7 to 8 for branch creation step
    current_step = 0
    
    try:
        cwd = Path.cwd()
        
        # Step 1: Detect repository
        current_step += 1
        print_step(current_step, total_steps, "Detecting Repository")
        
        try:
            detected_vcs, repo_root = detect_vcs(cwd) if vcs is None else (vcs, None)
        except SystemExit:
            raise click.exceptions.Exit(EXIT_NO_REPO)
        
        # If the user forced a VCS type, validate and find the repo root
        if vcs is not None:
            with ProgressIndicator(f"Validating {vcs.upper()} repository"):
                if vcs == "git":
                    repo_root = GitClient.find_repo_root(cwd)
                    if not repo_root:
                        print_error("Current directory is not inside a Git repository.")
                        raise click.exceptions.Exit(EXIT_NO_REPO)
                elif vcs == "svn":
                    repo_root = SVNClient.find_repo_root(cwd)
                    if not repo_root:
                        print_error("Current directory is not inside an SVN working copy.")
                        raise click.exceptions.Exit(EXIT_NO_REPO)
            detected_vcs = vcs
            print_success(f"Validated {detected_vcs.upper()} repository at: {repo_root}")
        
        assert repo_root is not None
        logger.debug("Detected VCS: %s, root: %s", detected_vcs, repo_root)
        
        # Step 2: Load configuration
        current_step += 1
        print_step(current_step, total_steps, "Loading Configuration")
        
        try:
            with ProgressIndicator("Reading Ollama configuration"):
                config = load_config(repo_root)
            
            print_success("Configuration loaded successfully")
            print_info(f"LLM Server: {config['base_url']}:{config['port']}", indent=1)
            print_info(f"Model: {config['model']}", indent=1)
            
        except ConfigError as exc:
            print_error(f"Configuration error: {exc}")
            raise click.exceptions.Exit(EXIT_CONFIG_ERROR)
        
        # Step 3: Initialize VCS client
        current_step += 1
        print_step(current_step, total_steps, "Initializing VCS Client")
        
        try:
            with ProgressIndicator(f"Setting up {detected_vcs.upper()} client"):
                client: any
                if detected_vcs == "git":
                    client = GitClient(repo_root)
                else:
                    client = SVNClient(repo_root)
            
            print_success(f"{detected_vcs.upper()} client initialized")
            
        except Exception as exc:
            print_error(f"Failed to initialize VCS client: {exc}")
            raise click.exceptions.Exit(EXIT_GENERIC_ERROR)
        
        # Step 4: Branch creation (new step)
        current_step += 1
        print_step(current_step, total_steps, "Branch Management")
        
        try:
            branch_created, branch_name = prompt_for_branch_creation(client, detected_vcs, yes)
        except (GitError, SVNError) as exc:
            print_error(f"Branch operation failed: {exc}")
            raise click.exceptions.Exit(EXIT_VCS_FAILURE)
        
        # Step 5: Detect changes
        current_step += 1
        print_step(current_step, total_steps, "Analyzing Changes")
        
        try:
            with ProgressIndicator("Scanning for modified files"):
                changes = client.get_changes()
            
            if not changes:
                print_warning("No changes detected to commit.")
                raise click.exceptions.Exit(EXIT_NO_CHANGES)
            
            print_success(f"Found {len(changes)} changed file{'s' if len(changes) != 1 else ''}")
            
            # Show changed files
            for change in changes[:5]:  # Show first 5
                print_info(f"{change.status} {change.path}", indent=1)
            if len(changes) > 5:
                print_info(f"... and {len(changes) - 5} more", indent=1)
            
        except (GitError, SVNError) as exc:
            print_error(f"VCS error: {exc}")
            raise click.exceptions.Exit(EXIT_VCS_FAILURE)
        
        # Step 6: Extract diffs
        current_step += 1
        print_step(current_step, total_steps, "Extracting Diffs")
        
        with ProgressIndicator(f"Reading diffs for {len(changes)} file(s)"):
            diffs = extract_diffs(client, changes)
        
        print_success(f"Extracted diffs for {len(diffs)} file(s)")
        
        # Calculate total diff size
        total_lines = sum(len(diff.splitlines()) for diff in diffs.values())
        print_info(f"Total changes: ~{total_lines} lines", indent=1)
        
        # Step 7: Generate commit groups using LLM
        current_step += 1
        print_step(current_step, total_steps, "Generating Commit Messages")
        
        try:
            with ProgressIndicator("Connecting to LLM server"):
                ollama_client = OllamaClient(
                    base_url=config["base_url"],
                    port=config["port"],
                    model=config["model"],
                    request_timeout=float(config.get("request_timeout", 60)),
                    max_tokens=config.get("max_tokens"),
                )
            
            print_success("Connected to LLM server")
            
            with ProgressIndicator("Analyzing changes and generating messages (this may take a moment)"):
                generator = CommitMessageGenerator(ollama_client)
                groups = generator.generate_groups(diffs)
            
            if not groups:
                print_error("No commit groups were generated.")
                raise click.exceptions.Exit(EXIT_GENERIC_ERROR)
            
            print_success(f"Generated {len(groups)} commit group{'s' if len(groups) != 1 else ''}")
            
            # Show group summary
            for idx, group in enumerate(groups, 1):
                print_info(f"Group {idx}: [{group.type}] - {len(group.files)} file(s)", indent=1)
            
        except LLMError as exc:
            print_error(f"LLM error: {exc}")
            print_info("Make sure Ollama is running and accessible", indent=1)
            raise click.exceptions.Exit(EXIT_LLM_FAILURE)
        
        # Step 8: Review and commit
        current_step += 1
        print_step(current_step, total_steps, "Review and Commit")
        
        accepted_groups: List[Tuple[CommitGroup, str]] = []
        declined_groups: List[CommitGroup] = []
        
        if yes:
            # Non-interactive mode: accept all groups
            print_info("Auto-accept mode enabled - accepting all groups")
            for group in groups:
                accepted_groups.append((group, group.message))
                print_success(f"Auto-accepted: [{group.type}] {len(group.files)} file(s)")
        else:
            # Interactive mode
            click.echo(f"\n📋 Please review {len(groups)} commit group{'s' if len(groups) != 1 else ''}:")
            click.echo(f"   A = Accept | E = Edit | D = Decline\n")
            
            for idx, group in enumerate(groups, start=1):
                message = prompt_user(group, idx, len(groups))
                if message is None:
                    declined_groups.append(group)
                else:
                    accepted_groups.append((group, message))
        
        if not accepted_groups:
            print_warning("All commit groups were declined; no changes committed.")
            raise click.exceptions.Exit(EXIT_ALL_DECLINED)
        
        # Apply each accepted commit group
        click.echo(f"\n{'='*60}")
        click.echo(f"💾 Committing Changes")
        click.echo(f"{'='*60}\n")
        
        for idx, (group, message) in enumerate(accepted_groups, 1):
            try:
                with ProgressIndicator(f"Committing group {idx}/{len(accepted_groups)}: [{group.type}]"):
                    if detected_vcs == "git":
                        # Stage, commit, and push for Git
                        client.stage_files(group.files)
                        client.commit(message)
                        # If we created a new branch, set upstream when pushing
                        client.push(set_upstream=branch_created)
                    else:
                        # For SVN, stage adds/deletes and commit
                        statuses = {change.path: change.status for change in changes if change.path in group.files}
                        client.stage_files(group.files, statuses=statuses)
                        client.commit(message, group.files)
                
                print_success(f"Committed: [{group.type}] {len(group.files)} file(s)")
                
            except (GitError, SVNError) as exc:
                print_error(f"Failed to commit/push changes: {exc}")
                raise click.exceptions.Exit(EXIT_VCS_FAILURE)
        
        # Print final summary
        click.echo(f"\n{'='*60}")
        click.echo(f"✨ Summary")
        click.echo(f"{'='*60}\n")
        
        summary_items = [
            f"✓ Branch: {branch_name}",
            f"✓ Committed: {len(accepted_groups)} group{'s' if len(accepted_groups) != 1 else ''}",
            f"✓ Files changed: {sum(len(g.files) for g, _ in accepted_groups)}",
        ]
        
        if declined_groups:
            summary_items.append(f"⚠ Declined: {len(declined_groups)} group{'s' if len(declined_groups) != 1 else ''}")
        
        for item in summary_items:
            click.echo(f"  {item}")
        
        click.echo(f"\n🎉 All done! Your changes have been committed successfully.\n")
        
        raise click.exceptions.Exit(EXIT_SUCCESS)
        
    except click.exceptions.Exit:
        # Click uses its own Exit exception; re-raise to let Click handle it
        raise
    except Exception as exc:
        # Catch any other unhandled errors
        logging.exception("Unhandled error: %s", exc)
        print_error(f"Unexpected error: {exc}")
        ctx.exit(EXIT_GENERIC_ERROR)