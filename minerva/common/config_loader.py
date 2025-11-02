import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from minerva.common.ai_config import AIProviderConfig, RateLimitConfig
from minerva.common.exceptions import ConfigError
from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True)

try:
    from jsonschema import Draft7Validator
    from jsonschema import ValidationError as JsonSchemaValidationError
except ImportError as error:
    logger.error("jsonschema library not installed. Run: pip install jsonschema")
    raise SystemExit(1) from error

ENV_VAR_PATTERN = r"^\$\{[A-Z_][A-Z0-9_]*\}$"


UNIFIED_CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["ai_providers", "indexing", "chat", "server"],
    "properties": {
        "ai_providers": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "provider_type"],
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
                        "description": "Unique identifier for the provider"
                    },
                    "display_name": {
                        "type": "string"
                    },
                    "provider_type": {
                        "type": "string",
                        "enum": ["ollama", "openai", "gemini", "azure", "anthropic", "lmstudio"],
                        "description": "Provider implementation"
                    },
                    "base_url": {
                        "type": ["string", "null"],
                        "description": "Default base URL for provider endpoints"
                    },
                    "api_key": {
                        "type": ["string", "null"],
                        "pattern": f"({ENV_VAR_PATTERN})|^$",
                        "description": "Environment variable placeholder for API key"
                    },
                    "embedding": {
                        "type": "object",
                        "required": ["model"],
                        "properties": {
                            "model": {"type": "string", "minLength": 1},
                            "base_url": {"type": ["string", "null"]},
                            "api_key": {
                                "type": ["string", "null"],
                                "pattern": f"({ENV_VAR_PATTERN})|^$"
                            }
                        },
                        "additionalProperties": False
                    },
                    "llm": {
                        "type": "object",
                        "required": ["model"],
                        "properties": {
                            "model": {"type": "string", "minLength": 1},
                            "base_url": {"type": ["string", "null"]},
                            "api_key": {
                                "type": ["string", "null"],
                                "pattern": f"({ENV_VAR_PATTERN})|^$"
                            }
                        },
                        "additionalProperties": False
                    },
                    "embedding_model": {
                        "type": "string",
                        "minLength": 1
                    },
                    "llm_model": {
                        "type": "string",
                        "minLength": 1
                    },
                    "rate_limit": {
                        "type": "object",
                        "properties": {
                            "requests_per_minute": {
                                "type": ["integer", "null"],
                                "minimum": 1
                            },
                            "concurrency": {
                                "type": ["integer", "null"],
                                "minimum": 1
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False,
                "anyOf": [
                    {"required": ["embedding"]},
                    {"required": ["embedding_model"]}
                ],
                "allOf": [
                    {
                        "anyOf": [
                            {"required": ["llm"]},
                            {"required": ["llm_model"]}
                        ]
                    }
                ]
            }
        },
        "indexing": {
            "type": "object",
            "required": ["chromadb_path", "collections"],
            "properties": {
                "chromadb_path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Absolute path to ChromaDB storage"
                },
                "default_chunk_size": {
                    "type": "integer",
                    "minimum": 300,
                    "maximum": 20000
                },
                "collections": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": [
                            "collection_name",
                            "description",
                            "json_file",
                            "ai_provider_id"
                        ],
                        "properties": {
                            "collection_name": {
                                "type": "string",
                                "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
                                "minLength": 1,
                                "maxLength": 63
                            },
                            "description": {
                                "type": "string",
                                "minLength": 10,
                                "maxLength": 2000
                            },
                            "json_file": {
                                "type": "string",
                                "minLength": 1
                            },
                            "chunk_size": {
                                "type": "integer",
                                "minimum": 300,
                                "maximum": 20000
                            },
                            "force_recreate": {
                                "type": "boolean"
                            },
                            "skip_ai_validation": {
                                "type": "boolean"
                            },
                            "ai_provider_id": {
                                "type": "string",
                                "minLength": 1
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            "additionalProperties": False
        },
        "chat": {
            "type": "object",
            "required": ["chat_provider_id", "mcp_server_url", "conversation_dir"],
            "properties": {
                "chat_provider_id": {
                    "type": "string",
                    "minLength": 1
                },
                "mcp_server_url": {
                    "type": "string",
                    "minLength": 1
                },
                "conversation_dir": {
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
                    "type": "string",
                    "minLength": 1
                }
            },
            "additionalProperties": False
        },
        "server": {
            "type": "object",
            "required": ["chromadb_path", "default_max_results"],
            "properties": {
                "chromadb_path": {
                    "type": "string",
                    "minLength": 1
                },
                "default_max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 15
                },
                "host": {
                    "type": "string",
                    "minLength": 1
                },
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535
                }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    provider_type: str
    embedding_model: str
    llm_model: str
    base_url: Optional[str]
    api_key: Optional[str]
    rate_limit: Optional[RateLimitConfig]
    display_name: Optional[str] = None

    def to_ai_provider_config(self) -> AIProviderConfig:
        return AIProviderConfig(
            provider_type=self.provider_type,
            embedding_model=self.embedding_model,
            llm_model=self.llm_model,
            base_url=self.base_url,
            api_key=self.api_key,
            rate_limit=self.rate_limit
        )


@dataclass(frozen=True)
class IndexingCollectionConfig:
    collection_name: str
    description: str
    json_file: str
    ai_provider_id: str
    chunk_size: int
    skip_ai_validation: bool
    force_recreate: bool


@dataclass(frozen=True)
class IndexingConfig:
    chromadb_path: str
    collections: tuple[IndexingCollectionConfig, ...]


@dataclass(frozen=True)
class ChatSection:
    chat_provider_id: str
    mcp_server_url: str
    conversation_dir: str
    enable_streaming: bool
    max_tool_iterations: int
    system_prompt_file: Optional[str]


@dataclass(frozen=True)
class ServerSection:
    chromadb_path: str
    default_max_results: int
    host: Optional[str]
    port: Optional[int]


@dataclass(frozen=True)
class UnifiedConfig:
    providers: Dict[str, ProviderDefinition]
    indexing: IndexingConfig
    chat: ChatSection
    server: ServerSection
    source_path: Path

    def get_provider(self, provider_id: str) -> ProviderDefinition:
        if provider_id not in self.providers:
            raise ConfigError(
                f"Unknown provider id: {provider_id}\n"
                f"  Defined providers: {', '.join(sorted(self.providers.keys())) or 'none'}"
            )
        return self.providers[provider_id]

    def get_ai_provider_config(self, provider_id: str) -> AIProviderConfig:
        return self.get_provider(provider_id).to_ai_provider_config()


def load_unified_config(config_path: str) -> UnifiedConfig:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"Configuration file not found: {config_path}\n"
            f"  Expected location: {path.resolve()}"
        )

    data = _read_json(path)
    _validate_schema(data, config_path)
    return _build_config(data, path)


def validate_unified_config(config_path: str) -> None:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"Configuration file not found: {config_path}\n"
            f"  Expected location: {path.resolve()}"
        )

    data = _read_json(path)
    _validate_schema(data, config_path)
    _build_config(data, path)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Invalid JSON syntax in configuration file: {path}\n"
            f"  Error: {error.msg} at line {error.lineno}, column {error.colno}"
        ) from error
    except Exception as error:
        raise ConfigError(f"Failed to read configuration file: {error}") from error

    if not isinstance(raw, dict):
        raise ConfigError(
            f"Configuration must be a JSON object at top level\n"
            f"  Found: {type(raw).__name__}"
        )

    return raw


