import json
from pathlib import Path
from unittest.mock import patch

import pytest

from minerva_doc.utils import init
from minerva_doc.constants import MINERVA_DOC_APP_DIR, COLLECTIONS_REGISTRY_PATH


@pytest.fixture
def temp_minerva_dir(tmp_path, monkeypatch):
    minerva_dir = tmp_path / ".minerva"
    chromadb_dir = minerva_dir / "chromadb"
    apps_dir = minerva_dir / "apps"
    app_dir = apps_dir / "minerva-doc"
    registry_path = app_dir / "collections.json"

    monkeypatch.setattr("minerva_common.paths.MINERVA_DIR", minerva_dir)
    monkeypatch.setattr("minerva_common.paths.CHROMADB_DIR", chromadb_dir)
    monkeypatch.setattr("minerva_common.paths.APPS_DIR", apps_dir)
    monkeypatch.setattr("minerva_common.init.MINERVA_DIR", minerva_dir)
    monkeypatch.setattr("minerva_common.init.CHROMADB_DIR", chromadb_dir)
    monkeypatch.setattr("minerva_doc.constants.MINERVA_DOC_APP_DIR", app_dir)
    monkeypatch.setattr("minerva_doc.constants.COLLECTIONS_REGISTRY_PATH", registry_path)
    monkeypatch.setattr("minerva_doc.utils.init.MINERVA_DOC_APP_DIR", app_dir)
    monkeypatch.setattr("minerva_doc.utils.init.COLLECTIONS_REGISTRY_PATH", registry_path)

    return {
        "minerva_dir": minerva_dir,
        "chromadb_dir": chromadb_dir,
        "apps_dir": apps_dir,
        "app_dir": app_dir,
        "registry_path": registry_path,
    }


def test_ensure_app_dir_creates_directory(temp_minerva_dir):
    app_dir = temp_minerva_dir["app_dir"]

    assert not app_dir.exists()

    result = init.ensure_app_dir()

    assert result == app_dir
    assert app_dir.exists()
    assert app_dir.is_dir()


def test_ensure_app_dir_sets_permissions(temp_minerva_dir):
    app_dir = temp_minerva_dir["app_dir"]

    init.ensure_app_dir()

    stat = app_dir.stat()
    assert oct(stat.st_mode)[-3:] == "700"


def test_ensure_app_dir_handles_existing_directory(temp_minerva_dir):
    app_dir = temp_minerva_dir["app_dir"]

    app_dir.mkdir(parents=True)

    result = init.ensure_app_dir()

    assert result == app_dir
    assert app_dir.exists()


def test_ensure_app_dir_handles_permission_error(temp_minerva_dir, monkeypatch):
    def mock_chmod(path, mode):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.chmod", mock_chmod)

    result = init.ensure_app_dir()

    assert result.exists()


def test_ensure_app_dir_creates_parent_dirs(temp_minerva_dir):
    minerva_dir = temp_minerva_dir["minerva_dir"]
    app_dir = temp_minerva_dir["app_dir"]

    assert not minerva_dir.exists()

    init.ensure_app_dir()

    assert minerva_dir.exists()
    assert app_dir.exists()


def test_ensure_registry_creates_registry(temp_minerva_dir):
    registry_path = temp_minerva_dir["registry_path"]

    assert not registry_path.exists()

    result = init.ensure_registry()

    assert result == registry_path
    assert registry_path.exists()
    assert registry_path.is_file()

    with registry_path.open("r") as f:
        registry = json.load(f)

    assert "collections" in registry
    assert registry["collections"] == {}


def test_ensure_registry_sets_permissions(temp_minerva_dir):
    registry_path = temp_minerva_dir["registry_path"]

    init.ensure_registry()

    stat = registry_path.stat()
    assert oct(stat.st_mode)[-3:] == "600"


def test_ensure_registry_returns_existing_registry(temp_minerva_dir):
    registry_path = temp_minerva_dir["registry_path"]

    result1 = init.ensure_registry()
    assert result1 == registry_path

    result2 = init.ensure_registry()
    assert result2 == registry_path


def test_ensure_registry_handles_permission_error(temp_minerva_dir, monkeypatch):
    def mock_chmod(path, mode):
        raise PermissionError("Permission denied")

    monkeypatch.setattr("os.chmod", mock_chmod)

    result = init.ensure_registry()

    assert result.exists()


def test_ensure_registry_uses_atomic_write(temp_minerva_dir):
    registry_path = temp_minerva_dir["registry_path"]

    init.ensure_registry()

    temp_path = registry_path.with_suffix(".tmp")
    assert not temp_path.exists()
    assert registry_path.exists()


def test_ensure_registry_creates_parent_dirs(temp_minerva_dir):
    minerva_dir = temp_minerva_dir["minerva_dir"]
    app_dir = temp_minerva_dir["app_dir"]
    registry_path = temp_minerva_dir["registry_path"]

    assert not minerva_dir.exists()

    init.ensure_registry()

    assert minerva_dir.exists()
    assert app_dir.exists()
    assert registry_path.exists()
