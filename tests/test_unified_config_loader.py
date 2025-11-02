import json
from pathlib import Path

import pytest

from minerva.common.config_loader import load_unified_config
from minerva.common.exceptions import ConfigError


def build_sample_config(base_dir: Path) -> dict:
    chroma_path = base_dir / "chromadb_data"
    notes_path = base_dir / "notes.json"
    conversation_dir = base_dir / "conversations"

    chroma_path.mkdir(parents=True, exist_ok=True)
    conversation_dir.mkdir(parents=True, exist_ok=True)
    notes_path.write_text("[]", encoding="utf-8")

    return {
        "ai_providers": [
            {
                "id": "lmstudio-local",
                "provider_type": "lmstudio",
                "base_url": "http://localhost:1234/v1",
                "embedding_model": "qwen2.5-7b-instruct",
                "llm_model": "qwen2.5-14b-instruct"
            }
        ],
        "indexing": {
            "chromadb_path": str(chroma_path),
            "collections": [
                {
                    "collection_name": "test-notes",
                    "description": "Test notes for config loader",
                    "json_file": str(notes_path),
                    "chunk_size": 1200,
                    "ai_provider_id": "lmstudio-local"
                }
            ]
        },
        "chat": {
            "chat_provider_id": "lmstudio-local",
            "mcp_server_url": "http://localhost:8000/mcp",
            "conversation_dir": str(conversation_dir),
            "enable_streaming": False,
            "max_tool_iterations": 5
        },
        "server": {
            "chromadb_path": str(chroma_path),
            "default_max_results": 5
        }
    }


def write_config(base_dir: Path, data: dict) -> Path:
    config_path = base_dir / "config.json"
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return config_path


def test_load_unified_config_success(temp_dir: Path):
    config_data = build_sample_config(temp_dir)
    config_path = write_config(temp_dir, config_data)

    config = load_unified_config(str(config_path))

    assert len(config.providers) == 1
    assert config.indexing.collections[0].collection_name == "test-notes"
    assert config.chat.chat_provider_id == "lmstudio-local"
    assert config.server.default_max_results == 5


def test_load_unified_config_unknown_provider_reference(temp_dir: Path):
    config_data = build_sample_config(temp_dir)
    config_data["indexing"]["collections"][0]["ai_provider_id"] = "missing"
    config_path = write_config(temp_dir, config_data)

    with pytest.raises(ConfigError) as exc:
        load_unified_config(str(config_path))

    assert "Unknown provider id" in str(exc.value)


def test_load_unified_config_rejects_relative_chromadb_path(temp_dir: Path):
    config_data = build_sample_config(temp_dir)
    config_data["indexing"]["chromadb_path"] = "relative/path"
    config_data["server"]["chromadb_path"] = "relative/path"
    config_path = write_config(temp_dir, config_data)

    with pytest.raises(ConfigError) as exc:
        load_unified_config(str(config_path))

    assert "Expected absolute path" in str(exc.value)


def test_load_unified_config_rejects_invalid_chunk_size(temp_dir: Path):
    config_data = build_sample_config(temp_dir)
    config_data["indexing"]["collections"][0]["chunk_size"] = 200
    config_path = write_config(temp_dir, config_data)

    with pytest.raises(ConfigError) as exc:
        load_unified_config(str(config_path))

    assert "chunk_size" in str(exc.value)


def test_load_unified_config_requires_chat_section(temp_dir: Path):
    config_data = build_sample_config(temp_dir)
    config_data.pop("chat")
    config_path = write_config(temp_dir, config_data)

    with pytest.raises(ConfigError):
        load_unified_config(str(config_path))
