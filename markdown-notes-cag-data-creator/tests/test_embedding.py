import math
from typing import List
from types import SimpleNamespace

import numpy as np
import pytest

import embedding
from models import Chunk, ChunkWithEmbedding


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


def test_l2_normalize_basic():
    vectors = np.array([[3.0, 4.0]])
    normalized = embedding.l2_normalize(vectors)
    assert math.isclose(np.linalg.norm(normalized[0]), 1.0, rel_tol=1e-6)


def test_l2_normalize_zero_vector():
    vectors = np.array([[0.0, 0.0]])
    normalized = embedding.l2_normalize(vectors)
    assert np.array_equal(normalized, np.array([[0.0, 0.0]]))


def test_generate_embedding_success(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)
    vector = embedding.generate_embedding("hello world")
    assert isinstance(vector, list)
    assert math.isclose(np.linalg.norm(vector), 1.0, rel_tol=1e-6)
    assert mock_ollama_service["embeddings"]


def test_generate_embedding_empty_text():
    with pytest.raises(ValueError):
        embedding.generate_embedding("   ")


def test_generate_embedding_retry_logic(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)
    attempts: List[int] = []

    def flaky_embeddings(model: str, prompt: str):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("temporary failure")
        return {"embedding": [0.5, 0.5, 0.5]}

    monkeypatch.setattr(embedding, "ollama_embeddings", flaky_embeddings)

    vector = embedding.generate_embedding("retry me", max_retries=1)
    assert len(attempts) == 2
    assert math.isclose(np.linalg.norm(vector), 1.0, rel_tol=1e-6)


def test_generate_embeddings_batch_success(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    def fake_generate_embedding(**kwargs):
        return [0.0, 0.1, 0.2]

    monkeypatch.setattr(embedding, "generate_embedding", lambda **kwargs: fake_generate_embedding())

    chunks = [build_chunk(f"chunk-{i}", content=f"content {i}", index=i) for i in range(2)]
    result = embedding.generate_embeddings(chunks)

    assert len(result) == 2
    assert all(isinstance(item, ChunkWithEmbedding) for item in result)


def test_validate_embedding_consistency_valid():
    vectors = [[1.0, 0.0], [0.0, 1.0]]
    assert embedding.validate_embedding_consistency(vectors)


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


def test_generate_embedding_retry_exhausted(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    def failing_embeddings(model: str, prompt: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(embedding, "ollama_embeddings", failing_embeddings)

    with pytest.raises(embedding.EmbeddingError):
        embedding.generate_embedding("will fail", max_retries=0)


def test_initialize_embedding_service_success(mock_ollama_service):
    status = embedding.initialize_embedding_service()
    assert status["service_available"]
    assert status["model_available"]
    assert status["ready"]


def test_initialize_embedding_service_ollama_not_running(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding, "check_ollama_service", lambda: False)
    with pytest.raises(embedding.OllamaServiceError):
        embedding.initialize_embedding_service()


def test_initialize_embedding_service_model_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding, "check_ollama_service", lambda: True)
    monkeypatch.setattr(embedding, "check_model_availability", lambda model: False)
    with pytest.raises(embedding.OllamaServiceError):
        embedding.initialize_embedding_service()


def test_generate_embedding_service_initialization_failure(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    def fail_init(*_args, **_kwargs):
        raise embedding.OllamaServiceError("init")

    monkeypatch.setattr(embedding, "initialize_embedding_service", fail_init)
    with pytest.raises(embedding.EmbeddingError):
        embedding.generate_embeddings([build_chunk("chunk-1")])


def test_check_ollama_service(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.ollama, "list", lambda: SimpleNamespace(models=[]))
    assert embedding.check_ollama_service() is True


def test_check_model_availability(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.ollama, "list", lambda: SimpleNamespace(models=[SimpleNamespace(model="model")]))
    assert embedding.check_model_availability("model") is True
    monkeypatch.setattr(embedding.ollama, "list", lambda: SimpleNamespace(models=[]))
    assert embedding.check_model_availability("model") is False

