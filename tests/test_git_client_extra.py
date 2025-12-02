from types import SimpleNamespace
from pathlib import Path
from vc_commit_helper.vcs.git_client import GitClient


def make_success(result_stdout: str = "", result_stderr: str = ""):
    return SimpleNamespace(stdout=result_stdout, stderr=result_stderr, returncode=0)


def test_stage_files_add_and_remove(tmp_path: Path):
    repo = tmp_path
    # create one existing file and one missing file
    (repo / "exists.txt").write_text("hello")

    client = GitClient(repo)
    calls = []

    def fake_run(args, check=True):
        calls.append((args, check))
        return make_success()

    client._run = fake_run
    client.stage_files(["exists.txt", "missing.txt"])

    # first should be add, second should be rm
    assert any(call for call in calls if call[0][0] == "add"), "git add was not called"
    assert any(call for call in calls if call[0][0] == "rm"), "git rm was not called"


def test_push_with_and_without_set_upstream(tmp_path: Path):
    client = GitClient(tmp_path)
    recorded = []

    def fake_run(args, check=True):
        recorded.append(args)
        # Simulate rev-parse returning current branch when requested
        if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return make_success(result_stdout="feature-branch\n")
        return make_success()

    client._run = fake_run

    # push without set_upstream
    client.push(set_upstream=False)
    assert any(r for r in recorded if r == ["push"]), recorded

    # reset and push with set_upstream True
    recorded.clear()
    client.push(set_upstream=True)
    assert any(r for r in recorded if r[0] == "push" and "--set-upstream" in r), recorded
