import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

import vc_commit_helper.cli as cli


class DummyGitClient:
    def __init__(self, root):
        self.root = root
        self.stage_called = []
        self.commit_called = []
        self.push_called = 0
        self.changes = []
        self.diffs = {}
        self.current_branch = "main"
        self.branches = ["main"]
        
    def get_current_branch(self):
        return self.current_branch
    
    def create_branch(self, name):
        self.branches.append(name)
        self.current_branch = name
    
    def branch_exists(self, name):
        return name in self.branches
    
    def get_changes(self, include_untracked: bool = False):
        return self.changes
    
    def get_diff(self, path):
        return self.diffs.get(path, "")
    
    def stage_files(self, files):
        self.stage_called.append(list(files))
    
    def commit(self, message, *args):  # accept extra args for SVN compatibility
        self.commit_called.append(message)
    
    def push(self, set_upstream=False):
        self.push_called += 1


class DummyGenerator:
    def __init__(self, groups):
        self.groups = groups
    
    def generate_groups(self, diffs):
        return self.groups


class TestCLI(unittest.TestCase):
    def test_cli_no_changes(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = []
                with patch.object(cli, "GitClient", return_value=dummy):
                    result = runner.invoke(cli.main, [])
                    self.assertEqual(result.exit_code, cli.EXIT_NO_CHANGES)

    def test_cli_yes_flow_git(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+def foo():\n"}
                with patch.object(cli, "GitClient", return_value=dummy):
                    from vc_commit_helper.grouping.group_model import CommitGroup
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: add foo", diffs={"a.py": "+def foo():\n"})
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            result = runner.invoke(cli.main, ["--yes"])
                            self.assertEqual(result.exit_code, cli.EXIT_SUCCESS)
                            self.assertEqual(dummy.stage_called, [["a.py"]])
                            self.assertEqual(dummy.commit_called, ["feat: add foo"])
                            self.assertEqual(dummy.push_called, 1)

    def test_cli_all_declined(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change\n"}
                with patch.object(cli, "GitClient", return_value=dummy):
                    from vc_commit_helper.grouping.group_model import CommitGroup
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: msg", diffs={"a.py": "+change\n"})
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            # Patch prompt_user to always decline
                            with patch.object(cli, "prompt_user", return_value=None):
                                result = runner.invoke(cli.main, [])
                                self.assertEqual(result.exit_code, cli.EXIT_ALL_DECLINED)


if __name__ == "__main__":
    unittest.main()