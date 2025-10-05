import json
from pathlib import Path

import pytest

import config_loader
from config_loader import ConfigError, CollectionConfig


def write_json(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def minimal_config_dict() -> dict:
    return {
        "collection_name": "notes",
        "description": "Use this collection when reviewing backend deployment notes and runbooks.",
        "chromadb_path": "./chromadb",
        "json_file": "notes.json",
        "chunk_size": 1200,
    }


def test_load_collection_config_success(tmp_path: Path):
    config_path = write_json(tmp_path / "config.json", minimal_config_dict())
    result = config_loader.load_collection_config(str(config_path))
    assert isinstance(result, CollectionConfig)
    assert result.collection_name == "notes"


def test_load_collection_config_file_not_found(tmp_path: Path):
    with pytest.raises(ConfigError):
        config_loader.load_collection_config(str(tmp_path / "missing.json"))


def test_load_collection_config_invalid_json(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{ invalid", encoding="utf-8")
    with pytest.raises(ConfigError):
        config_loader.load_collection_config(str(config_path))


def test_load_collection_config_missing_required_fields(tmp_path: Path):
    data = minimal_config_dict()
    del data["description"]
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError):
        config_loader.load_collection_config(str(config_path))


def test_validate_config_schema_valid():
    config_loader.validate_config_schema(minimal_config_dict(), "path")


def test_validate_config_schema_invalid_type():
    data = minimal_config_dict()
    data["chunk_size"] = "large"
    with pytest.raises(ConfigError):
        config_loader.validate_config_schema(data, "path")


def test_validate_config_schema_additional_properties():
    data = minimal_config_dict()
    data["extra"] = True
    with pytest.raises(ConfigError):
        config_loader.validate_config_schema(data, "path")
