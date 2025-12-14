import json
from pathlib import Path

import pytest

from minerva_common.config_builder import build_index_config, save_index_config


def test_build_index_config_basic():
    provider = {
        "provider_type": "ollama",
        "base_url": "http://localhost:11434",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
    }

    config = build_index_config(
        collection_name="test-collection",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
        description="Test collection",
    )

    assert config["chromadb_path"] == "/path/to/chromadb"
    assert config["collection"]["name"] == "test-collection"
    assert config["collection"]["description"] == "Test collection"
    assert config["collection"]["json_file"] == "/path/to/notes.json"
    assert config["collection"]["chunk_size"] == 1200
    assert config["collection"]["force_recreate"] is False
    assert config["collection"]["skip_ai_validation"] is False
    assert config["provider"] == provider


def test_build_index_config_with_path_objects():
    provider = {"provider_type": "ollama"}

    config = build_index_config(
        collection_name="test",
        json_file=Path("/path/to/notes.json"),
        chromadb_path=Path("/path/to/chromadb"),
        provider=provider,
    )

    assert config["chromadb_path"] == "/path/to/chromadb"
    assert config["collection"]["json_file"] == "/path/to/notes.json"


def test_build_index_config_custom_chunk_size():
    provider = {"provider_type": "ollama"}

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
        chunk_size=2000,
    )

    assert config["collection"]["chunk_size"] == 2000


def test_build_index_config_force_recreate():
    provider = {"provider_type": "ollama"}

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
        force_recreate=True,
    )

    assert config["collection"]["force_recreate"] is True


def test_build_index_config_skip_ai_validation():
    provider = {"provider_type": "ollama"}

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
        skip_ai_validation=True,
    )

    assert config["collection"]["skip_ai_validation"] is True


def test_build_index_config_openai_provider():
    provider = {
        "provider_type": "openai",
        "api_key": "${OPENAI_API_KEY}",
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
    }

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
        description="OpenAI test",
    )

    assert config["provider"]["provider_type"] == "openai"
    assert config["provider"]["api_key"] == "${OPENAI_API_KEY}"
    assert config["provider"]["embedding_model"] == "text-embedding-3-small"


def test_build_index_config_gemini_provider():
    provider = {
        "provider_type": "gemini",
        "api_key": "${GEMINI_API_KEY}",
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
    }

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
    )

    assert config["provider"]["provider_type"] == "gemini"
    assert config["provider"]["api_key"] == "${GEMINI_API_KEY}"


def test_build_index_config_lmstudio_provider():
    provider = {
        "provider_type": "lmstudio",
        "base_url": "http://localhost:1234/v1",
        "embedding_model": "qwen2.5-7b-instruct",
        "llm_model": "qwen2.5-14b-instruct",
    }

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
    )

    assert config["provider"]["provider_type"] == "lmstudio"
    assert config["provider"]["base_url"] == "http://localhost:1234/v1"


def test_build_index_config_empty_description():
    provider = {"provider_type": "ollama"}

    config = build_index_config(
        collection_name="test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
    )

    assert config["collection"]["description"] == ""


def test_save_index_config_creates_file(tmp_path):
    config = {
        "chromadb_path": "/path/to/chromadb",
        "collection": {
            "name": "test",
            "description": "Test",
            "json_file": "/path/to/notes.json",
            "chunk_size": 1200,
            "force_recreate": False,
            "skip_ai_validation": False,
        },
        "provider": {"provider_type": "ollama"},
    }

    output_path = tmp_path / "config.json"
    save_index_config(config, output_path)

    assert output_path.exists()
    with output_path.open("r") as f:
        saved_config = json.load(f)
    assert saved_config == config


def test_save_index_config_creates_parent_directory(tmp_path):
    config = {"chromadb_path": "/path/to/chromadb", "collection": {}, "provider": {}}

    output_path = tmp_path / "nested" / "dirs" / "config.json"
    save_index_config(config, output_path)

    assert output_path.exists()
    assert output_path.parent.exists()


def test_save_index_config_uses_atomic_write(tmp_path):
    config = {"chromadb_path": "/path/to/chromadb", "collection": {}, "provider": {}}

    output_path = tmp_path / "config.json"
    save_index_config(config, output_path)

    temp_path = output_path.with_suffix(".tmp")
    assert not temp_path.exists()
    assert output_path.exists()


def test_save_index_config_sets_permissions(tmp_path):
    config = {"chromadb_path": "/path/to/chromadb", "collection": {}, "provider": {}}

    output_path = tmp_path / "config.json"
    save_index_config(config, output_path)

    stat = output_path.stat()
    assert oct(stat.st_mode)[-3:] == "600"


def test_save_index_config_overwrites_existing(tmp_path):
    config1 = {"chromadb_path": "/path1", "collection": {}, "provider": {}}
    config2 = {"chromadb_path": "/path2", "collection": {}, "provider": {}}

    output_path = tmp_path / "config.json"

    save_index_config(config1, output_path)
    save_index_config(config2, output_path)

    with output_path.open("r") as f:
        saved_config = json.load(f)
    assert saved_config["chromadb_path"] == "/path2"


def test_save_index_config_formatting(tmp_path):
    config = {"chromadb_path": "/path/to/chromadb", "collection": {}, "provider": {}}

    output_path = tmp_path / "config.json"
    save_index_config(config, output_path)

    content = output_path.read_text()
    assert content.endswith("\n")
    assert '"chromadb_path"' in content
    assert content.count("\n") > 3


def test_roundtrip_build_and_save(tmp_path):
    provider = {
        "provider_type": "ollama",
        "base_url": "http://localhost:11434",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
    }

    config = build_index_config(
        collection_name="roundtrip-test",
        json_file="/path/to/notes.json",
        chromadb_path="/path/to/chromadb",
        provider=provider,
        description="Roundtrip test collection",
        chunk_size=1500,
        force_recreate=True,
    )

    output_path = tmp_path / "config.json"
    save_index_config(config, output_path)

    with output_path.open("r") as f:
        loaded_config = json.load(f)

    assert loaded_config["collection"]["name"] == "roundtrip-test"
    assert loaded_config["collection"]["description"] == "Roundtrip test collection"
    assert loaded_config["collection"]["chunk_size"] == 1500
    assert loaded_config["collection"]["force_recreate"] is True
    assert loaded_config["provider"]["provider_type"] == "ollama"
