from __future__ import annotations

import json
import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from minerva.common.ai_config import (
    AIProviderConfig,
    AI_PROVIDER_JSON_SCHEMA,
    build_ai_provider_config,
)
from minerva.common.exceptions import ConfigError


INDEX_CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["chromadb_path", "collection", "provider"],
    "properties": {
        "chromadb_path": {
            "type": "string",
            "minLength": 1
        },
        "collection": {
            "type": "object",
            "required": ["name", "description", "json_file"],
            "properties": {
                "name": {
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
                }
            },
            "additionalProperties": False
        },
        "provider": copy.deepcopy(AI_PROVIDER_JSON_SCHEMA)
    },
    "additionalProperties": False
}


@dataclass(frozen=True)
class CollectionConfig:
    name: str
    description: str
    json_file: str
    chunk_size: int
    force_recreate: bool
    skip_ai_validation: bool


@dataclass(frozen=True)
class IndexConfig:
    chromadb_path: str
    collection: CollectionConfig
    provider: AIProviderConfig
    source_path: Path


def load_index_config(config_path: str) -> IndexConfig:
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(
            f"Index configuration file not found: {config_path}\n"
            f"  Expected location: {path.resolve()}"
        )

    data = _read_json(path)
    _validate_schema(data, path)
    return _build_index_config(data, path)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Invalid JSON syntax in configuration file: {path}\n"
            f"  Error: {error.msg} at line {error.lineno}, column {error.colno}"
        ) from error
    except Exception as error:
        raise ConfigError(f"Failed to read configuration file: {error}") from error

    if not isinstance(payload, dict):
        raise ConfigError(
            f"Configuration must be a JSON object at the root\n"
            f"  File: {path}"
        )

    return payload


def _validate_schema(payload: Dict[str, Any], path: Path) -> None:
    validator = Draft7Validator(INDEX_CONFIG_SCHEMA)
    try:
        validator.validate(payload)
    except JsonSchemaValidationError as error:
        location = " → ".join(str(piece) for piece in error.path) or "root"
        raise ConfigError(
            f"Schema validation error in index configuration: {path}\n"
            f"  Field: {location}\n"
            f"  Error: {error.message}"
        ) from error


def _build_index_config(payload: Dict[str, Any], path: Path) -> IndexConfig:
    base_dir = path.parent

    chromadb_path = _resolve_path(payload["chromadb_path"], base_dir)
    _ensure_absolute_path(chromadb_path, "chromadb_path", path)

    collection_block = payload["collection"]
    collection = _build_collection(collection_block, base_dir, path)

    provider_block = payload["provider"]
    provider = build_ai_provider_config(provider_block, source_path=path, context="provider")

    return IndexConfig(
        chromadb_path=chromadb_path,
        collection=collection,
        provider=provider,
        source_path=path
    )


def _build_collection(block: Dict[str, Any], base_dir: Path, source_path: Path) -> CollectionConfig:
    name = block["name"].strip()
    if not name:
        raise ConfigError(
            "Collection name cannot be empty after trimming whitespace\n"
            f"  File: {source_path}"
        )

    description = block["description"].strip()
    if not description:
        raise ConfigError(
            "Collection description cannot be empty after trimming whitespace\n"
            f"  File: {source_path}"
        )
    json_file = _resolve_path(block["json_file"], base_dir)

    try:
        chunk_size = int(block.get("chunk_size", 1200))
    except (TypeError, ValueError):
        raise ConfigError(
            "chunk_size must be an integer value\n"
            f"  File: {source_path}"
        )
    if chunk_size < 300 or chunk_size > 20000:
        raise ConfigError(
            f"chunk_size must be between 300 and 20000 characters\n"
            f"  Value: {chunk_size}\n"
            f"  File: {source_path}"
        )

    force_recreate = bool(block.get("force_recreate", False))
    skip_validation = bool(block.get("skip_ai_validation", False))

    return CollectionConfig(
        name=name,
        description=description,
        json_file=json_file,
        chunk_size=chunk_size,
        force_recreate=force_recreate,
        skip_ai_validation=skip_validation
    )


def _resolve_path(value: Any, base_dir: Path) -> str:
    path = Path(str(value).strip()).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return str(path)


def _ensure_absolute_path(value: str, field_name: str, source_path: Path) -> None:
    if not Path(value).is_absolute():
        raise ConfigError(
            f"Expected absolute path for {field_name}\n"
            f"  Value: {value}\n"
            f"  File: {source_path}"
        )
