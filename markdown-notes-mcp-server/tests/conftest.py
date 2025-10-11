"""Shared test fixtures for MCP server tests.

This module provides reusable fixtures for mocking ChromaDB collections,
embeddings, and test data across all test modules.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone


# Embedding dimensions for mxbai-embed-large model
EMBEDDING_DIM = 1024


@pytest.fixture
def sample_embedding():
    """Generate a single normalized embedding vector (1024 dimensions)."""
    # Create random vector and normalize to unit length (L2 normalization)
    vec = np.random.randn(EMBEDDING_DIM).astype(np.float32)
    normalized = vec / np.linalg.norm(vec)
    return normalized.tolist()


@pytest.fixture
def sample_embeddings():
    """Generate multiple normalized embedding vectors for batch operations."""
    embeddings = []
    for _ in range(5):
        vec = np.random.randn(EMBEDDING_DIM).astype(np.float32)
        normalized = vec / np.linalg.norm(vec)
        embeddings.append(normalized.tolist())
    return embeddings


@pytest.fixture
def mock_chromadb_client():
    """Create a mock ChromaDB client with collections."""
    client = Mock()

    # Create sample collections
    bear_collection = Mock()
    bear_collection.name = "bear_notes"
    bear_collection.metadata = {
        "description": "Personal notes from Bear app covering software development and productivity",
        "created_at": "2025-09-20T08:49:00Z",
        "version": "1.0"
    }
    bear_collection.count.return_value = 150

    wiki_collection = Mock()
    wiki_collection.name = "wikipedia_history"
    wiki_collection.metadata = {
        "description": "Wikipedia articles on world history and major events",
        "created_at": "2025-09-25T14:30:00Z",
        "version": "1.0"
    }
    wiki_collection.count.return_value = 42

    # Configure client methods
    client.list_collections.return_value = [bear_collection, wiki_collection]
    client.get_collection.side_effect = lambda name: {
        "bear_notes": bear_collection,
        "wikipedia_history": wiki_collection
    }.get(name)

    return client


@pytest.fixture
def sample_chunks():
    """Generate sample chunk data with metadata for testing search results."""
    return [
        {
            "id": "chunk_001",
            "content": "Python async/await provides a clean way to write concurrent code. The asyncio library is built into Python 3.7+.",
            "metadata": {
                "noteId": "note_abc123",
                "title": "Python Concurrency Patterns",
                "chunkIndex": 2,
                "totalChunks": 5,
                "modificationDate": "2025-09-15T10:30:00Z",
                "collectionName": "bear_notes"
            }
        },
        {
            "id": "chunk_002",
            "content": "Context managers in Python use the __enter__ and __exit__ methods to manage resources efficiently.",
            "metadata": {
                "noteId": "note_def456",
                "title": "Python Design Patterns",
                "chunkIndex": 1,
                "totalChunks": 3,
                "modificationDate": "2025-09-18T14:20:00Z",
                "collectionName": "bear_notes"
            }
        },
        {
            "id": "chunk_003",
            "content": "The Battle of Waterloo in 1815 marked the end of Napoleon's rule as Emperor of France.",
            "metadata": {
                "noteId": "note_xyz789",
                "title": "Napoleonic Wars",
                "chunkIndex": 0,
                "totalChunks": 1,
                "modificationDate": "2025-09-22T09:15:00Z",
                "collectionName": "wikipedia_history"
            }
        }
    ]


@pytest.fixture
def mock_collection_with_search_results(sample_chunks, sample_embeddings):
    """Create a mock ChromaDB collection with pre-configured search results."""
    collection = Mock()
    collection.name = "bear_notes"
    collection.metadata = {
        "description": "Personal notes from Bear app",
        "created_at": "2025-09-20T08:49:00Z",
        "version": "1.0"
    }
    collection.count.return_value = 150

    # Configure query method to return search results
    # ChromaDB query returns: {'ids': [[...]], 'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
    collection.query.return_value = {
        "ids": [[sample_chunks[0]["id"], sample_chunks[1]["id"]]],
        "documents": [[sample_chunks[0]["content"], sample_chunks[1]["content"]]],
        "metadatas": [[sample_chunks[0]["metadata"], sample_chunks[1]["metadata"]]],
        "distances": [[0.15, 0.23]]  # Lower is better (cosine distance)
    }

    # Configure get method for fetching chunks by metadata
    def mock_get(where=None, ids=None):
        """Mock get method that filters by metadata or IDs."""
        if ids:
            # Return chunks matching IDs
            matching = [c for c in sample_chunks if c["id"] in ids]
            return {
                "ids": [c["id"] for c in matching],
                "documents": [c["content"] for c in matching],
                "metadatas": [c["metadata"] for c in matching]
            }
        if where:
            # Filter by metadata (e.g., note_id, chunk_index)
            matching = []
            for chunk in sample_chunks:
                match = True
                for key, value in where.items():
                    if chunk["metadata"].get(key) != value:
                        match = False
                        break
                if match:
                    matching.append(chunk)

            return {
                "ids": [c["id"] for c in matching],
                "documents": [c["content"] for c in matching],
                "metadatas": [c["metadata"] for c in matching]
            }
        return {"ids": [], "documents": [], "metadatas": []}

    collection.get.side_effect = mock_get

    return collection


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "chromadb_path": "/absolute/path/to/chromadb_data",
        "default_max_results": 3,
        "embedding_model": "mxbai-embed-large:latest"
    }


@pytest.fixture
def sample_search_results():
    """Sample formatted search results as returned by search_knowledge_base."""
    return [
        {
            "note_title": "Python Concurrency Patterns",
            "note_id": "note_abc123",
            "chunk_index": 2,
            "total_chunks": 5,
            "modification_date": "2025-09-15T10:30:00Z",
            "collection_name": "bear_notes",
            "similarity_score": 0.85,
            "content": "Python async/await provides a clean way to write concurrent code. The asyncio library is built into Python 3.7+."
        },
        {
            "note_title": "Python Design Patterns",
            "note_id": "note_def456",
            "chunk_index": 1,
            "total_chunks": 3,
            "modification_date": "2025-09-18T14:20:00Z",
            "collection_name": "bear_notes",
            "similarity_score": 0.77,
            "content": "Context managers in Python use the __enter__ and __exit__ methods to manage resources efficiently."
        }
    ]