def _validate_schema(data: Dict[str, Any], config_path: str) -> None:
    validator = Draft7Validator(UNIFIED_CONFIG_SCHEMA)
    try:
        validator.validate(data)
    except JsonSchemaValidationError as error:
        path = " → ".join(str(piece) for piece in error.path) or "root"
        raise ConfigError(
            f"Schema validation error in configuration file: {config_path}\n"
            f"  Field: {path}\n"
            f"  Error: {error.message}"
        ) from error


def _build_config(data: Dict[str, Any], source_path: Path) -> UnifiedConfig:
    base_dir = source_path.parent
    providers = _build_providers(data.get("ai_providers", []), source_path)
    indexing_section = _build_indexing_section(data["indexing"], providers, base_dir)
    chat_section = _build_chat_section(data["chat"], providers, base_dir)
    server_section = _build_server_section(data["server"], base_dir)

    return UnifiedConfig(
        providers=providers,
        indexing=indexing_section,
        chat=chat_section,
        server=server_section,
        source_path=source_path
    )


def _build_providers(raw_providers: List[Dict[str, Any]], source_path: Path) -> Dict[str, ProviderDefinition]:
    providers: Dict[str, ProviderDefinition] = {}

    for provider_data in raw_providers:
        provider_id = provider_data["id"]
        if provider_id in providers:
            raise ConfigError(
                f"Duplicate provider id detected: {provider_id}\n"
                f"  File: {source_path}"
            )

        provider = _build_provider(provider_data, provider_id, source_path)
        providers[provider_id] = provider

    return providers


