from minerva_common.collection_ops import get_collection_count
from minerva_common.paths import CHROMADB_DIR
from minerva_common.registry import Registry

from minerva_doc.constants import COLLECTIONS_REGISTRY_PATH


def run_status(collection_name: str) -> int:
    try:
        return execute_status(collection_name)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


def execute_status(collection_name: str) -> int:
    registry = Registry(COLLECTIONS_REGISTRY_PATH)

    collection = registry.get_collection(collection_name)
    if collection is None:
        print(f"Error: Collection '{collection_name}' not found")
        print(f"  This collection is not managed by minerva-doc")
        print()
        print("Actions:")
        print(f"  - List all collections: minerva-doc list")
        print(f"  - Check minerva-kb:     minerva-kb status {collection_name}")
        return 1

    chunk_count = get_collection_count(CHROMADB_DIR, collection_name)

    display_status(collection, chunk_count)

    return 0


def display_status(collection: dict, chunk_count: int | None) -> None:
    provider = collection.get("provider", {})

    print()
    print("=" * 60)
    print(f"Collection Status: {collection['collection_name']}")
    print("=" * 60)
    print()

    print("General Information:")
    print(f"  Name:         {collection['collection_name']}")
    print(f"  Description:  {collection.get('description', 'N/A')}")
    print(f"  Source JSON:  {collection.get('records_path', 'N/A')}")
    print()

    print("AI Provider:")
    print(f"  Type:             {provider.get('provider_type', 'N/A')}")
    print(f"  Embedding model:  {provider.get('embedding_model', 'N/A')}")
    print(f"  LLM model:        {provider.get('llm_model', 'N/A')}")
    if "base_url" in provider:
        print(f"  Base URL:         {provider.get('base_url', 'N/A')}")
    print()

    print("ChromaDB Status:")
    if chunk_count is not None:
        print(f"  Chunks:       {chunk_count:,}")
        print(f"  Status:       ✓ Indexed")
    else:
        print(f"  Chunks:       0")
        print(f"  Status:       ✗ Not found in ChromaDB")
    print()

    print("Dates:")
    print(f"  Created:      {collection.get('created_at', 'N/A')}")
    print(f"  Last indexed: {collection.get('indexed_at', 'N/A')}")
    print()

    print("=" * 60)
    print()

    if chunk_count is None:
        print("⚠️  Warning: Collection not found in ChromaDB")
        print("    The collection may have been deleted manually.")
        print("    Try re-indexing or removing and recreating it.")
        print()
