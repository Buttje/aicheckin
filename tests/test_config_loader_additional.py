import json
import pytest

from vc_commit_helper.config import loader


def write_config(path, data):
    p = path / ".ollama_config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_missing_config_file_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_get_install_directory", lambda: tmp_path)
    with pytest.raises(loader.ConfigError) as exc:
        loader.load_config()
    assert "Missing Ollama configuration file" in str(exc.value)


def test_invalid_json_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_get_install_directory", lambda: tmp_path)
    p = tmp_path / ".ollama_config.json"
    p.write_text("{ invalid json", encoding="utf-8")
    with pytest.raises(loader.ConfigError) as exc:
        loader.load_config()
    assert "Invalid JSON" in str(exc.value) or "Invalid JSON" in repr(exc.value)


def test_missing_required_keys_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_get_install_directory", lambda: tmp_path)
    # missing 'model'
    write_config(tmp_path, {"base_url": "http://localhost", "port": 8080})
    with pytest.raises(loader.ConfigError) as exc:
        loader.load_config()
    assert "Missing required configuration keys" in str(exc.value)


@pytest.mark.parametrize(
    "bad_data, msg",
    [
        ({"base_url": 123, "port": 8080, "model": "m"}, "'base_url' must be a string"),
        ({"base_url": "u", "port": "notint", "model": "m"}, "'port' must be an integer"),
        ({"base_url": "u", "port": 1, "model": 5}, "'model' must be a string"),
    ],
)
def test_required_key_types_enforced(tmp_path, monkeypatch, bad_data, msg):
    monkeypatch.setattr(loader, "_get_install_directory", lambda: tmp_path)
    write_config(tmp_path, bad_data)
    with pytest.raises(loader.ConfigError) as exc:
        loader.load_config()
    assert msg in str(exc.value)


def test_optional_key_types_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_get_install_directory", lambda: tmp_path)
    # request_timeout wrong type
    write_config(tmp_path, {
        "base_url": "http://x",
        "port": 8000,
        "model": "m",
        "request_timeout": "fast",
    })
    with pytest.raises(loader.ConfigError) as exc:
        loader.load_config()
    assert "'request_timeout' must be a number" in str(exc.value)

    # max_tokens wrong type
    write_config(tmp_path, {
        "base_url": "http://x",
        "port": 8000,
        "model": "m",
        "max_tokens": "lots",
    })
    with pytest.raises(loader.ConfigError) as exc:
        loader.load_config()
    assert "'max_tokens' must be an integer" in str(exc.value)


def test_load_config_success(tmp_path, monkeypatch):
    monkeypatch.setattr(loader, "_get_install_directory", lambda: tmp_path)
    data = {
        "base_url": "http://localhost",
        "port": 1234,
        "model": "gpt",
        "request_timeout": 10,
        "max_tokens": 256,
    }
    write_config(tmp_path, data)
    cfg = loader.load_config()
    assert cfg["base_url"] == data["base_url"]
    assert cfg["port"] == data["port"]
    assert cfg["model"] == data["model"]
    assert cfg["request_timeout"] == data["request_timeout"]
    assert cfg["max_tokens"] == data["max_tokens"]


def _make_loader_layout(tmp_path, include_init=False, include_config=False):
    """Create a fake package layout under tmp_path to use as module_dir.

    Returns the path to a fake loader file to set as loader.__file__.
    """
    pkg = tmp_path / "fakepkg"
    cfg_dir = pkg / "config"
    cfg_dir.mkdir(parents=True)
    loader_file = cfg_dir / "loader.py"
    loader_file.write_text("# fake loader file", encoding="utf-8")
    if include_init:
        (pkg / "__init__.py").write_text("# init", encoding="utf-8")
    if include_config:
        (pkg / ".ollama_config.json").write_text("{}", encoding="utf-8")
    return str(loader_file)


def test_get_install_directory_prefers_config(tmp_path, monkeypatch):
    # Create fake layout with .ollama_config.json present
    fake_loader = _make_loader_layout(tmp_path, include_init=False, include_config=True)
    monkeypatch.setattr(loader, "__file__", fake_loader)
    result = loader._get_install_directory()
    assert result == loader.Path(fake_loader).parent.parent


def test_get_install_directory_with_init(tmp_path, monkeypatch):
    # Create fake layout with __init__.py present and no config
    fake_loader = _make_loader_layout(tmp_path, include_init=True, include_config=False)
    monkeypatch.setattr(loader, "__file__", fake_loader)
    result = loader._get_install_directory()
    assert result == loader.Path(fake_loader).parent.parent


def test_get_install_directory_fallback(tmp_path, monkeypatch):
    # Create fake layout without __init__ or config -> fallback to module_dir
    fake_loader = _make_loader_layout(tmp_path, include_init=False, include_config=False)
    monkeypatch.setattr(loader, "__file__", fake_loader)
    result = loader._get_install_directory()
    assert result == loader.Path(fake_loader).parent.parent
