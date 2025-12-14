import json
from pathlib import Path
from unittest.mock import patch

import pytest

from minerva_common import init
from minerva_common.paths import CHROMADB_DIR, MINERVA_DIR, SERVER_CONFIG_PATH


@pytest.fixture
def temp_minerva_dir(tmp_path, monkeypatch):
    minerva_dir = tmp_path / ".minerva"
    chromadb_dir = minerva_dir / "chromadb"
    server_config_path = minerva_dir / "server.json"

    monkeypatch.setattr("minerva_common.paths.MINERVA_DIR", minerva_dir)
    monkeypatch.setattr("minerva_common.paths.CHROMADB_DIR", chromadb_dir)
    monkeypatch.setattr("minerva_common.paths.SERVER_CONFIG_PATH", server_config_path)
    monkeypatch.setattr("minerva_common.init.MINERVA_DIR", minerva_dir)
    monkeypatch.setattr("minerva_common.init.CHROMADB_DIR", chromadb_dir)
    monkeypatch.setattr("minerva_common.init.SERVER_CONFIG_PATH", server_config_path)

    return {
        "minerva_dir": minerva_dir,
        "chromadb_dir": chromadb_dir,
        "server_config_path": server_config_path,
    }


def test_ensure_shared_dirs_creates_directories(temp_minerva_dir):
    minerva_dir = temp_minerva_dir["minerva_dir"]
    chromadb_dir = temp_minerva_dir["chromadb_dir"]

    assert not minerva_dir.exists()
    assert not chromadb_dir.exists()

    init.ensure_shared_dirs()

    assert minerva_dir.exists()
    assert minerva_dir.is_dir()
    assert chromadb_dir.exists()
    assert chromadb_dir.is_dir()


def test_ensure_shared_dirs_sets_permissions(temp_minerva_dir):
    minerva_dir = temp_minerva_dir["minerva_dir"]
    chromadb_dir = temp_minerva_dir["chromadb_dir"]

    init.ensure_shared_dirs()

    minerva_stat = minerva_dir.stat()
    assert oct(minerva_stat.st_mode)[-3:] == "700"

    chromadb_stat = chromadb_dir.stat()
    assert oct(chromadb_stat.st_mode)[-3:] == "700"


def test_ensure_shared_dirs_handles_existing_directories(temp_minerva_dir):
    minerva_dir = temp_minerva_dir["minerva_dir"]
    chromadb_dir = temp_minerva_dir["chromadb_dir"]

    minerva_dir.mkdir(parents=True)
    chromadb_dir.mkdir(parents=True)

    init.ensure_shared_dirs()

    assert minerva_dir.exists()
    assert chromadb_dir.exists()


def test_ensure_shared_dirs_handles_permission_error(temp_minerva_dir, monkeypatch):
    def mock_chmod(path, mode):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.chmod", mock_chmod)

    init.ensure_shared_dirs()

    assert temp_minerva_dir["minerva_dir"].exists()
    assert temp_minerva_dir["chromadb_dir"].exists()


def test_ensure_server_config_creates_config(temp_minerva_dir):
    server_config_path = temp_minerva_dir["server_config_path"]
    chromadb_dir = temp_minerva_dir["chromadb_dir"]

    assert not server_config_path.exists()

    path, created = init.ensure_server_config()

    assert path == server_config_path
    assert created is True
    assert server_config_path.exists()
    assert server_config_path.is_file()

    with server_config_path.open("r") as f:
        config = json.load(f)

    assert config["chromadb_path"] == str(chromadb_dir)
    assert config["default_max_results"] == 5
    assert config["host"] == "127.0.0.1"
    assert config["port"] == 8337


def test_ensure_server_config_sets_permissions(temp_minerva_dir):
    server_config_path = temp_minerva_dir["server_config_path"]

    init.ensure_server_config()

    stat = server_config_path.stat()
    assert oct(stat.st_mode)[-3:] == "600"


def test_ensure_server_config_returns_existing_config(temp_minerva_dir):
    server_config_path = temp_minerva_dir["server_config_path"]

    path1, created1 = init.ensure_server_config()
    assert created1 is True

    path2, created2 = init.ensure_server_config()
    assert path2 == path1
    assert created2 is False


def test_ensure_server_config_creates_parent_dirs(temp_minerva_dir):
    server_config_path = temp_minerva_dir["server_config_path"]
    minerva_dir = temp_minerva_dir["minerva_dir"]

    assert not minerva_dir.exists()

    init.ensure_server_config()

    assert minerva_dir.exists()
    assert server_config_path.exists()


def test_ensure_server_config_handles_permission_error(temp_minerva_dir, monkeypatch):
    def mock_chmod(path, mode):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.chmod", mock_chmod)

    path, created = init.ensure_server_config()

    assert created is True
    assert path.exists()


def test_ensure_server_config_uses_atomic_write(temp_minerva_dir):
    server_config_path = temp_minerva_dir["server_config_path"]

    init.ensure_server_config()

    temp_path = server_config_path.with_suffix(".tmp")
    assert not temp_path.exists()
    assert server_config_path.exists()
