import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path to import from markdown-notes-cag-data-creator
sys.path.insert(0, str(Path(__file__).parent.parent / "markdown-notes-cag-data-creator"))

try:
    import chromadb
except ImportError:
    print("Error: chromadb library not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)

from storage import initialize_chromadb_client, ChromaDBConnectionError


class CollectionDiscoveryError(Exception):
    """Raised when collection discovery operations fail."""
    pass


def list_collections(chromadb_path: str) -> List[Dict[str, Any]]:
    try:
        # Step 1: Initialize ChromaDB client
        client = initialize_chromadb_client(chromadb_path)

        # Step 2: Query all collections
        collections = client.list_collections()

        # Step 3: Extract metadata and chunk count for each collection
        result = []
        for collection in collections:
            # Get collection metadata
            metadata = collection.metadata or {}

            # Extract key fields with defaults
            collection_info = {
                "name": collection.name,
                "description": metadata.get("description", "No description available"),
                "chunk_count": collection.count(),
                "created_at": metadata.get("created_at", "Unknown")
            }

            result.append(collection_info)

        return result

    except ChromaDBConnectionError as error:
        raise CollectionDiscoveryError(
            f"Failed to connect to ChromaDB at '{chromadb_path}'\n"
            f"  Error: {error}\n"
            f"\n"
            f"  Troubleshooting:\n"
            f"  1. Verify the ChromaDB path is correct in your config.json\n"
            f"  2. Ensure the directory exists and is accessible\n"
            f"  3. Check file permissions for the ChromaDB directory"
        ) from error

    except Exception as error:
        raise CollectionDiscoveryError(
            f"Failed to list collections\n"
            f"  Error: {error}\n"
            f"\n"
            f"  This may indicate:\n"
            f"  - ChromaDB database corruption\n"
            f"  - Permission issues\n"
            f"  - Incompatible ChromaDB version"
        ) from error


if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python collection_discovery.py <chromadb_path>", file=sys.stderr)
        sys.exit(1)

    chromadb_path = sys.argv[1]

    try:
        collections = list_collections(chromadb_path)

        print(f"Found {len(collections)} collection(s):\n")
        print(json.dumps(collections, indent=2))

    except CollectionDiscoveryError as error:
        print(f"Collection discovery error:\n{error}", file=sys.stderr)
        sys.exit(1)
