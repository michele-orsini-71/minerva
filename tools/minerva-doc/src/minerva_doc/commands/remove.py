from minerva_common.collection_ops import get_collection_count, remove_chromadb_collection
from minerva_common.paths import CHROMADB_DIR
from minerva_common.registry import Registry

from minerva_doc.constants import COLLECTIONS_REGISTRY_PATH


def run_remove(collection_name: str) -> int:
    try:
        return execute_remove(collection_name)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


def execute_remove(collection_name: str) -> int:
    registry = Registry(COLLECTIONS_REGISTRY_PATH)

    collection = registry.get_collection(collection_name)
    if collection is None:
        return handle_unmanaged_collection(collection_name)

    display_collection_info(collection)

    if not confirm_removal(collection_name):
        print("Operation cancelled")
        return 0

    if not remove_from_chromadb(collection_name):
        return 1

    registry.remove_collection(collection_name)

    display_success(collection_name)
    return 0


def handle_unmanaged_collection(collection_name: str) -> int:
    chunk_count = get_collection_count(CHROMADB_DIR, collection_name)

    if chunk_count is not None:
        print(f"Error: Collection '{collection_name}' not found in minerva-doc registry")
        print(f"  The collection exists in ChromaDB with {chunk_count:,} chunks")
        print(f"  but is not managed by minerva-doc.")
        print()
        print("Possible actions:")
        print(f"  - Check if managed by minerva-kb: minerva-kb status {collection_name}")
        print(f"  - Remove manually: Use minerva CLI directly")
        print()
        return 1
    else:
        print(f"Error: Collection '{collection_name}' not found")
        print(f"  Not in minerva-doc registry")
        print(f"  Not in ChromaDB")
        print()
        print("Actions:")
        print(f"  - List all collections: minerva-doc list")
        return 1


def display_collection_info(collection: dict) -> None:
    provider = collection.get("provider", {})

    print()
    print("=" * 60)
    print("Collection to Remove")
    print("=" * 60)
    print(f"  Name:         {collection['collection_name']}")
    print(f"  Description:  {collection.get('description', 'N/A')[:50]}...")
    print(f"  Provider:     {provider.get('provider_type', 'N/A')}")
    print(f"  Source JSON:  {collection.get('records_path', 'N/A')}")
    print("=" * 60)
    print()
    print("⚠️  WARNING: This operation cannot be undone!")
    print()
    print("Will delete:")
    print("  - All embeddings from ChromaDB")
    print("  - Collection metadata from registry")
    print()
    print("Will NOT delete:")
    print("  - Source JSON file (your documents are safe)")
    print("  - Shared server configuration")
    print()


def confirm_removal(collection_name: str) -> bool:
    while True:
        response = input("Type 'YES' to confirm removal: ").strip()
        if response == "YES":
            return True
        if response in {"no", "n", ""}:
            return False
        print("Please type 'YES' exactly to confirm, or press Enter to cancel")


def remove_from_chromadb(collection_name: str) -> bool:
    print(f"Removing collection from ChromaDB...")

    try:
        remove_chromadb_collection(CHROMADB_DIR, collection_name)
        print("✓ Removed from ChromaDB")
        return True
    except Exception as e:
        print(f"✗ Failed to remove from ChromaDB: {e}")
        print("  The collection may have already been deleted.")
        print("  Continuing with registry cleanup...")
        return True


def display_success(collection_name: str) -> None:
    print()
    print("=" * 60)
    print("✓ Collection removed successfully!")
    print("=" * 60)
    print(f"  Collection: {collection_name}")
    print()
    print("Next steps:")
    print("  - List remaining collections: minerva-doc list")
    print("  - Add a new collection:       minerva-doc add <json-file> --name <name>")
    print()
