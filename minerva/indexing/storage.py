import os
import re
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from minerva.common.exceptions import StorageError, ChromaDBConnectionError
from minerva.common.logger import get_logger

logger = get_logger(__name__, mode="cli")

try:
    import chromadb
    from chromadb.config import Settings
except ImportError as error:
    message = "chromadb library not installed"
    logger.error(f"{message}. Run: pip install chromadb")
    raise StorageError(message) from error

# Import our immutable models
from minerva.common.models import ChunkWithEmbedding, ChunkWithEmbeddingList

# Configuration constants
DEFAULT_BATCH_SIZE = 64
HNSW_SPACE = "cosine"  # Distance metric for HNSW index


def initialize_chromadb_client(db_path: str) -> chromadb.PersistentClient:
    try:
        # Ensure path is absolute and create parent directories
        db_path = os.path.abspath(os.path.expanduser(db_path))
        Path(db_path).mkdir(parents=True, exist_ok=True)

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

def remove_collection(client: chromadb.PersistentClient, collection_name: str) -> None:
    if not collection_exists(client, collection_name):
        raise StorageError(
            f"Collection '{collection_name}' does not exist\n"
            f"  Suggestion: Run 'minerva peek {collection_name}' to verify available collections"
        )

    try:
        client.delete_collection(collection_name)
    except Exception as error:
        raise StorageError(
            f"Failed to delete collection '{collection_name}': {error}\n"
            f"  Suggestion: Check ChromaDB permissions"
        )


def delete_existing_collection(client: chromadb.PersistentClient, collection_name: str) -> None:
    exists = collection_exists(client, collection_name)

    if exists:
        try:
            remove_collection(client, collection_name)
            logger.warning(f"   Deleted existing collection '{collection_name}'")
            logger.warning(f"   WARNING: All existing data in this collection has been permanently deleted!")
        except StorageError:
            raise


