import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path to import search_tools module
sys.path.insert(0, str(Path(__file__).parent.parent))

from search_tools import (
    search_knowledge_base,
    validate_collection_exists,
    SearchError,
    CollectionNotFoundError
)
from ai_provider import AIProvider, AIProviderError, ProviderUnavailableError


class TestValidateCollectionExists:
    """Test collection validation functionality."""

    def test_validate_collection_exists_success(self):
        """Test successful validation when collection exists."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"

        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        result = validate_collection_exists(mock_client, "test_collection")

        assert result == mock_collection
        mock_client.get_collection.assert_called_once_with("test_collection")

    def test_validate_collection_not_found(self):
        """Test validation raises error when collection doesn't exist."""
        mock_client = Mock()
        mock_collection1 = Mock()
        mock_collection1.name = "other_collection"

        mock_client.list_collections.return_value = [mock_collection1]

        with pytest.raises(CollectionNotFoundError) as exc_info:
            validate_collection_exists(mock_client, "missing_collection")

        assert "missing_collection" in str(exc_info.value)
        assert "list_knowledge_bases" in str(exc_info.value)
        assert "other_collection" in str(exc_info.value)

    def test_validate_collection_no_collections(self):
        """Test validation when no collections exist."""
        mock_client = Mock()
        mock_client.list_collections.return_value = []

        with pytest.raises(CollectionNotFoundError) as exc_info:
            validate_collection_exists(mock_client, "any_collection")

        assert "any_collection" in str(exc_info.value)
        assert "none" in str(exc_info.value).lower()


