import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Add parent directory to path to import collection_discovery module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from collection_discovery import (
    list_collections,
    reconstruct_provider_from_metadata,
    discover_collections_with_providers,
    CollectionDiscoveryError
)


class TestListCollections:
    """Test collection listing functionality."""

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_success(self, mock_init_client):
        """Test successful listing of collections with complete metadata."""
        # Create mock client
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        # Create mock collections with metadata
        mock_collection1 = Mock()
        mock_collection1.name = "bear_notes"
        mock_collection1.metadata = {
            "description": "Personal notes from Bear app",
            "created_at": "2024-01-15T10:30:00Z",
            "version": "1.0"
        }
        mock_collection1.count.return_value = 150

        mock_collection2 = Mock()
        mock_collection2.name = "zim_articles"
        mock_collection2.metadata = {
            "description": "Wikipedia articles from Zim",
            "created_at": "2024-02-20T14:45:00Z",
            "version": "1.0"
        }
        mock_collection2.count.return_value = 42

        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]

        # Test collection listing
        collections = list_collections("/fake/path/to/chromadb")

        # Verify results
        assert len(collections) == 2

        # Verify first collection
        assert collections[0]["name"] == "bear_notes"
        assert collections[0]["description"] == "Personal notes from Bear app"
        assert collections[0]["chunk_count"] == 150
        assert collections[0]["created_at"] == "2024-01-15T10:30:00Z"

        # Verify second collection
        assert collections[1]["name"] == "zim_articles"
        assert collections[1]["description"] == "Wikipedia articles from Zim"
        assert collections[1]["chunk_count"] == 42
        assert collections[1]["created_at"] == "2024-02-20T14:45:00Z"

        # Verify client was initialized with correct path
        mock_init_client.assert_called_once_with("/fake/path/to/chromadb")

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_empty_database(self, mock_init_client):
        """Test listing when ChromaDB has no collections."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client
        mock_client.list_collections.return_value = []

        collections = list_collections("/fake/path/to/chromadb")

        assert collections == []
        assert len(collections) == 0

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_missing_metadata(self, mock_init_client):
        """Test listing collections with missing metadata fields."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        # Collection with no metadata at all
        mock_collection1 = Mock()
        mock_collection1.name = "minimal_collection"
        mock_collection1.metadata = None
        mock_collection1.count.return_value = 10

        # Collection with partial metadata (missing description)
        mock_collection2 = Mock()
        mock_collection2.name = "partial_collection"
        mock_collection2.metadata = {
            "created_at": "2024-03-10T08:00:00Z"
        }
        mock_collection2.count.return_value = 25

        # Collection with empty metadata dict
        mock_collection3 = Mock()
        mock_collection3.name = "empty_metadata"
        mock_collection3.metadata = {}
        mock_collection3.count.return_value = 5

        mock_client.list_collections.return_value = [
            mock_collection1,
            mock_collection2,
            mock_collection3
        ]

        collections = list_collections("/fake/path/to/chromadb")

        # Verify default values are used for missing fields
        assert len(collections) == 3

        # Collection with no metadata
        assert collections[0]["name"] == "minimal_collection"
        assert collections[0]["description"] == "No description available"
        assert collections[0]["created_at"] == "Unknown"
        assert collections[0]["chunk_count"] == 10

        # Collection with partial metadata
        assert collections[1]["name"] == "partial_collection"
        assert collections[1]["description"] == "No description available"
        assert collections[1]["created_at"] == "2024-03-10T08:00:00Z"
        assert collections[1]["chunk_count"] == 25

        # Collection with empty metadata
        assert collections[2]["name"] == "empty_metadata"
        assert collections[2]["description"] == "No description available"
        assert collections[2]["created_at"] == "Unknown"
        assert collections[2]["chunk_count"] == 5

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_zero_chunks(self, mock_init_client):
        """Test listing collection with zero chunks."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "empty_collection"
        mock_collection.metadata = {
            "description": "Collection with no data yet",
            "created_at": "2024-04-01T12:00:00Z"
        }
        mock_collection.count.return_value = 0

        mock_client.list_collections.return_value = [mock_collection]

        collections = list_collections("/fake/path/to/chromadb")

        assert len(collections) == 1
        assert collections[0]["chunk_count"] == 0

    @patch('collection_discovery.initialize_chromadb_client')
    def test_chromadb_connection_error(self, mock_init_client):
        """Test handling of ChromaDB connection failures."""
        from storage import ChromaDBConnectionError

        # Simulate connection failure
        mock_init_client.side_effect = ChromaDBConnectionError(
            "Failed to initialize ChromaDB client at '/invalid/path': Connection refused"
        )

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections("/invalid/path")

        error_msg = str(exc_info.value)
        assert "Failed to connect to ChromaDB" in error_msg
        assert "/invalid/path" in error_msg
        assert "Troubleshooting:" in error_msg
        assert "Verify the ChromaDB path" in error_msg

    @patch('collection_discovery.initialize_chromadb_client')
    def test_list_collections_query_error(self, mock_init_client):
        """Test handling of errors during collection listing."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        # Simulate error when listing collections
        mock_client.list_collections.side_effect = Exception("Database corruption detected")

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections("/fake/path/to/chromadb")

        error_msg = str(exc_info.value)
        assert "Failed to list collections" in error_msg
        assert "Database corruption detected" in error_msg
        assert "ChromaDB database corruption" in error_msg

    @patch('collection_discovery.initialize_chromadb_client')
    def test_collection_count_error(self, mock_init_client):
        """Test handling of errors when getting collection count."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "problematic_collection"
        mock_collection.metadata = {"description": "Test collection"}
        # Simulate error when calling count()
        mock_collection.count.side_effect = Exception("Count operation failed")

        mock_client.list_collections.return_value = [mock_collection]

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections("/fake/path/to/chromadb")

        error_msg = str(exc_info.value)
        assert "Failed to list collections" in error_msg


class TestCollectionMetadataExtraction:
    """Test metadata extraction from collections."""

    @patch('collection_discovery.initialize_chromadb_client')
    def test_metadata_field_types(self, mock_init_client):
        """Test that metadata fields have correct types."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.metadata = {
            "description": "Test description",
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_collection.count.return_value = 100

        mock_client.list_collections.return_value = [mock_collection]

        collections = list_collections("/fake/path/to/chromadb")

        assert len(collections) == 1
        col = collections[0]

        # Verify field types
        assert isinstance(col["name"], str)
        assert isinstance(col["description"], str)
        assert isinstance(col["chunk_count"], int)
        assert isinstance(col["created_at"], str)

    @patch('collection_discovery.initialize_chromadb_client')
    def test_special_characters_in_metadata(self, mock_init_client):
        """Test handling of special characters in metadata."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "special_chars_collection"
        mock_collection.metadata = {
            "description": "Description with special chars: 日本語, emoji 🎉, quotes \"test\"",
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_collection.count.return_value = 50

        mock_client.list_collections.return_value = [mock_collection]

        collections = list_collections("/fake/path/to/chromadb")

        assert len(collections) == 1
        assert "日本語" in collections[0]["description"]
        assert "🎉" in collections[0]["description"]
        assert "\"test\"" in collections[0]["description"]

    @patch('collection_discovery.initialize_chromadb_client')
    def test_very_long_description(self, mock_init_client):
        """Test handling of very long descriptions."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        long_description = "A" * 10000  # Very long description

        mock_collection = Mock()
        mock_collection.name = "long_description_collection"
        mock_collection.metadata = {
            "description": long_description,
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_collection.count.return_value = 75

        mock_client.list_collections.return_value = [mock_collection]

        collections = list_collections("/fake/path/to/chromadb")

        # Should handle long descriptions without error
        assert len(collections) == 1
        assert collections[0]["description"] == long_description


class TestCollectionListingEdgeCases:
    """Test edge cases in collection listing."""

    @patch('collection_discovery.initialize_chromadb_client')
    def test_many_collections(self, mock_init_client):
        """Test listing many collections."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        # Create 100 mock collections
        mock_collections = []
        for i in range(100):
            mock_collection = Mock()
            mock_collection.name = f"collection_{i:03d}"
            mock_collection.metadata = {
                "description": f"Collection number {i}",
                "created_at": "2024-01-01T00:00:00Z"
            }
            mock_collection.count.return_value = i * 10
            mock_collections.append(mock_collection)

        mock_client.list_collections.return_value = mock_collections

        collections = list_collections("/fake/path/to/chromadb")

        # Verify all collections are listed
        assert len(collections) == 100
        assert collections[0]["name"] == "collection_000"
        assert collections[99]["name"] == "collection_099"
        assert collections[50]["chunk_count"] == 500

    @patch('collection_discovery.initialize_chromadb_client')
    def test_collection_names_with_special_chars(self, mock_init_client):
        """Test collection names with special characters."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        special_names = [
            "collection-with-dashes",
            "collection_with_underscores",
            "collection.with.dots",
            "collection123",
            "UPPERCASE_COLLECTION"
        ]

        mock_collections = []
        for name in special_names:
            mock_collection = Mock()
            mock_collection.name = name
            mock_collection.metadata = {
                "description": f"Collection {name}",
                "created_at": "2024-01-01T00:00:00Z"
            }
            mock_collection.count.return_value = 10
            mock_collections.append(mock_collection)

        mock_client.list_collections.return_value = mock_collections

        collections = list_collections("/fake/path/to/chromadb")

        assert len(collections) == len(special_names)
        returned_names = [col["name"] for col in collections]
        assert set(returned_names) == set(special_names)