def _validate_no_actual_api_keys(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or value is None:
        return

    secret_patterns = [
        r'sk-[a-zA-Z0-9]{20,}',  # OpenAI keys
        r'AIza[a-zA-Z0-9_-]{35}',  # Google API keys
        r'[a-zA-Z0-9]{32,}',  # Generic long strings that might be keys
    ]

    for pattern in secret_patterns:
        if re.search(pattern, value):
            raise StorageError(
                f"Attempted to store actual API key in {field_name}\n"
                f"  Security error: API keys must be stored as environment variable templates\n"
                f"  Example: Use '${{OPENAI_API_KEY}}' instead of actual key value\n"
                f"  Suggestion: Update your config to use environment variable templates"
            )


def build_collection_metadata(description: str, embedding_metadata: Dict[str, Any], chunk_size: int = 1200, note_count: Optional[int] = None) -> Dict[str, Any]:
    from datetime import datetime, timezone

    if not embedding_metadata:
        raise StorageError(
            "Embedding metadata is required when creating collections\n"
            "  AI provider metadata must be provided for all new collections\n"
            "  Required fields: embedding_model, embedding_provider, embedding_dimension\n"
            "  Suggestion: Ensure the pipeline initializes the AI provider and passes metadata to storage"
        )

    current_timestamp = datetime.now(timezone.utc).isoformat()

    metadata = {
        "hnsw:space": HNSW_SPACE,
        "version": "2.0",
        "note_hash_algorithm": "sha256",
        "chunk_size": chunk_size,
        "created_at": current_timestamp,
        "last_updated": current_timestamp,
        "description": description
    }

    # Add note_count if provided (instant retrieval for peek command)
    if note_count is not None:
        metadata["note_count"] = note_count

    allowed_fields = [
        'embedding_model',
        'embedding_provider',
        'embedding_dimension',
        'embedding_base_url',
        'embedding_api_key_ref',
        'llm_model'
    ]

    for field in allowed_fields:
        if field in embedding_metadata:
            value = embedding_metadata[field]

            # Skip None values - ChromaDB doesn't accept null metadata
            # MCP server handles missing keys via .get() which returns None
            if value is None:
                continue

            if field == 'embedding_api_key_ref':
                _validate_no_actual_api_keys(value, field)

            metadata[field] = value

    # Required fields (embedding_dimension is optional - may be None if test embedding fails)
    required_fields = ['embedding_model', 'embedding_provider']
    missing_fields = [f for f in required_fields if f not in metadata]

    if missing_fields:
        raise StorageError(
            f"Missing required embedding metadata fields: {', '.join(missing_fields)}\n"
            f"  All collections must include AI provider metadata\n"
            f"  Suggestion: Ensure the pipeline calls get_embedding_metadata() and passes result to storage"
        )

    return metadata


def create_new_collection(client: chromadb.PersistentClient, collection_name: str, metadata: Dict[str, Any]) -> chromadb.Collection:
    try:
        collection = client.create_collection(
            name=collection_name,
            metadata=metadata
        )
        return collection
    except Exception as error:
        raise StorageError(f"Failed to create collection '{collection_name}': {error}")


def print_collection_creation_summary(collection_name: str, description: str, created_at: str) -> None:
    logger.success(f"   Created new collection '{collection_name}'")
    if description:
        logger.info(f"   Description: {description[:80]}...")
    logger.info(f"   Created at: {created_at}")


def create_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
    description: str,
    embedding_metadata: Dict[str, Any],
    chunk_size: int = 1200,
    note_count: Optional[int] = None,
) -> chromadb.Collection:
    try:
        if collection_exists(client, collection_name):
            raise StorageError(
                f"Collection '{collection_name}' already exists\n"
                f"  Options:\n"
                f"    1. Use a different collection name\n"
                f"    2. Use recreate_collection() to delete and recreate\n"
                f"       (WARNING: This will permanently delete all existing data!)\n"
            )

        metadata = build_collection_metadata(description, embedding_metadata, chunk_size, note_count)

        collection = create_new_collection(client, collection_name, metadata)

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
    embedding_metadata: Dict[str, Any],
    chunk_size: int = 1200,
    note_count: Optional[int] = None,
) -> chromadb.Collection:
    try:
        delete_existing_collection(client, collection_name)

        metadata = build_collection_metadata(description, embedding_metadata, chunk_size, note_count)

        collection = create_new_collection(client, collection_name, metadata)

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
    embedding_metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = 1200,
    note_count: Optional[int] = None,
) -> chromadb.Collection:
    if not embedding_metadata:
        raise StorageError(
            "Embedding metadata is required when creating collections\n"
            "  This function is deprecated - use create_collection() or recreate_collection() directly\n"
            "  Suggestion: Update code to pass embedding_metadata parameter"
        )

    if force_recreate:
        return recreate_collection(client, collection_name, description, embedding_metadata, chunk_size, note_count)
    else:
        return create_collection(client, collection_name, description, embedding_metadata, chunk_size, note_count)


def compute_adjacent_chunk_ids(chunks_with_embeddings: ChunkWithEmbeddingList) -> Dict[str, Dict[str, Optional[str]]]:
    # Group chunks by noteId
    chunks_by_note: Dict[str, List[ChunkWithEmbedding]] = {}
    for chunk in chunks_with_embeddings:
        note_id = chunk.noteId
        if note_id not in chunks_by_note:
            chunks_by_note[note_id] = []
        chunks_by_note[note_id].append(chunk)

    # Sort each note's chunks by chunkIndex
    for note_id in chunks_by_note:
        chunks_by_note[note_id].sort(key=lambda c: c.chunkIndex)

    # Compute adjacent IDs for each chunk
    adjacent_ids: Dict[str, Dict[str, Optional[str]]] = {}

    for note_id, note_chunks in chunks_by_note.items():
        for i, chunk in enumerate(note_chunks):
            adjacent_ids[chunk.id] = {
                'prev2': note_chunks[i-2].id if i >= 2 else None,
                'prev1': note_chunks[i-1].id if i >= 1 else None,
                'next1': note_chunks[i+1].id if i < len(note_chunks) - 1 else None,
                'next2': note_chunks[i+2].id if i < len(note_chunks) - 2 else None
            }

    return adjacent_ids


