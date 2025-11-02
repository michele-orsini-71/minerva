import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

from minerva.common.ai_config import AIProviderConfig, RateLimitConfig, resolve_env_variable
from minerva.common.exceptions import ChatConfigError
from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True)

try:
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
except ImportError as error:
    logger.error("jsonschema library not installed. Run: pip install jsonschema")
    raise SystemExit(1) from error

@dataclass(frozen=True)
class ChatConfig:
    chromadb_path: str
    ai_provider: AIProviderConfig
    conversation_dir: str
    default_max_results: int
    enable_streaming: bool

    def __post_init__(self):
        if not self.chromadb_path:
            raise ValueError("chromadb_path cannot be empty")
        if not os.path.isabs(self.chromadb_path):
            raise ValueError(
                f"chromadb_path must be an absolute path, got: {self.chromadb_path}"
            )


CHAT_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["chromadb_path", "ai_provider"],
    "properties": {
        "chromadb_path": {
            "type": "string",
            "minLength": 1,
            "description": "Absolute path to ChromaDB storage location"
        },
        "ai_provider": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["ollama", "openai", "gemini", "azure", "anthropic", "lmstudio"],
                    "description": "AI provider type"
                },
                "embedding": {
                    "type": "object",
                    "required": ["model"],
                    "properties": {
                        "model": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Embedding model name"
                        },
                        "base_url": {
                            "type": ["string", "null"],
                            "description": "Custom base URL for the provider API"
                        },
                        "api_key": {
                            "type": ["string", "null"],
                            "description": "API key as environment variable template (e.g., ${OPENAI_API_KEY}) or null"
                        }
                    },
                    "additionalProperties": False
                },
                "llm": {
                    "type": "object",
                    "required": ["model"],
                    "properties": {
                        "model": {
                            "type": "string",
                            "minLength": 1,
                            "description": "LLM model name for chat completions"
                        },
                        "base_url": {
                            "type": ["string", "null"],
                            "description": "Custom base URL for the provider API"
                        },
                        "api_key": {
                            "type": ["string", "null"],
                            "description": "API key as environment variable template (e.g., ${OPENAI_API_KEY}) or null"
                        }
                    },
                    "additionalProperties": False
                },
                "rate_limit": {
                    "type": "object",
                    "properties": {
                        "requests_per_minute": {
                            "type": ["integer", "null"],
                            "minimum": 1,
                            "description": "Maximum number of requests per minute"
                        },
                        "concurrency": {
                            "type": ["integer", "null"],
                            "minimum": 1,
                            "description": "Maximum number of concurrent requests"
                        }
                    },
                    "additionalProperties": False,
                    "description": "Optional rate limiting configuration"
                }
            },
            "required": ["type", "embedding", "llm"],
            "additionalProperties": False,
            "description": "AI provider configuration for embeddings and chat"
        },
        "conversation_dir": {
            "type": "string",
            "description": "Directory for storing conversation history (default: ~/.minerva/conversations)"
        },
        "default_max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 15,
            "description": "Default number of search results to return (default: 3)"
        },
        "enable_streaming": {
            "type": "boolean",
            "description": "Enable streaming responses (default: true)"
        }
    },
    "additionalProperties": False
}


def validate_config_schema(data: Dict[str, Any], config_path: str) -> None:
    try:
        validate(instance=data, schema=CHAT_CONFIG_SCHEMA)
    except JsonSchemaValidationError as error:
        error_path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"

        if "is a required property" in error.message:
            missing_field = error.message.split("'")[1]
            raise ChatConfigError(
                f"Missing required field in configuration file: {config_path}\n"
                f"  Missing field: '{missing_field}'\n"
                f"  Location: {error_path}\n"
                f"  Suggestion: Add the required field to your config"
            )
        elif "is not of type" in error.message:
            raise ChatConfigError(
                f"Type validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {error.message}"
            )
        elif "is not one of" in error.message and "ai_provider" in error_path:
            raise ChatConfigError(
                f"Invalid AI provider type in: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {error.message}\n"
                f"  Supported types: ollama, openai, gemini, azure, anthropic, lmstudio"
            )
        elif "Additional properties are not allowed" in error.message:
            raise ChatConfigError(
                f"Unknown fields in configuration file: {config_path}\n"
                f"  Error: {error.message}\n"
                f"  Allowed fields: {', '.join(CHAT_CONFIG_SCHEMA['properties'].keys())}"
            )
        else:
            raise ChatConfigError(
                f"Schema validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {error.message}"
            )