class TestCollectionDiscoveryErrorMessages:
    """Test error message quality and helpfulness."""

    @patch('collection_discovery.initialize_chromadb_client')
    def test_connection_error_message_includes_path(self, mock_init_client):
        """Test that connection error messages include the problematic path."""
        from storage import ChromaDBConnectionError

        test_path = "/test/path/to/chromadb"
        mock_init_client.side_effect = ChromaDBConnectionError(
            f"Failed to initialize ChromaDB client at '{test_path}': Error"
        )

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections(test_path)

        assert test_path in str(exc_info.value)

    @patch('collection_discovery.initialize_chromadb_client')
    def test_error_message_includes_troubleshooting(self, mock_init_client):
        """Test that error messages include troubleshooting steps."""
        from storage import ChromaDBConnectionError

        mock_init_client.side_effect = ChromaDBConnectionError("Connection failed")

        with pytest.raises(CollectionDiscoveryError) as exc_info:
            list_collections("/fake/path")

        error_msg = str(exc_info.value)
        # Should include helpful troubleshooting steps
        assert "Troubleshooting:" in error_msg
        error_msg_lower = error_msg.lower()
        assert any(keyword in error_msg_lower for keyword in ["verify", "check", "ensure"])


class TestReconstructProviderFromMetadata:
    """Test provider reconstruction from collection metadata."""

    @patch('collection_discovery.AIProvider')
    @patch('collection_discovery.AIProviderConfig')
    def test_successful_provider_reconstruction(self, mock_config_class, mock_provider_class):
        """Test successful reconstruction of provider from complete metadata."""
        metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'llm_model': 'llama3.1:8b',
            'embedding_base_url': 'http://localhost:11434',
            'embedding_api_key_ref': None
        }

        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_provider = Mock()
        mock_provider.check_availability.return_value = {'available': True, 'dimension': 1024}
        mock_provider_class.return_value = mock_provider

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is not None
        assert error is None
        mock_config_class.assert_called_once_with(
            provider_type='ollama',
            embedding_model='mxbai-embed-large:latest',
            llm_model='llama3.1:8b',
            base_url='http://localhost:11434',
            api_key=None
        )

    def test_missing_provider_type(self):
        """Test reconstruction fails gracefully when provider_type is missing."""
        metadata = {
            'embedding_model': 'mxbai-embed-large:latest',
            'llm_model': 'llama3.1:8b'
        }

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert error == "Missing AI provider metadata (created with old pipeline)"

    def test_missing_embedding_model(self):
        """Test reconstruction fails gracefully when embedding_model is missing."""
        metadata = {
            'embedding_provider': 'ollama',
            'llm_model': 'llama3.1:8b'
        }

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert error == "Missing AI provider metadata (created with old pipeline)"

    def test_missing_llm_model(self):
        """Test reconstruction fails gracefully when llm_model is missing."""
        metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest'
        }

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert error == "Missing AI provider metadata (created with old pipeline)"

    def test_empty_metadata(self):
        """Test reconstruction with empty metadata."""
        metadata = {}

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert error == "Missing AI provider metadata (created with old pipeline)"

    @patch('collection_discovery.AIProvider')
    @patch('collection_discovery.AIProviderConfig')
    def test_provider_unavailable(self, mock_config_class, mock_provider_class):
        """Test handling when provider check_availability returns unavailable."""
        metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'llm_model': 'llama3.1:8b'
        }

        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_provider = Mock()
        mock_provider.check_availability.return_value = {
            'available': False,
            'error': 'Provider unavailable: connection refused'
        }
        mock_provider_class.return_value = mock_provider

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert error == 'Provider unavailable: connection refused'

    @patch('collection_discovery.AIProviderConfig')
    def test_api_key_missing_error(self, mock_config_class):
        """Test handling of missing API key errors."""
        from ai_config import APIKeyMissingError

        metadata = {
            'embedding_provider': 'openai',
            'embedding_model': 'text-embedding-3-small',
            'llm_model': 'gpt-4o-mini',
            'embedding_api_key_ref': '${OPENAI_API_KEY}'
        }

        mock_config_class.side_effect = APIKeyMissingError("Environment variable 'OPENAI_API_KEY' is not set")

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert "Environment variable 'OPENAI_API_KEY' is not set" in error

    @patch('collection_discovery.AIProvider')
    @patch('collection_discovery.AIProviderConfig')
    def test_provider_initialization_error(self, mock_config_class, mock_provider_class):
        """Test handling of provider initialization errors."""
        from ai_provider import AIProviderError

        metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'llm_model': 'llama3.1:8b'
        }

        mock_config = Mock()
        mock_config_class.return_value = mock_config

        mock_provider_class.side_effect = AIProviderError("LiteLLM is not installed")

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert "Provider initialization failed" in error

    @patch('collection_discovery.AIProvider')
    @patch('collection_discovery.AIProviderConfig')
    def test_unexpected_error(self, mock_config_class, mock_provider_class):
        """Test handling of unexpected errors during reconstruction."""
        metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'llm_model': 'llama3.1:8b'
        }

        mock_config_class.side_effect = Exception("Unexpected error")

        provider, error = reconstruct_provider_from_metadata(metadata)

        assert provider is None
        assert "Unexpected error during provider reconstruction" in error


