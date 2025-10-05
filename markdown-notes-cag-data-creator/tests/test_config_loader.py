import json
import importlib
from pathlib import Path
from unittest import mock

import builtins
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


def test_collection_config_requires_non_empty_fields():
    with pytest.raises(ValueError):
        CollectionConfig(
            collection_name="",
            description="valid",
            chromadb_path="./chromadb",
            json_file="notes.json",
        )

    with pytest.raises(ValueError):
        CollectionConfig(
            collection_name="notes",
            description="",
            chromadb_path="./chromadb",
            json_file="notes.json",
        )


def test_validate_config_schema_description_too_short():
    data = minimal_config_dict()
    data["description"] = "short"
    with pytest.raises(ConfigError) as error_info:
        config_loader.validate_config_schema(data, "path")

    assert "Length validation error" in str(error_info.value)


def test_validate_config_schema_pattern_error():
    data = minimal_config_dict()
    data["collection_name"] = "invalid name"
    with pytest.raises(ConfigError) as error_info:
        config_loader.validate_config_schema(data, "path")

    assert "Pattern validation error" in str(error_info.value)


def test_validate_config_schema_generic_error():
    data = minimal_config_dict()
    data["chunk_size"] = 100  # Below minimum to trigger generic branch
    with pytest.raises(ConfigError) as error_info:
        config_loader.validate_config_schema(data, "path")

    assert "Schema validation error" in str(error_info.value)


def test_read_json_config_file_permission_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    def fake_open(*_args, **_kwargs):
        raise OSError("denied")

    monkeypatch.setattr(builtins, "open", fake_open)

    with pytest.raises(ConfigError) as error_info:
        config_loader.read_json_config_file(config_path, str(config_path))

    assert "Failed to read configuration file" in str(error_info.value)


def test_read_json_config_file_requires_object(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(ConfigError):
        config_loader.read_json_config_file(config_path, str(config_path))


def test_load_collection_config_wraps_unexpected_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    config_path = write_json(tmp_path / "config.json", minimal_config_dict())

    def fail_extract(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(config_loader, "extract_config_fields", fail_extract)

    with pytest.raises(ConfigError) as error_info:
        config_loader.load_collection_config(str(config_path))

    assert "Unexpected error loading configuration" in str(error_info.value)


def test_config_loader_missing_jsonschema_dependency():
    module = importlib.import_module("config_loader")
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "jsonschema" or name.startswith("jsonschema."):
            raise ImportError("jsonschema missing")
        return original_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(SystemExit) as exit_info:
            importlib.reload(module)

    assert exit_info.value.code == 1
    importlib.reload(module)