def prepare_chunk_batch_data(batch, adjacent_ids_map: Optional[Dict[str, Dict[str, Optional[str]]]] = None):
    ids = [chunk.id for chunk in batch]
    documents = [chunk.content for chunk in batch]
    embeddings = [chunk.embedding for chunk in batch]

    metadatas = []
    for chunk in batch:
        metadata = {
            'noteId': chunk.noteId,
            'title': chunk.title,
            'modificationDate': chunk.modificationDate,
            'creationDate': chunk.creationDate,
            'size': chunk.size,
            'chunkIndex': chunk.chunkIndex
        }

        # Add content hash for first chunk only
        if chunk.content_hash is not None:
            metadata['content_hash'] = chunk.content_hash

        # Add adjacent chunk IDs as a delimited string (schema-flexible for future extensions)
        # Format: "prev2:prev1:next1:next2" where None becomes empty string
        if adjacent_ids_map and chunk.id in adjacent_ids_map:
            adjacent_ids = adjacent_ids_map[chunk.id]
            adjacent_ids_str = ':'.join([
                adjacent_ids.get('prev2') or '',
                adjacent_ids.get('prev1') or '',
                adjacent_ids.get('next1') or '',
                adjacent_ids.get('next2') or ''
            ])
            metadata['adjacent_chunk_ids'] = adjacent_ids_str

        metadatas.append(metadata)

    return ids, documents, embeddings, metadatas


def insert_batch_to_collection(collection, batch, batch_num, stats, adjacent_ids_map=None):
    try:
        ids, documents, embeddings, metadatas = prepare_chunk_batch_data(batch, adjacent_ids_map)

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
        logger.error(f"   {error_msg}")
        return False


def print_storage_summary(stats):
    logger.info(f"   Storage complete:")
    logger.info(f"  Successfully stored: {stats['successful']} chunks")
    logger.info(f"  Failed: {stats['failed']} chunks")
    logger.info(f"  Batches processed: {stats['batches']}")

    if stats["errors"]:
        logger.warning(f"\n   Storage errors:")
        for error in stats["errors"]:
            logger.warning(f"  - {error}")


def insert_chunks(
    collection: chromadb.Collection,
    chunks_with_embeddings: ChunkWithEmbeddingList,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, Any]:
    if not chunks_with_embeddings:
        return {"total_chunks": 0, "batches": 0, "successful": 0, "failed": 0}

    logger.info(f"   Storing {len(chunks_with_embeddings)} chunks in ChromaDB...")

    # Pre-compute adjacent chunk IDs for all chunks (enables fast context retrieval)
    logger.info(f"   Computing adjacent chunk IDs for context retrieval...")
    adjacent_ids_map = compute_adjacent_chunk_ids(chunks_with_embeddings)
    logger.success(f"   ✓ Computed adjacency relationships for {len(adjacent_ids_map)} chunks")

    stats = {
        "total_chunks": len(chunks_with_embeddings),
        "batches": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    try:
        for i in range(0, len(chunks_with_embeddings), batch_size):
            batch = chunks_with_embeddings[i:i + batch_size]
            batch_num = stats["batches"] + 1

            # Insert batch with adjacent IDs and update stats
            insert_batch_to_collection(collection, batch, batch_num, stats, adjacent_ids_map)

            # Progress callback
            if progress_callback:
                progress_callback(min(i + batch_size, len(chunks_with_embeddings)), len(chunks_with_embeddings))

        # Print summary
        print_storage_summary(stats)

        return stats

    except Exception as error:
        raise StorageError(f"Chunk storage failed: {error}")
