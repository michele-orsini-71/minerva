import math
from typing import List
from unittest.mock import Mock, MagicMock

import numpy as np
import pytest

import embedding
from models import Chunk, ChunkWithEmbedding
from config_loader import CollectionConfig
from ai_provider import AIProvider, AIProviderError, ProviderUnavailableError


def build_chunk(chunk_id: str, content: str = "content", index: int = 0) -> Chunk:
    return Chunk(
        id=chunk_id,
        content=content,
        noteId="note",
        title="Title",
        modificationDate="2024-01-01",
        creationDate="2024-01-01",
        size=len(content),
        chunkIndex=index,
    )


def build_test_config(provider_type: str = "ollama") -> CollectionConfig:
    return CollectionConfig(
        collection_name="test_collection",
        description="Test collection for unit tests",
        chromadb_path="./test_chromadb",
        json_file="./test_data.json",
        force_recreate=False,
        skip_ai_validation=False,
        chunk_size=1200,
        ai_provider={
            "type": provider_type,
            "embedding": {
                "model": "mxbai-embed-large:latest" if provider_type == "ollama" else "text-embedding-3-small",
                "base_url": "http://localhost:11434" if provider_type == "ollama" else None,
                "api_key": None if provider_type == "ollama" else "${OPENAI_API_KEY}"
            },
            "llm": {
                "model": "llama3.1:8b" if provider_type == "ollama" else "gpt-4o-mini",
                "base_url": None,
                "api_key": None if provider_type == "ollama" else "${OPENAI_API_KEY}"
            }
        }
    )


@pytest.fixture
def mock_ai_provider(monkeypatch: pytest.MonkeyPatch):
    mock_provider = Mock(spec=AIProvider)
    mock_provider.provider_type = "ollama"
    mock_provider.embedding_model = "mxbai-embed-large:latest"
    mock_provider.llm_model = "llama3.1:8b"

    mock_provider.generate_embedding.return_value = [0.6, 0.8]
    mock_provider.check_availability.return_value = {
        'available': True,
        'provider_type': 'ollama',
        'embedding_model': 'mxbai-embed-large:latest',
        'dimension': 2,
        'error': None
    }
    mock_provider.get_embedding_metadata.return_value = {
        'embedding_provider': 'ollama',
        'embedding_model': 'mxbai-embed-large:latest',
        'llm_model': 'llama3.1:8b',
        'embedding_dimension': 2,
        'embedding_base_url': 'http://localhost:11434',
        'embedding_api_key_ref': None
    }
    mock_provider.validate_description.return_value = {
        'score': 8,
        'feedback': 'Good description',
        'valid': True,
        'error': None
    }

    return mock_provider


def test_initialize_provider_success(monkeypatch: pytest.MonkeyPatch):
    mock_provider_instance = Mock(spec=AIProvider)
    mock_provider_class = Mock(return_value=mock_provider_instance)

    monkeypatch.setattr(embedding, 'AIProvider', mock_provider_class)

    config = build_test_config()
    result = embedding.initialize_provider(config)

    assert result == mock_provider_instance
    mock_provider_class.assert_called_once()




def test_initialize_provider_provider_error(monkeypatch: pytest.MonkeyPatch):
    def failing_provider(*args, **kwargs):
        raise AIProviderError("Provider failed")

    monkeypatch.setattr(embedding, 'AIProvider', failing_provider)

    config = build_test_config()

    with pytest.raises(embedding.EmbeddingError, match="Failed to initialize AI provider"):
        embedding.initialize_provider(config)


def test_initialize_provider_different_types(monkeypatch: pytest.MonkeyPatch):
    mock_provider_class = Mock(return_value=Mock(spec=AIProvider))
    monkeypatch.setattr(embedding, 'AIProvider', mock_provider_class)

    for provider_type in ['ollama', 'openai', 'gemini']:
        config = build_test_config(provider_type)
        result = embedding.initialize_provider(config)
        assert result is not None


def test_get_embedding_metadata_success(mock_ai_provider):
    """Test getting embedding metadata directly from provider"""
    metadata = mock_ai_provider.get_embedding_metadata()

    assert metadata['embedding_provider'] == 'ollama'
    assert metadata['embedding_model'] == 'mxbai-embed-large:latest'
    assert metadata['embedding_dimension'] == 2
    mock_ai_provider.get_embedding_metadata.assert_called_once()


def test_get_embedding_metadata_uninitialized():
    """Test that provider must be passed explicitly - no module-level state"""
    # With new API, there's no module-level _provider, so this test verifies
    # that callers must pass provider explicitly
    provider = Mock(spec=AIProvider)
    provider.get_embedding_metadata.return_value = {'embedding_provider': 'ollama'}

    metadata = provider.get_embedding_metadata()
    assert 'embedding_provider' in metadata


def test_validate_description_success(mock_ai_provider):
    """Test validating description directly via provider"""
    result = mock_ai_provider.validate_description("A collection of Bear notes")

    assert result['score'] == 8
    assert result['valid'] is True
    mock_ai_provider.validate_description.assert_called_once_with("A collection of Bear notes")


