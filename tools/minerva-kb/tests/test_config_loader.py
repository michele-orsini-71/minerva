import json
from pathlib import Path

import pytest

from minerva_kb.utils import config_loader


def _patch_app_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config_loader, "MINERVA_KB_APP_DIR", tmp_path)
    return tmp_path


def _index_config(tmp_path: Path) -> dict:
    return {
        "chromadb_path": str(tmp_path / "chromadb"),
        "collection": {
            "name": "alpha",
            "description": "Alpha collection",
            "json_file": str(tmp_path / "alpha.json"),
            "chunk_size": 1200,
        },
        "provider": {
            "provider_type": "openai",
            "embedding_model": "text-embedding-3-small",
            "llm_model": "gpt-4o-mini",
        },
    }


def _watcher_config(tmp_path: Path) -> dict:
    return {
        "repository_path": str(tmp_path / "repo"),
        "collection_name": "alpha",
        "extracted_json_path": str(tmp_path / "alpha-extracted.json"),
        "index_config_path": str(tmp_path / "alpha-index.json"),
        "debounce_seconds": 60.0,
        "include_extensions": [".md"],
        "ignore_patterns": [".git"],
    }


def test_load_index_config_reads_file(tmp_path, monkeypatch):
    app_dir = _patch_app_dir(tmp_path, monkeypatch)
    payload = _index_config(tmp_path)
    (app_dir / "alpha-index.json").write_text(json.dumps(payload))

    loaded = config_loader.load_index_config("alpha")
    assert loaded == payload


def test_load_index_config_invalid_json_raises(tmp_path, monkeypatch):
    app_dir = _patch_app_dir(tmp_path, monkeypatch)
    (app_dir / "alpha-index.json").write_text("{" )

    with pytest.raises(ValueError):
        config_loader.load_index_config("alpha")


def test_save_index_config_writes_file(tmp_path, monkeypatch):
    app_dir = _patch_app_dir(tmp_path, monkeypatch)
    payload = _index_config(tmp_path)

    path = config_loader.save_index_config("alpha", payload)
    assert path == app_dir / "alpha-index.json"
    assert json.loads(path.read_text()) == payload


def test_load_watcher_config_reads_file(tmp_path, monkeypatch):
    app_dir = _patch_app_dir(tmp_path, monkeypatch)
    payload = _watcher_config(tmp_path)
    (app_dir / "alpha-watcher.json").write_text(json.dumps(payload))

    loaded = config_loader.load_watcher_config("alpha")
    assert loaded == payload


def test_save_watcher_config_validates_data(tmp_path, monkeypatch):
    _patch_app_dir(tmp_path, monkeypatch)
    payload = _watcher_config(tmp_path)
    path = config_loader.save_watcher_config("alpha", payload)
    assert path.name == "alpha-watcher.json"


def test_save_index_config_rejects_invalid_chunk_size(tmp_path, monkeypatch):
    _patch_app_dir(tmp_path, monkeypatch)
    payload = _index_config(tmp_path)
    payload["collection"]["chunk_size"] = 0

    with pytest.raises(ValueError):
        config_loader.save_index_config("alpha", payload)


def test_load_watcher_config_invalid_structure(tmp_path, monkeypatch):
    app_dir = _patch_app_dir(tmp_path, monkeypatch)
    payload = _watcher_config(tmp_path)
    payload.pop("repository_path")
    (app_dir / "alpha-watcher.json").write_text(json.dumps(payload))

    with pytest.raises(ValueError):
        config_loader.load_watcher_config("alpha")
