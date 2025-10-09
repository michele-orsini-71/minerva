import sys
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Add parent directory to path to import from markdown-notes-cag-data-creator
sys.path.insert(0, str(Path(__file__).parent.parent / "markdown-notes-cag-data-creator"))

try:
    import chromadb
except ImportError:
    print("Error: chromadb library not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)

from storage import initialize_chromadb_client, ChromaDBConnectionError
from ai_config import AIProviderConfig, APIKeyMissingError
from ai_provider import AIProvider, AIProviderError, ProviderUnavailableError


class CollectionDiscoveryError(Exception):
    """Raised when collection discovery operations fail."""
    pass


def reconstruct_provider_from_metadata(metadata: Dict[str, Any]) -> Tuple[Optional[AIProvider], Optional[str]]:
    try:
        provider_type = metadata.get('embedding_provider')
        embedding_model = metadata.get('embedding_model')
        llm_model = metadata.get('llm_model')
        base_url = metadata.get('embedding_base_url')
        api_key_ref = metadata.get('embedding_api_key_ref')

        if not provider_type or not embedding_model or not llm_model:
            return None, "Missing AI provider metadata (created with old pipeline)"

        config = AIProviderConfig(
            provider_type=provider_type,
            embedding_model=embedding_model,
            llm_model=llm_model,
            base_url=base_url,
            api_key=api_key_ref
        )

        provider = AIProvider(config)

        availability = provider.check_availability()

        if not availability['available']:
            reason = availability.get('error', 'Unknown error')
            return None, reason

        return provider, None

    except APIKeyMissingError as error:
        return None, str(error)
    except (AIProviderError, ProviderUnavailableError) as error:
        return None, f"Provider initialization failed: {error}"
    except Exception as error:
        return None, f"Unexpected error during provider reconstruction: {error}"


def discover_collections_with_providers(chromadb_path: str) -> Tuple[Dict[str, AIProvider], List[Dict[str, Any]]]:
    try:
        client = initialize_chromadb_client(chromadb_path)
        collections = client.list_collections()

        provider_map = {}
        collection_details = []

        for collection in collections:
            metadata = collection.metadata or {}
            provider, unavailable_reason = reconstruct_provider_from_metadata(metadata)

            collection_info = {
                "name": collection.name,
                "description": metadata.get("description", "No description available"),
                "chunk_count": collection.count(),
                "created_at": metadata.get("created_at", "Unknown"),
                "available": provider is not None,
                "provider_type": metadata.get("embedding_provider"),
                "embedding_model": metadata.get("embedding_model"),
                "llm_model": metadata.get("llm_model"),
                "embedding_dimension": metadata.get("embedding_dimension"),
                "unavailable_reason": unavailable_reason
            }

            if provider is not None:
                provider_map[collection.name] = provider

            collection_details.append(collection_info)

        return provider_map, collection_details

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
            f"Failed to discover collections\n"
            f"  Error: {error}\n"
            f"\n"
            f"  This may indicate:\n"
            f"  - ChromaDB database corruption\n"
            f"  - Permission issues\n"
            f"  - Incompatible ChromaDB version"
        ) from error


def list_collections(chromadb_path: str) -> List[Dict[str, Any]]:
    try:
        # Step 1: Initialize ChromaDB client
        client = initialize_chromadb_client(chromadb_path)

        # Step 2: Query all collections
        collections = client.list_collections()

        # Step 3: Extract metadata, chunk count, and provider availability for each collection
        result = []
        for collection in collections:
            metadata = collection.metadata or {}

            provider, unavailable_reason = reconstruct_provider_from_metadata(metadata)

            collection_info = {
                "name": collection.name,
                "description": metadata.get("description", "No description available"),
                "chunk_count": collection.count(),
                "created_at": metadata.get("created_at", "Unknown"),
                "available": provider is not None,
                "provider_type": metadata.get("embedding_provider"),
                "embedding_model": metadata.get("embedding_model"),
                "unavailable_reason": unavailable_reason
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
