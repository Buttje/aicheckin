import pytest
from types import SimpleNamespace
from pathlib import Path

from vc_commit_helper.vcs.git_client import GitClient, GitError


def make_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_find_repo_root_and_is_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    client = GitClient(repo)
    assert GitClient.is_repo(repo)
    # find from nested path
    nested = repo / "sub" / "dir"
    nested.mkdir(parents=True)
    found = GitClient.find_repo_root(nested)
    assert found == repo


def test__run_raises_on_unicode_decode_error(monkeypatch, tmp_path: Path):
    repo = tmp_path
    client = GitClient(repo)

    def fake_run(*args, **kwargs):
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "fail")

    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(GitError):
        client._run(["status"])


def test_get_changes_untracked_and_renamed(monkeypatch, tmp_path: Path):
    client = GitClient(tmp_path)

    # Simulate porcelain with untracked and renamed files
    stdout = "?? newfile.txt\nR  old.txt -> new.txt\n M modified.txt\n"
    monkeypatch.setattr(client, "_run", lambda args, check=True: make_result(stdout=stdout))

    # By default, untracked files are excluded
    changes = client.get_changes()
    paths = [c.path for c in changes]
    assert "newfile.txt" not in paths

    # When include_untracked=True, untracked are included as 'N'
    changes2 = client.get_changes(include_untracked=True)
    assert any(c for c in changes2 if c.path == "newfile.txt" and c.status == "N")
    # Renamed file should appear with the arrow syntax
    assert any(c for c in changes2 if "old.txt -> new.txt" in c.path)


def test_get_diff_for_existing_and_deleted(monkeypatch, tmp_path: Path):
    repo = tmp_path
    (repo / "exists.txt").write_text("x")
    client = GitClient(repo)

    # existing file: _run should be called and stdout returned
    monkeypatch.setattr(client, "_run", lambda args, check=True: make_result(stdout="diff content"))
    diff = client.get_diff("exists.txt")
    assert "diff content" in diff

    # deleted file: path does not exist -> empty diff
    diff2 = client.get_diff("missing.txt")
    assert diff2 == ""
