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

    except Exception as e:
        raise ChromaDBConnectionError(f"Failed to initialize ChromaDB client at '{db_path}': {e}")


def collection_exists(client: chromadb.PersistentClient, collection_name: str) -> bool:
    try:
        existing_collections = [col.name for col in client.list_collections()]
        return collection_name in existing_collections
    except Exception as e:
        raise StorageError(f"Failed to check if collection '{collection_name}' exists: {e}")

def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    description: str,
    force_recreate: bool = False,
) -> chromadb.Collection:
    try:

        collection_exists = collection_exists(client, collection_name)
        if collection_exists and force_recreate:
            # Force recreation: delete existing collection
            try:
                client.delete_collection(collection_name)
                print(f"   Deleted existing collection '{collection_name}' for recreation (force_recreate=True)")
                print(f"   WARNING: All existing data in this collection has been permanently deleted!")
                collection_exists = False  # Collection no longer exists after deletion
            except Exception as e:
                raise StorageError(
                    f"Failed to delete existing collection '{collection_name}': {e}\n"
                    f"  Suggestion: Check ChromaDB permissions or set force_recreate=False"
                )

        # Prepare metadata
        from datetime import datetime, timezone

        metadata = {
            "hnsw:space": HNSW_SPACE,  # Cosine similarity for L2-normalized embeddings
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": description
        }

        collection = client.create_collection(
            name=collection_name,
            metadata=metadata
        )

        print(f"   Created new collection '{collection_name}'")
        if description:
            print(f"   Description: {description[:80]}...")
        print(f"   Created at: {metadata['created_at']}")

        return collection

    except StorageError:
        # Re-raise StorageError as-is
        raise
    except Exception as e:
        raise StorageError(f"Failed to create/access collection '{collection_name}': {e}")


def prepare_batch_data(chunks: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    if not chunks:
        return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}

    try:
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for chunk in chunks:
            # Validate required fields
            required_fields = ['id', 'content']
            for field in required_fields:
                if field not in chunk:
                    raise StorageError(f"Missing required field '{field}' in chunk data")

            ids.append(chunk['id'])
            documents.append(chunk['content'])

            # Prepare metadata (exclude content and embedding to avoid duplication)
            metadata = {k: v for k, v in chunk.items() if k not in ['content', 'embedding']}
            metadatas.append(metadata)

            # Extract embedding if present
            if 'embedding' in chunk:
                if not isinstance(chunk['embedding'], list):
                    raise StorageError(f"Embedding must be a list, got {type(chunk['embedding'])}")
                embeddings.append(chunk['embedding'])
            else:
                # No embedding provided - ChromaDB will handle this case
                embeddings.append(None)

        # Filter out None embeddings if all are None
        if all(emb is None for emb in embeddings):
            embeddings = None

        return {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
            "embeddings": embeddings
        }

    except Exception as e:
        raise StorageError(f"Failed to prepare batch data: {e}")

def get_collection_stats(collection: chromadb.Collection) -> Dict[str, Any]:
    try:
        # Get collection count
        count = collection.count()

        # Get collection metadata
        metadata = collection.metadata

        # Sample a few documents to understand structure (if any exist)
        sample_data = None
        if count > 0:
            try:
                sample_results = collection.peek(limit=1)
                if sample_results and len(sample_results.get('ids', [])) > 0:
                    sample_data = {
                        'sample_id': sample_results['ids'][0],
                        'sample_metadata_keys': list(sample_results['metadatas'][0].keys()) if sample_results.get('metadatas') else [],
                        'has_embeddings': len(sample_results.get('embeddings', [])) > 0
                    }
            except Exception:
                # Sample retrieval failed, continue without sample data
                pass

        return {
            "collection_name": collection.name,
            "total_chunks": count,
            "metadata": metadata,
            "sample_data": sample_data
        }

    except Exception as e:
        raise StorageError(f"Failed to retrieve collection stats: {e}")

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

            try:
                # Convert ChunkWithEmbedding objects to ChromaDB format
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

                # Insert batch into collection
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )

                stats["successful"] += len(batch)
                stats["batches"] += 1

                # Progress callback
                if progress_callback:
                    progress_callback(min(i + batch_size, len(chunks_with_embeddings)), len(chunks_with_embeddings))

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {e}"
                stats["errors"].append(error_msg)
                stats["failed"] += len(batch)
                print(f"   {error_msg}", file=sys.stderr)
                continue

        # Summary
        print(f"   Storage complete:")
        print(f"  Successfully stored: {stats['successful']} chunks")
        print(f"  Failed: {stats['failed']} chunks")
        print(f"  Batches processed: {stats['batches']}")

        if stats["errors"]:
            print(f"\n   Storage errors:")
            for error in stats["errors"]:
                print(f"  - {error}")

        return stats

    except Exception as e:
        raise StorageError(f"Chunk storage failed: {e}")
