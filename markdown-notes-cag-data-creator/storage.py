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
DEFAULT_CHROMADB_PATH = "../chromadb_data/bear_notes_embeddings"
DEFAULT_COLLECTION_NAME = "bear_notes_chunks"
DEFAULT_BATCH_SIZE = 64
HNSW_SPACE = "cosine"  # Distance metric for HNSW index


class StorageError(Exception):
    pass


class ChromaDBConnectionError(Exception):
    pass


def initialize_chromadb_client(db_path: str = DEFAULT_CHROMADB_PATH) -> chromadb.PersistentClient:
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


def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    description: Optional[str] = None,
    force_recreate: bool = False,
    reset_collection: bool = False  # Deprecated parameter kept for backward compatibility
) -> chromadb.Collection:
    try:
        # Handle backward compatibility (reset_collection is deprecated)
        if reset_collection:
            print("   Warning: 'reset_collection' parameter is deprecated, use 'force_recreate' instead")
            force_recreate = True

        # Check if collection already exists
        existing_collections = [col.name for col in client.list_collections()]
        collection_exists = collection_name in existing_collections

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

        elif collection_exists and not force_recreate:
            # Collection exists but force_recreate=False - this is an error condition
            raise StorageError(
                f"Collection '{collection_name}' already exists\n"
                f"  Options:\n"
                f"    1. Use a different collection name\n"
                f"    2. Set 'forceRecreate': true in your configuration file to delete and recreate\n"
                f"       (WARNING: This will permanently delete all existing data!)\n"
                f"    3. Use the existing collection (not currently supported)\n"
                f"  Note: force_recreate is a destructive operation - use with caution!"
            )

        # Prepare metadata
        from datetime import datetime, timezone

        metadata = {
            "hnsw:space": HNSW_SPACE,  # Cosine similarity for L2-normalized embeddings
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Add description to metadata if provided
        if description:
            metadata["description"] = description
        else:
            # Use default description with warning
            metadata["description"] = "Markdown notes semantic chunks with metadata"
            print(f"   Using default description for collection '{collection_name}'")
            print(f"   Suggestion: Provide a custom description via --config for better organization")

        # Create collection (we know it doesn't exist at this point)
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


def insert_chunks_batch(
    collection: chromadb.Collection,
    chunks: List[Dict[str, Any]],
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    if not chunks:
        return {"total_chunks": 0, "batches": 0, "successful": 0, "failed": 0}

    stats = {
        "total_chunks": len(chunks),
        "batches": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    try:
        # Process chunks in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = stats["batches"] + 1

            try:
                # Prepare batch data
                batch_data = prepare_batch_data(batch)

                # Insert batch into collection
                if batch_data["embeddings"] is not None:
                    collection.add(
                        ids=batch_data["ids"],
                        documents=batch_data["documents"],
                        metadatas=batch_data["metadatas"],
                        embeddings=batch_data["embeddings"]
                    )
                else:
                    # Let ChromaDB generate embeddings (if configured)
                    collection.add(
                        ids=batch_data["ids"],
                        documents=batch_data["documents"],
                        metadatas=batch_data["metadatas"]
                    )

                stats["successful"] += len(batch)
                stats["batches"] += 1

                # Progress callback
                if progress_callback:
                    progress_callback(min(i + batch_size, len(chunks)), len(chunks))

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {e}"
                stats["errors"].append(error_msg)
                stats["failed"] += len(batch)
                print(f"   {error_msg}", file=sys.stderr)
                continue

        return stats

    except Exception as e:
        raise StorageError(f"Batch insertion failed: {e}")


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


def validate_storage_setup(
    db_path: str = DEFAULT_CHROMADB_PATH,
    collection_name: str = DEFAULT_COLLECTION_NAME
) -> Dict[str, Any]:
    try:
        # Initialize client
        client = initialize_chromadb_client(db_path)

        # Get or create collection
        collection = get_or_create_collection(client, collection_name, reset_collection=False)

        # Get collection stats
        stats = get_collection_stats(collection)

        # Return validation results
        return {
            "db_path": os.path.abspath(os.path.expanduser(db_path)),
            "client_ready": True,
            "collection_ready": True,
            "collection_stats": stats
        }

    except Exception as e:
        raise ChromaDBConnectionError(f"Storage validation failed: {e}")


class BearNotesStorage:
    def __init__(
        self,
        db_path: str = DEFAULT_CHROMADB_PATH,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        batch_size: int = DEFAULT_BATCH_SIZE
    ):
        """
        Initialize storage manager.

        Args:
            db_path: Path to ChromaDB data directory
            collection_name: Name of the collection
            batch_size: Default batch size for operations
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.client = None
        self.collection = None

    def initialize(self, reset_collection: bool = False) -> Dict[str, Any]:
        try:
            # Initialize client
            self.client = initialize_chromadb_client(self.db_path)

            # Get or create collection
            self.collection = get_or_create_collection(
                self.client,
                self.collection_name,
                reset_collection=reset_collection
            )

            # Get initial stats
            stats = get_collection_stats(self.collection)

            return {
                "status": "initialized",
                "db_path": os.path.abspath(os.path.expanduser(self.db_path)),
                "collection_name": self.collection_name,
                "reset_performed": reset_collection,
                "stats": stats
            }

        except Exception as e:
            raise ChromaDBConnectionError(f"Storage initialization failed: {e}")

    def store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Store chunks in the ChromaDB collection.

        Args:
            chunks: List of chunk dictionaries
            progress_callback: Optional progress callback

        Returns:
            Storage operation statistics

        Raises:
            StorageError: If storage operation fails
        """
        if not self.collection:
            raise StorageError("Storage not initialized. Call initialize() first.")

        return insert_chunks_batch(
            self.collection,
            chunks,
            batch_size=self.batch_size,
            progress_callback=progress_callback
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.

        Returns:
            Collection statistics dictionary

        Raises:
            StorageError: If collection is not initialized
        """
        if not self.collection:
            raise StorageError("Storage not initialized. Call initialize() first.")

        return get_collection_stats(self.collection)

    def query_similar(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.collection:
            raise StorageError("Storage not initialized. Call initialize() first.")

        try:
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=metadata_filter
            )
            return results

        except Exception as e:
            raise StorageError(f"Query failed: {e}")


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
