import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vc_commit_helper.vcs.svn_client import FileChange, SVNClient


class DummyProc(SimpleNamespace):
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class TestSVNClient(unittest.TestCase):
    def test_get_changes_parses_status(self) -> None:
        output = (
            "M       modified_file.txt\n"
            "A       added_file.txt\n"
            "D       deleted_file.txt\n"
            "?       unversioned.txt\n"
        )

        def fake_run(self, args, check=True):
            if args[0] == "status":
                return DummyProc(returncode=0, stdout=output, stderr="")
            raise AssertionError(f"Unexpected svn command: {args}")

        # Patch the _run method using a mock and assign side effect
        with patch.object(SVNClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            client = SVNClient(Path("/repo"))
            changes = client.get_changes()
            self.assertIn(FileChange(path="modified_file.txt", status="M"), changes)
            self.assertIn(FileChange(path="added_file.txt", status="A"), changes)
            self.assertIn(FileChange(path="deleted_file.txt", status="D"), changes)
            self.assertTrue(all(ch.path != "unversioned.txt" for ch in changes))

    def test_stage_and_commit(self) -> None:
        calls = []

        def fake_run(self, args, check=True):
            calls.append(args)
            return DummyProc(returncode=0, stdout="", stderr="")

        with patch.object(SVNClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            client = SVNClient(Path("/repo"))
            statuses = {"new.txt": "A", "gone.txt": "D"}
            client.stage_files(["new.txt", "changed.txt", "gone.txt"], statuses=statuses)
            # After staging, expect add and delete calls
            self.assertIn(["add", "--", "new.txt"], calls)
            self.assertIn(["delete", "--", "gone.txt"], calls)
            calls.clear()
            client.commit("message", ["file1.txt", "file2.txt"])
            self.assertIn(["commit", "-m", "message", "--", "file1.txt", "file2.txt"], calls)

    def test_commit_with_empty_files_list_raises_error(self) -> None:
        """Test that commit raises SVNError when files list is empty."""
        from vc_commit_helper.vcs.svn_client import SVNError
        
        client = SVNClient(Path("/repo"))
        with self.assertRaises(SVNError) as cm:
            client.commit("Test message", [])
        
        self.assertIn("files list is empty", str(cm.exception))

    def test_commit_with_multiline_message(self) -> None:
        """Test that commit works with multiline messages."""
        calls = []

        def fake_run(self, args, check=True):
            calls.append(args)
            return DummyProc(returncode=0, stdout="", stderr="")

        with patch.object(SVNClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            client = SVNClient(Path("/repo"))
            
            multiline_msg = "First line\nSecond line\nThird line"
            client.commit(multiline_msg, ["file1.txt"])
            
            # Verify the command was constructed correctly
            self.assertEqual(calls[-1], ["commit", "-m", multiline_msg, "--", "file1.txt"])

    def test_commit_with_special_characters(self) -> None:
        """Test that commit works with special characters in message."""
        calls = []

        def fake_run(self, args, check=True):
            calls.append(args)
            return DummyProc(returncode=0, stdout="", stderr="")

        with patch.object(SVNClient, "_run", autospec=True) as mock_run:
            mock_run.side_effect = fake_run
            client = SVNClient(Path("/repo"))
            
            special_msg = "Fix: <tag> & 'quotes' \"and\" $vars"
            client.commit(special_msg, ["file1.txt", "file2.txt"])
            
            # Verify the command was constructed correctly
            self.assertEqual(calls[-1], ["commit", "-m", special_msg, "--", "file1.txt", "file2.txt"])


if __name__ == "__main__":
    unittest.main()