#!/usr/bin/env python3
"""
ChromaDB storage module for Bear Notes RAG system.

Handles vector database operations including collection management, batch insertion,
and metadata persistence. Configured for cosine similarity with HNSW index.
"""

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
    """Exception raised when storage operations fail."""
    pass


class ChromaDBConnectionError(Exception):
    """Exception raised when ChromaDB connection fails."""
    pass


def initialize_chromadb_client(db_path: str = DEFAULT_CHROMADB_PATH) -> chromadb.PersistentClient:
    """
    Initialize ChromaDB persistent client with proper configuration.

    Args:
        db_path: Path to ChromaDB data directory

    Returns:
        Configured ChromaDB persistent client

    Raises:
        ChromaDBConnectionError: If client initialization fails
    """
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
    reset_collection: bool = False
) -> chromadb.Collection:
    """
    Get or create ChromaDB collection with optimal configuration for Bear notes.

    Args:
        client: ChromaDB client instance
        collection_name: Name of the collection
        reset_collection: If True, delete existing collection before creating

    Returns:
        Configured ChromaDB collection

    Raises:
        StorageError: If collection operations fail
    """
    try:
        # Reset collection if requested
        if reset_collection:
            try:
                client.delete_collection(collection_name)
                print(f"🗑️  Deleted existing collection '{collection_name}' for clean rebuild")
            except Exception as e:
                # Collection might not exist, which is fine
                print(f"ℹ️  Collection '{collection_name}' not found for deletion (expected if first run)")

        # Create or get collection with optimal settings
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": HNSW_SPACE,  # Cosine similarity for L2-normalized embeddings
                "description": "Bear Notes semantic chunks with metadata",
                "version": "1.0"
            }
        )

        return collection

    except Exception as e:
        raise StorageError(f"Failed to create/access collection '{collection_name}': {e}")


def prepare_batch_data(chunks: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Prepare chunk data for batch ChromaDB insertion.

    Args:
        chunks: List of chunk dictionaries with content, metadata, and embeddings

    Returns:
        Dictionary with formatted data for ChromaDB batch operations

    Raises:
        StorageError: If data preparation fails
    """
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
    """
    Insert chunks into ChromaDB collection in batches.

    Args:
        collection: ChromaDB collection instance
        chunks: List of chunk dictionaries
        batch_size: Number of chunks per batch
        progress_callback: Optional callback function(current, total) for progress updates

    Returns:
        Dictionary with insertion statistics

    Raises:
        StorageError: If batch insertion fails
    """
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
                print(f"⚠️  {error_msg}", file=sys.stderr)
                continue

        return stats

    except Exception as e:
        raise StorageError(f"Batch insertion failed: {e}")


def get_collection_stats(collection: chromadb.Collection) -> Dict[str, Any]:
    """
    Get statistics about the ChromaDB collection.

    Args:
        collection: ChromaDB collection instance

    Returns:
        Dictionary with collection statistics

    Raises:
        StorageError: If stats retrieval fails
    """
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
    """
    Validate ChromaDB storage setup and return status information.

    Args:
        db_path: Path to ChromaDB data directory
        collection_name: Name of the collection to validate

    Returns:
        Dictionary with validation results

    Raises:
        ChromaDBConnectionError: If validation fails
    """
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
    """
    High-level storage manager for Bear Notes ChromaDB operations.

    Provides a clean interface for all storage operations with proper error handling
    and resource management.
    """

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
        """
        Initialize the storage system.

        Args:
            reset_collection: If True, delete existing collection

        Returns:
            Initialization status and statistics

        Raises:
            ChromaDBConnectionError: If initialization fails
        """
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
        """
        Query for similar chunks using embeddings.

        Args:
            query_embeddings: List of query embedding vectors
            n_results: Number of results to return
            metadata_filter: Optional metadata filter

        Returns:
            Query results from ChromaDB

        Raises:
            StorageError: If query fails
        """
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
    """
    Insert ChunkWithEmbedding objects into ChromaDB collection.

    This is the new immutable API that takes ChunkWithEmbedding objects directly,
    eliminating data conversion between pipeline stages.

    Args:
        collection: ChromaDB collection instance
        chunks_with_embeddings: List of ChunkWithEmbedding objects
        batch_size: Number of chunks per batch
        progress_callback: Optional callback function(current, total) for progress updates

    Returns:
        Dictionary with insertion statistics

    Raises:
        StorageError: If batch insertion fails
    """
    if not chunks_with_embeddings:
        return {"total_chunks": 0, "batches": 0, "successful": 0, "failed": 0}

    print(f"🗄️  Storing {len(chunks_with_embeddings)} chunks in ChromaDB...")

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
                        'note_id': chunk.note_id,
                        'title': chunk.title,
                        'modificationDate': chunk.modificationDate,
                        'creationDate': chunk.creationDate,
                        'size': chunk.size,
                        'chunk_index': chunk.chunk_index
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
                print(f"⚠️  {error_msg}", file=sys.stderr)
                continue

        # Summary
        print(f"✅ Storage complete:")
        print(f"  Successfully stored: {stats['successful']} chunks")
        print(f"  Failed: {stats['failed']} chunks")
        print(f"  Batches processed: {stats['batches']}")

        if stats["errors"]:
            print(f"\n❌ Storage errors:")
            for error in stats["errors"]:
                print(f"  - {error}")

        return stats

    except Exception as e:
        raise StorageError(f"Chunk storage failed: {e}")


if __name__ == "__main__":
    # Simple test when run directly
    print("🧪 Testing storage.py module")
    print("=" * 50)

    try:
        # Test storage validation
        print("🔍 Validating storage setup...")
        validation = validate_storage_setup()
        print(f"✅ Storage validation: {validation}")
        print()

        # Test storage manager
        print("📦 Testing storage manager...")
        storage = BearNotesStorage()

        init_result = storage.initialize(reset_collection=True)
        print(f"✅ Storage initialized: {init_result}")

        stats = storage.get_stats()
        print(f"✅ Collection stats: {stats}")
        print()

        print("🎉 All storage tests completed successfully!")

    except Exception as e:
        print(f"❌ Storage test failed: {e}", file=sys.stderr)
        sys.exit(1)