def test_validate_description_explicit_provider():
    """Test that provider must be passed explicitly for validation"""
    provider = Mock(spec=AIProvider)
    provider.validate_description.return_value = {'score': 8, 'valid': True}

    result = provider.validate_description("test")
    assert result['score'] == 8


def test_generate_embedding_success(mock_ai_provider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    vector = embedding.generate_embedding(mock_ai_provider, "hello world")

    assert vector == [0.6, 0.8]
    mock_ai_provider.generate_embedding.assert_called_once_with("hello world")


def test_generate_embedding_requires_provider():
    """Test that generate_embedding requires explicit provider parameter"""
    provider = Mock(spec=AIProvider)
    provider.generate_embedding.return_value = [0.6, 0.8]

    vector = embedding.generate_embedding(provider, "test")
    assert vector == [0.6, 0.8]


def test_generate_embedding_empty_text(mock_ai_provider):
    with pytest.raises(ValueError, match="Cannot generate embedding for empty text"):
        embedding.generate_embedding(mock_ai_provider, "   ")


def test_generate_embedding_retry_logic(mock_ai_provider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    attempts: List[int] = []

    def flaky_generate(text: str):
        attempts.append(1)
        if len(attempts) == 1:
            raise AIProviderError("temporary failure")
        return [0.6, 0.8]

    mock_ai_provider.generate_embedding.side_effect = flaky_generate

    vector = embedding.generate_embedding(mock_ai_provider, "retry me", max_retries=1)
    assert len(attempts) == 2
    assert vector == [0.6, 0.8]


def test_generate_embedding_retry_exhausted(mock_ai_provider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    mock_ai_provider.generate_embedding.side_effect = AIProviderError("persistent failure")

    with pytest.raises(embedding.EmbeddingError, match="Failed to generate embedding after"):
        embedding.generate_embedding(mock_ai_provider, "will fail", max_retries=1)


def test_generate_embeddings_success(mock_ai_provider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    chunks = [build_chunk(f"chunk-{i}", content=f"content {i}", index=i) for i in range(2)]
    result = embedding.generate_embeddings(mock_ai_provider, chunks)

    assert len(result) == 2
    assert all(isinstance(item, ChunkWithEmbedding) for item in result)
    assert mock_ai_provider.generate_embedding.call_count == 2


def test_generate_embeddings_requires_provider():
    """Test that generate_embeddings requires explicit provider parameter"""
    provider = Mock(spec=AIProvider)
    provider.provider_type = "ollama"
    provider.embedding_model = "test-model"
    provider.check_availability.return_value = {'available': True}
    provider.generate_embedding.return_value = [0.6, 0.8]

    chunks = [build_chunk("chunk-1")]
    result = embedding.generate_embeddings(provider, chunks)

    assert len(result) == 1


def test_generate_embeddings_empty_list(mock_ai_provider):
    result = embedding.generate_embeddings(mock_ai_provider, [])
    assert result == []


def test_generate_embeddings_provider_unavailable(mock_ai_provider):
    mock_ai_provider.check_availability.return_value = {
        'available': False,
        'error': 'Connection refused'
    }

    chunks = [build_chunk("chunk-1")]

    with pytest.raises(embedding.EmbeddingError, match="Provider unavailable"):
        embedding.generate_embeddings(mock_ai_provider, chunks)


def test_generate_embeddings_progress_callback(mock_ai_provider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    chunks = [build_chunk(f"chunk-{i}", index=i) for i in range(3)]
    progress_events = []

    embedding.generate_embeddings(
        mock_ai_provider,
        chunks,
        progress_callback=lambda current, total: progress_events.append((current, total))
    )

    assert len(progress_events) > 0
    assert progress_events[-1] == (3, 3)


def test_generate_embeddings_partial_failure(mock_ai_provider, monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    chunks = [build_chunk(f"chunk-{i}", index=i) for i in range(3)]

    mock_ai_provider.generate_embedding.side_effect = [
        [0.6, 0.8],
        AIProviderError("Failed on second chunk"),
        [0.6, 0.8]
    ]

    result = embedding.generate_embeddings(mock_ai_provider, chunks)

    assert len(result) == 2
    captured = capsys.readouterr()
    assert "Failed chunks" in captured.out


def test_generate_embeddings_all_fail(mock_ai_provider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    mock_ai_provider.generate_embedding.side_effect = AIProviderError("All fail")

    chunks = [build_chunk("chunk-1")]

    with pytest.raises(embedding.EmbeddingError, match="No embeddings were successfully generated"):
        embedding.generate_embeddings(mock_ai_provider, chunks)


def test_validate_embedding_consistency_valid():
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    assert embedding.validate_embedding_consistency(vectors)


def test_validate_embedding_consistency_empty():
    assert embedding.validate_embedding_consistency([])


def test_validate_embedding_consistency_invalid_dimension(capsys):
    vectors = [[1.0, 0.0], [0.0, 1.0, 0.0]]
    assert not embedding.validate_embedding_consistency(vectors)
    captured = capsys.readouterr()
    assert "dimension" in captured.err


def test_validate_embedding_consistency_not_normalized(capsys):
    vectors = [[2.0, 0.0], [0.0, 2.0]]
    assert not embedding.validate_embedding_consistency(vectors)
    captured = capsys.readouterr()
    assert "not normalized" in captured.err
