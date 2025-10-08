import builtins
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
        "ai_provider": {
            "type": "ollama",
            "embedding": {
                "model": "mxbai-embed-large:latest",
                "base_url": None,
                "api_key": None
            },
            "llm": {
                "model": "llama3.1:8b",
                "base_url": None,
                "api_key": None
            }
        }
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
    ai_provider = {
        "type": "ollama",
        "embedding": {"model": "test"},
        "llm": {"model": "test"}
    }

    with pytest.raises(ValueError):
        CollectionConfig(
            collection_name="",
            description="valid",
            chromadb_path="./chromadb",
            json_file="notes.json",
            ai_provider=ai_provider,
        )

    with pytest.raises(ValueError):
        CollectionConfig(
            collection_name="notes",
            description="",
            chromadb_path="./chromadb",
            json_file="notes.json",
            ai_provider=ai_provider,
        )

    with pytest.raises(ValueError):
        CollectionConfig(
            collection_name="notes",
            description="valid",
            chromadb_path="./chromadb",
            json_file="notes.json",
            ai_provider={},
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




def test_ai_provider_valid_ollama_config(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "ollama",
        "embedding": {"model": "mxbai-embed-large:latest"},
        "llm": {"model": "llama3.1:8b"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    result = config_loader.load_collection_config(str(config_path))
    assert result.ai_provider is not None
    assert result.ai_provider["type"] == "ollama"
    assert result.ai_provider["embedding"]["model"] == "mxbai-embed-large:latest"


def test_ai_provider_valid_openai_config_with_api_key_template(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "openai",
        "embedding": {
            "model": "text-embedding-3-small",
            "api_key": "${OPENAI_API_KEY}"
        },
        "llm": {
            "model": "gpt-4o-mini",
            "api_key": "${OPENAI_API_KEY}"
        }
    }
    config_path = write_json(tmp_path / "config.json", data)
    result = config_loader.load_collection_config(str(config_path))
    assert result.ai_provider["type"] == "openai"
    assert result.ai_provider["embedding"]["api_key"] == "${OPENAI_API_KEY}"


def test_ai_provider_valid_gemini_config(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "gemini",
        "embedding": {"model": "text-embedding-004"},
        "llm": {"model": "gemini-1.5-flash"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    result = config_loader.load_collection_config(str(config_path))
    assert result.ai_provider["type"] == "gemini"


def test_ai_provider_invalid_type(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "invalid_provider",
        "embedding": {"model": "some-model"},
        "llm": {"model": "some-model"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError) as error_info:
        config_loader.load_collection_config(str(config_path))
    assert "Invalid AI provider type" in str(error_info.value)


def test_ai_provider_missing_type(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "embedding": {"model": "some-model"},
        "llm": {"model": "some-model"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError) as error_info:
        config_loader.load_collection_config(str(config_path))
    assert "Missing field: 'type'" in str(error_info.value)


def test_ai_provider_missing_embedding(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "ollama",
        "llm": {"model": "llama3.1:8b"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError) as error_info:
        config_loader.load_collection_config(str(config_path))
    assert "Missing field: 'embedding'" in str(error_info.value)


def test_ai_provider_missing_llm(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "ollama",
        "embedding": {"model": "mxbai-embed-large:latest"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError) as error_info:
        config_loader.load_collection_config(str(config_path))
    assert "Missing field: 'llm'" in str(error_info.value)


def test_ai_provider_invalid_api_key_format(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "openai",
        "embedding": {
            "model": "text-embedding-3-small",
            "api_key": "sk-plaintext-key-not-allowed"
        },
        "llm": {"model": "gpt-4o-mini"}
    }
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError) as error_info:
        config_loader.load_collection_config(str(config_path))
    assert "Invalid API key format" in str(error_info.value)


def test_ai_provider_null_api_key_allowed(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "ollama",
        "embedding": {"model": "mxbai-embed-large:latest", "api_key": None},
        "llm": {"model": "llama3.1:8b", "api_key": None}
    }
    config_path = write_json(tmp_path / "config.json", data)
    result = config_loader.load_collection_config(str(config_path))
    assert result.ai_provider["embedding"]["api_key"] is None


def test_ai_provider_missing_required_field(tmp_path: Path):
    data = minimal_config_dict()
    del data["ai_provider"]
    config_path = write_json(tmp_path / "config.json", data)
    with pytest.raises(ConfigError, match="ai_provider"):
        config_loader.load_collection_config(str(config_path))


def test_ai_provider_all_supported_types(tmp_path: Path):
    supported_types = ["ollama", "openai", "gemini", "azure", "anthropic"]

    for provider_type in supported_types:
        data = minimal_config_dict()
        data["ai_provider"] = {
            "type": provider_type,
            "embedding": {"model": "test-model"},
            "llm": {"model": "test-llm"}
        }
        config_path = write_json(tmp_path / f"config_{provider_type}.json", data)
        result = config_loader.load_collection_config(str(config_path))
        assert result.ai_provider["type"] == provider_type


def test_ai_provider_with_base_url(tmp_path: Path):
    data = minimal_config_dict()
    data["ai_provider"] = {
        "type": "ollama",
        "embedding": {
            "model": "mxbai-embed-large:latest",
            "base_url": "http://localhost:11434"
        },
        "llm": {
            "model": "llama3.1:8b",
            "base_url": "http://localhost:11434"
        }
    }
    config_path = write_json(tmp_path / "config.json", data)
    result = config_loader.load_collection_config(str(config_path))
    assert result.ai_provider["embedding"]["base_url"] == "http://localhost:11434"
