import json
from datetime import datetime
from pathlib import Path
from typing import Any

from chromadb import PersistentClient

from minerva_kb.constants import CHROMADB_DIR, MINERVA_KB_APP_DIR, PROVIDER_DISPLAY_NAMES
from minerva_kb.utils.config_loader import load_index_config, load_watcher_config
from minerva_kb.utils.process_manager import find_watcher_pid


COLORS = {
    "header": "\033[95m",
    "bold": "\033[1m",
    "end": "\033[0m",
}


def run_status(collection_name: str) -> int:
    watcher_path = MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"
    if not watcher_path.exists():
        _display_error(f"Collection '{collection_name}' not found")
        _suggest_available_collections()
        return 1

    state = _gather_state(collection_name, watcher_path)
    exit_code = _determine_exit_code(state)
    _print_state(collection_name, state)
    return exit_code


def _gather_state(collection_name: str, watcher_path: Path) -> dict[str, Any]:
    watcher_config = _safe_load(lambda: load_watcher_config(collection_name))
    index_config = _safe_load(lambda: load_index_config(collection_name))
    chroma_state = _fetch_chroma_state(collection_name)
    watcher_state = _fetch_watcher_state(watcher_path)

    return {
        "watcher": watcher_config,
        "index": index_config,
        "chroma": chroma_state,
        "watcher_process": watcher_state,
    }


def _safe_load(loader):
    try:
        return loader()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _fetch_chroma_state(collection_name: str) -> dict[str, Any]:
    if not CHROMADB_DIR.exists():
        return {"error": "ChromaDB directory missing"}
    try:
        client = PersistentClient(path=str(CHROMADB_DIR))
        collection = client.get_collection(collection_name)
        return {
            "exists": True,
            "count": collection.count(),
            "metadata": collection.metadata,
        }
    except Exception as exc:  # noqa: BLE001
        return {"exists": False, "error": str(exc)}


def _fetch_watcher_state(watcher_path: Path) -> dict[str, Any]:
    pid = find_watcher_pid(watcher_path)
    return {
        "running": pid is not None,
        "pid": pid,
        "config_path": str(watcher_path),
    }


def _determine_exit_code(state: dict[str, Any]) -> int:
    if "error" in state["watcher"] or "error" in state["index"]:
        return 2
    chroma = state["chroma"]
    if chroma.get("exists") is False:
        return 2
    return 0


def _print_state(collection_name: str, state: dict[str, Any]) -> None:
    _print_header(collection_name)
    _print_section("Repository", _repository_details(state["watcher"]))
    _print_section("AI Provider", _provider_details(state["index"]))
    _print_section("ChromaDB", _chroma_details(state["chroma"]))
    _print_section("Configuration Files", _config_details(collection_name))
    _print_section("Watcher", _watcher_details(state["watcher"], state["watcher_process"]))


def _print_header(collection_name: str) -> None:
    print()
    print(f"{COLORS['header']}{COLORS['bold']}{collection_name}{COLORS['end']}")
    print("=" * len(collection_name))


def _print_section(title: str, lines: list[str]) -> None:
    print()
    print(f"{COLORS['bold']}{title}{COLORS['end']}")
    for line in lines:
        print(f"  {line}")


def _repository_details(watcher_config: dict[str, Any]) -> list[str]:
    if not watcher_config:
        return ["❌ Watcher config missing"]
    if "error" in watcher_config:
        return [f"❌ {watcher_config['error']}"]
    repository_path = watcher_config.get("repository_path", "unknown")
    last_indexed = _format_timestamp(watcher_config.get("extracted_json_path"))
    return [
        f"Path: {repository_path}",
        f"Last indexed file: {watcher_config.get('extracted_json_path', 'unknown')}",
        f"Last indexed at: {last_indexed or 'unknown'}",
    ]


def _provider_details(index_config: dict[str, Any]) -> list[str]:
    if not index_config:
        return ["❌ Index config missing"]
    if "error" in index_config:
        return [f"❌ {index_config['error']}"]

    provider = index_config.get("provider", {})
    provider_type = provider.get("provider_type")
    name = PROVIDER_DISPLAY_NAMES.get(provider_type, provider_type or "Unknown")
    embedding = provider.get("embedding_model", "unknown")
    llm_model = provider.get("llm_model", "unknown")

    lines = [
        f"Provider: {name}",
        f"Embedding: {embedding}",
        f"LLM: {llm_model}",
    ]

    api_key = provider.get("api_key")
    if api_key:
        lines.append(f"API Key: referenced as {api_key}")
    else:
        lines.append("API Key: not required")

    return lines


def _chroma_details(chroma_state: dict[str, Any]) -> list[str]:
    if chroma_state.get("exists"):
        count = chroma_state.get("count")
        return [
            "Collection: ✓ Present",
            f"Chunks: {count if count is not None else 'unknown'}",
            f"Metadata: {json.dumps(chroma_state.get('metadata', {}), indent=2)}",
        ]
    return [
        "Collection: ❌ Missing",
        f"Error: {chroma_state.get('error', 'unknown')}",
    ]


def _config_details(collection_name: str) -> list[str]:
    base = MINERVA_KB_APP_DIR
    paths = {
        "Watcher": base / f"{collection_name}-watcher.json",
        "Index": base / f"{collection_name}-index.json",
        "Extracted": base / f"{collection_name}-extracted.json",
    }
    lines = []
    for label, path in paths.items():
        status = "✓" if path.exists() else "❌"
        size = _format_size(path) if path.exists() else "-"
        lines.append(f"{status} {label}: {path} ({size})")
    return lines


def _watcher_details(watcher_config: dict[str, Any], process_state: dict[str, Any]) -> list[str]:
    lines = []
    if "error" in watcher_config:
        lines.append(f"❌ {watcher_config['error']}")
    else:
        include_patterns = ", ".join(watcher_config.get("include_extensions", []))
        ignore_patterns = ", ".join(watcher_config.get("ignore_patterns", []))
        lines.extend(
            [
                f"Repository: {watcher_config.get('repository_path', 'unknown')}",
                f"Debounce: {watcher_config.get('debounce_seconds', 'unknown')}s",
                f"Include: {include_patterns or 'default'}",
                f"Ignore: {ignore_patterns or 'default'}",
            ]
        )
    if process_state.get("running"):
        lines.append(f"Watcher: ✓ Running (PID {process_state['pid']})")
    else:
        lines.append("Watcher: ⚠ Not running")
    return lines


def _format_timestamp(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    if not path.exists():
        return None
    timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _format_size(path: Path) -> str:
    try:
        size = path.stat().st_size
        return f"{size / (1024 * 1024):.2f} MB"
    except FileNotFoundError:
        return "-"


def _display_error(message: str) -> None:
    print(f"❌ {message}")


def _suggest_available_collections() -> None:
    if not MINERVA_KB_APP_DIR.exists():
        return
    print("Available collections:")
    for watcher_path in sorted(MINERVA_KB_APP_DIR.glob("*-watcher.json")):
        name = watcher_path.stem.replace("-watcher", "")
        print(f"  • {name}")
