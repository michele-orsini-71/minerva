import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def valid_note() -> dict[str, Any]:
    return {
        "title": "Test Note",
        "markdown": "# Test Content\n\nThis is a test note.",
        "size": len("# Test Content\n\nThis is a test note.".encode("utf-8")),
        "modificationDate": "2025-01-15T10:30:00Z",
        "creationDate": "2025-01-10T08:00:00Z",
    }


@pytest.fixture
def valid_notes_list(valid_note: dict[str, Any]) -> list[dict[str, Any]]:
    note2 = {
        "title": "Another Note",
        "markdown": "Different content here.",
        "size": len("Different content here.".encode("utf-8")),
        "modificationDate": "2025-01-16T12:00:00Z",
    }
    note3 = {
        "title": "Third Note",
        "markdown": "More content.",
        "size": len("More content.".encode("utf-8")),
        "modificationDate": "2025-01-17T14:30:00Z",
    }
    return [valid_note, note2, note3]


@pytest.fixture
def invalid_note_missing_title() -> dict[str, Any]:
    return {
        "markdown": "Content without title",
        "size": 100,
        "modificationDate": "2025-01-15T10:30:00Z",
    }


@pytest.fixture
def invalid_note_empty_title() -> dict[str, Any]:
    return {
        "title": "",
        "markdown": "Content with empty title",
        "size": 100,
        "modificationDate": "2025-01-15T10:30:00Z",
    }


@pytest.fixture
def invalid_note_missing_markdown() -> dict[str, Any]:
    return {
        "title": "Test Note",
        "size": 100,
        "modificationDate": "2025-01-15T10:30:00Z",
    }


@pytest.fixture
def invalid_note_negative_size() -> dict[str, Any]:
    return {
        "title": "Test Note",
        "markdown": "Content",
        "size": -1,
        "modificationDate": "2025-01-15T10:30:00Z",
    }


@pytest.fixture
def invalid_note_bad_date_format() -> dict[str, Any]:
    return {
        "title": "Test Note",
        "markdown": "Content",
        "size": 100,
        "modificationDate": "2025-01-15",
    }


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_json_file(temp_dir: Path, valid_notes_list: list[dict[str, Any]]) -> Path:
    json_file = temp_dir / "notes.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(valid_notes_list, f, indent=2)
    return json_file


@pytest.fixture
def temp_invalid_json_file(temp_dir: Path) -> Path:
    json_file = temp_dir / "invalid.json"
    with open(json_file, "w", encoding="utf-8") as f:
        f.write("not valid json{")
    return json_file


@pytest.fixture
def temp_chromadb_dir(temp_dir: Path) -> Path:
    chroma_dir = temp_dir / "chromadb"
    chroma_dir.mkdir()
    return chroma_dir


@pytest.fixture
def sample_index_config(temp_dir: Path, temp_json_file: Path, temp_chromadb_dir: Path) -> dict[str, Any]:
    return {
        "collection_name": "test_collection",
        "description": "Test collection for unit tests",
        "chromadb_path": str(temp_chromadb_dir),
        "json_file": str(temp_json_file),
        "forceRecreate": False,
        "skipAiValidation": True,
    }


@pytest.fixture
def sample_index_config_file(temp_dir: Path, sample_index_config: dict[str, Any]) -> Path:
    config_file = temp_dir / "index-config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_index_config, f, indent=2)
    return config_file


@pytest.fixture
def sample_server_config(temp_chromadb_dir: Path) -> dict[str, Any]:
    return {
        "chromadb_path": str(temp_chromadb_dir),
        "log_level": "INFO",
    }


@pytest.fixture
def sample_server_config_file(temp_dir: Path, sample_server_config: dict[str, Any]) -> Path:
    config_file = temp_dir / "server-config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(sample_server_config, f, indent=2)
    return config_file


@pytest.fixture
def sample_chunked_note(valid_note: dict[str, Any]) -> dict[str, Any]:
    chunked = valid_note.copy()
    chunked["chunks"] = [
        {
            "chunk_id": "chunk_1",
            "text": "# Test Content",
            "char_count": 15,
        },
        {
            "chunk_id": "chunk_2",
            "text": "This is a test note.",
            "char_count": 20,
        },
    ]
    return chunked


@pytest.fixture
def env_vars_backup():
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_ollama_config() -> dict[str, Any]:
    return {
        "provider_type": "ollama",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "base_url": "http://localhost:11434",
    }


@pytest.fixture
def mock_openai_config() -> dict[str, Any]:
    return {
        "provider_type": "openai",
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
    }
