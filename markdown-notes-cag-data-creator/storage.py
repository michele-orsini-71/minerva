import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("Error: chromadb library not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)

# Import our immutable models
from models import ChunkWithEmbedding, ChunkWithEmbeddingList

# Configuration constants
DEFAULT_BATCH_SIZE = 64
HNSW_SPACE = "cosine"  # Distance metric for HNSW index

class StorageError(Exception):
    pass


class ChromaDBConnectionError(Exception):
    pass


def initialize_chromadb_client(db_path: str) -> chromadb.PersistentClient:
    try:
        # Ensure path is absolute and create parent directories
        db_path = os.path.abspath(os.path.expanduser(db_path))
        Path(db_path).mkdir(parents=True, exist_ok=True)

        # Initialize persistent client
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry for privacy
                allow_reset=True  # Enable collection reset functionality
            )
        )

        # Test connection with a simple operation
        client.heartbeat()

        return client

    except Exception as error:
        raise ChromaDBConnectionError(f"Failed to initialize ChromaDB client at '{db_path}': {error}")


def collection_exists(client: chromadb.PersistentClient, collection_name: str) -> bool:
    try:
        existing_collections = [col.name for col in client.list_collections()]
        return collection_name in existing_collections
    except Exception as error:
        raise StorageError(f"Failed to check if collection '{collection_name}' exists: {error}")

def delete_existing_collection(client: chromadb.PersistentClient, collection_name: str) -> None:
    """Delete an existing collection if it exists."""
    exists = collection_exists(client, collection_name)

    if exists:
        try:
            client.delete_collection(collection_name)
            print(f"   Deleted existing collection '{collection_name}'")
            print(f"   WARNING: All existing data in this collection has been permanently deleted!")
        except Exception as error:
            raise StorageError(
                f"Failed to delete existing collection '{collection_name}': {error}\n"
                f"  Suggestion: Check ChromaDB permissions"
            )


def build_collection_metadata(description: str) -> Dict[str, Any]:
    """Build metadata dictionary for ChromaDB collection."""
    from datetime import datetime, timezone

    return {
        "hnsw:space": HNSW_SPACE,  # Cosine similarity for L2-normalized embeddings
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": description
    }


def create_new_collection(client: chromadb.PersistentClient, collection_name: str, metadata: Dict[str, Any]) -> chromadb.Collection:
    """Create a new ChromaDB collection with provided metadata."""
    try:
        collection = client.create_collection(
            name=collection_name,
            metadata=metadata
        )
        return collection
    except Exception as error:
        raise StorageError(f"Failed to create collection '{collection_name}': {error}")


def print_collection_creation_summary(collection_name: str, description: str, created_at: str) -> None:
    """Print summary of collection creation."""
    print(f"   Created new collection '{collection_name}'")
    if description:
        print(f"   Description: {description[:80]}...")
    print(f"   Created at: {created_at}")


def create_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    description: str,
) -> chromadb.Collection:
    """
    Create a new ChromaDB collection.

    Raises StorageError if collection already exists.
    Use recreate_collection() if you want to delete and recreate.
    """
    try:
        # Check if collection already exists
        if collection_exists(client, collection_name):
            raise StorageError(
                f"Collection '{collection_name}' already exists\n"
                f"  Options:\n"
                f"    1. Use a different collection name\n"
                f"    2. Use recreate_collection() to delete and recreate\n"
                f"       (WARNING: This will permanently delete all existing data!)\n"
            )

        # Step 1: Build metadata
        metadata = build_collection_metadata(description)

        # Step 2: Create new collection
        collection = create_new_collection(client, collection_name, metadata)

        # Step 3: Print summary
        print_collection_creation_summary(collection_name, description, metadata['created_at'])

        return collection

    except StorageError:
        # Re-raise StorageError as-is
        raise
    except Exception as error:
        raise StorageError(f"Failed to create collection '{collection_name}': {error}")


def recreate_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    description: str,
) -> chromadb.Collection:
    """
    Delete existing collection (if it exists) and create a new one.

    WARNING: This is a destructive operation that permanently deletes all data.
    """
    try:
        # Step 1: Delete existing collection if it exists
        delete_existing_collection(client, collection_name)

        # Step 2: Build metadata
        metadata = build_collection_metadata(description)

        # Step 3: Create new collection
        collection = create_new_collection(client, collection_name, metadata)

        # Step 4: Print summary
        print_collection_creation_summary(collection_name, description, metadata['created_at'])

        return collection

    except StorageError:
        # Re-raise StorageError as-is
        raise
    except Exception as error:
        raise StorageError(f"Failed to recreate collection '{collection_name}': {error}")


# Backward compatibility: Keep old function but mark as deprecated
def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    description: str,
    force_recreate: bool = False,
) -> chromadb.Collection:
    """
    DEPRECATED: Use create_collection() or recreate_collection() instead.

    This function is kept for backward compatibility but will be removed in future versions.
    """
    if force_recreate:
        return recreate_collection(client, collection_name, description)
    else:
        return create_collection(client, collection_name, description)


def prepare_chunk_batch_data(batch):
    """Prepare a batch of chunks for ChromaDB insertion."""
    ids = [chunk.id for chunk in batch]
    documents = [chunk.content for chunk in batch]
    embeddings = [chunk.embedding for chunk in batch]
    metadatas = [
        {
            'noteId': chunk.noteId,
            'title': chunk.title,
            'modificationDate': chunk.modificationDate,
            'creationDate': chunk.creationDate,
            'size': chunk.size,
            'chunkIndex': chunk.chunkIndex
        }
        for chunk in batch
    ]
    return ids, documents, embeddings, metadatas


def insert_batch_to_collection(collection, batch, batch_num, stats):
    """Insert a single batch of chunks into ChromaDB collection."""
    try:
        ids, documents, embeddings, metadatas = prepare_chunk_batch_data(batch)

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        stats["successful"] += len(batch)
        stats["batches"] += 1
        return True

    except Exception as error:
        error_msg = f"Batch {batch_num} failed: {error}"
        stats["errors"].append(error_msg)
        stats["failed"] += len(batch)
        print(f"   {error_msg}", file=sys.stderr)
        return False


def print_storage_summary(stats):
    """Print comprehensive summary of storage operation."""
    print(f"   Storage complete:")
    print(f"  Successfully stored: {stats['successful']} chunks")
    print(f"  Failed: {stats['failed']} chunks")
    print(f"  Batches processed: {stats['batches']}")

    if stats["errors"]:
        print(f"\n   Storage errors:")
        for error in stats["errors"]:
            print(f"  - {error}")


def insert_chunks(
    collection: chromadb.Collection,
    chunks_with_embeddings: ChunkWithEmbeddingList,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    if not chunks_with_embeddings:
        return {"total_chunks": 0, "batches": 0, "successful": 0, "failed": 0}

    print(f"   Storing {len(chunks_with_embeddings)} chunks in ChromaDB...")

    stats = {
        "total_chunks": len(chunks_with_embeddings),
        "batches": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    try:
        # Process chunks in batches
        for i in range(0, len(chunks_with_embeddings), batch_size):
            batch = chunks_with_embeddings[i:i + batch_size]
            batch_num = stats["batches"] + 1

            # Insert batch and update stats
            insert_batch_to_collection(collection, batch, batch_num, stats)

            # Progress callback
            if progress_callback:
                progress_callback(min(i + batch_size, len(chunks_with_embeddings)), len(chunks_with_embeddings))

        # Print summary
        print_storage_summary(stats)

        return stats

    except Exception as error:
        raise StorageError(f"Chunk storage failed: {error}")
