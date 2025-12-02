import json
from types import SimpleNamespace
from pathlib import Path

import importlib
import os


def test_attempt_install_program_apt(monkeypatch):
    install = importlib.import_module("install")
    calls = []

    def fake_run(cmd, check=True):
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(install, "subprocess", install.subprocess)
    monkeypatch.setattr("subprocess.run", fake_run)

    ok = install.attempt_install_program("git", "apt", auto_yes=True)
    assert ok is True
    # Expect apt update then apt install
    assert calls[0][:3] == ["sudo", "apt", "update"]
    assert calls[1][:4] == ["sudo", "apt", "install", "-y"]


def test_setup_config_creates_home_config(monkeypatch, tmp_path: Path):
    install = importlib.import_module("install")
    # Force home to tmp_path via env
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    home_dir = tmp_path / ".ollama_server"
    config_path = home_dir / ".ollama_config.json"
    if config_path.exists():
        config_path.unlink()
    if home_dir.exists():
        for p in home_dir.iterdir():
            p.unlink()
        home_dir.rmdir()

    ok = install.setup_config()
    assert ok is True
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "base_url" in data and "port" in data and "model" in data


def test_check_and_install_dependencies_calls_attempt(monkeypatch):
    install = importlib.import_module("install")
    # Simulate git and svn missing, ollama present
    def fake_is_program_installed(exe_name: str) -> bool:
        return exe_name == "ollama"

    called = []

    def fake_attempt_install_program(prog, pm, auto_yes=False):
        called.append((prog, pm, auto_yes))
        return True

    monkeypatch.setattr(install, "is_program_installed", fake_is_program_installed)
    monkeypatch.setattr(install, "find_package_manager", lambda: "apt")
    monkeypatch.setattr(install, "attempt_install_program", fake_attempt_install_program)

    install.check_and_install_dependencies(auto_yes=True)
    # Should attempt to install git and svn (order may vary)
    progs = {c[0] for c in called}
    assert "git" in progs or "svn" in progs
