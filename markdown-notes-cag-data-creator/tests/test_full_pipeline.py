from types import SimpleNamespace

import pytest

import full_pipeline
from embedding import EmbeddingError
from models import Chunk, ChunkWithEmbedding
from storage import StorageError


def build_config(force_recreate: bool = False):
    return SimpleNamespace(
        collection_name="collection",
        description="A sample description",
        force_recreate=force_recreate,
        chromadb_path="/tmp/chroma",
        json_file="notes.json",
        chunk_size=500,
    )


def build_chunk(index: int = 0) -> Chunk:
    return Chunk(
        id=f"chunk-{index}",
        content="content",
        noteId="note",
        title="Title",
        modificationDate="2024-01-01",
        creationDate="2024-01-01",
        size=100,
        chunkIndex=index,
    )


def build_chunk_with_embedding(index: int = 0) -> ChunkWithEmbedding:
    chunk = build_chunk(index)
    return ChunkWithEmbedding(chunk=chunk, embedding=[0.1, 0.2])


def patch_common_dependencies(monkeypatch: pytest.MonkeyPatch, *, dry_run: bool):
    args = SimpleNamespace(dry_run=dry_run, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    monkeypatch.setattr(full_pipeline, "load_and_validate_config", lambda path, verbose: build_config(force_recreate=False))
    monkeypatch.setattr(full_pipeline, "load_json_notes", lambda path: [
        {
            "title": "Note",
            "markdown": "content",
            "size": 100,
            "modificationDate": "2024-01-01",
            "creationDate": "2024-01-01",
        }
    ])
    monkeypatch.setattr(full_pipeline, "initialize_chromadb_client", lambda path: object())
    times = iter([100.0, 105.0])
    monkeypatch.setattr(full_pipeline.time, "time", lambda: next(times))
    return args


def test_pipeline_dry_run_success(monkeypatch: pytest.MonkeyPatch):
    patch_common_dependencies(monkeypatch, dry_run=True)
    monkeypatch.setattr(full_pipeline, "collection_exists", lambda client, name: False)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 0


def test_pipeline_dry_run_collection_exists_error(monkeypatch: pytest.MonkeyPatch):
    patch_common_dependencies(monkeypatch, dry_run=True)
    monkeypatch.setattr(full_pipeline, "collection_exists", lambda client, name: True)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 1


def test_pipeline_full_run_success(monkeypatch: pytest.MonkeyPatch):
    patch_common_dependencies(monkeypatch, dry_run=False)
    monkeypatch.setattr(full_pipeline, "create_chunks_from_notes", lambda notes, target_chars: [build_chunk(0)])
    monkeypatch.setattr(full_pipeline, "generate_embeddings", lambda chunks: [build_chunk_with_embedding(0)])
    monkeypatch.setattr(full_pipeline, "create_collection", lambda client, collection_name, description: object())
    def fake_insert(collection, chunks_with_embeddings, batch_size=64, progress_callback=None):
        return {
            "successful": len(chunks_with_embeddings),
            "failed": 0,
            "total_chunks": len(chunks_with_embeddings),
            "batches": 1,
            "errors": [],
        }

    monkeypatch.setattr(full_pipeline, "insert_chunks", fake_insert)

    full_pipeline.main()  # Should not raise


def test_pipeline_handles_embedding_error(monkeypatch: pytest.MonkeyPatch):
    patch_common_dependencies(monkeypatch, dry_run=False)
    monkeypatch.setattr(full_pipeline, "create_chunks_from_notes", lambda notes, target_chars: [build_chunk(0)])
    def raise_embedding_error(_chunks):
        raise EmbeddingError("boom")

    monkeypatch.setattr(full_pipeline, "generate_embeddings", raise_embedding_error)

    def fail_handler(error, config_path):
        raise SystemExit(99)

    monkeypatch.setattr(full_pipeline, "handle_embedding_error", fail_handler)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 99


def test_pipeline_handles_storage_error(monkeypatch: pytest.MonkeyPatch):
    patch_common_dependencies(monkeypatch, dry_run=False)
    monkeypatch.setattr(full_pipeline, "create_chunks_from_notes", lambda notes, target_chars: [build_chunk(0)])
    monkeypatch.setattr(full_pipeline, "generate_embeddings", lambda chunks: [build_chunk_with_embedding(0)])

    def raise_storage_error(_client, *, collection_name, description):
        raise StorageError("fail")

    monkeypatch.setattr(full_pipeline, "create_collection", raise_storage_error)

    def fail_handler(error, collection_name, config_path):
        raise SystemExit(77)

    monkeypatch.setattr(full_pipeline, "handle_storage_error", fail_handler)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 77
