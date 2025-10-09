"""
Unit tests for the AI provider abstraction layer.

Tests cover:
- AIProviderConfig dataclass validation
- Environment variable resolution
- AIProvider initialization and configuration
- Embedding generation (single and batch)
- Metadata retrieval
- Availability checking
- Description validation
- Error handling for missing API keys and unavailable providers
"""

import os
from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import Mock, patch

import numpy as np
import pytest

from ai_config import (
    AIProviderConfig,
    APIKeyMissingError,
    resolve_env_variable,
)
from ai_provider import (
    AIProvider,
    AIProviderError,
    ProviderUnavailableError,
)


class TestAIProviderConfig:
    """Tests for AIProviderConfig dataclass"""

    def test_valid_ollama_config(self):
        """Test creating valid Ollama configuration"""
        config = AIProviderConfig(
            provider_type='ollama',
            embedding_model='mxbai-embed-large:latest',
            llm_model='llama3.1:8b',
            base_url='http://localhost:11434'
        )
        assert config.provider_type == 'ollama'
        assert config.embedding_model == 'mxbai-embed-large:latest'
        assert config.llm_model == 'llama3.1:8b'
        assert config.base_url == 'http://localhost:11434'
        assert config.api_key is None

    def test_valid_openai_config(self):
        """Test creating valid OpenAI configuration with API key template"""
        config = AIProviderConfig(
            provider_type='openai',
            embedding_model='text-embedding-3-small',
            llm_model='gpt-4o-mini',
            api_key='${OPENAI_API_KEY}'
        )
        assert config.provider_type == 'openai'
        assert config.api_key == '${OPENAI_API_KEY}'

    def test_invalid_provider_type(self):
        """Test that invalid provider type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid provider_type"):
            AIProviderConfig(
                provider_type='invalid_provider',
                embedding_model='model',
                llm_model='llm'
            )

    def test_empty_embedding_model(self):
        """Test that empty embedding model raises ValueError"""
        with pytest.raises(ValueError, match="embedding_model cannot be empty"):
            AIProviderConfig(
                provider_type='ollama',
                embedding_model='',
                llm_model='llama3.1:8b'
            )

    def test_empty_llm_model(self):
        """Test that empty LLM model raises ValueError"""
        with pytest.raises(ValueError, match="llm_model cannot be empty"):
            AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model=''
            )

    def test_resolve_api_key_method(self, monkeypatch):
        """Test the resolve_api_key() method on AIProviderConfig"""
        monkeypatch.setenv('TEST_API_KEY', 'secret-key-value')

        config = AIProviderConfig(
            provider_type='openai',
            embedding_model='text-embedding-3-small',
            llm_model='gpt-4o-mini',
            api_key='${TEST_API_KEY}'
        )

        resolved = config.resolve_api_key()
        assert resolved == 'secret-key-value'

    def test_resolve_api_key_none(self):
        """Test that resolve_api_key() returns None when no api_key is set"""
        config = AIProviderConfig(
            provider_type='ollama',
            embedding_model='mxbai-embed-large:latest',
            llm_model='llama3.1:8b'
        )

        resolved = config.resolve_api_key()
        assert resolved is None


class TestEnvironmentVariableResolution:
    """Tests for resolve_env_variable function"""

    def test_resolve_single_env_var(self, monkeypatch):
        """Test resolving a single environment variable"""
        monkeypatch.setenv('MY_API_KEY', 'secret123')
        result = resolve_env_variable('${MY_API_KEY}')
        assert result == 'secret123'

    def test_resolve_env_var_in_string(self, monkeypatch):
        """Test resolving environment variable within a string"""
        monkeypatch.setenv('MY_KEY', 'abc123')
        result = resolve_env_variable('prefix_${MY_KEY}_suffix')
        assert result == 'prefix_abc123_suffix'

    def test_resolve_multiple_env_vars(self, monkeypatch):
        """Test resolving multiple environment variables"""
        monkeypatch.setenv('VAR1', 'value1')
        monkeypatch.setenv('VAR2', 'value2')
        result = resolve_env_variable('${VAR1}-${VAR2}')
        assert result == 'value1-value2'

    def test_resolve_none_value(self):
        """Test that None is returned for None input"""
        result = resolve_env_variable(None)
        assert result is None

    def test_resolve_missing_env_var(self):
        """Test that missing environment variable raises APIKeyMissingError"""
        with pytest.raises(APIKeyMissingError, match="Environment variable 'NONEXISTENT_VAR' is not set"):
            resolve_env_variable('${NONEXISTENT_VAR}')

    def test_resolve_plain_string(self):
        """Test that plain strings without variables pass through unchanged"""
        result = resolve_env_variable('plain_string')
        assert result == 'plain_string'


class TestAIProviderInitialization:
    """Tests for AIProvider initialization"""

    def test_ollama_initialization_no_api_key(self):
        """Test initializing Ollama provider without API key"""
        with patch('litellm.embedding'):
            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b',
                base_url='http://localhost:11434'
            )
            provider = AIProvider(config)

            assert provider.provider_type == 'ollama'
            assert provider.embedding_model == 'mxbai-embed-large:latest'
            assert provider.llm_model == 'llama3.1:8b'
            assert provider.api_key is None
            assert provider.base_url == 'http://localhost:11434'

    def test_openai_initialization_with_api_key(self, monkeypatch):
        """Test initializing OpenAI provider with API key from environment"""
        with patch('litellm.embedding'):
            monkeypatch.setenv('OPENAI_API_KEY', 'sk-test123')

            config = AIProviderConfig(
                provider_type='openai',
                embedding_model='text-embedding-3-small',
                llm_model='gpt-4o-mini',
                api_key='${OPENAI_API_KEY}'
            )
            # RAII: API key resolved automatically during construction
            provider = AIProvider(config)

            assert provider.provider_type == 'openai'
            assert provider.api_key == 'sk-test123'
            assert os.environ.get('OPENAI_API_KEY') == 'sk-test123'

    def test_initialization_with_missing_api_key(self):
        """Test that missing API key raises APIKeyMissingError during initialization"""
        with patch('litellm.embedding'):
            config = AIProviderConfig(
                provider_type='openai',
                embedding_model='text-embedding-3-small',
                llm_model='gpt-4o-mini',
                api_key='${MISSING_KEY}'
            )

            # Error should occur during AIProvider.__init__ (RAII)
            with pytest.raises(APIKeyMissingError, match="Environment variable 'MISSING_KEY' is not set"):
                AIProvider(config)


class TestEmbeddingGeneration:
    """Tests for embedding generation methods"""

    def test_generate_single_embedding(self):
        """Test generating embedding for single text"""
        with patch('litellm.embedding') as mock_embedding:
            # Setup mock
            mock_embedding.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3, 0.4]}]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            # Generate embedding
            result = provider.generate_embedding("test text")

            # Verify result is normalized
            assert isinstance(result, list)
            assert len(result) == 4
            norm = np.linalg.norm(result)
            assert 0.99 <= norm <= 1.01  # Should be L2 normalized

    def test_generate_embedding_empty_text(self):
        """Test that empty text raises ValueError"""
        with patch('litellm.embedding'):
            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
                provider.generate_embedding("")

    def test_generate_embeddings_batch(self):
        """Test generating embeddings for multiple texts"""
        with patch('litellm.embedding') as mock_embedding:
            # Setup mock
            mock_embedding.return_value = {
                'data': [
                    {'embedding': [0.1, 0.2, 0.3]},
                    {'embedding': [0.4, 0.5, 0.6]},
                    {'embedding': [0.7, 0.8, 0.9]}
                ]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            # Generate batch embeddings
            texts = ["text1", "text2", "text3"]
            results = provider.generate_embeddings_batch(texts)

            # Verify results
            assert len(results) == 3
            for result in results:
                assert isinstance(result, list)
                assert len(result) == 3
                norm = np.linalg.norm(result)
                assert 0.99 <= norm <= 1.01

    def test_generate_embeddings_batch_empty_list(self):
        """Test that empty list returns empty list"""
        with patch('litellm.embedding'):
            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.generate_embeddings_batch([])
            assert result == []

    def test_generate_embeddings_batch_with_empty_texts(self):
        """Test batch generation rejects empty texts"""
        config = AIProviderConfig(
            provider_type='ollama',
            embedding_model='mxbai-embed-large:latest',
            llm_model='llama3.1:8b'
        )
        provider = AIProvider(config)

        # Mix valid and empty texts - should raise ValueError
        texts = ["text1", "", "text2"]

        with pytest.raises(ValueError) as exc_info:
            provider.generate_embeddings_batch(texts)

        # Verify error message mentions the empty text
        assert "Cannot generate embedding for empty text at index 1" in str(exc_info.value)

    def test_provider_unavailable_error(self):
        """Test that connection errors raise ProviderUnavailableError"""
        with patch('litellm.embedding') as mock_embedding:
            mock_embedding.side_effect = Exception("Connection refused")

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            with pytest.raises(ProviderUnavailableError, match="provider is unavailable"):
                provider.generate_embedding("test")


class TestMetadataAndAvailability:
    """Tests for metadata and availability checking"""

    def test_get_embedding_metadata(self):
        """Test retrieving embedding metadata"""
        with patch('litellm.embedding') as mock_embedding:
            # Setup mock for test embedding
            mock_embedding.return_value = {
                'data': [{'embedding': [0.1] * 1024}]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b',
                base_url='http://localhost:11434'
            )
            provider = AIProvider(config)

            metadata = provider.get_embedding_metadata()

            assert metadata['embedding_provider'] == 'ollama'
            assert metadata['embedding_model'] == 'mxbai-embed-large:latest'
            assert metadata['llm_model'] == 'llama3.1:8b'
            assert metadata['embedding_base_url'] == 'http://localhost:11434'
            assert metadata['embedding_dimension'] == 1024

    def test_check_availability_success(self):
        """Test availability check when provider is available"""
        with patch('litellm.embedding') as mock_embedding:
            mock_embedding.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3]}]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.check_availability()

            assert result['available'] is True
            assert result['provider_type'] == 'ollama'
            assert result['embedding_model'] == 'mxbai-embed-large:latest'
            assert result['dimension'] == 3
            assert result['error'] is None

    def test_check_availability_failure(self):
        """Test availability check when provider is unavailable"""
        with patch('litellm.embedding') as mock_embedding:
            mock_embedding.side_effect = Exception("Connection timeout")

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.check_availability()

            assert result['available'] is False
            assert result['dimension'] is None
            assert 'timeout' in result['error'].lower()


class TestDescriptionValidation:
    """Tests for LLM-based description validation"""

    def test_validate_description_success(self):
        """Test successful description validation with good score"""
        with patch('litellm.completion') as mock_completion:
            # Mock LLM response
            mock_completion.return_value = {
                'choices': [{
                    'message': {
                        'content': 'SCORE: 9\nFEEDBACK: Excellent description with clear domain and purpose.'
                    }
                }]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.validate_description("A collection of technical documentation for Python libraries")

            assert result['score'] == 9
            assert result['valid'] is True
            assert 'Excellent' in result['feedback']
            assert result['error'] is None

    def test_validate_description_low_score(self):
        """Test description validation with low score"""
        with patch('litellm.completion') as mock_completion:
            mock_completion.return_value = {
                'choices': [{
                    'message': {
                        'content': 'SCORE: 4\nFEEDBACK: Too vague, needs more specificity about the content domain.'
                    }
                }]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.validate_description("Some notes")

            assert result['score'] == 4
            assert result['valid'] is False  # Score < 7
            assert 'vague' in result['feedback'].lower()

    def test_validate_empty_description(self):
        """Test validating empty description"""
        with patch('litellm.embedding'):
            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.validate_description("")

            assert result['score'] == 0
            assert result['valid'] is False
            assert result['error'] == "Description is empty"

    def test_validate_description_parse_error(self):
        """Test handling LLM response that doesn't match expected format"""
        with patch('litellm.completion') as mock_completion:
            mock_completion.return_value = {
                'choices': [{
                    'message': {
                        'content': 'This is a free-form response without the expected format.'
                    }
                }]
            }

            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            result = provider.validate_description("Test description")

            assert result['error'] == "Could not parse score from LLM response"
            assert result['valid'] is False


