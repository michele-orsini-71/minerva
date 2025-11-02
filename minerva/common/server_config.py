from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator
from jsonschema import ValidationError as JsonSchemaValidationError

from minerva.common.exceptions import ConfigError


SERVER_CONFIG_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
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
            "type": ["string", "null"],
            "minLength": 1
        },
        "port": {
            "type": ["integer", "null"],
            "minimum": 1,
            "maximum": 65535
        }
    },
    "additionalProperties": False
}


@dataclass(frozen=True)
class ServerConfig:
    chromadb_path: str
    default_max_results: int
    host: str | None
    port: int | None
    source_path: Path


def load_server_config(config_path: str) -> ServerConfig:
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(
            f"Server configuration file not found: {config_path}\n"
            f"  Expected location: {path.resolve()}"
        )

    payload = _read_json(path)
    _validate_schema(payload, path)
    return _build_server_config(payload, path)


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Invalid JSON syntax in configuration file: {path}\n"
            f"  Error: {error.msg} at line {error.lineno}, column {error.colno}"
        ) from error
    except Exception as error:
        raise ConfigError(f"Failed to read configuration file: {error}") from error

    if not isinstance(data, dict):
        raise ConfigError(
            f"Configuration must be a JSON object at the root\n"
            f"  File: {path}"
        )

    return data


def _validate_schema(payload: Dict[str, Any], path: Path) -> None:
    validator = Draft7Validator(SERVER_CONFIG_SCHEMA)
    try:
        validator.validate(payload)
    except JsonSchemaValidationError as error:
        location = " → ".join(str(piece) for piece in error.path) or "root"
        raise ConfigError(
            f"Schema validation error in server configuration: {path}\n"
            f"  Field: {location}\n"
            f"  Error: {error.message}"
        ) from error


def _build_server_config(payload: Dict[str, Any], path: Path) -> ServerConfig:
    base_dir = path.parent

    chromadb_path = _resolve_path(payload["chromadb_path"], base_dir)
    _ensure_absolute_path(chromadb_path, "chromadb_path", path)

    try:
        default_max_results = int(payload["default_max_results"])
    except (TypeError, ValueError):
        raise ConfigError(
            "default_max_results must be an integer\n"
            f"  File: {path}"
        )

    if default_max_results < 1 or default_max_results > 15:
        raise ConfigError(
            "default_max_results must be between 1 and 15\n"
            f"  Value: {default_max_results}\n"
            f"  File: {path}"
        )

    host = payload.get("host")
    host_value = _clean_host(host, path)

    port_field = payload.get("port")
    port_value = _clean_port(port_field, path)

    return ServerConfig(
        chromadb_path=chromadb_path,
        default_max_results=default_max_results,
        host=host_value,
        port=port_value,
        source_path=path
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


def _clean_host(host: Any, source_path: Path) -> str | None:
    if host is None:
        return None

    host_str = str(host).strip()
    if not host_str:
        raise ConfigError(
            "Host value cannot be empty string\n"
            f"  File: {source_path}"
        )

    return host_str


def _clean_port(port: Any, source_path: Path) -> int | None:
    if port is None:
        return None

    try:
        port_int = int(port)
    except (TypeError, ValueError):
        raise ConfigError(
            "Port must be an integer when provided\n"
            f"  File: {source_path}"
        )

    if port_int < 1 or port_int > 65535:
        raise ConfigError(
            "Port must be between 1 and 65535\n"
            f"  Value: {port_int}\n"
            f"  File: {source_path}"
        )

    return port_int
