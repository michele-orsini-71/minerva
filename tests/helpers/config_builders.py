from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from minerva.chat.config import ChatConfig, load_chat_config_from_file
from minerva.common.index_config import IndexConfig, load_index_config
from minerva.common.server_config import ServerConfig, load_server_config


def make_index_config(
    base_dir: Path,
    *,
    filename: str = "index-config.json",
    collection_overrides: Mapping[str, Any] | None = None,
    provider_overrides: Mapping[str, Any] | None = None,
) -> tuple[IndexConfig, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)

    chroma_dir = (base_dir / "chromadb").resolve()
    chroma_dir.mkdir(parents=True, exist_ok=True)

    notes_path = base_dir / "notes.json"
    if not notes_path.exists():
        notes_path.write_text("[]", encoding="utf-8")

    payload: dict[str, Any] = {
        "chromadb_path": str(chroma_dir),
        "collection": {
            "name": "test_collection",
            "description": "Test collection for unit tests",
            "json_file": str(notes_path.resolve()),
            "chunk_size": 1200,
            "force_recreate": False,
            "skip_ai_validation": False,
        },
        "provider": {
            "provider_type": "lmstudio",
            "embedding_model": "qwen-embed",
            "llm_model": "qwen-chat",
            "base_url": "http://localhost:1234/v1",
        },
    }

    if collection_overrides:
        payload["collection"].update(collection_overrides)
    if provider_overrides:
        payload["provider"].update(provider_overrides)

    config_path = base_dir / filename
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    config = load_index_config(str(config_path))
    return config, config_path


def make_chat_config(
    base_dir: Path,
    *,
    filename: str = "chat-config.json",
    provider_overrides: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> tuple[ChatConfig, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)

    conversation_dir = base_dir / "conversations"

    payload: dict[str, Any] = {
        "conversation_dir": str(conversation_dir),
        "mcp_server_url": "http://localhost:8000/mcp",
        "enable_streaming": False,
        "max_tool_iterations": 5,
        "system_prompt_file": None,
        "provider": {
            "provider_type": "ollama",
            "embedding_model": "mxbai-embed-large:latest",
            "llm_model": "llama3.1:8b",
            "base_url": "http://localhost:11434",
        },
    }

    if overrides:
        payload.update(overrides)
    if provider_overrides:
        payload["provider"].update(provider_overrides)

    config_path = base_dir / filename
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    config = load_chat_config_from_file(str(config_path))
    return config, config_path


def make_server_config(
    base_dir: Path,
    *,
    filename: str = "server-config.json",
    overrides: Mapping[str, Any] | None = None,
) -> tuple[ServerConfig, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)

    chroma_dir = (base_dir / "chromadb").resolve()
    chroma_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "chromadb_path": str(chroma_dir),
        "default_max_results": 5,
        "host": None,
        "port": None,
    }

    if overrides:
        payload.update(overrides)

    config_path = base_dir / filename
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    config = load_server_config(str(config_path))
    return config, config_path