class TestModelNameConversion:
    """Tests for LiteLLM model name formatting"""

    def test_ollama_model_name_format(self):
        """Test that Ollama model names are prefixed correctly"""
        with patch('litellm.embedding'):
            config = AIProviderConfig(
                provider_type='ollama',
                embedding_model='mxbai-embed-large:latest',
                llm_model='llama3.1:8b'
            )
            provider = AIProvider(config)

            # Test embedding model name
            embedding_name = provider._get_model_name_for_litellm('mxbai-embed-large:latest', for_embedding=True)
            assert embedding_name == 'ollama/mxbai-embed-large:latest'

            # Test LLM model name
            llm_name = provider._get_model_name_for_litellm('llama3.1:8b', for_embedding=False)
            assert llm_name == 'ollama/llama3.1:8b'

    def test_openai_model_name_format(self, monkeypatch):
        """Test that OpenAI model names are formatted correctly"""
        with patch('litellm.embedding'):
            monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')

            config = AIProviderConfig(
                provider_type='openai',
                embedding_model='text-embedding-3-small',
                llm_model='gpt-4o-mini',
                api_key='${OPENAI_API_KEY}'
            )
            provider = AIProvider(config)

            # Test embedding model name (OpenAI embeddings get prefix)
            embedding_name = provider._get_model_name_for_litellm('text-embedding-3-small', for_embedding=True)
            assert embedding_name == 'openai/text-embedding-3-small'

            # Test LLM model name (no prefix for completion)
            llm_name = provider._get_model_name_for_litellm('gpt-4o-mini', for_embedding=False)
            assert llm_name == 'gpt-4o-mini'
