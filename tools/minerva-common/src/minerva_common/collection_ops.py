from pathlib import Path

import chromadb


def list_chromadb_collections(chromadb_path: str | Path) -> list[dict]:
    chromadb_path = Path(chromadb_path)

    if not chromadb_path.exists():
        return []

    try:
        client = chromadb.PersistentClient(path=str(chromadb_path))
        collections = client.list_collections()

        result = []
        for collection in collections:
            result.append({"name": collection.name, "count": collection.count()})

        return result

    except Exception:
        return []


def remove_chromadb_collection(chromadb_path: str | Path, collection_name: str) -> bool:
    chromadb_path = Path(chromadb_path)

    if not chromadb_path.exists():
        return False

    try:
        client = chromadb.PersistentClient(path=str(chromadb_path))
        client.delete_collection(name=collection_name)
        return True

    except ValueError:
        return False

    except Exception:
        return False


def get_collection_count(chromadb_path: str | Path, collection_name: str) -> int | None:
    chromadb_path = Path(chromadb_path)

    if not chromadb_path.exists():
        return None

    try:
        client = chromadb.PersistentClient(path=str(chromadb_path))
        collection = client.get_collection(name=collection_name)
        return collection.count()

    except ValueError:
        return None

    except Exception:
        return None
