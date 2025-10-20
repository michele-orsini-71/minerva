"""Integration tests for the MCP server.

These tests verify the complete flow from tool invocation through to result formatting,
testing the interaction between all modules: config, collection_discovery, search_tools,
context_retrieval, and startup_validation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collection_discovery import list_collections, CollectionDiscoveryError
from search_tools import search_knowledge_base, SearchError, CollectionNotFoundError
from context_retrieval import get_chunk_only_content, get_enhanced_content, get_full_note_content
from config import load_config, ConfigError, ConfigValidationError
from startup_validation import validate_server_prerequisites


class TestCompleteFlow:
    """Test complete end-to-end flow: list collections → search → retrieve context."""

    @patch('collection_discovery.initialize_chromadb_client')
    @patch('search_tools.initialize_chromadb_client')
    def test_full_workflow_list_then_search(
        self,
        mock_search_init,
        mock_list_init,
        mock_chromadb_client,
        sample_embedding,
        sample_chunks
    ):
        """Test complete workflow: list collections, then search a specific collection."""
        # Setup: All modules use the same mocked client
        mock_list_init.return_value = mock_chromadb_client
        mock_search_init.return_value = mock_chromadb_client

        # Setup: Configure collection
        bear_collection = Mock()
        bear_collection.name = "bear_notes"
        bear_collection.metadata = {
            "description": "Personal notes from Bear app",
            "created_at": "2025-09-20T08:49:00Z",
            "version": "1.0",
            "embedding_dimension": 1024,
            "embedding_provider": "ollama",
            "embedding_model": "mxbai-embed-large:latest"
        }
        bear_collection.count.return_value = 150

        # Configure search results - use a function to always return the dictionary
        def mock_query(query_embeddings=None, n_results=1, include=None):
            return {
                "ids": [[sample_chunks[0]["id"]]],
                "documents": [[sample_chunks[0]["content"]]],
                "metadatas": [[sample_chunks[0]["metadata"]]],
                "distances": [[0.15]]
            }
        bear_collection.query.side_effect = mock_query

        # Prepare chunk fixtures for context retrieval
        note_chunks = [
            {
                "id": "chunk_000",
                "content": "Introduction to Python concurrency.",
                "metadata": {
                    "noteId": "note_abc123",
                    "title": "Python Concurrency Patterns",
                    "chunkIndex": 0,
                    "totalChunks": 5,
                    "modificationDate": "2025-09-15T10:30:00Z"
                }
            },
            {
                "id": "chunk_001",
                "content": "Threading vs multiprocessing trade-offs.",
                "metadata": {
                    "noteId": "note_abc123",
                    "title": "Python Concurrency Patterns",
                    "chunkIndex": 1,
                    "totalChunks": 5,
                    "modificationDate": "2025-09-15T10:30:00Z"
                }
            },
            sample_chunks[0],  # chunkIndex: 2 (matched chunk)
            {
                "id": "chunk_003",
                "content": "Best practices for async error handling.",
                "metadata": {
                    "noteId": "note_abc123",
                    "title": "Python Concurrency Patterns",
                    "chunkIndex": 3,
                    "totalChunks": 5,
                    "modificationDate": "2025-09-15T10:30:00Z"
                }
            },
            {
                "id": "chunk_004",
                "content": "Conclusion and further resources.",
                "metadata": {
                    "noteId": "note_abc123",
                    "title": "Python Concurrency Patterns",
                    "chunkIndex": 4,
                    "totalChunks": 5,
                    "modificationDate": "2025-09-15T10:30:00Z"
                }
            }
        ]
        chunks_by_id = {chunk["id"]: chunk for chunk in note_chunks}

        # Configure get method for context retrieval
        def mock_get(where=None, ids=None, include=None):
            if ids:
                matching = [chunks_by_id.get(chunk_id) for chunk_id in ids if chunk_id in chunks_by_id]
                if not matching:
                    return {"ids": [], "documents": [], "metadatas": []}
                return {
                    "ids": [chunk["id"] for chunk in matching],
                    "documents": [chunk["content"] for chunk in matching],
                    "metadatas": [chunk["metadata"] for chunk in matching]
                }

            if not where:
                return {"ids": [], "documents": [], "metadatas": []}

            # Handle both simple queries and $and queries
            note_id_to_match = None
            chunk_index_gte = None
            chunk_index_lte = None

            if "$and" in where:
                for condition in where["$and"]:
                    if "noteId" in condition and "$eq" in condition["noteId"]:
                        note_id_to_match = condition["noteId"]["$eq"]
                    elif "chunkIndex" in condition:
                        if "$gte" in condition["chunkIndex"]:
                            chunk_index_gte = condition["chunkIndex"]["$gte"]
                        if "$lte" in condition["chunkIndex"]:
                            chunk_index_lte = condition["chunkIndex"]["$lte"]
            elif "noteId" in where and "$eq" in where["noteId"]:
                note_id_to_match = where["noteId"]["$eq"]

            if note_id_to_match != "note_abc123":
                return {"ids": [], "documents": [], "metadatas": []}

            if chunk_index_gte is not None or chunk_index_lte is not None:
                filtered = [
                    c for c in note_chunks
                    if (chunk_index_gte is None or c["metadata"]["chunkIndex"] >= chunk_index_gte) and
                       (chunk_index_lte is None or c["metadata"]["chunkIndex"] <= chunk_index_lte)
                ]
            else:
                filtered = note_chunks

            return {
                "ids": [c["id"] for c in filtered],
                "documents": [c["content"] for c in filtered],
                "metadatas": [c["metadata"] for c in filtered]
            }

        bear_collection.get.side_effect = mock_get

        mock_chromadb_client.list_collections.return_value = [bear_collection]
        # Reset side_effect from fixture and set return_value
        mock_chromadb_client.get_collection.side_effect = None
        mock_chromadb_client.get_collection.return_value = bear_collection

        # Create mock AI provider
        mock_provider = Mock()
        mock_provider.generate_embedding.return_value = sample_embedding

        # Step 1: List available collections
        collections = list_collections("/fake/chromadb/path")

        assert len(collections) == 1
        assert collections[0]["name"] == "bear_notes"
        assert collections[0]["description"] == "Personal notes from Bear app"
        assert collections[0]["chunk_count"] == 150

        # Step 2: Search in discovered collection
        results = search_knowledge_base(
            query="Python async patterns",
            collection_name="bear_notes",
            chromadb_path="/fake/chromadb/path",
            provider=mock_provider,
            context_mode="enhanced",
            max_results=1
        )

        assert len(results) == 1
        assert results[0]["noteTitle"] == "Python Concurrency Patterns"
        assert results[0]["noteId"] == "note_abc123"
        assert results[0]["chunkIndex"] == 2
        assert results[0]["totalChunks"] == 5
        # Enhanced mode should include markers
        assert "[MATCH START]" in results[0]["content"]
        assert "[MATCH END]" in results[0]["content"]

        # Verify embedding was generated
        mock_provider.generate_embedding.assert_called_once_with("Python async patterns")

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_with_multiple_collections(
        self,
        mock_init,
        mock_chromadb_client
    ):
        """Test listing multiple collections with varying metadata."""
        mock_init.return_value = mock_chromadb_client

        # Add a third collection
        docs_collection = Mock()
        docs_collection.name = "project_docs"
        docs_collection.metadata = {
            "description": "Technical documentation for current projects",
            "created_at": "2025-10-01T12:00:00Z",
            "version": "1.0"
        }
        docs_collection.count.return_value = 75

        collections = mock_chromadb_client.list_collections.return_value
        mock_chromadb_client.list_collections.return_value = collections + [docs_collection]

        # List all collections
        result = list_collections("/fake/chromadb/path")

        assert len(result) == 3
        collection_names = [c["name"] for c in result]
        assert "bear_notes" in collection_names
        assert "wikipedia_history" in collection_names
        assert "project_docs" in collection_names

        # Verify project_docs metadata
        project_docs = [c for c in result if c["name"] == "project_docs"][0]
        assert project_docs["chunk_count"] == 75
        assert "Technical documentation" in project_docs["description"]

    @patch('search_tools.initialize_chromadb_client')
    def test_search_all_context_modes(
        self,
        mock_search_init,
        sample_embedding,
        sample_chunks
    ):
        """Test search with all three context modes: chunk_only, enhanced, full_note."""
        # Setup mocked collection
        collection = Mock()
        collection.name = "bear_notes"
        collection.metadata = {
            "embedding_dimension": 1024,
            "embedding_provider": "ollama",
            "embedding_model": "mxbai-embed-large:latest"
        }

        collection.query.return_value = {
            "ids": [[sample_chunks[0]["id"]]],
            "documents": [[sample_chunks[0]["content"]]],
            "metadatas": [[sample_chunks[0]["metadata"]]],
            "distances": [[0.15]]
        }

        all_chunks = [
            {
                "id": f"chunk_{i:03d}",
                "content": f"Content of chunk {i}",
                "metadata": {
                    "noteId": "note_abc123",
                    "title": "Python Concurrency Patterns",
                    "chunkIndex": i,
                    "totalChunks": 5,
                    "modificationDate": "2025-09-15T10:30:00Z"
                }
            }
            for i in range(5)
        ]
        all_chunks[2]["content"] = sample_chunks[0]["content"]
        chunks_by_id = {chunk["id"]: chunk for chunk in all_chunks}

        def mock_get(where=None, ids=None, include=None):
            if ids:
                matching = [chunks_by_id.get(chunk_id) for chunk_id in ids if chunk_id in chunks_by_id]
                if not matching:
                    return {"ids": [], "documents": [], "metadatas": []}
                return {
                    "ids": [chunk["id"] for chunk in matching],
                    "documents": [chunk["content"] for chunk in matching],
                    "metadatas": [chunk["metadata"] for chunk in matching]
                }

            if not where:
                return {"ids": [], "documents": [], "metadatas": []}

            note_id_to_match = None
            chunk_index_gte = None
            chunk_index_lte = None

            if "$and" in where:
                for condition in where["$and"]:
                    if "noteId" in condition and "$eq" in condition["noteId"]:
                        note_id_to_match = condition["noteId"]["$eq"]
                    elif "chunkIndex" in condition:
                        if "$gte" in condition["chunkIndex"]:
                            chunk_index_gte = condition["chunkIndex"]["$gte"]
                        if "$lte" in condition["chunkIndex"]:
                            chunk_index_lte = condition["chunkIndex"]["$lte"]
            elif "noteId" in where and "$eq" in where["noteId"]:
                note_id_to_match = where["noteId"]["$eq"]

            if note_id_to_match != "note_abc123":
                return {"ids": [], "documents": [], "metadatas": []}

            if chunk_index_gte is not None or chunk_index_lte is not None:
                filtered = [
                    c for c in all_chunks
                    if (chunk_index_gte is None or c["metadata"]["chunkIndex"] >= chunk_index_gte) and
                       (chunk_index_lte is None or c["metadata"]["chunkIndex"] <= chunk_index_lte)
                ]
            else:
                filtered = all_chunks

            return {
                "ids": [c["id"] for c in filtered],
                "documents": [c["content"] for c in filtered],
                "metadatas": [c["metadata"] for c in filtered]
            }

        collection.get.side_effect = mock_get

        client = Mock()
        client.list_collections.return_value = [collection]
        client.get_collection.return_value = collection

        mock_search_init.return_value = client

        # Create mock AI provider
        mock_provider = Mock()
        mock_provider.generate_embedding.return_value = sample_embedding

        # Test chunk_only mode
        results_chunk_only = search_knowledge_base(
            query="test query",
            collection_name="bear_notes",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="chunk_only",
            max_results=1
        )
        assert len(results_chunk_only) == 1
        assert "[MATCH START]" not in results_chunk_only[0]["content"]
        assert results_chunk_only[0]["content"] == sample_chunks[0]["content"]

        # Test enhanced mode
        results_enhanced = search_knowledge_base(
            query="test query",
            collection_name="bear_notes",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="enhanced",
            max_results=1
        )
        assert len(results_enhanced) == 1
        assert "[MATCH START]" in results_enhanced[0]["content"]
        assert "[MATCH END]" in results_enhanced[0]["content"]
        # Should include surrounding chunks
        assert "Content of chunk 0" in results_enhanced[0]["content"]
        assert "Content of chunk 4" in results_enhanced[0]["content"]

        # Test full_note mode
        results_full = search_knowledge_base(
            query="test query",
            collection_name="bear_notes",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="full_note",
            max_results=1
        )
        assert len(results_full) == 1
        assert "[MATCH AT CHUNK 2]" in results_full[0]["content"]
        # Should include all 5 chunks (chunk 2 has the actual matched content)
        assert "Content of chunk 0" in results_full[0]["content"]
        assert "Content of chunk 1" in results_full[0]["content"]
        # Chunk 2 contains the matched sample text, not "Content of chunk 2"
        assert sample_chunks[0]["content"] in results_full[0]["content"]
        assert "Content of chunk 3" in results_full[0]["content"]
        assert "Content of chunk 4" in results_full[0]["content"]


class TestErrorScenarios:
    """Test error handling in integration scenarios."""

    @patch('search_tools.initialize_chromadb_client')
    def test_search_collection_not_found(self, mock_init):
        """Test searching a collection that doesn't exist."""
        client = Mock()
        client.list_collections.return_value = []  # No collections exist
        client.get_collection.side_effect = Exception("Collection not found")
        mock_init.return_value = client

        # Create mock AI provider
        mock_provider = Mock()
        mock_provider.generate_embedding.return_value = [0.1] * 1024

        with pytest.raises(CollectionNotFoundError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="nonexistent_collection",
                chromadb_path="/fake/path",
                provider=mock_provider,
                context_mode="chunk_only",
                max_results=3
            )

        assert "Collection 'nonexistent_collection' not found" in str(exc_info.value)
        assert "list_knowledge_bases" in str(exc_info.value)

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_chromadb_connection_failure(self, mock_init):
        """Test ChromaDB connection failure when listing collections."""
        mock_init.side_effect = Exception("Failed to connect to ChromaDB")

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections("/invalid/chromadb/path")

        assert "Failed to connect to ChromaDB" in str(exc_info.value)

    @patch('search_tools.initialize_chromadb_client')
    def test_search_ollama_unavailable(self, mock_init):
        """Test search when AI provider service is unavailable."""
        # Setup collection with metadata
        collection = Mock()
        collection.name = "bear_notes"
        collection.metadata = {"embedding_dimension": 1024, "embedding_provider": "ollama"}

        client = Mock()
        client.list_collections.return_value = [collection]
        client.get_collection.return_value = collection
        mock_init.return_value = client

        # Create mock AI provider that raises error
        mock_provider = Mock()
        from ai_provider import ProviderUnavailableError
        mock_provider.generate_embedding.side_effect = ProviderUnavailableError("AI provider service unavailable")

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="bear_notes",
                chromadb_path="/fake/path",
                provider=mock_provider,
                context_mode="chunk_only",
                max_results=3
            )

        assert "AI provider unavailable" in str(exc_info.value)

    @patch('startup_validation.Path')
    def test_startup_validation_chromadb_path_invalid(self, mock_path):
        """Test startup validation with invalid ChromaDB path."""
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        config = {
            "chromadb_path": "/nonexistent/path",
            "default_max_results": 3,
            "embedding_model": "mxbai-embed-large:latest"
        }

        success, error = validate_server_prerequisites(config)

        assert success is False
        assert "ChromaDB path does not exist" in error
        assert "/nonexistent/path" in error

    @patch('startup_validation.os.access')
    @patch('startup_validation.Path')
    @patch('startup_validation.initialize_chromadb_client')
    def test_startup_validation_no_collections(self, mock_init, mock_path, mock_access):
        """Test startup validation when no collections exist."""
        # Path exists and is readable
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path.return_value = mock_path_instance
        mock_access.return_value = True  # Path is readable

        # But no collections
        client = Mock()
        client.list_collections.return_value = []
        mock_init.return_value = client

        config = {
            "chromadb_path": "/valid/path",
            "default_max_results": 3
        }

        success, error = validate_server_prerequisites(config)

        assert success is False
        assert "No collections found" in error
        assert "run the" in error.lower() and "pipeline" in error.lower()

    @patch('startup_validation.os.access')
    @patch('startup_validation.Path')
    @patch('startup_validation.initialize_chromadb_client')
    def test_startup_validation_success(
        self,
        mock_init,
        mock_path,
        mock_access
    ):
        """Test startup validation with all prerequisites met.

        Note: Provider validation (Ollama/OpenAI/Gemini) happens during collection
        discovery, not during startup validation. Startup only validates ChromaDB
        path and collection existence.
        """
        # Everything is configured correctly
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path.return_value = mock_path_instance
        mock_access.return_value = True  # Path is readable

        client = Mock()
        collection = Mock()
        collection.name = "bear_notes"
        client.list_collections.return_value = [collection]
        mock_init.return_value = client

        config = {
            "chromadb_path": "/valid/path",
            "default_max_results": 3
        }

        success, error = validate_server_prerequisites(config)

        assert success is True
        assert error is None


