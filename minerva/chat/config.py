from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from jsonschema import Draft7Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from minerva.common.ai_config import (
    AIProviderConfig,
    AI_PROVIDER_JSON_SCHEMA,
    build_ai_provider_config,
)
from minerva.common.exceptions import ChatConfigError, ConfigError


CHAT_CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "conversation_dir",
        "mcp_server_url",
        "provider"
    ],
    "properties": {
        "conversation_dir": {
            "type": "string",
            "minLength": 1
        },
        "mcp_server_url": {
            "type": "string",
            "minLength": 1
        },
        "enable_streaming": {
            "type": "boolean"
        },
        "max_tool_iterations": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10
        },
        "system_prompt_file": {
            "type": ["string", "null"],
            "minLength": 1
        },
        "provider": copy.deepcopy(AI_PROVIDER_JSON_SCHEMA)
    },
    "additionalProperties": False
}


@dataclass(frozen=True)
class ChatConfig:
    llm_provider: AIProviderConfig
    conversation_dir: str
    enable_streaming: bool
    mcp_server_url: str
    max_tool_iterations: int
    system_prompt_file: Optional[str]
    source_path: Optional[Path] = None

    @property
    def ai_provider(self) -> AIProviderConfig:
        return self.llm_provider


def load_chat_config_from_file(config_path: str) -> ChatConfig:
    path = Path(config_path)

    if not path.exists():
        raise ChatConfigError(
            f"Chat configuration file not found: {config_path}\n"
            f"  Expected location: {path.resolve()}"
        )

    payload = _read_json(path)
    _validate_schema(payload, path)

    try:
        return _build_chat_config(payload, path)
    except ConfigError as error:
        raise ChatConfigError(str(error)) from error


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as error:
        raise ChatConfigError(
            f"Invalid JSON syntax in configuration file: {path}\n"
            f"  Error: {error.msg} at line {error.lineno}, column {error.colno}"
        ) from error
    except Exception as error:
        raise ChatConfigError(f"Failed to read configuration file: {error}") from error

    if not isinstance(data, dict):
        raise ChatConfigError(
            f"Configuration must be a JSON object at the root\n"
            f"  File: {path}"
        )

    return data


def _validate_schema(payload: Dict[str, Any], path: Path) -> None:
    validator = Draft7Validator(CHAT_CONFIG_SCHEMA)
    try:
        validator.validate(payload)
    except JsonSchemaValidationError as error:
        location = " → ".join(str(piece) for piece in error.path) or "root"
        raise ChatConfigError(
            f"Schema validation error in chat configuration: {path}\n"
            f"  Field: {location}\n"
            f"  Error: {error.message}"
        ) from error


def _build_chat_config(payload: Dict[str, Any], path: Path) -> ChatConfig:
    base_dir = path.parent

    conversation_dir_raw = str(payload["conversation_dir"]).strip()
    if not conversation_dir_raw:
        raise ChatConfigError(
            "conversation_dir cannot be empty after trimming whitespace\n"
            f"  File: {path}"
        )

    conversation_dir = _resolve_path(conversation_dir_raw, base_dir)
    _ensure_directory(conversation_dir)

    mcp_server_url = str(payload["mcp_server_url"]).strip()
    _validate_mcp_url(mcp_server_url, path)

    enable_streaming = bool(payload.get("enable_streaming", False))

    try:
        max_tool_iterations = int(payload.get("max_tool_iterations", 5))
    except (TypeError, ValueError):
        raise ChatConfigError(
            "max_tool_iterations must be an integer value\n"
            f"  File: {path}"
        )

    if max_tool_iterations < 1 or max_tool_iterations > 10:
        raise ChatConfigError(
            "max_tool_iterations must be between 1 and 10\n"
            f"  Value: {max_tool_iterations}\n"
            f"  File: {path}"
        )

    system_prompt_file = payload.get("system_prompt_file")
    system_prompt_path: Optional[str] = None
    if system_prompt_file:
        trimmed = str(system_prompt_file).strip()
        if not trimmed:
            raise ChatConfigError(
                "system_prompt_file cannot be empty string\n"
                f"  File: {path}"
            )
        system_prompt_path = _resolve_path(trimmed, base_dir)

    llm_provider = build_ai_provider_config(
        payload["provider"],
        source_path=path,
        context="provider"
    )

    return ChatConfig(
        llm_provider=llm_provider,
        conversation_dir=conversation_dir,
        enable_streaming=enable_streaming,
        mcp_server_url=mcp_server_url,
        max_tool_iterations=max_tool_iterations,
        system_prompt_file=system_prompt_path,
        source_path=path
    )


def _resolve_path(value: Any, base_dir: Path) -> str:
    path = Path(str(value).strip()).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return str(path)


def _ensure_directory(directory: str) -> None:
    path = Path(directory)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as error:
        raise ChatConfigError(
            f"Failed to create conversation directory: {directory}\n"
            f"  Error: {error}"
        ) from error


def _validate_mcp_url(url: str, source_path: Path) -> None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ChatConfigError(
            f"Invalid MCP server URL: {url}\n"
            f"  File: {source_path}\n"
            f"  Expected format: http(s)://host[:port]/path"
        )

