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
from search_tools import search_knowledge_base, SearchError
from context_retrieval import get_chunk_only_content, get_enhanced_content, get_full_note_content
from config import load_config, ConfigError, ConfigValidationError
from startup_validation import validate_server_prerequisites


class TestCompleteFlow:
    """Test complete end-to-end flow: list collections → search → retrieve context."""

    @patch('collection_discovery.initialize_chromadb_client')
    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.generate_embedding')
    def test_full_workflow_list_then_search(
        self,
        mock_generate_embedding,
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
            "version": "1.0"
        }
        bear_collection.count.return_value = 150

        # Configure search results
        bear_collection.query.return_value = {
            "ids": [[sample_chunks[0]["id"]]],
            "documents": [[sample_chunks[0]["content"]]],
            "metadatas": [[sample_chunks[0]["metadata"]]],
            "distances": [[0.15]]
        }

        # Configure get method for context retrieval
        def mock_get(where=None, ids=None):
            if where and where.get("note_id") == "note_abc123":
                # Return chunks for the matched note
                note_chunks = [
                    {
                        "id": "chunk_000",
                        "content": "Introduction to Python concurrency.",
                        "metadata": {
                            "note_id": "note_abc123",
                            "title": "Python Concurrency Patterns",
                            "chunk_index": 0,
                            "total_chunks": 5,
                            "modification_date": "2025-09-15T10:30:00Z"
                        }
                    },
                    {
                        "id": "chunk_001",
                        "content": "Threading vs multiprocessing trade-offs.",
                        "metadata": {
                            "note_id": "note_abc123",
                            "title": "Python Concurrency Patterns",
                            "chunk_index": 1,
                            "total_chunks": 5,
                            "modification_date": "2025-09-15T10:30:00Z"
                        }
                    },
                    sample_chunks[0],  # chunk_index: 2 (matched chunk)
                    {
                        "id": "chunk_003",
                        "content": "Best practices for async error handling.",
                        "metadata": {
                            "note_id": "note_abc123",
                            "title": "Python Concurrency Patterns",
                            "chunk_index": 3,
                            "total_chunks": 5,
                            "modification_date": "2025-09-15T10:30:00Z"
                        }
                    },
                    {
                        "id": "chunk_004",
                        "content": "Conclusion and further resources.",
                        "metadata": {
                            "note_id": "note_abc123",
                            "title": "Python Concurrency Patterns",
                            "chunk_index": 4,
                            "total_chunks": 5,
                            "modification_date": "2025-09-15T10:30:00Z"
                        }
                    }
                ]
                # Filter by chunk_index if specified
                if "$gte" in where.get("chunk_index", {}) or "$lte" in where.get("chunk_index", {}):
                    gte = where.get("chunk_index", {}).get("$gte", 0)
                    lte = where.get("chunk_index", {}).get("$lte", 999)
                    filtered = [c for c in note_chunks if gte <= c["metadata"]["chunk_index"] <= lte]
                else:
                    filtered = note_chunks

                return {
                    "ids": [c["id"] for c in filtered],
                    "documents": [c["content"] for c in filtered],
                    "metadatas": [c["metadata"] for c in filtered]
                }
            return {"ids": [], "documents": [], "metadatas": []}

        bear_collection.get.side_effect = mock_get

        mock_chromadb_client.list_collections.return_value = [bear_collection]
        mock_chromadb_client.get_collection.return_value = bear_collection

        mock_generate_embedding.return_value = sample_embedding

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
            context_mode="enhanced",
            max_results=1
        )

        assert len(results) == 1
        assert results[0]["note_title"] == "Python Concurrency Patterns"
        assert results[0]["note_id"] == "note_abc123"
        assert results[0]["chunk_index"] == 2
        assert results[0]["total_chunks"] == 5
        # Enhanced mode should include markers
        assert "[MATCH START]" in results[0]["content"]
        assert "[MATCH END]" in results[0]["content"]

        # Verify embedding was generated
        mock_generate_embedding.assert_called_once_with("Python async patterns")

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
    @patch('search_tools.generate_embedding')
    def test_search_all_context_modes(
        self,
        mock_generate_embedding,
        mock_search_init,
        sample_embedding,
        sample_chunks
    ):
        """Test search with all three context modes: chunk_only, enhanced, full_note."""
        # Setup mocked collection
        collection = Mock()
        collection.name = "bear_notes"

        collection.query.return_value = {
            "ids": [[sample_chunks[0]["id"]]],
            "documents": [[sample_chunks[0]["content"]]],
            "metadatas": [[sample_chunks[0]["metadata"]]],
            "distances": [[0.15]]
        }

        def mock_get(where=None, ids=None):
            if where and where.get("note_id") == "note_abc123":
                # Return all chunks for the note
                all_chunks = [
                    {
                        "id": f"chunk_{i:03d}",
                        "content": f"Content of chunk {i}",
                        "metadata": {
                            "note_id": "note_abc123",
                            "title": "Python Concurrency Patterns",
                            "chunk_index": i,
                            "total_chunks": 5,
                            "modification_date": "2025-09-15T10:30:00Z"
                        }
                    }
                    for i in range(5)
                ]
                # Match chunk at index 2
                all_chunks[2]["content"] = sample_chunks[0]["content"]

                # Filter by chunk_index range if specified
                if "$gte" in where.get("chunk_index", {}) or "$lte" in where.get("chunk_index", {}):
                    gte = where.get("chunk_index", {}).get("$gte", 0)
                    lte = where.get("chunk_index", {}).get("$lte", 999)
                    filtered = [c for c in all_chunks if gte <= c["metadata"]["chunk_index"] <= lte]
                else:
                    filtered = all_chunks

                return {
                    "ids": [c["id"] for c in filtered],
                    "documents": [c["content"] for c in filtered],
                    "metadatas": [c["metadata"] for c in filtered]
                }
            return {"ids": [], "documents": [], "metadatas": []}

        collection.get.side_effect = mock_get

        client = Mock()
        client.get_collection.return_value = collection

        mock_search_init.return_value = client
        mock_generate_embedding.return_value = sample_embedding

        # Test chunk_only mode
        results_chunk_only = search_knowledge_base(
            query="test query",
            collection_name="bear_notes",
            chromadb_path="/fake/path",
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
            context_mode="full_note",
            max_results=1
        )
        assert len(results_full) == 1
        assert "[MATCH AT CHUNK 2]" in results_full[0]["content"]
        # Should include all 5 chunks
        for i in range(5):
            assert f"Content of chunk {i}" in results_full[0]["content"]


