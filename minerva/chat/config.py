from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from minerva.common.ai_config import AIProviderConfig
from minerva.common.config_loader import UnifiedConfig
from minerva.common.exceptions import ChatConfigError


@dataclass(frozen=True)
class ChatConfig:
    ai_provider: AIProviderConfig
    conversation_dir: str
    chromadb_path: str
    enable_streaming: bool
    mcp_server_url: str
    max_tool_iterations: int
    system_prompt_file: Optional[str]


def build_chat_config(unified_config: UnifiedConfig) -> ChatConfig:
    chat_section = unified_config.chat
    server_section = unified_config.server

    ai_provider_config = unified_config.get_ai_provider_config(chat_section.chat_provider_id)

    conversation_dir = chat_section.conversation_dir
    if not conversation_dir:
        raise ChatConfigError("conversation_dir must be provided in chat configuration")

    conversation_path = Path(conversation_dir)
    try:
        conversation_path.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        raise ChatConfigError(
            f"Failed to create conversation directory: {conversation_dir}\n"
            f"  Error: {error}"
        ) from error

    chromadb_path = server_section.chromadb_path
    if not chromadb_path:
        raise ChatConfigError("Server chromadb_path is missing from configuration")

    if chat_section.max_tool_iterations < 1:
        raise ChatConfigError("max_tool_iterations must be at least 1")

    return ChatConfig(
        ai_provider=ai_provider_config,
        conversation_dir=str(conversation_path),
        chromadb_path=chromadb_path,
        enable_streaming=chat_section.enable_streaming,
        mcp_server_url=chat_section.mcp_server_url,
        max_tool_iterations=chat_section.max_tool_iterations,
        system_prompt_file=chat_section.system_prompt_file,
    )
