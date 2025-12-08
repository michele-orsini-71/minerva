import json
import os
from pathlib import Path
from typing import Any

from minerva_kb.constants import MINERVA_KB_APP_DIR

INDEX_SUFFIX = "-index.json"
WATCHER_SUFFIX = "-watcher.json"


def load_index_config(collection_name: str) -> dict[str, Any]:
    path = _config_path(collection_name, INDEX_SUFFIX)
    data = _read_json(path)
    _validate_index_config(data, path)
    return data


def load_watcher_config(collection_name: str) -> dict[str, Any]:
    path = _config_path(collection_name, WATCHER_SUFFIX)
    data = _read_json(path)
    _validate_watcher_config(data, path)
    return data


def save_index_config(collection_name: str, config: dict[str, Any]) -> Path:
    path = _config_path(collection_name, INDEX_SUFFIX)
    _validate_index_config(config, path)
    _write_json(path, config)
    return path


def save_watcher_config(collection_name: str, config: dict[str, Any]) -> Path:
    path = _config_path(collection_name, WATCHER_SUFFIX)
    _validate_watcher_config(config, path)
    _write_json(path, config)
    return path


def _config_path(collection_name: str, suffix: str) -> Path:
    name = collection_name.strip()
    if not name:
        raise ValueError("Collection name cannot be empty")
    return MINERVA_KB_APP_DIR / f"{name}{suffix}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _write_json(path: Path, data: dict[str, Any]) -> None:
    _ensure_app_dir()
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    temp_path.replace(path)
    try:
        os.chmod(path, 0o600)
    except PermissionError:
        pass


def _ensure_app_dir() -> None:
    MINERVA_KB_APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(MINERVA_KB_APP_DIR, 0o700)
    except PermissionError:
        pass


def _validate_index_config(data: dict[str, Any], path: Path | None) -> None:
    _require_str(data, "chromadb_path", path)
    collection = _require_dict(data, "collection", path)
    _require_str(collection, "name", path)
    _require_str(collection, "description", path)
    _require_str(collection, "json_file", path)
    chunk_size = collection.get("chunk_size")
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError(_error_prefix(path, "collection.chunk_size must be positive integer"))
    provider = _require_dict(data, "provider", path)
    _require_str(provider, "provider_type", path)
    _require_str(provider, "embedding_model", path)
    _require_str(provider, "llm_model", path)
    if "api_key" in provider and provider["api_key"] is not None:
        _require_str(provider, "api_key", path)


def _validate_watcher_config(data: dict[str, Any], path: Path | None) -> None:
    _require_str(data, "repository_path", path)
    _require_str(data, "collection_name", path)
    _require_str(data, "extracted_json_path", path)
    _require_str(data, "index_config_path", path)
    debounce = data.get("debounce_seconds")
    if not isinstance(debounce, (int, float)) or debounce <= 0:
        raise ValueError(_error_prefix(path, "debounce_seconds must be positive number"))
    include_extensions = data.get("include_extensions")
    _require_string_list(include_extensions, "include_extensions", path)
    ignore_patterns = data.get("ignore_patterns")
    _require_string_list(ignore_patterns, "ignore_patterns", path)


def _require_dict(data: dict[str, Any], key: str, path: Path | None) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(_error_prefix(path, f"{key} must be an object"))
    return value


def _require_str(data: dict[str, Any], key: str, path: Path | None) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(_error_prefix(path, f"{key} must be a non-empty string"))
    return value


def _require_string_list(value: Any, key: str, path: Path | None) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(_error_prefix(path, f"{key} must be a non-empty list"))
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(_error_prefix(path, f"{key} must contain non-empty strings"))


def _error_prefix(path: Path | None, message: str) -> str:
    if path is None:
        return message
    return f"{message} ({path})"
