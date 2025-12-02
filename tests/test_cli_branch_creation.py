"""Tests for branch creation functionality."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

import vc_commit_helper.cli as cli
from vc_commit_helper.grouping.group_model import CommitGroup


class DummyGitClient:
    def __init__(self, root):
        self.root = root
        self.changes = []
        self.diffs = {}
        self.staged = []
        self.commits = []
        self.pushed = 0
        self.current_branch = "main"
        self.branches = ["main"]
        self.branch_created = None

    def get_current_branch(self):
        return self.current_branch
    
    def create_branch(self, name):
        self.branches.append(name)
        self.current_branch = name
        self.branch_created = name
    
    def branch_exists(self, name):
        return name in self.branches

    def get_changes(self):
        return self.changes

    def get_changes(self, include_untracked: bool = False):
        return self.changes

    def get_diff(self, path):
        return self.diffs.get(path, "")

    def stage_files(self, files):
        self.staged.append(list(files))

    def commit(self, message, *args):
        self.commits.append(message)

    def push(self, set_upstream=False):
        self.pushed += 1


class DummyGenerator:
    def __init__(self, groups):
        self.groups = groups

    def generate_groups(self, diffs):
        return self.groups


class TestBranchCreation(unittest.TestCase):
    """Tests for branch creation functionality."""

    def test_branch_creation_yes_mode_skips_prompt(self):
        """Test that --yes mode skips branch creation prompt."""
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                
                with patch.object(cli, "GitClient", return_value=dummy):
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: msg", diffs={"a.py": "+change"})
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            result = runner.invoke(cli.main, ["--yes"])
                            self.assertEqual(result.exit_code, cli.EXIT_SUCCESS)
                            # Should not create a new branch
                            self.assertIsNone(dummy.branch_created)
                            self.assertEqual(dummy.current_branch, "main")

    def test_branch_creation_decline(self):
        """Test declining branch creation."""
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                
                with patch.object(cli, "GitClient", return_value=dummy):
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: msg", diffs={"a.py": "+change"})
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            # Simulate user declining branch creation, then accepting commit
                            with patch("click.confirm", return_value=False):
                                with patch.object(cli, "prompt_user", return_value="feat: msg"):
                                    result = runner.invoke(cli.main, [])
                                    self.assertEqual(result.exit_code, cli.EXIT_SUCCESS)
                                    # Should not create a new branch
                                    self.assertIsNone(dummy.branch_created)
                                    self.assertEqual(dummy.current_branch, "main")

    def test_branch_creation_accept(self):
        """Test accepting branch creation."""
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                
                with patch.object(cli, "GitClient", return_value=dummy):
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: msg", diffs={"a.py": "+change"})
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            # Simulate user accepting branch creation
                            with patch("click.confirm", return_value=True):
                                with patch("click.prompt", return_value="feature-branch"):
                                    with patch.object(cli, "prompt_user", return_value="feat: msg"):
                                        result = runner.invoke(cli.main, [])
                                        self.assertEqual(result.exit_code, cli.EXIT_SUCCESS)
                                        # Should create a new branch
                                        self.assertEqual(dummy.branch_created, "feature-branch")
                                        self.assertEqual(dummy.current_branch, "feature-branch")

    def test_branch_already_exists(self):
        """Test handling when branch name already exists."""
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                dummy.branches = ["main", "existing-branch"]
                
                with patch.object(cli, "GitClient", return_value=dummy):
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: msg", diffs={"a.py": "+change"})
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            # Simulate user trying existing branch, then declining retry
                            confirm_calls = [True, False]  # Accept branch creation, then decline retry
                            prompt_calls = ["existing-branch"]  # Try existing branch name
                            
                            with patch("click.confirm", side_effect=confirm_calls):
                                with patch("click.prompt", side_effect=prompt_calls):
                                    with patch.object(cli, "prompt_user", return_value="feat: msg"):
                                        result = runner.invoke(cli.main, [])
                                        self.assertEqual(result.exit_code, cli.EXIT_SUCCESS)
                                        # Should not create a new branch (stayed on main)
                                        self.assertEqual(dummy.current_branch, "main")


if __name__ == "__main__":
    unittest.main()