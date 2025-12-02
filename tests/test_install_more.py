import subprocess
import sys
import json
from types import SimpleNamespace
from pathlib import Path
import importlib
import os


import pytest


install = importlib.import_module("install")


def test_detect_platform_and_system_info(monkeypatch):
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")
    monkeypatch.setattr(install.platform, "machine", lambda: "AMD64")
    os_name, arch = install.get_system_info()
    assert os_name == "Windows"
    assert arch == "AMD64"
    assert install.detect_platform() == "windows"


def test_find_package_manager(monkeypatch):
    # Simulate dnf present
    def fake_which(name):
        return "/usr/bin/" + name if name == "dnf" else None

    monkeypatch.setattr(install.shutil, "which", fake_which)
    assert install.find_package_manager() == "dnf"


def test_attempt_install_program_various(monkeypatch):
    calls = []

    def fake_run(cmd, check=True, **kwargs):
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(install.subprocess, "run", fake_run)

    for pm in ["apt", "dnf", "pacman", "zypper", "brew", "choco", "winget"]:
        calls.clear()
        ok = install.attempt_install_program("git", pm, auto_yes=True)
        assert ok is True
        assert len(calls) >= 1


def test_attempt_install_program_failure(monkeypatch):
    def fake_run(cmd, check=True, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="fail")

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    ok = install.attempt_install_program("git", "apt", auto_yes=True)
    assert ok is False


def test_install_package_success_and_path_warning(monkeypatch, tmp_path):
    # Simulate pip install returning path-warning text
    def fake_run(cmd, cwd=None, capture_output=None, text=None, check=None, **kwargs):
        return SimpleNamespace(returncode=0, stdout="Scripts is not on PATH", stderr="")

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    ok, path_warn = install.install_package()
    assert ok is True
    assert isinstance(path_warn, bool)


def test_install_package_failure(monkeypatch):
    def fake_run(cmd, cwd=None, capture_output=None, text=None, check=None, **kwargs):
        e = subprocess.CalledProcessError(2, cmd)
        # attach attributes similar to CompletedProcess
        e.stderr = "err"
        e.stdout = "out"
        raise e

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    ok, warn = install.install_package()
    assert ok is False
    assert warn is False


def test_find_scripts_directory_pip_show(monkeypatch, tmp_path):
    site = tmp_path / "lib" / "pythonX" / "site-packages"
    site.mkdir(parents=True)
    # location parent's bin exists
    bin_dir = site.parent / "bin"
    bin_dir.mkdir(parents=True)

    def fake_run(cmd, capture_output=True, text=True, check=True, **kwargs):
        return SimpleNamespace(stdout=f"Name: vc-commit-helper\nLocation: {site}\n")

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    res = install.find_scripts_directory()
    assert res is not None


def test_add_to_path_windows_full(monkeypatch, tmp_path):
    # Create fake winreg module
    class FakeReg:
        HKEY_CURRENT_USER = object()
        KEY_READ = 1
        KEY_WRITE = 2
        REG_EXPAND_SZ = 3

        def __init__(self):
            self._path = ""

        def OpenKey(self, *a, **k):
            return "key"

        def QueryValueEx(self, key, name):
            # Simulate no existing path
            raise FileNotFoundError()

        def SetValueEx(self, key, name, zero, reg_type, value):
            self._path = value

        def CloseKey(self, key):
            return None

    fake = FakeReg()
    import sys as _sys
    _sys.modules["winreg"] = fake

    scripts_dir = tmp_path / "Scripts"
    scripts_dir.mkdir()

    # Call the function; it should return True
    ok = install.add_to_path_windows(scripts_dir)
    assert ok is True


def test_find_scripts_directory_windows_store(monkeypatch, tmp_path):
    # Simulate Windows store location
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")

    user_base = tmp_path / "AppData" / "Local" / "Packages"
    python_dir = user_base / "PythonSoftwareFoundation.Python.TEST"
    scripts_dir = python_dir / "LocalCache" / "local-packages" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts"
    scripts_dir.mkdir(parents=True)

    res = install.find_scripts_directory()
    assert res is not None


def test_find_scripts_directory_user_base(monkeypatch, tmp_path):
    # Simulate the site --user-base output
    base = tmp_path / "userbase"
    binp = base / "bin"
    binp.mkdir(parents=True)

    def fake_run(cmd, capture_output=True, text=True, **kwargs):
        return SimpleNamespace(stdout=str(base))

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    monkeypatch.setattr(install.platform, "system", lambda: "Linux")
    res = install.find_scripts_directory()
    assert res is not None


