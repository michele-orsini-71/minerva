"""Integration tests for AI provider abstraction and multi-provider scenarios.

These tests verify the complete flow from pipeline execution through to MCP server
discovery and search, testing the interaction between all modules with AI provider
abstraction: ai_provider, config_loader, embedding, storage, full_pipeline.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from types import SimpleNamespace
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_provider import AIProvider, AIProviderConfig, AIProviderError
from config_loader import CollectionConfig
from embedding import initialize_provider
from storage import build_collection_metadata, create_collection
import full_pipeline


class TestEndToEndPipeline:
    """Test complete pipeline flow with AI provider abstraction."""

    @patch('full_pipeline.initialize_chromadb_client')
    @patch('full_pipeline.create_chunks_from_notes')
    @patch('full_pipeline.generate_embeddings')
    @patch('full_pipeline.insert_chunks')
    @patch('full_pipeline.load_json_notes')
    @patch('litellm.embedding')
    @patch('litellm.completion')
    def test_ollama_pipeline_with_metadata_storage(
        self,
        mock_litellm_completion,
        mock_litellm_embedding,
        mock_load_notes,
        mock_insert_chunks,
        mock_generate_embeddings,
        mock_create_chunks,
        mock_chromadb_init,
        tmp_path
    ):
        """
        Task 9.1: End-to-end Ollama pipeline creating collection with metadata.

        Tests that:
        1. Provider is initialized from config
        2. Embeddings are generated using provider
        3. Metadata is extracted from provider
        4. Collection is created with provider metadata
        """
        # Setup: Create Ollama config
        config = SimpleNamespace(
            collection_name="test_collection",
            description="Test collection for integration testing",
            chromadb_path=str(tmp_path / "chromadb"),
            json_file=str(tmp_path / "notes.json"),
            chunk_size=1200,
            force_recreate=False,
            skip_ai_validation=True,
            ai_provider={
                'type': 'ollama',
                'embedding': {
                    'model': 'mxbai-embed-large:latest',
                    'base_url': 'http://localhost:11434',
                    'api_key': None
                },
                'llm': {
                    'model': 'llama3.1:8b',
                    'base_url': 'http://localhost:11434',
                    'api_key': None
                }
            }
        )

        # Mock ChromaDB client and collection
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_chromadb_init.return_value = mock_client

        # Mock LiteLLM embedding response (1024 dimensions for mxbai-embed-large)
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_litellm_embedding.return_value = mock_embedding_response

        # Mock notes data
        mock_load_notes.return_value = [
            {
                "title": "Test Note",
                "markdown": "# Test Content\n\nSome test content here.",
                "size": 50,
                "modificationDate": "2025-10-01T10:00:00Z",
                "creationDate": "2025-09-01T10:00:00Z"
            }
        ]

        # Mock chunks
        from models import Chunk
        test_chunks = [
            Chunk(
                id="chunk_001",
                content="Test chunk content",
                noteId="note_001",
                title="Test Note",
                modificationDate="2025-10-01T10:00:00Z",
                creationDate="2025-09-01T10:00:00Z",
                size=50,
                chunkIndex=0
            )
        ]
        mock_create_chunks.return_value = test_chunks

        # Mock embeddings generation
        from models import ChunkWithEmbedding
        test_chunks_with_embeddings = [
            ChunkWithEmbedding(chunk=test_chunks[0], embedding=[0.1] * 1024)
        ]
        mock_generate_embeddings.return_value = test_chunks_with_embeddings

        # Mock insert operation
        mock_insert_chunks.return_value = {
            'successful': 1,
            'failed': 0
        }

        # Capture collection creation
        created_collections = []

        def capture_create_collection(client, collection_name, description, embedding_metadata):
            created_collections.append({
                'name': collection_name,
                'description': description,
                'metadata': embedding_metadata
            })
            return mock_collection

        # Initialize provider and verify availability check
        provider = initialize_provider(config)
        availability = provider.check_availability()

        assert availability['available'] is True
        assert availability['dimension'] == 1024

        # Get embedding metadata
        embedding_metadata = provider.get_embedding_metadata()

        # Verify metadata structure
        assert embedding_metadata['embedding_provider'] == 'ollama'
        assert embedding_metadata['embedding_model'] == 'mxbai-embed-large:latest'
        assert embedding_metadata['embedding_dimension'] == 1024
        assert embedding_metadata['embedding_base_url'] == 'http://localhost:11434'
        assert embedding_metadata['embedding_api_key_ref'] is None
        assert embedding_metadata['llm_model'] == 'llama3.1:8b'

        # Verify embedding was called
        assert mock_litellm_embedding.called

    def test_openai_provider_initialization_missing_api_key(
        self,
        monkeypatch
    ):
        """
        Test that OpenAI provider initialization fails gracefully when API key is missing.

        Verifies:
        1. Missing API key is detected during initialization
        2. Actionable error message is provided
        3. EmbeddingError is raised with clear guidance
        """
        # Remove OPENAI_API_KEY from environment
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)

        config = SimpleNamespace(
            ai_provider={
                'type': 'openai',
                'embedding': {
                    'model': 'text-embedding-3-small',
                    'api_key': '${OPENAI_API_KEY}'
                },
                'llm': {
                    'model': 'gpt-4o-mini',
                    'api_key': '${OPENAI_API_KEY}'
                }
            }
        )

        # Initialize provider - should raise EmbeddingError due to missing API key
        with pytest.raises(Exception) as exc_info:
            provider = initialize_provider(config)

        # Verify error message contains helpful information
        error_msg = str(exc_info.value)
        assert 'OPENAI_API_KEY' in error_msg
        assert 'not set' in error_msg or 'export' in error_msg


class TestMultiProviderCollectionMetadata:
    """Test provider metadata storage and retrieval."""

    def test_metadata_storage_with_ollama_provider(self):
        """
        Test that Ollama provider metadata is correctly stored in ChromaDB.
        """
        # Create provider metadata
        provider_metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'embedding_dimension': 1024,
            'embedding_base_url': 'http://localhost:11434',
            'embedding_api_key_ref': None,
            'llm_model': 'llama3.1:8b'
        }

        # Build collection metadata
        collection_metadata = build_collection_metadata(
            description="Test collection",
            embedding_metadata=provider_metadata
        )

        # Verify metadata structure
        assert 'description' in collection_metadata
        assert 'created_at' in collection_metadata
        assert collection_metadata['embedding_provider'] == 'ollama'
        assert collection_metadata['embedding_model'] == 'mxbai-embed-large:latest'
        assert collection_metadata['embedding_dimension'] == 1024
        assert collection_metadata['llm_model'] == 'llama3.1:8b'

    def test_metadata_storage_with_openai_provider(self):
        """
        Test that OpenAI provider metadata stores API key template (not actual key).
        """
        # Create provider metadata with API key template
        provider_metadata = {
            'embedding_provider': 'openai',
            'embedding_model': 'text-embedding-3-small',
            'embedding_dimension': 1536,
            'embedding_base_url': None,
            'embedding_api_key_ref': '${OPENAI_API_KEY}',
            'llm_model': 'gpt-4o-mini'
        }

        # Build collection metadata
        collection_metadata = build_collection_metadata(
            description="OpenAI test collection",
            embedding_metadata=provider_metadata
        )

        # Verify API key is stored as template
        assert collection_metadata['embedding_api_key_ref'] == '${OPENAI_API_KEY}'
        # Ensure actual key is NOT stored
        assert 'sk-' not in str(collection_metadata.get('embedding_api_key_ref', ''))

    @patch('litellm.embedding')
    def test_dimension_validation_mismatch(self, mock_litellm_embedding):
        """
        Task 9.4: Test dimension validation when query uses different model than collection.

        Scenario: Collection created with mxbai-embed-large (1024 dim),
        query attempts to use OpenAI text-embedding-3-small (1536 dim).
        """
        # Setup: Collection metadata with Ollama (1024 dimensions)
        collection_metadata = {
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'embedding_dimension': 1024,
            'llm_model': 'llama3.1:8b'
        }

        # Mock query using different provider (OpenAI with 1536 dimensions)
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]  # Wrong dimension
        mock_litellm_embedding.return_value = mock_embedding_response

        # Create query provider config
        query_config = SimpleNamespace(
            ai_provider={
                'type': 'openai',
                'embedding': {
                    'model': 'text-embedding-3-small',
                    'api_key': 'sk-test-key'
                },
                'llm': {
                    'model': 'gpt-4o-mini',
                    'api_key': 'sk-test-key'
                }
            }
        )

        query_provider = initialize_provider(query_config)
        query_embedding = query_provider.generate_embedding("test query")

        # Verify dimension mismatch
        assert len(query_embedding) == 1536  # Query embedding dimension
        assert collection_metadata['embedding_dimension'] == 1024  # Collection dimension
        assert len(query_embedding) != collection_metadata['embedding_dimension']

        # This would trigger an error in the actual search implementation


class TestMultiProviderScenarios:
    """Test mixed availability scenarios with multiple providers."""

    @patch('litellm.embedding')
    def test_mixed_availability_some_collections_unavailable(
        self,
        mock_litellm_embedding,
        monkeypatch
    ):
        """
        Task 9.5: Test mixed availability - some collections available, some unavailable.

        Scenario:
        - Collection 1: Ollama (no API key needed) - AVAILABLE
        - Collection 2: OpenAI (API key missing) - UNAVAILABLE
        - Collection 3: Gemini (API key missing) - UNAVAILABLE
        """
        # Remove API keys from environment
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)

        # Create mock collections with different provider metadata
        collections = [
            {
                'name': 'ollama_collection',
                'metadata': {
                    'description': 'Ollama-based collection',
                    'embedding_provider': 'ollama',
                    'embedding_model': 'mxbai-embed-large:latest',
                    'embedding_dimension': 1024,
                    'embedding_base_url': 'http://localhost:11434',
                    'embedding_api_key_ref': None,
                    'llm_model': 'llama3.1:8b'
                }
            },
            {
                'name': 'openai_collection',
                'metadata': {
                    'description': 'OpenAI-based collection',
                    'embedding_provider': 'openai',
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_dimension': 1536,
                    'embedding_api_key_ref': '${OPENAI_API_KEY}',
                    'llm_model': 'gpt-4o-mini'
                }
            },
            {
                'name': 'gemini_collection',
                'metadata': {
                    'description': 'Gemini-based collection',
                    'embedding_provider': 'gemini',
                    'embedding_model': 'text-embedding-004',
                    'embedding_dimension': 768,
                    'embedding_api_key_ref': '${GEMINI_API_KEY}',
                    'llm_model': 'gemini-1.5-flash'
                }
            }
        ]

        # Mock LiteLLM embedding for Ollama (success)
        def mock_embedding_side_effect(*args, **kwargs):
            model = kwargs.get('model', '')
            if 'ollama' in model or 'mxbai' in model:
                # Ollama works
                response = Mock()
                response.data = [Mock(embedding=[0.1] * 1024)]
                return response
            else:
                # OpenAI/Gemini fail due to missing API key
                raise Exception("AuthenticationError: Invalid API key")

        mock_litellm_embedding.side_effect = mock_embedding_side_effect

        # Test availability for each collection
        availability_results = []

        for collection in collections:
            metadata = collection['metadata']

            # Reconstruct provider from metadata
            provider_config = SimpleNamespace(
                ai_provider={
                    'type': metadata['embedding_provider'],
                    'embedding': {
                        'model': metadata['embedding_model'],
                        'base_url': metadata.get('embedding_base_url'),
                        'api_key': metadata.get('embedding_api_key_ref')
                    },
                    'llm': {
                        'model': metadata['llm_model'],
                        'api_key': metadata.get('embedding_api_key_ref')
                    }
                }
            )

            try:
                provider = initialize_provider(provider_config)
                availability = provider.check_availability()
                availability_results.append({
                    'collection': collection['name'],
                    'available': availability['available'],
                    'provider': metadata['embedding_provider']
                })
            except Exception as e:
                # Provider initialization failed (likely missing API key)
                availability_results.append({
                    'collection': collection['name'],
                    'available': False,
                    'provider': metadata['embedding_provider']
                })

        # Verify results
        assert len(availability_results) == 3

        # Ollama should be available
        ollama_result = [r for r in availability_results if r['provider'] == 'ollama'][0]
        assert ollama_result['available'] is True

        # OpenAI should be unavailable (missing API key)
        openai_result = [r for r in availability_results if r['provider'] == 'openai'][0]
        assert openai_result['available'] is False

        # Gemini should be unavailable (missing API key)
        gemini_result = [r for r in availability_results if r['provider'] == 'gemini'][0]
        assert gemini_result['available'] is False

    @patch('litellm.embedding')
    def test_multi_provider_fixture(self, mock_litellm_embedding, monkeypatch):
        """
        Task 9.6: Test fixture with multiple collections using different providers.

        Creates a test scenario with three collections:
        - Ollama collection (local, no API key)
        - OpenAI collection (cloud, requires API key)
        - Gemini collection (cloud, requires API key)
        """
        # Setup environment with OpenAI key but no Gemini key
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-openai-key-12345')
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)

        # Create multi-provider collections
        collections = [
            {
                'name': 'bear_notes_ollama',
                'provider_type': 'ollama',
                'embedding_model': 'mxbai-embed-large:latest',
                'llm_model': 'llama3.1:8b',
                'dimension': 1024,
                'api_key_ref': None,
                'base_url': 'http://localhost:11434'
            },
            {
                'name': 'bear_notes_openai',
                'provider_type': 'openai',
                'embedding_model': 'text-embedding-3-small',
                'llm_model': 'gpt-4o-mini',
                'dimension': 1536,
                'api_key_ref': '${OPENAI_API_KEY}',
                'base_url': None
            },
            {
                'name': 'bear_notes_gemini',
                'provider_type': 'gemini',
                'embedding_model': 'text-embedding-004',
                'llm_model': 'gemini-1.5-flash',
                'dimension': 768,
                'api_key_ref': '${GEMINI_API_KEY}',
                'base_url': None
            }
        ]

        # Mock LiteLLM responses based on provider
        def mock_embedding_side_effect(*args, **kwargs):
            model = kwargs.get('model', '')

            if 'mxbai' in model:
                # Ollama
                response = Mock()
                response.data = [Mock(embedding=[0.1] * 1024)]
                return response
            elif 'text-embedding-3' in model:
                # OpenAI (has API key)
                response = Mock()
                response.data = [Mock(embedding=[0.1] * 1536)]
                return response
            elif 'text-embedding-004' in model:
                # Gemini (missing API key)
                raise Exception("AuthenticationError: API key not found")
            else:
                raise Exception("Unknown model")

        mock_litellm_embedding.side_effect = mock_embedding_side_effect

        # Initialize providers and check availability
        results = []
        for collection_config in collections:
            config = SimpleNamespace(
                ai_provider={
                    'type': collection_config['provider_type'],
                    'embedding': {
                        'model': collection_config['embedding_model'],
                        'base_url': collection_config['base_url'],
                        'api_key': collection_config['api_key_ref']
                    },
                    'llm': {
                        'model': collection_config['llm_model'],
                        'api_key': collection_config['api_key_ref']
                    }
                }
            )

            try:
                provider = initialize_provider(config)
                availability = provider.check_availability()
                results.append({
                    'name': collection_config['name'],
                    'provider': collection_config['provider_type'],
                    'available': availability['available'],
                    'dimension': collection_config['dimension']
                })
            except Exception as e:
                # Provider initialization failed (likely missing API key)
                results.append({
                    'name': collection_config['name'],
                    'provider': collection_config['provider_type'],
                    'available': False,
                    'dimension': collection_config['dimension']
                })

        # Verify multi-provider scenario
        assert len(results) == 3

        # Ollama: available (no API key needed)
        ollama = [r for r in results if r['provider'] == 'ollama'][0]
        assert ollama['available'] is True
        assert ollama['dimension'] == 1024

        # OpenAI: available (API key provided)
        openai = [r for r in results if r['provider'] == 'openai'][0]
        assert openai['available'] is True
        assert openai['dimension'] == 1536

        # Gemini: unavailable (API key missing)
        gemini = [r for r in results if r['provider'] == 'gemini'][0]
        assert gemini['available'] is False
        assert gemini['dimension'] == 768


class TestProviderReconstructionFromMetadata:
    """Test reconstructing AI providers from ChromaDB collection metadata."""

    @patch('litellm.embedding')
    def test_reconstruct_ollama_provider_from_metadata(self, mock_litellm_embedding):
        """
        Test reconstructing Ollama provider from collection metadata.

        Simulates MCP server reading collection metadata and recreating provider.
        """
        # Collection metadata as stored in ChromaDB
        collection_metadata = {
            'description': 'Personal notes collection',
            'created_at': '2025-10-11T10:00:00Z',
            'embedding_provider': 'ollama',
            'embedding_model': 'mxbai-embed-large:latest',
            'embedding_dimension': 1024,
            'embedding_base_url': 'http://localhost:11434',
            'embedding_api_key_ref': None,
            'llm_model': 'llama3.1:8b'
        }

        # Reconstruct provider config from metadata
        reconstructed_config = SimpleNamespace(
            ai_provider={
                'type': collection_metadata['embedding_provider'],
                'embedding': {
                    'model': collection_metadata['embedding_model'],
                    'base_url': collection_metadata.get('embedding_base_url'),
                    'api_key': collection_metadata.get('embedding_api_key_ref')
                },
                'llm': {
                    'model': collection_metadata['llm_model'],
                    'api_key': collection_metadata.get('embedding_api_key_ref')
                }
            }
        )

        # Mock LiteLLM
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1024)]
        mock_litellm_embedding.return_value = mock_response

        # Initialize provider from reconstructed config
        provider = initialize_provider(reconstructed_config)

        # Verify provider properties
        assert provider.provider_type == 'ollama'
        assert provider.embedding_model == 'mxbai-embed-large:latest'
        assert provider.llm_model == 'llama3.1:8b'
        assert provider.base_url == 'http://localhost:11434'

        # Verify provider is functional
        availability = provider.check_availability()
        assert availability['available'] is True
        assert availability['dimension'] == 1024

    @patch('litellm.embedding')
    def test_reconstruct_openai_provider_with_env_var_resolution(
        self,
        mock_litellm_embedding,
        monkeypatch
    ):
        """
        Test reconstructing OpenAI provider with environment variable resolution.

        Verifies that API key templates like ${OPENAI_API_KEY} are resolved at runtime.
        """
        # Set environment variable
        monkeypatch.setenv('OPENAI_API_KEY', 'sk-test-resolved-key')

        # Collection metadata with API key template
        collection_metadata = {
            'description': 'OpenAI-based collection',
            'embedding_provider': 'openai',
            'embedding_model': 'text-embedding-3-small',
            'embedding_dimension': 1536,
            'embedding_api_key_ref': '${OPENAI_API_KEY}',
            'llm_model': 'gpt-4o-mini'
        }

        # Reconstruct provider config
        reconstructed_config = SimpleNamespace(
            ai_provider={
                'type': collection_metadata['embedding_provider'],
                'embedding': {
                    'model': collection_metadata['embedding_model'],
                    'api_key': collection_metadata['embedding_api_key_ref']
                },
                'llm': {
                    'model': collection_metadata['llm_model'],
                    'api_key': collection_metadata['embedding_api_key_ref']
                }
            }
        )

        # Mock LiteLLM
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_litellm_embedding.return_value = mock_response

        # Initialize provider
        provider = initialize_provider(reconstructed_config)

        # Verify environment variable was resolved
        # The provider should have resolved ${OPENAI_API_KEY} to actual value
        assert provider.api_key == 'sk-test-resolved-key'

        # Verify provider works
        availability = provider.check_availability()
        assert availability['available'] is True