class TestSearchKnowledgeBase:
    """Test semantic search functionality."""

    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.apply_context_mode')
    def test_search_success_basic(self, mock_context, mock_init_client):
        """Test successful search with basic results."""
        # Setup mocks
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {'embedding_dimension': 1024}
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        # Mock provider
        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 1024

        # Mock search results
        mock_collection.query.return_value = {
            'ids': [['chunk1', 'chunk2']],
            'documents': [['First chunk content', 'Second chunk content']],
            'metadatas': [[
                {
                    'title': 'Test Note',
                    'noteId': 'note123',
                    'chunkIndex': 0,
                    'modificationDate': '2024-01-01T00:00:00Z'
                },
                {
                    'title': 'Test Note',
                    'noteId': 'note123',
                    'chunkIndex': 1,
                    'modificationDate': '2024-01-01T00:00:00Z'
                }
            ]],
            'distances': [[0.2, 0.3]]
        }

        # Mock context mode to return results as-is
        mock_context.return_value = [
            {
                'noteTitle': 'Test Note',
                'noteId': 'note123',
                'chunkIndex': 0,
                'modificationDate': '2024-01-01T00:00:00Z',
                'collectionName': 'test_notes',
                'similarityScore': 0.8,
                'content': 'First chunk content',
                'totalChunks': 1
            }
        ]

        # Execute search
        results = search_knowledge_base(
            query="test query",
            collection_name="test_notes",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="chunk_only",
            max_results=5
        )

        # Verify
        assert len(results) == 1
        assert results[0]['noteTitle'] == 'Test Note'
        assert results[0]['noteId'] == 'note123'
        mock_provider.generate_embedding.assert_called_once_with("test query")
        mock_context.assert_called_once()

    @patch('search_tools.initialize_chromadb_client')
    def test_search_collection_not_found(self, mock_init_client):
        """Test search fails when collection doesn't exist."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client
        mock_client.list_collections.return_value = []

        mock_provider = Mock(spec=AIProvider)

        with pytest.raises(CollectionNotFoundError):
            search_knowledge_base(
                query="test query",
                collection_name="missing_collection",
                chromadb_path="/fake/path",
                provider=mock_provider
            )

    def test_search_empty_query(self):
        """Test search fails with empty query."""
        mock_provider = Mock(spec=AIProvider)

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider
            )

        assert "empty" in str(exc_info.value).lower()

    def test_search_invalid_max_results(self):
        """Test search fails with invalid max_results."""
        mock_provider = Mock(spec=AIProvider)

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider,
                max_results=0
            )

        assert "max_results" in str(exc_info.value)

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider,
                max_results=101
            )

        assert "max_results" in str(exc_info.value)

    def test_search_invalid_context_mode(self):
        """Test search fails with invalid context mode."""
        mock_provider = Mock(spec=AIProvider)

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider,
                context_mode="invalid_mode"
            )

        assert "context_mode" in str(exc_info.value)
        assert "chunk_only" in str(exc_info.value)
        assert "enhanced" in str(exc_info.value)
        assert "full_note" in str(exc_info.value)

    @patch('search_tools.initialize_chromadb_client')
    def test_search_provider_unavailable(self, mock_init_client):
        """Test search handles provider unavailability."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'embedding_dimension': 1024
        }
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.side_effect = ProviderUnavailableError("Connection refused")

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider
            )

        assert "provider unavailable" in str(exc_info.value).lower()

    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.apply_context_mode')
    def test_search_no_results(self, mock_context, mock_init_client):
        """Test search with no matching results."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {'embedding_dimension': 1024}
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 1024

        # Mock empty results
        mock_collection.query.return_value = {
            'ids': [[]],
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }

        mock_context.return_value = []

        results = search_knowledge_base(
            query="no matches",
            collection_name="test_notes",
            chromadb_path="/fake/path",
            provider=mock_provider
        )

        assert len(results) == 0

    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.apply_context_mode')
    def test_search_similarity_score_calculation(self, mock_context, mock_init_client):
        """Test similarity score is calculated correctly from distance."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {'embedding_dimension': 1024}
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 1024

        # Mock results with known distance
        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'documents': [['Content']],
            'metadatas': [[{
                'title': 'Note',
                'noteId': 'id1',
                'chunkIndex': 0,
                'modificationDate': '2024-01-01T00:00:00Z'
            }]],
            'distances': [[0.25]]
        }

        # Capture what gets passed to context mode
        def capture_results(collection, results, mode):
            assert results[0]['similarityScore'] == 0.75
            return results

        mock_context.side_effect = capture_results

        search_knowledge_base(
            query="test",
            collection_name="test_notes",
            chromadb_path="/fake/path",
            provider=mock_provider
        )

    @patch('search_tools.initialize_chromadb_client')
    def test_search_embedding_dimension_mismatch(self, mock_init_client):
        """Test embedding dimension validation with mismatching dimensions."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest'
        }
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 768

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider
            )

        error_msg = str(exc_info.value)
        assert "dimension mismatch" in error_msg.lower()
        assert "768" in error_msg
        assert "1024" in error_msg

    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.apply_context_mode')
    def test_search_embedding_dimension_matching(self, mock_context, mock_init_client):
        """Test search succeeds when embedding dimensions match."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest'
        }
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 1024

        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'documents': [['Content']],
            'metadatas': [[{
                'title': 'Note',
                'noteId': 'id1',
                'chunkIndex': 0,
                'modificationDate': '2024-01-01T00:00:00Z'
            }]],
            'distances': [[0.2]]
        }

        mock_context.return_value = [{
            'noteTitle': 'Note',
            'noteId': 'id1',
            'chunkIndex': 0,
            'modificationDate': '2024-01-01T00:00:00Z',
            'collectionName': 'test_notes',
            'similarityScore': 0.8,
            'content': 'Content',
            'totalChunks': 1
        }]

        results = search_knowledge_base(
            query="test query",
            collection_name="test_notes",
            chromadb_path="/fake/path",
            provider=mock_provider
        )

        assert len(results) == 1
        mock_provider.generate_embedding.assert_called_once_with("test query")

    @patch('search_tools.initialize_chromadb_client')
    def test_search_no_metadata_error(self, mock_init_client):
        """Test search fails when collection has no metadata (old collections not supported)."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = None
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)

        with pytest.raises(SearchError) as exc_info:
            search_knowledge_base(
                query="test query",
                collection_name="test_notes",
                chromadb_path="/fake/path",
                provider=mock_provider
            )

        error_msg = str(exc_info.value)
        assert "has no metadata" in error_msg
        assert "old pipeline" in error_msg.lower()

    @patch('search_tools.initialize_chromadb_client')
    @patch('search_tools.apply_context_mode')
    def test_search_missing_dimension_in_metadata(self, mock_context, mock_init_client):
        """Test search succeeds when collection metadata exists but dimension is missing (skips validation)."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_notes"
        mock_collection.metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest'
        }
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection

        mock_provider = Mock(spec=AIProvider)
        mock_provider.generate_embedding.return_value = [0.1] * 768

        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'documents': [['Content']],
            'metadatas': [[{
                'title': 'Note',
                'noteId': 'id1',
                'chunkIndex': 0,
                'modificationDate': '2024-01-01T00:00:00Z'
            }]],
            'distances': [[0.2]]
        }

        mock_context.return_value = [{
            'noteTitle': 'Note',
            'noteId': 'id1',
            'chunkIndex': 0,
            'modificationDate': '2024-01-01T00:00:00Z',
            'collectionName': 'test_notes',
            'similarityScore': 0.8,
            'content': 'Content',
            'totalChunks': 1
        }]

        results = search_knowledge_base(
            query="test query",
            collection_name="test_notes",
            chromadb_path="/fake/path",
            provider=mock_provider
        )

        assert len(results) == 1
