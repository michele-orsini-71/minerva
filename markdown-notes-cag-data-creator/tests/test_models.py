from dataclasses import FrozenInstanceError, asdict

import pytest

from models import Chunk, ChunkWithEmbedding


def build_chunk(**overrides) -> Chunk:
    defaults = {
        "id": "chunk-1",
        "content": "Chunk content",
        "noteId": "note-123",
        "title": "Sample Note",
        "modificationDate": "2024-01-01",
        "creationDate": "2024-01-01",
        "size": 100,
        "chunkIndex": 0,
    }
    defaults.update(overrides)
    return Chunk(**defaults)


def test_chunk_creation_valid():
    chunk = build_chunk()
    assert chunk.id == "chunk-1"
    assert chunk.chunkIndex == 0


def test_chunk_creation_empty_id_raises():
    with pytest.raises(ValueError):
        build_chunk(id="")


def test_chunk_creation_empty_content_raises():
    with pytest.raises(ValueError):
        build_chunk(content="   ")


def test_chunk_creation_negative_index_raises():
    with pytest.raises(ValueError):
        build_chunk(chunkIndex=-1)


def test_chunk_immutability():
    chunk = build_chunk()
    with pytest.raises(FrozenInstanceError):
        chunk.title = "New Title"


def test_chunk_with_embedding_creation_valid():
    chunk = build_chunk()
    cwe = ChunkWithEmbedding(chunk=chunk, embedding=[0.1, 0.2])
    assert cwe.embedding == [0.1, 0.2]
    assert cwe.id == chunk.id


def test_chunk_with_embedding_empty_embedding_raises():
    chunk = build_chunk()
    with pytest.raises(ValueError):
        ChunkWithEmbedding(chunk=chunk, embedding=[])


def test_chunk_with_embedding_non_numeric_raises():
    chunk = build_chunk()
    with pytest.raises(ValueError):
        ChunkWithEmbedding(chunk=chunk, embedding=["not", "numbers"])


def test_chunk_with_embedding_to_storage_dict():
    chunk = build_chunk()
    cwe = ChunkWithEmbedding(chunk=chunk, embedding=[0.0, 1.0])
    storage_dict = asdict(cwe)
    assert storage_dict["chunk"]["id"] == chunk.id
    assert storage_dict["embedding"] == [0.0, 1.0]


def test_chunk_with_embedding_convenience_properties():
    chunk = build_chunk()
    cwe = ChunkWithEmbedding(chunk=chunk, embedding=[0.3, 0.4])
    assert cwe.title == chunk.title
    assert cwe.chunkIndex == chunk.chunkIndex
    assert cwe.noteId == chunk.noteId
