from click.testing import CliRunner
from types import SimpleNamespace
from pathlib import Path
import importlib
import json


cli = importlib.import_module("vc_commit_helper.cli")
grouping = importlib.import_module("vc_commit_helper.grouping.group_model")


def test_cli_main_yes(monkeypatch, tmp_path):
    runner = CliRunner()

    # Mock configuration loader
    monkeypatch.setattr(cli, "load_config", lambda repo_root=None: {
        "base_url": "http://localhost",
        "port": 11434,
        "model": "llama3",
        "request_timeout": 60,
    })

    # Fake GitClient
    class FakeGitClient:
        @staticmethod
        def find_repo_root(start):
            return tmp_path

        def __init__(self, root):
            self.root = root

        def get_current_branch(self):
            return "main"

        def get_changes(self, include_untracked=False):
            return [SimpleNamespace(path="file1.py", status="M")]

        def stage_files(self, files, statuses=None):
            return None

        def commit(self, message, files=None):
            return None

        def push(self, set_upstream=False):
            return None

    monkeypatch.setattr(cli, "GitClient", FakeGitClient)

    # Mock diffs extraction
    monkeypatch.setattr(cli, "extract_diffs", lambda client, changes: {"file1.py": "-old+new"})

    # Mock Ollama and generator
    class FakeGenerator:
        def __init__(self, client):
            pass

        def generate_groups(self, diffs):
            g = grouping.CommitGroup(type="feat", files=["file1.py"], message="Add feature")
            return [g]

    monkeypatch.setattr(cli, "CommitMessageGenerator", lambda c: FakeGenerator(c))
    monkeypatch.setattr(cli, "OllamaClient", lambda **kw: object())

    result = runner.invoke(cli.main, ["--yes", "--vcs", "git"])
    assert result.exit_code == 0
