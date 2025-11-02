from pathlib import Path

import pytest

from minerva.chat.config import build_chat_config, ChatConfig, ChatConfigError
from minerva.common.config_loader import (
    UnifiedConfig,
    ProviderDefinition,
    IndexingConfig,
    IndexingCollectionConfig,
    ChatSection,
    ServerSection,
)


def make_unified_config(base_dir: Path, max_iterations: int = 5) -> UnifiedConfig:
    chroma_path = base_dir / "chromadb"
    chroma_path.mkdir(parents=True, exist_ok=True)

    notes_path = base_dir / "notes.json"
    notes_path.write_text("[]", encoding="utf-8")

    providers = {
        "lmstudio-local": ProviderDefinition(
            id="lmstudio-local",
            provider_type="lmstudio",
            embedding_model="qwen-embed",
            llm_model="qwen-chat",
            base_url="http://localhost:1234/v1",
            api_key=None,
            rate_limit=None,
            display_name=None
        )
    }

    indexing = IndexingConfig(
        chromadb_path=str(chroma_path),
        collections=(
            IndexingCollectionConfig(
                collection_name="unit-tests",
                description="Unit test collection",
                json_file=str(notes_path),
                ai_provider_id="lmstudio-local",
                chunk_size=1200,
                skip_ai_validation=False,
                force_recreate=False
            ),
        )
    )

    conversation_dir = base_dir / "conversations"

    chat_section = ChatSection(
        chat_provider_id="lmstudio-local",
        mcp_server_url="http://localhost:8000/mcp",
        conversation_dir=str(conversation_dir),
        enable_streaming=False,
        max_tool_iterations=max_iterations,
        system_prompt_file=None
    )

    server_section = ServerSection(
        chromadb_path=str(chroma_path),
        default_max_results=5,
        host=None,
        port=None
    )

    return UnifiedConfig(
        providers=providers,
        indexing=indexing,
        chat=chat_section,
        server=server_section,
        source_path=base_dir / "config.json"
    )


def test_build_chat_config_success(tmp_path: Path):
    unified_config = make_unified_config(tmp_path)

    chat_config = build_chat_config(unified_config)

    assert isinstance(chat_config, ChatConfig)
    assert Path(chat_config.conversation_dir).exists()
    assert chat_config.ai_provider.provider_type == "lmstudio"
    assert chat_config.mcp_server_url == "http://localhost:8000/mcp"


def test_build_chat_config_fails_when_conversation_dir_unwritable(tmp_path: Path):
    unified_config = make_unified_config(tmp_path)
    convo_path = Path(unified_config.chat.conversation_dir)
    convo_path.write_text("file", encoding="utf-8")

    with pytest.raises(ChatConfigError):
        build_chat_config(unified_config)


def test_build_chat_config_rejects_invalid_iteration_count(tmp_path: Path):
    unified_config = make_unified_config(tmp_path, max_iterations=0)

    with pytest.raises(ChatConfigError):
        build_chat_config(unified_config)