class TestErrorScenarios:
    """Test error handling in integration scenarios."""

    @patch('search_tools.initialize_chromadb_client')
    def test_search_collection_not_found(self, mock_init):
        """Test searching a collection that doesn't exist."""
        client = Mock()
        client.get_collection.side_effect = Exception("Collection not found")
        mock_init.return_value = client

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="nonexistent_collection",
                chromadb_path="/fake/path",
                context_mode="chunk_only",
                max_results=3
            )

        assert "Collection 'nonexistent_collection' does not exist" in str(exc_info.value)
        assert "list_knowledge_bases" in str(exc_info.value)

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_chromadb_connection_failure(self, mock_init):
        """Test ChromaDB connection failure when listing collections."""
        mock_init.side_effect = Exception("Failed to connect to ChromaDB")

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections("/invalid/chromadb/path")

        assert "Failed to connect to ChromaDB" in str(exc_info.value)

    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.generate_embedding')
    def test_search_ollama_unavailable(self, mock_generate_embedding, mock_init):
        """Test search when Ollama service is unavailable."""
        mock_init.return_value = Mock()
        mock_generate_embedding.side_effect = Exception("Ollama service unavailable")

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="bear_notes",
                chromadb_path="/fake/path",
                context_mode="chunk_only",
                max_results=3
            )

        assert "Failed to generate embedding" in str(exc_info.value)

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

    @patch('startup_validation.Path')
    @patch('startup_validation.initialize_chromadb_client')
    def test_startup_validation_no_collections(self, mock_init, mock_path):
        """Test startup validation when no collections exist."""
        # Path exists
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        # But no collections
        client = Mock()
        client.list_collections.return_value = []
        mock_init.return_value = client

        config = {
            "chromadb_path": "/valid/path",
            "default_max_results": 3,
            "embedding_model": "mxbai-embed-large:latest"
        }

        success, error = validate_server_prerequisites(config)

        assert success is False
        assert "No collections found" in error
        assert "run the pipeline" in error.lower()

    @patch('startup_validation.Path')
    @patch('startup_validation.initialize_chromadb_client')
    @patch('startup_validation.check_ollama_service')
    def test_startup_validation_ollama_unavailable(
        self,
        mock_check_ollama,
        mock_init,
        mock_path
    ):
        """Test startup validation when Ollama service is down."""
        # Path exists and has collections
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        client = Mock()
        collection = Mock()
        collection.name = "bear_notes"
        client.list_collections.return_value = [collection]
        mock_init.return_value = client

        # But Ollama is unavailable
        mock_check_ollama.return_value = False

        config = {
            "chromadb_path": "/valid/path",
            "default_max_results": 3,
            "embedding_model": "mxbai-embed-large:latest"
        }

        success, error = validate_server_prerequisites(config)

        assert success is False
        assert "Ollama embedding service is unavailable" in error
        assert "ollama serve" in error

    @patch('startup_validation.Path')
    @patch('startup_validation.initialize_chromadb_client')
    @patch('startup_validation.check_ollama_service')
    @patch('startup_validation.check_model_availability')
    def test_startup_validation_model_unavailable(
        self,
        mock_check_model,
        mock_check_ollama,
        mock_init,
        mock_path
    ):
        """Test startup validation when embedding model is not available."""
        # Path exists, collections exist, Ollama running
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        client = Mock()
        collection = Mock()
        collection.name = "bear_notes"
        client.list_collections.return_value = [collection]
        mock_init.return_value = client

        mock_check_ollama.return_value = True

        # But model is not available
        mock_check_model.return_value = False

        config = {
            "chromadb_path": "/valid/path",
            "default_max_results": 3,
            "embedding_model": "mxbai-embed-large:latest"
        }

        success, error = validate_server_prerequisites(config)

        assert success is False
        assert "Embedding model 'mxbai-embed-large:latest' is not available" in error
        assert "ollama pull" in error

    @patch('startup_validation.Path')
    @patch('startup_validation.initialize_chromadb_client')
    @patch('startup_validation.check_ollama_service')
    @patch('startup_validation.check_model_availability')
    def test_startup_validation_success(
        self,
        mock_check_model,
        mock_check_ollama,
        mock_init,
        mock_path
    ):
        """Test startup validation with all prerequisites met."""
        # Everything is configured correctly
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        client = Mock()
        collection = Mock()
        collection.name = "bear_notes"
        client.list_collections.return_value = [collection]
        mock_init.return_value = client

        mock_check_ollama.return_value = True
        mock_check_model.return_value = True

        config = {
            "chromadb_path": "/valid/path",
            "default_max_results": 3,
            "embedding_model": "mxbai-embed-large:latest"
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
            "default_max_results": 5,
            "embedding_model": "mxbai-embed-large:latest"
        }''')

        config = load_config(str(config_file))

        assert config["chromadb_path"] == "/absolute/path/to/chromadb"
        assert config["default_max_results"] == 5
        assert config["embedding_model"] == "mxbai-embed-large:latest"

    def test_load_config_with_missing_fields(self, tmp_path):
        """Test loading config with missing required fields."""
        config_file = tmp_path / "config.json"
        config_file.write_text('''{
            "chromadb_path": "/absolute/path/to/chromadb"
        }''')

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "Missing required configuration field" in str(exc_info.value)

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