def _build_provider(provider_data: Dict[str, Any], provider_id: str, source_path: Path) -> ProviderDefinition:
    embedding_model = _resolve_model(provider_data, "embedding", provider_id, source_path)
    llm_model = _resolve_model(provider_data, "llm", provider_id, source_path)

    base_url = _resolve_endpoint(provider_data, "base_url")
    api_key = _resolve_secret(provider_data, "api_key")

    embedding_block = provider_data.get("embedding") or {}
    llm_block = provider_data.get("llm") or {}

    if not base_url:
        base_url = embedding_block.get("base_url") or llm_block.get("base_url")

    if not api_key:
        api_key = embedding_block.get("api_key") or llm_block.get("api_key")

    rate_limit = _resolve_rate_limit(provider_data.get("rate_limit"))

    return ProviderDefinition(
        id=provider_id,
        provider_type=provider_data["provider_type"],
        embedding_model=embedding_model,
        llm_model=llm_model,
        base_url=_strip(value=base_url),
        api_key=_strip(value=api_key),
        rate_limit=rate_limit,
        display_name=_strip(value=provider_data.get("display_name"))
    )


def _resolve_model(
    provider_data: Dict[str, Any],
    key: str,
    provider_id: str,
    source_path: Path
) -> str:
    explicit_key = f"{key}_model"
    model = provider_data.get(explicit_key)

    if not model:
        block = provider_data.get(key)
        if isinstance(block, dict):
            model = block.get("model")

    if not model:
        raise ConfigError(
            f"Missing {key} model for provider '{provider_id}'\n"
            f"  File: {source_path}\n"
            f"  Provide either '{explicit_key}' or an '{key}' block with a 'model' field"
        )

    return str(model)


def _resolve_endpoint(provider_data: Dict[str, Any], key: str) -> Optional[str]:
    value = provider_data.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _resolve_secret(provider_data: Dict[str, Any], key: str) -> Optional[str]:
    value = provider_data.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _resolve_rate_limit(raw: Optional[Dict[str, Any]]) -> Optional[RateLimitConfig]:
    if not raw:
        return None

    requests_per_minute = raw.get("requests_per_minute")
    concurrency = raw.get("concurrency")

    if requests_per_minute is None and concurrency is None:
        return None

    return RateLimitConfig(
        requests_per_minute=requests_per_minute,
        concurrency=concurrency
    )


