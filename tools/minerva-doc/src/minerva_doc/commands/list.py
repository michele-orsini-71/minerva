import json

from chromadb import PersistentClient

from minerva_common.collection_ops import list_chromadb_collections
from minerva_common.paths import CHROMADB_DIR
from minerva_common.registry import Registry

from minerva_doc.constants import COLLECTIONS_REGISTRY_PATH


def run_list(format_type: str = "table") -> int:
    try:
        return execute_list(format_type)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


def execute_list(format_type: str) -> int:
    chromadb_collections = get_chromadb_collections()

    registry = Registry(COLLECTIONS_REGISTRY_PATH)
    managed_collections = registry.list_collections()

    managed_names = {c["collection_name"] for c in managed_collections}

    managed_with_details = []
    for collection_meta in managed_collections:
        name = collection_meta["collection_name"]
        chromadb_info = next((c for c in chromadb_collections if c["name"] == name), None)

        managed_with_details.append({
            "name": name,
            "description": collection_meta.get("description", ""),
            "provider": collection_meta.get("provider", {}).get("provider_type", "unknown"),
            "chunks": chromadb_info["count"] if chromadb_info else 0,
            "indexed_at": collection_meta.get("indexed_at", "unknown"),
            "records_path": collection_meta.get("records_path", "unknown"),
        })

    unmanaged = [c for c in chromadb_collections if c["name"] not in managed_names]

    if format_type == "json":
        output = {
            "managed": managed_with_details,
            "unmanaged": [{"name": c["name"], "chunks": c["count"]} for c in unmanaged],
        }
        print(json.dumps(output, indent=2))
    else:
        display_table(managed_with_details, unmanaged)

    return 0


def get_chromadb_collections() -> list[dict]:
    try:
        return list_chromadb_collections(CHROMADB_DIR)
    except Exception as e:
        print(f"Error: Failed to query ChromaDB: {e}")
        print(f"  ChromaDB path: {CHROMADB_DIR}")
        print(f"  Check that ChromaDB is accessible and not corrupted")
        print(f"  Try: ls -la {CHROMADB_DIR}")
        return []


def display_table(managed: list[dict], unmanaged: list[dict]) -> None:
    if not managed and not unmanaged:
        print("No collections found in ChromaDB")
        print()
        print("Get started:")
        print("  minerva-doc add <json-file> --name <collection-name>")
        return

    if managed:
        print()
        print("=" * 80)
        print("Managed Collections (minerva-doc)")
        print("=" * 80)
        print()

        for collection in managed:
            print(f"Collection: {collection['name']}")
            print(f"  Description:  {collection['description'][:60]}...")
            print(f"  Provider:     {collection['provider']}")
            print(f"  Chunks:       {collection['chunks']:,}")
            print(f"  Indexed:      {collection['indexed_at'][:19]}")
            print(f"  Source:       {collection['records_path']}")
            print()

    if unmanaged:
        print("=" * 80)
        print("Unmanaged Collections")
        print("=" * 80)
        print()
        print("⚠️  These collections exist in ChromaDB but are not managed by minerva-doc.")
        print("    They may be managed by minerva-kb or created directly via minerva CLI.")
        print()

        for collection in unmanaged:
            print(f"  - {collection['name']} ({collection['count']:,} chunks)")

        print()
        print("To manage these collections, use the appropriate tool:")
        print("  minerva-kb list        # For repository-based collections")
        print("  minerva-doc list       # For document-based collections")
        print()

    print("=" * 80)
    print(f"Total: {len(managed)} managed, {len(unmanaged)} unmanaged")
    print("=" * 80)
    print()
