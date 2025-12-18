import json
from datetime import datetime
from pathlib import Path
from typing import Any

from chromadb import PersistentClient

from minerva_kb.constants import CHROMADB_DIR, MINERVA_KB_APP_DIR, PROVIDER_DISPLAY_NAMES
from minerva_kb.utils.config_loader import WATCHER_SUFFIX, load_index_config, load_watcher_config
from minerva_kb.utils.display import display_error
from minerva_kb.utils.process_manager import find_watcher_pid


def run_list(output_format: str) -> int:
    if output_format not in {"table", "json"}:
        display_error("Invalid format. Use 'table' or 'json'.")
        return 2
    chroma_collections = _discover_chroma_collections()
    managed = _discover_managed_collections(chroma_collections)
    unmanaged = _discover_unmanaged_collections(chroma_collections, {entry["name"] for entry in managed})

    if output_format == "json":
        payload = {
            "managed_collections": [
                {
                    "name": entry["name"],
                    "repository_path": entry["repository_path"],
                    "provider": entry["provider"],
                    "chunks": entry["chunk_count"],
                    "watcher": entry["watcher"],
                    "last_indexed": entry["last_indexed"],
                    "status": entry["status"],
                    "notes": entry["notes"],
                }
                for entry in managed
            ],
            "unmanaged_collections": unmanaged,
        }
        print(json.dumps(payload, indent=2))
        return 0

    _print_managed_table(managed)
    if unmanaged:
        _print_unmanaged_table(unmanaged)

    # Print summary
    print("=" * 80)
    print(f"Total: {len(managed)} managed, {len(unmanaged)} unmanaged")
    print("=" * 80)
    print()
    return 0


def _discover_chroma_collections() -> dict[str, dict[str, Any]]:
    if not CHROMADB_DIR.exists():
        return {}
    try:
        client = PersistentClient(path=str(CHROMADB_DIR))
    except Exception:
        return {}

    collections: dict[str, dict[str, Any]] = {}
    try:
        for collection in client.list_collections():
            collections[collection.name] = {
                "count": _safe_count(collection),
            }
    except Exception:
        return {}
    return collections


def _safe_count(collection: Any) -> int | None:
    try:
        return collection.count()
    except Exception:
        return None


def _discover_managed_collections(chroma_collections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not MINERVA_KB_APP_DIR.exists():
        return entries
    suffix_length = len(WATCHER_SUFFIX)

    for watcher_path in sorted(MINERVA_KB_APP_DIR.glob(f"*{WATCHER_SUFFIX}")):
        collection_name = watcher_path.name[:-suffix_length]
        entry = _build_managed_entry(collection_name, watcher_path, chroma_collections)
        entries.append(entry)
    return entries


def _build_managed_entry(
    collection_name: str,
    watcher_path: Path,
    chroma_collections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    notes: list[str] = []
    try:
        watcher_config = load_watcher_config(collection_name)
    except ValueError as exc:
        watcher_config = {}
        notes.append(f"Watcher config error: {exc}")

    try:
        index_config = load_index_config(collection_name)
        provider_info = index_config.get("provider", {})
    except ValueError as exc:
        index_config = {}
        provider_info = {}
        notes.append(f"Index config error: {exc}")

    chunk_entry = chroma_collections.get(collection_name)
    chunk_count = chunk_entry.get("count") if chunk_entry else None
    status = "healthy"
    if notes:
        status = "config_error"
    elif chunk_count is None:
        status = "not_indexed"

    repository_path = watcher_config.get("repository_path", "unknown")
    last_indexed = _format_timestamp(watcher_config.get("extracted_json_path"))

    pid = find_watcher_pid(watcher_path)
    watcher_info = {
        "running": pid is not None,
        "pid": pid,
        "config_path": str(watcher_path),
    }

    return {
        "name": collection_name,
        "repository_path": repository_path,
        "provider": _format_provider(provider_info),
        "chunk_count": chunk_count,
        "watcher": watcher_info,
        "last_indexed": last_indexed,
        "status": status,
        "notes": notes,
    }


def _discover_unmanaged_collections(
    chroma_collections: dict[str, dict[str, Any]],
    managed_names: set[str],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name, metadata in sorted(chroma_collections.items()):
        if name in managed_names:
            continue
        entries.append(
            {
                "name": name,
                "chunk_count": metadata.get("count"),
            }
        )
    return entries


def _print_managed_table(entries: list[dict[str, Any]]) -> None:
    if not entries:
        print()
        print("=" * 80)
        print("No collections found")
        print("=" * 80)
        print()
        print("Get started:")
        print("  minerva-kb add /path/to/repository")
        return

    print()
    print("=" * 80)
    print("Managed Collections (minerva-kb)")
    print("=" * 80)
    print()

    for entry in entries:
        _print_managed_entry(entry)
        print()


def _print_managed_entry(entry: dict[str, Any]) -> None:
    name = entry["name"]
    provider_label = _provider_label(entry["provider"])
    chunk_label = _format_chunk_display(entry["chunk_count"])
    last_indexed = entry["last_indexed"] or "unknown"
    watcher_line = _watcher_label(entry["watcher"])

    print(f"Collection: {name}")
    print(f"  Repository:   {entry['repository_path']}")
    if entry["status"] == "not_indexed":
        print("  ⚠ Not indexed (ChromaDB collection missing)")
    print(f"  Provider:     {provider_label}")
    if entry["status"] != "not_indexed":
        print(f"  Chunks:       {chunk_label}")
    print(f"  Watcher:      {watcher_line}")
    print(f"  Last indexed: {last_indexed}")
    for note in entry["notes"]:
        print(f"  ⚠ {note}")


def _print_unmanaged_table(entries: list[dict[str, Any]]) -> None:
    print("=" * 80)
    print("Unmanaged Collections")
    print("=" * 80)
    print()
    print("⚠️  These collections exist in ChromaDB but are not managed by minerva-kb.")
    print("    They may be managed by minerva-doc or created directly via minerva CLI.")
    print()

    for entry in entries:
        chunk_label = _format_chunk_display(entry.get("chunk_count"))
        print(f"  - {entry['name']} ({chunk_label} chunks)")

    print()


def _provider_label(provider: dict[str, Any]) -> str:
    provider_type = provider.get("provider_type")
    name = PROVIDER_DISPLAY_NAMES.get(provider_type, provider_type or "Unknown")
    embedding = provider.get("embedding_model", "?")
    llm = provider.get("llm_model", "?")
    return f"{name} ({llm} + {embedding})"


def _format_provider(provider: dict[str, Any]) -> dict[str, Any]:
    provider_type = provider.get("provider_type")
    return {
        "provider_type": provider_type,
        "provider_name": PROVIDER_DISPLAY_NAMES.get(provider_type, provider_type or "Unknown"),
        "embedding_model": provider.get("embedding_model"),
        "llm_model": provider.get("llm_model"),
    }


def _format_chunk_display(chunk_count: int | None) -> str:
    if chunk_count is None:
        return "unknown"
    return f"{chunk_count:,}"


def _watcher_label(info: dict[str, Any]) -> str:
    if info.get("running") and info.get("pid"):
        return f"✓ Running (PID {info['pid']})"
    return "⚠ Not running"


def _format_timestamp(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    if not path.exists():
        return None
    timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")