def _build_indexing_section(
    indexing_data: Dict[str, Any],
    providers: Dict[str, ProviderDefinition],
    base_dir: Path
) -> IndexingConfig:
    chromadb_path = _resolve_path(indexing_data["chromadb_path"], base_dir)
    _ensure_absolute_path(chromadb_path, "indexing.chromadb_path")

    default_chunk_size = indexing_data.get("default_chunk_size", 1200)

    collections: List[IndexingCollectionConfig] = []
    seen_names: set[str] = set()

    for raw_collection in indexing_data.get("collections", []):
        collection_name = raw_collection["collection_name"]
        if collection_name in seen_names:
            raise ConfigError(
                f"Duplicate collection name detected: {collection_name}\n"
                f"  Section: indexing.collections"
            )

        provider_id = raw_collection["ai_provider_id"]
        if provider_id not in providers:
            raise ConfigError(
                f"Unknown provider id '{provider_id}' referenced by collection '{collection_name}'"
            )

        chunk_size = raw_collection.get("chunk_size", default_chunk_size)

        collection = IndexingCollectionConfig(
            collection_name=collection_name,
            description=raw_collection["description"].strip(),
            json_file=_resolve_path(raw_collection["json_file"], base_dir),
            ai_provider_id=provider_id,
            chunk_size=int(chunk_size),
            skip_ai_validation=bool(raw_collection.get("skip_ai_validation", False)),
            force_recreate=bool(raw_collection.get("force_recreate", False))
        )

        collections.append(collection)
        seen_names.add(collection_name)

    return IndexingConfig(
        chromadb_path=chromadb_path,
        collections=tuple(collections)
    )


def _build_chat_section(
    chat_data: Dict[str, Any],
    providers: Dict[str, ProviderDefinition],
    base_dir: Path
) -> ChatSection:
    provider_id = chat_data["chat_provider_id"]
    if provider_id not in providers:
        raise ConfigError(
            f"Unknown provider id referenced in chat section: {provider_id}"
        )

    mcp_url = chat_data["mcp_server_url"].strip()
    _validate_mcp_url(mcp_url)

    conversation_dir = _resolve_path(chat_data["conversation_dir"], base_dir)

    enable_streaming = bool(chat_data.get("enable_streaming", False))
    max_tool_iterations = int(chat_data.get("max_tool_iterations", 5))
    system_prompt_file = chat_data.get("system_prompt_file")
    if system_prompt_file:
        system_prompt_file = _resolve_path(system_prompt_file, base_dir)

    return ChatSection(
        chat_provider_id=provider_id,
        mcp_server_url=mcp_url,
        conversation_dir=conversation_dir,
        enable_streaming=enable_streaming,
        max_tool_iterations=max_tool_iterations,
        system_prompt_file=system_prompt_file
    )


def _build_server_section(server_data: Dict[str, Any], base_dir: Path) -> ServerSection:
    chromadb_path = _resolve_path(server_data["chromadb_path"], base_dir)
    _ensure_absolute_path(chromadb_path, "server.chromadb_path")

    default_max_results = int(server_data["default_max_results"])

    host = server_data.get("host")
    if host is not None:
        host = str(host).strip() or None

    port = server_data.get("port")
    if port is not None:
        port = int(port)

    return ServerSection(
        chromadb_path=chromadb_path,
        default_max_results=default_max_results,
        host=host,
        port=port
    )


def _resolve_path(value: str, base_dir: Path) -> str:
    expanded = os.path.expanduser(str(value).strip())
    path = Path(expanded)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return str(path)


def _ensure_absolute_path(path_value: str, field_name: str) -> None:
    if not Path(path_value).is_absolute():
        raise ConfigError(
            f"Expected absolute path for {field_name}\n"
            f"  Value: {path_value}"
        )


def _strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _validate_mcp_url(url: str) -> None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ConfigError(
            f"Invalid MCP server URL: {url}\n"
            f"  Expected format: http(s)://host[:port]/path"
        )
