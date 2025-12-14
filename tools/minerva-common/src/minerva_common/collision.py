import json
from pathlib import Path

from minerva_common.collection_ops import get_collection_count
from minerva_common.paths import APPS_DIR, CHROMADB_DIR


def check_collection_exists(collection_name: str, chromadb_path: str | Path | None = None) -> tuple[bool, str | None]:
    if chromadb_path is None:
        chromadb_path = CHROMADB_DIR

    chromadb_path = Path(chromadb_path)

    exists_in_chromadb = get_collection_count(chromadb_path, collection_name) is not None

    if not exists_in_chromadb:
        return (False, None)

    owner = find_collection_owner(collection_name)

    return (True, owner)


def find_collection_owner(collection_name: str) -> str | None:
    kb_owner = check_registry_owner(collection_name, "minerva-kb")
    if kb_owner:
        return kb_owner

    doc_owner = check_registry_owner(collection_name, "minerva-doc")
    if doc_owner:
        return doc_owner

    return None


def check_registry_owner(collection_name: str, app_name: str) -> str | None:
    registry_path = APPS_DIR / app_name / "collections.json"

    if not registry_path.exists():
        return None

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        collections = registry.get("collections", {})

        if collection_name in collections:
            return app_name

        return None

    except (json.JSONDecodeError, KeyError, OSError):
        return None
