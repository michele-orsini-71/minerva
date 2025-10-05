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


def test_generate_embedding_missing_field(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)
    monkeypatch.setattr(embedding, "ollama_embeddings", lambda model, prompt: {})

    with pytest.raises(embedding.EmbeddingError):
        embedding.generate_embedding("missing", max_retries=0)


def test_generate_embedding_empty_vector(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)
    monkeypatch.setattr(embedding, "ollama_embeddings", lambda model, prompt: {"embedding": []})

    with pytest.raises(embedding.EmbeddingError):
        embedding.generate_embedding("empty", max_retries=0)


def test_generate_embedding_connection_error(mock_ollama_service, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.time, "sleep", lambda *_: None)

    def connection_error(model: str, prompt: str):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(embedding, "ollama_embeddings", connection_error)

    with pytest.raises(embedding.OllamaServiceError):
        embedding.generate_embedding("down", max_retries=0)


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

    def raise_error():
        raise RuntimeError("offline")

    monkeypatch.setattr(embedding.ollama, "list", raise_error)
    assert embedding.check_ollama_service() is False


def test_check_model_availability(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding.ollama, "list", lambda: SimpleNamespace(models=[SimpleNamespace(model="model")]))
    assert embedding.check_model_availability("model") is True
    monkeypatch.setattr(embedding.ollama, "list", lambda: SimpleNamespace(models=[]))
    assert embedding.check_model_availability("model") is False

    def explode():
        raise RuntimeError("offline")

    monkeypatch.setattr(embedding.ollama, "list", explode)
    assert embedding.check_model_availability("model") is False


def test_generate_embeddings_progress_and_failures(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setattr(embedding, "initialize_embedding_service", lambda model: {"model_name": model})

    chunks = [build_chunk(chunk_id="chunk-0", index=0), build_chunk(chunk_id="chunk-1", index=1)]
    invocation = {"count": 0}

    def generate_with_tracking(text: str, **_kwargs):
        if invocation["count"] == 1:
            raise embedding.EmbeddingError("fail")
        invocation["count"] += 1
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(embedding, "generate_embedding", generate_with_tracking)

    progress_events = []

    result = embedding.generate_embeddings(
        chunks,
        progress_callback=lambda current, total: progress_events.append((current, total)),
    )

    assert len(result) == 1
    assert progress_events[-1] == (len(chunks), len(chunks))
    captured = capsys.readouterr()
    assert "Failed chunks" in captured.out
    assert progress_events == [(0, 2), (1, 2), (2, 2)]


def test_generate_embeddings_all_fail(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(embedding, "initialize_embedding_service", lambda model: {"model_name": model})
    def fail_generate_embedding(*_args, **_kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(embedding, "generate_embedding", fail_generate_embedding)

    chunks = [build_chunk(chunk_id="chunk-0", index=0)]

    with pytest.raises(embedding.EmbeddingError):
        embedding.generate_embeddings(chunks)
