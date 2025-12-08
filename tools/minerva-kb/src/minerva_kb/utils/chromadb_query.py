from pathlib import Path
from typing import Any

from chromadb import PersistentClient


def get_chromadb_client(chromadb_path: Path | str) -> PersistentClient:
    path = Path(chromadb_path).expanduser()
    return PersistentClient(path=str(path))


def list_all_collections(client: PersistentClient) -> list[str]:
    try:
        return sorted(collection.name for collection in client.list_collections())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to list collections: {exc}") from exc


def collection_exists(client: PersistentClient, collection_name: str) -> bool:
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False


def get_collection_metadata(client: PersistentClient, collection_name: str) -> dict[str, Any]:
    collection = client.get_collection(collection_name)
    try:
        count = collection.count()
    except Exception:
        count = None
    return {
        "count": count,
        "metadata": getattr(collection, "metadata", {}) or {},
    }
