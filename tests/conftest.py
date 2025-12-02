import shutil
from pathlib import Path
import tempfile
import pytest


@pytest.fixture(scope="session", autouse=True)
def isolate_home_config():
    """Temporarily move any existing user-level Ollama config out of the way.

    Some tests expect no user-level config to exist. This fixture moves the
    file aside for the duration of the test session and restores it afterwards.
    """
    home = Path.home()
    server_dir = home / ".ollama_server"
    config_path = server_dir / ".ollama_config.json"
    backup_dir = None
    moved = False
    if config_path.exists():
        backup_dir = Path(tempfile.mkdtemp(prefix="ollama_backup_"))
        shutil.move(str(config_path), str(backup_dir / ".ollama_config.json"))
        moved = True

    try:
        yield
    finally:
        # restore
        if moved and backup_dir is not None:
            dst_dir = config_path.parent
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_dir / ".ollama_config.json"), str(config_path))
            shutil.rmtree(str(backup_dir), ignore_errors=True)