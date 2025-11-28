import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

import vc_commit_helper.cli as cli


class DummyGitClient:
    def __init__(self, root):
        self.root = root
        self.changes = []
        self.diffs = {}
        self.staged = []
        self.commits = []
        self.pushed = 0

    def get_changes(self):
        return self.changes

    def get_diff(self, path):
        return self.diffs.get(path, "")

    def stage_files(self, files):
        self.staged.append(list(files))

    def commit(self, message, *args):
        # Accept extra args for SVN compatibility
        self.commits.append(message)

    def push(self):
        self.pushed += 1


class DummyGenerator:
    def __init__(self, groups):
        self.groups = groups

    def generate_groups(self, diffs):
        return self.groups


class TestCLIMoreFlows(unittest.TestCase):
    """Additional tests to increase coverage of CLI edge cases."""

    def test_cli_config_error(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", side_effect=cli.ConfigError("bad")):
                with patch.object(cli, "GitClient", return_value=DummyGitClient(Path("/repo"))):
                    result = runner.invoke(cli.main, [])
                    self.assertEqual(result.exit_code, cli.EXIT_CONFIG_ERROR)

    def test_cli_vcs_error(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                # Configure client.get_changes to raise GitError
                def raise_error():
                    raise cli.GitError("oops")

                with patch.object(cli, "GitClient", return_value=dummy):
                    with patch.object(dummy, "get_changes", side_effect=cli.GitError("oops")):
                        result = runner.invoke(cli.main, [])
                        self.assertEqual(result.exit_code, cli.EXIT_VCS_FAILURE)

    def test_cli_llm_error(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                with patch.object(cli, "GitClient", return_value=dummy):
                    # Patch CommitMessageGenerator to raise LLMError on generate_groups
                    with patch.object(cli, "CommitMessageGenerator") as mock_gen:
                        mock_instance = mock_gen.return_value
                        mock_instance.generate_groups.side_effect = cli.LLMError("nope")
                        with patch.object(cli, "OllamaClient") as mock_client:
                            result = runner.invoke(cli.main, [])
                            self.assertEqual(result.exit_code, cli.EXIT_LLM_FAILURE)

    def test_cli_no_repo_detect(self) -> None:
        runner = CliRunner()
        # Force detect_vcs to raise SystemExit, causing no repo
        with patch.object(cli, "detect_vcs", side_effect=SystemExit(cli.EXIT_NO_REPO)):
            result = runner.invoke(cli.main, [])
            self.assertEqual(result.exit_code, cli.EXIT_NO_REPO)

    def test_cli_no_groups_generated(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                with patch.object(cli, "GitClient", return_value=dummy):
                    group_list = []  # no groups generated
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator(group_list)):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            result = runner.invoke(cli.main, [])
                            self.assertEqual(result.exit_code, cli.EXIT_GENERIC_ERROR)

    def test_cli_edit_flow(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "detect_vcs", return_value=("git", Path("/repo"))):
            with patch.object(cli, "load_config", return_value={"base_url": "http://", "port": 1, "model": "m"}):
                dummy = DummyGitClient(Path("/repo"))
                dummy.changes = [SimpleNamespace(path="a.py", status="M")]
                dummy.diffs = {"a.py": "+change"}
                with patch.object(cli, "GitClient", return_value=dummy):
                    from vc_commit_helper.grouping.group_model import CommitGroup
                    group = CommitGroup(type="feat", files=["a.py"], message="feat: msg", diffs={"a.py": "+change"})
                    # Always edit message
                    with patch.object(cli, "CommitMessageGenerator", return_value=DummyGenerator([group])):
                        with patch.object(cli, "OllamaClient", return_value=None):
                            with patch.object(cli, "prompt_user", return_value="edited message"):
                                result = runner.invoke(cli.main, [])
                                self.assertEqual(result.exit_code, cli.EXIT_SUCCESS)
                                self.assertEqual(dummy.commits, ["edited message"])
                                self.assertEqual(dummy.pushed, 1)

    def test_cli_force_vcs_invalid_repo(self) -> None:
        runner = CliRunner()
        # Provide --vcs git when not actually in a git repo
        with patch.object(cli, "GitClient", return_value=DummyGitClient(Path("/repo"))):
            with patch.object(cli.GitClient, "find_repo_root", return_value=None):
                result = runner.invoke(cli.main, ["--vcs", "git"])
                self.assertEqual(result.exit_code, cli.EXIT_NO_REPO)


if __name__ == "__main__":
    unittest.main()