class TestConfigurationIntegration:
    """Test configuration loading and validation in integration scenarios."""

    def test_load_valid_config_file(self, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.json"
        config_file.write_text('''{
            "chromadb_path": "/absolute/path/to/chromadb",
            "default_max_results": 5
        }''')

        config = load_config(str(config_file))

        assert config["chromadb_path"] == "/absolute/path/to/chromadb"
        assert config["default_max_results"] == 5

    def test_load_config_with_missing_fields(self, tmp_path):
        """Test loading config with missing required fields."""
        config_file = tmp_path / "config.json"
        config_file.write_text('''{
            "chromadb_path": "/absolute/path/to/chromadb"
        }''')

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        # The actual error message format is "Missing required field"
        assert "Missing required field" in str(exc_info.value)

    def test_load_config_invalid_json(self, tmp_path):
        """Test loading malformed JSON config file."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{invalid json')

        with pytest.raises(ConfigError) as exc_info:
            load_config(str(config_file))

        assert "Invalid JSON in configuration file" in str(exc_info.value)

    def test_load_config_nonexistent_file(self):
        """Test loading a config file that doesn't exist."""
        with pytest.raises(ConfigError) as exc_info:
            load_config("/nonexistent/config.json")

        assert "Configuration file not found" in str(exc_info.value)
