import pytest
from types import SimpleNamespace
from pathlib import Path

from vc_commit_helper.vcs.svn_client import SVNClient, SVNError


def make_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_get_changes_ignores_and_unversioned(monkeypatch, tmp_path: Path):
    client = SVNClient(tmp_path)

    # Simulate svn status output: ignored (I), unversioned (?), added (A)
    out = "I       ignored.bin\n?       new.txt\nA       added.txt\nD       removed.txt\n"
    monkeypatch.setattr(client, "_run", lambda args, check=True: make_result(stdout=out))

    # By default unversioned are skipped
    changes_default = client.get_changes()
    paths = [c.path for c in changes_default]
    assert "new.txt" not in paths

    # include_untracked should include new.txt as status 'N'
    changes = client.get_changes(include_untracked=True)
    assert any(c for c in changes if c.path == "new.txt" and c.status == "N")
    # Ensure added and deleted are mapped correctly
    assert any(c for c in changes if c.path == "added.txt" and c.status == "A")
    assert any(c for c in changes if c.path == "removed.txt" and c.status == "D")


def test_get_diff_non_strict(monkeypatch, tmp_path: Path):
    client = SVNClient(tmp_path)
    # Simulate diff returning some text even if file missing
    monkeypatch.setattr(client, "_run", lambda args, check=True: make_result(stdout="svn diff"))
    diff = client.get_diff("somefile.txt")
    assert "svn diff" in diff


def test_stage_files_add_and_delete(monkeypatch, tmp_path: Path):
    client = SVNClient(tmp_path)
    calls = []

    def fake_run(args, check=True):
        calls.append(args)
        return make_result()

    monkeypatch.setattr(client, "_run", fake_run)
    client.stage_files(["a.txt", "d.txt"], statuses={"a.txt": "A", "d.txt": "D"})

    assert any(c for c in calls if c[0] == "add" or (len(c) > 1 and c[1] == "add"))
    assert any(c for c in calls if c[0] == "delete" or (len(c) > 1 and c[1] == "delete"))


def test_commit_builds_args(monkeypatch, tmp_path: Path):
    client = SVNClient(tmp_path)
    recorded = []

    def fake_run(args, check=True):
        recorded.append(args)
        return make_result()

    monkeypatch.setattr(client, "_run", fake_run)
    client.commit("msg", ["one.txt", "two.txt"])
    # commit args should include -m and files
    assert any("commit" in a for a in recorded[0])
    assert "-m" in recorded[0]
    assert "one.txt" in recorded[0] and "two.txt" in recorded[0]