def validate_config_file_exists(config_path: str) -> Path:
    config_file = Path(config_path)

    if not config_file.exists():
        raise ChatConfigError(
            f"Configuration file not found: {config_path}\n"
            f"  Expected location: {config_file.absolute()}\n"
            f"  Suggestion: Create a JSON config file with required fields:\n"
            f"    - chromadb_path (required, absolute path to ChromaDB)\n"
            f"    - ai_provider (required, AI provider configuration)\n"
            f"    - conversation_dir (optional, default: ~/.minerva/conversations)\n"
            f"    - default_max_results (optional, default: 3)\n"
            f"    - enable_streaming (optional, default: true)"
        )

    return config_file


def read_json_config_file(config_file: Path, config_path: str) -> Dict[str, Any]:
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as error:
        raise ChatConfigError(
            f"Invalid JSON syntax in configuration file: {config_path}\n"
            f"  Error: {error.msg} at line {error.lineno}, column {error.colno}\n"
            f"  Suggestion: Validate your JSON using a JSON validator or linter"
        )
    except Exception as error:
        raise ChatConfigError(
            f"Failed to read configuration file: {config_path}\n"
            f"  Error: {error}"
        )

    if not isinstance(data, dict):
        raise ChatConfigError(
            f"Configuration file must contain a JSON object, got {type(data).__name__}\n"
            f"  File: {config_path}"
        )

    return data


def expand_path(path: str) -> str:
    expanded = os.path.expanduser(path)
    return os.path.abspath(expanded)


def create_ai_provider_config(ai_provider_data: Dict[str, Any]) -> AIProviderConfig:
    provider_type = ai_provider_data.get('type') or ai_provider_data.get('provider_type')

    if not provider_type:
        raise ChatConfigError("ai_provider configuration missing 'type' field")

    embedding_config = ai_provider_data['embedding']
    llm_config = ai_provider_data['llm']

    embedding_model = embedding_config['model']
    llm_model = llm_config['model']

    base_url = embedding_config.get('base_url') or llm_config.get('base_url')
    api_key = embedding_config.get('api_key') or llm_config.get('api_key')

    rate_limit = None  # Chat command ignores rate limiting; reserved for MCP server configuration

    return AIProviderConfig(
        provider_type=provider_type,
        embedding_model=embedding_model,
        llm_model=llm_model,
        base_url=base_url,
        api_key=api_key,
        rate_limit=rate_limit
    )


def extract_config_fields(data: Dict[str, Any]) -> ChatConfig:
    chromadb_path = expand_path(data['chromadb_path'])

    ai_provider = create_ai_provider_config(data['ai_provider'])

    conversation_dir = data.get('conversation_dir', '~/.minerva/conversations')
    conversation_dir = expand_path(conversation_dir)

    default_max_results = data.get('default_max_results', 3)
    enable_streaming = data.get('enable_streaming', True)

    return ChatConfig(
        chromadb_path=chromadb_path,
        ai_provider=ai_provider,
        conversation_dir=conversation_dir,
        default_max_results=default_max_results,
        enable_streaming=enable_streaming
    )


def load_chat_config(config_path: str) -> ChatConfig:
    try:
        config_file = validate_config_file_exists(config_path)

        data = read_json_config_file(config_file, config_path)

        validate_config_schema(data, config_path)

        return extract_config_fields(data)

    except ChatConfigError:
        raise
    except Exception as error:
        raise ChatConfigError(
            f"Unexpected error loading configuration: {config_path}\n"
            f"  Error: {error}"
        )