class TestDiscoverCollectionsWithProviders:
    """Test discovery of collections with provider instances."""

    @patch('collection_discovery.initialize_chromadb_client')
    @patch('collection_discovery.reconstruct_provider_from_metadata')
    def test_discover_with_available_providers(self, mock_reconstruct, mock_init_client):
        """Test discovering collections where all providers are available."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection1 = Mock()
        mock_collection1.name = "collection1"
        mock_collection1.metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'model1',
            'llm_model': 'llm1',
            'description': 'Collection 1'
        }
        mock_collection1.count.return_value = 100

        mock_collection2 = Mock()
        mock_collection2.name = "collection2"
        mock_collection2.metadata = {
            'embedding_provider': 'openai',
            'embedding_model': 'model2',
            'llm_model': 'llm2',
            'description': 'Collection 2'
        }
        mock_collection2.count.return_value = 200

        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]

        mock_provider1 = Mock()
        mock_provider2 = Mock()

        mock_reconstruct.side_effect = [
            (mock_provider1, None),
            (mock_provider2, None)
        ]

        provider_map, collections = discover_collections_with_providers("/fake/path")

        assert len(provider_map) == 2
        assert "collection1" in provider_map
        assert "collection2" in provider_map
        assert provider_map["collection1"] == mock_provider1
        assert provider_map["collection2"] == mock_provider2

        assert len(collections) == 2
        assert collections[0]['available'] is True
        assert collections[1]['available'] is True

    @patch('collection_discovery.initialize_chromadb_client')
    @patch('collection_discovery.reconstruct_provider_from_metadata')
    def test_discover_with_unavailable_providers(self, mock_reconstruct, mock_init_client):
        """Test discovering collections where some providers are unavailable."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection1 = Mock()
        mock_collection1.name = "available_collection"
        mock_collection1.metadata = {'embedding_provider': 'ollama', 'embedding_model': 'model1', 'llm_model': 'llm1'}
        mock_collection1.count.return_value = 100

        mock_collection2 = Mock()
        mock_collection2.name = "unavailable_collection"
        mock_collection2.metadata = {'embedding_provider': 'openai', 'embedding_model': 'model2', 'llm_model': 'llm2'}
        mock_collection2.count.return_value = 200

        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]

        mock_provider1 = Mock()

        mock_reconstruct.side_effect = [
            (mock_provider1, None),
            (None, "API key missing")
        ]

        provider_map, collections = discover_collections_with_providers("/fake/path")

        assert len(provider_map) == 1
        assert "available_collection" in provider_map
        assert "unavailable_collection" not in provider_map

        assert len(collections) == 2
        assert collections[0]['available'] is True
        assert collections[1]['available'] is False
        assert collections[1]['unavailable_reason'] == "API key missing"

    @patch('collection_discovery.initialize_chromadb_client')
    @patch('collection_discovery.reconstruct_provider_from_metadata')
    def test_discover_with_old_collections(self, mock_reconstruct, mock_init_client):
        """Test discovering collections created with old pipeline (no metadata)."""
        mock_client = Mock()
        mock_init_client.return_value = mock_client

        mock_collection = Mock()
        mock_collection.name = "old_collection"
        mock_collection.metadata = {}
        mock_collection.count.return_value = 50

        mock_client.list_collections.return_value = [mock_collection]

        mock_reconstruct.return_value = (None, "Missing AI provider metadata (created with old pipeline)")

        provider_map, collections = discover_collections_with_providers("/fake/path")

        assert len(provider_map) == 0
        assert len(collections) == 1
        assert collections[0]['available'] is False
        assert "old pipeline" in collections[0]['unavailable_reason']


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