def test_add_to_path_unix_rc_contains(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    rc = tmp_path / ".zshrc"
    scripts_dir = tmp_path / "bin"
    scripts_dir.mkdir()
    rc.write_text(str(scripts_dir))
    ok = install.add_to_path_unix(scripts_dir)
    assert ok is True


def test_attempt_install_program_input_skip(monkeypatch):
    # input returns 'n' so should skip and return False
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    monkeypatch.setattr(install.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    ok = install.attempt_install_program("git", "apt", auto_yes=False)
    assert ok is False


def test_check_and_install_dependencies_all_present(monkeypatch, capsys):
    monkeypatch.setattr(install, "is_program_installed", lambda exe: True)
    install.check_and_install_dependencies(auto_yes=True)
    captured = capsys.readouterr()
    assert "All required external programs are installed" in captured.out


def test_verify_installation_error(monkeypatch):
    def fake_run(*a, **k):
        raise Exception("boom")

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    assert install.verify_installation() is False


def test_run_module_main_success(monkeypatch, tmp_path):
    import runpy
    # Ensure pytest args don't leak into argparse
    monkeypatch.setattr(sys, "argv", ["install.py"]) 

    # Patch subprocess.run globally so the fresh module uses it
    def fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    import subprocess as real_sub
    real_sub.run = fake_run

    # Patch shutil.which to avoid missing-tools branches
    import shutil as real_shutil
    real_shutil.which = lambda name: "/usr/bin/" + name

    # Run the module as __main__; it calls sys.exit so catch SystemExit
    try:
        runpy.run_module("install", run_name="__main__")
    except SystemExit as e:
        assert e.code == 0


def test_run_module_main_keyboardinterrupt(monkeypatch, tmp_path):
    import runpy
    monkeypatch.setattr(sys, "argv", ["install.py"]) 

    # Make subprocess.run raise KeyboardInterrupt to hit that handler
    def fake_run(*a, **k):
        raise KeyboardInterrupt()

    import subprocess as real_sub
    real_sub.run = fake_run

    try:
        runpy.run_module("install", run_name="__main__")
    except SystemExit as e:
        assert e.code == 1


def test_add_to_path_unix_appends(monkeypatch, tmp_path):
    # Setup fake home and shell
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")

    rc = tmp_path / ".bashrc"
    rc.write_text("# existing")

    scripts_dir = tmp_path / "bin"
    scripts_dir.mkdir()

    ok = install.add_to_path_unix(scripts_dir)
    assert ok is True
    content = rc.read_text()
    assert "Added by aicheckin installer" in content or str(scripts_dir) in content


def test_setup_path_no_warning():
    assert install.setup_path(False) is False


def test_setup_path_with_scripts_found(monkeypatch, tmp_path):
    scripts_dir = tmp_path / "bin"
    scripts_dir.mkdir()
    monkeypatch.setattr(install, "find_scripts_directory", lambda: scripts_dir)
    monkeypatch.setattr(install.platform, "system", lambda: "Linux")
    # ensure add_to_path_unix works
    monkeypatch.setattr(install, "add_to_path_unix", lambda p: True)
    assert install.setup_path(True) is True


def test_setup_config_existing_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    home_dir = tmp_path / ".ollama_server"
    home_dir.mkdir()
    config_path = home_dir / ".ollama_config.json"
    config_path.write_text(json.dumps({"base_url": "http://x", "port": 1, "model": "m"}))
    assert install.setup_config() is True


def test_setup_config_existing_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    home_dir = tmp_path / ".ollama_server"
    # ensure no config exists so setup creates one
    if home_dir.exists():
        for p in home_dir.iterdir():
            p.unlink()
        home_dir.rmdir()
    assert install.setup_config() is True
    config_path = home_dir / ".ollama_config.json"
    data = json.loads(config_path.read_text())
    assert "base_url" in data


def test_verify_installation_success(monkeypatch):
    monkeypatch.setattr(install.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    assert install.verify_installation() is True


def test_verify_installation_module_success(monkeypatch):
    # first raise FileNotFoundError, second return success
    def fake_run_first(*a, **k):
        raise FileNotFoundError()

    def fake_run_second(*a, **k):
        return SimpleNamespace(returncode=0)

    calls = {"n": 0}

    def fake_run(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise FileNotFoundError()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    assert install.verify_installation() is True


def test_print_usage_instructions_outputs(monkeypatch, capsys):
    monkeypatch.setattr(install.platform, "system", lambda: "Linux")
    install.print_usage_instructions(path_updated=False, installation_verified=True)
    captured = capsys.readouterr()
    assert "Usage:" in captured.out


def test_main_flow_success(monkeypatch):
    # Monkeypatch internal steps to simulate success path
    monkeypatch.setattr(install, "check_python_version", lambda: True)
    monkeypatch.setattr(install, "install_package", lambda: (True, False))
    monkeypatch.setattr(install, "setup_path", lambda x: False)
    monkeypatch.setattr(install, "check_and_install_dependencies", lambda auto_yes=False: None)
    monkeypatch.setattr(install, "setup_config", lambda: True)
    monkeypatch.setattr(install, "verify_installation", lambda: True)
    # avoid argparse reading pytest args
    monkeypatch.setattr(sys, "argv", ["install.py"])
    # Ensure main returns 0
    assert install.main() == 0


def test_main_python_version_fail(monkeypatch):
    monkeypatch.setattr(install, "check_python_version", lambda: False)
    monkeypatch.setattr(sys, "argv", ["install.py"])
    assert install.main() == 1
