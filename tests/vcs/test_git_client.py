import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vc_commit_helper.vcs.git_client import FileChange, GitClient


class DummyProc(SimpleNamespace):
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class TestGitClient(unittest.TestCase):
    def test_get_changes_parses_status(self) -> None:
        # Simulate git status --porcelain output
        output = (
            " M modified_file.py\n"
            "A  added_file.py\n"
            "D  deleted_file.py\n"
            "R  renamed_old.py -> renamed_new.py\n"
            "?? untracked.txt\n"
        )

        def fake_run(self, args, check=True):
            # Simulate 'git status --porcelain' call
            if args[0] == "status":
                return DummyProc(returncode=0, stdout=output, stderr="")
            raise AssertionError(f"Unexpected git command: {args}")

        # Patch the _run method and assign our side effect
        with patch.object(GitClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            client = GitClient(Path("/repo"))
            changes = client.get_changes()
            self.assertIn(FileChange(path="modified_file.py", status="M"), changes)
            self.assertIn(FileChange(path="added_file.py", status="A"), changes)
            self.assertIn(FileChange(path="deleted_file.py", status="D"), changes)
            self.assertIn(FileChange(path="renamed_old.py -> renamed_new.py", status="R"), changes)
            self.assertTrue(all(ch.path != "untracked.txt" for ch in changes))

    def test_stage_files_calls_correct_commands(self) -> None:
        calls = []

        def fake_run(self, args, check=True):
            calls.append(args)
            return DummyProc(returncode=0, stdout="", stderr="")

        # Patch the _run method using a mock and assign side effect
        with patch.object(GitClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            tmp_repo = Path("/tmp/repo")
            client = GitClient(tmp_repo)
            # Patch Path.exists to simulate existing and deleted files
            with patch("pathlib.Path.exists", lambda self: self.name != "file_deleted.py"):
                client.stage_files(["file_exists.py", "file_deleted.py"])
        # Expect git add for existing and git rm for deleted
        self.assertIn(["add", "--", "file_exists.py"], calls)
        self.assertIn(["rm", "--", "file_deleted.py"], calls)


if __name__ == "__main__":
    unittest.main()