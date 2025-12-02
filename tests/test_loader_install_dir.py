import os
from pathlib import Path

from vc_commit_helper.config.loader import _get_install_directory


def make_loader_path(base: Path) -> Path:
    """Return a synthetic loader.py path under base/vc_commit_helper/config/loader.py"""
    loader = base / "vc_commit_helper" / "config" / "loader.py"
    loader.parent.mkdir(parents=True, exist_ok=True)
    # create an empty loader file to represent the module file
    loader.write_text("# loader placeholder\n")
    return loader


def test_get_install_directory_with_config_in_source(tmp_path: Path):
    # Create a source-like layout and a .ollama_config.json in the package dir
    loader_file = make_loader_path(tmp_path)
    package_dir = loader_file.parent.parent
    config_file = package_dir / ".ollama_config.json"
    config_file.write_text("{}")

    result = _get_install_directory(module_file=loader_file)
    assert result == package_dir


def test_get_install_directory_with_init_py(tmp_path: Path):
    # Create a layout that looks like an installed package (has __init__.py)
    loader_file = make_loader_path(tmp_path)
    package_dir = loader_file.parent.parent
    init_file = package_dir / "__init__.py"
    init_file.write_text("# package init\n")

    result = _get_install_directory(module_file=loader_file)
    assert result == package_dir


def test_get_install_directory_fallback(tmp_path: Path):
    # No config file and no __init__.py -> fallback should return module_dir
    loader_file = make_loader_path(tmp_path)
    package_dir = loader_file.parent.parent

    result = _get_install_directory(module_file=loader_file)
    assert result == package_dir
