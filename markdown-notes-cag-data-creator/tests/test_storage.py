from types import SimpleNamespace
from typing import List

import pytest

import storage
from models import Chunk, ChunkWithEmbedding


def build_chunk(index: int = 0) -> Chunk:
    return Chunk(
        id=f"chunk-{index}",
        content=f"content-{index}",
        noteId="note",
        title="Title",
        modificationDate="2024-01-01",
        creationDate="2024-01-01",
        size=100 + index,
        chunkIndex=index,
    )


def build_chunk_with_embedding(index: int = 0) -> ChunkWithEmbedding:
    chunk = build_chunk(index=index)
    return ChunkWithEmbedding(chunk=chunk, embedding=[float(index), float(index + 1)])


def test_initialize_chromadb_client_success(tmp_path, monkeypatch: pytest.MonkeyPatch):
    created_clients: List[object] = []

    class DummyClient:
        def __init__(self, path, settings):
            self.path = path
            self.settings = settings
            self.heartbeat_called = False
            created_clients.append(self)

        def heartbeat(self):
            self.heartbeat_called = True

    class DummySettings:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(storage, "Settings", DummySettings)
    monkeypatch.setattr(storage.chromadb, "PersistentClient", DummyClient)

    client = storage.initialize_chromadb_client(str(tmp_path / "db"))
    assert client.heartbeat_called
    assert created_clients


def test_initialize_chromadb_client_invalid_path(monkeypatch: pytest.MonkeyPatch):
    class ExplodingClient:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("cannot create client")

    monkeypatch.setattr(storage.chromadb, "PersistentClient", ExplodingClient)

    with pytest.raises(storage.ChromaDBConnectionError):
        storage.initialize_chromadb_client("/invalid/path")


def test_collection_exists_true(monkeypatch: pytest.MonkeyPatch):
    client = SimpleNamespace(list_collections=lambda: [SimpleNamespace(name="target")])
    assert storage.collection_exists(client, "target")


def test_collection_exists_false(monkeypatch: pytest.MonkeyPatch):
    client = SimpleNamespace(list_collections=lambda: [SimpleNamespace(name="other")])
    assert not storage.collection_exists(client, "target")


def test_get_or_create_collection_new(monkeypatch: pytest.MonkeyPatch):
    sentinel = object()
    monkeypatch.setattr(storage, "create_collection", lambda *args, **kwargs: sentinel)
    result = storage.get_or_create_collection(object(), "name", "desc", force_recreate=False)
    assert result is sentinel


def test_get_or_create_collection_force_recreate(monkeypatch: pytest.MonkeyPatch):
    sentinel = object()
    monkeypatch.setattr(storage, "recreate_collection", lambda *args, **kwargs: sentinel)
    result = storage.get_or_create_collection(object(), "name", "desc", force_recreate=True)
    assert result is sentinel


def test_prepare_batch_data_success():
    chunks = [build_chunk_with_embedding(0), build_chunk_with_embedding(1)]
    ids, documents, embeddings, metadatas = storage.prepare_chunk_batch_data(chunks)
    assert ids == ["chunk-0", "chunk-1"]
    assert documents[0] == "content-0"
    assert metadatas[0]["noteId"] == "note"


def test_prepare_batch_data_missing_fields():
    class Minimal:
        def __init__(self):
            self.id = "id"
            self.content = "content"
            self.embedding = [0.1]
            # Missing note metadata attributes

    with pytest.raises(AttributeError):
        storage.prepare_chunk_batch_data([Minimal()])


def test_insert_chunks_success(monkeypatch: pytest.MonkeyPatch):
    calls = []

    class DummyCollection:
        def add(self, *, ids, documents, metadatas, embeddings):
            calls.append((ids, documents, metadatas, embeddings))

    monkeypatch.setattr(storage, "print_storage_summary", lambda stats: None)
    chunks = [build_chunk_with_embedding(0), build_chunk_with_embedding(1)]
    stats = storage.insert_chunks(DummyCollection(), chunks, batch_size=1)
    assert stats["successful"] == 2
    assert stats["batches"] == 2
    assert len(calls) == 2



def test_insert_chunks_empty_list():
    stats = storage.insert_chunks(SimpleNamespace(), [])
    assert stats == {"total_chunks": 0, "batches": 0, "successful": 0, "failed": 0}


def test_get_collection_stats(monkeypatch: pytest.MonkeyPatch):
    class DummyCollection:
        def add(self, *, ids, documents, metadatas, embeddings):
            pass

    monkeypatch.setattr(storage, "print_storage_summary", lambda stats: None)
    chunks = [build_chunk_with_embedding(0)]
    stats = storage.insert_chunks(DummyCollection(), chunks, batch_size=10)
    assert stats["total_chunks"] == 1
    assert stats["successful"] == 1
    assert stats["failed"] == 0

def test_delete_existing_collection_deletes(monkeypatch: pytest.MonkeyPatch):
    client_calls = {"deleted": False}

    class DummyClient:
        def delete_collection(self, name):
            client_calls["deleted"] = True

    monkeypatch.setattr(storage, "collection_exists", lambda client, name: True)
    storage.delete_existing_collection(DummyClient(), "collection")
    assert client_calls["deleted"]


def test_delete_existing_collection_noop(monkeypatch: pytest.MonkeyPatch):
    class DummyClient:
        def delete_collection(self, name):
            raise AssertionError("should not delete")

    monkeypatch.setattr(storage, "collection_exists", lambda client, name: False)
    storage.delete_existing_collection(DummyClient(), "collection")


def test_build_collection_metadata_includes_fields():
    metadata = storage.build_collection_metadata("Sample description")
    assert metadata["description"] == "Sample description"
    assert metadata["hnsw:space"] == storage.HNSW_SPACE
    assert "created_at" in metadata


def test_create_collection_existing_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(storage, "collection_exists", lambda client, name: True)
    with pytest.raises(storage.StorageError):
        storage.create_collection(object(), "collection", "desc")


def test_recreate_collection_calls_delete(monkeypatch: pytest.MonkeyPatch):
    calls = {"deleted": False, "created": False}

    monkeypatch.setattr(storage, "delete_existing_collection", lambda client, name: calls.update({"deleted": True}))
    monkeypatch.setattr(storage, "build_collection_metadata", lambda description: {"created_at": "now", "description": description})
    monkeypatch.setattr(storage, "create_new_collection", lambda client, name, metadata: calls.update({"created": True}) or SimpleNamespace(name=name, metadata=metadata))
    monkeypatch.setattr(storage, "print_collection_creation_summary", lambda *args, **kwargs: None)

    storage.recreate_collection(object(), "collection", "desc")
    assert calls["deleted"] and calls["created"]


def test_insert_batch_to_collection_failure(monkeypatch: pytest.MonkeyPatch, capsys):
    stats = {"successful": 0, "batches": 0, "errors": [], "failed": 0}
    chunk = build_chunk_with_embedding(0)

    class FailingCollection:
        def add(self, **kwargs):
            raise RuntimeError("failure")

    result = storage.insert_batch_to_collection(FailingCollection(), [chunk], 1, stats)
    assert not result
    assert stats["failed"] == 1
    captured = capsys.readouterr()
    assert "Batch 1 failed" in captured.err


def test_print_storage_summary_outputs(capsys):
    storage.print_storage_summary({"successful": 1, "failed": 0, "batches": 1, "errors": []})
    captured = capsys.readouterr()
    assert "Storage complete" in captured.out
