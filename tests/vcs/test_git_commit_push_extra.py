import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vc_commit_helper.vcs.git_client import GitClient


class DummyProc(SimpleNamespace):
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class TestGitClientCommitPush(unittest.TestCase):
    """Additional tests for commit and push methods of GitClient."""

    def test_commit_and_push_calls_correct_commands(self) -> None:
        calls = []

        def fake_run(self, args, check=True):
            calls.append(args)
            return DummyProc(returncode=0, stdout="", stderr="")

        with patch.object(GitClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            client = GitClient(Path("/repo"))
            # Call commit
            client.commit("message")
            # Call push
            client.push()
        # The first call should be commit, second push
        self.assertIn(["commit", "-m", "message"], calls)
        self.assertIn(["push"], calls)


if __name__ == "__main__":
    unittest.main()