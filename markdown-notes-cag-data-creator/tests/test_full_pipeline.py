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


def test_calculate_dry_run_estimates():
    config = SimpleNamespace(chunk_size=500)
    notes = [{"markdown": "a" * 1000}, {"markdown": "b" * 500}]
    estimates = full_pipeline.calculate_dry_run_estimates(notes, config)
    assert estimates["total_chars"] == 1500
    assert estimates["estimated_chunks"] > 0


def test_print_dry_run_summary_outputs(capsys):
    config = SimpleNamespace(
        collection_name="collection",
        description="desc",
        force_recreate=False,
        json_file="notes.json",
        chunk_size=500,
        chromadb_path="/tmp",
    )
    notes = [{"markdown": "text"}]
    estimates = {"total_chars": 4, "avg_note_size": 4, "estimated_chunks": 1, "total_estimated_size": 0.1}

    full_pipeline.print_dry_run_summary(config, notes, estimates, exists=True)
    captured = capsys.readouterr()
    assert "Collection Configuration" in captured.out


def test_validate_dry_run_config_force_recreate(capsys):
    config = SimpleNamespace(force_recreate=True)
    full_pipeline.validate_dry_run_config(config, exists=True)
    captured = capsys.readouterr()
    assert "DELETE and recreate" in captured.out


def test_validate_dry_run_config_failure_exit(capsys):
    config = SimpleNamespace(force_recreate=False)
    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.validate_dry_run_config(config, exists=True)

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "DRY-RUN VALIDATION FAILED" in captured.out


def test_validate_dry_run_config_success_branch(capsys):
    config = SimpleNamespace(force_recreate=False)
    full_pipeline.validate_dry_run_config(config, exists=False)
    captured = capsys.readouterr()
    assert "Will create new collection" in captured.out


def test_run_dry_run_mode_success(monkeypatch: pytest.MonkeyPatch):
    config = SimpleNamespace(
        chromadb_path="/tmp",
        collection_name="collection",
        chunk_size=500,
        json_file="notes.json",
        force_recreate=False,
        description="desc",
    )
    args = SimpleNamespace(dry_run=True)
    notes = [{"markdown": "text"}]

    monkeypatch.setattr(full_pipeline, "initialize_chromadb_client", lambda path: object())
    monkeypatch.setattr(full_pipeline, "collection_exists", lambda client, name: False)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.run_dry_run_mode(config, args, notes)

    assert exit_info.value.code == 0


def test_run_normal_pipeline_force_recreate(monkeypatch: pytest.MonkeyPatch, capsys):
    config = SimpleNamespace(
        collection_name="collection",
        description="desc",
        chromadb_path="/tmp",
        chunk_size=256,
        force_recreate=True,
    )
    args = SimpleNamespace(verbose=True)
    notes = [
        {
            "title": "Note",
            "markdown": "content",
            "modificationDate": "2024-01-01",
        }
    ]
    chunks = [build_chunk(0)]
    embeddings = [build_chunk_with_embedding(0)]

    def fake_create_chunks(notes_arg, target_chars, overlap_chars=200):
        return chunks

    monkeypatch.setattr(full_pipeline, "create_chunks_from_notes", fake_create_chunks)
    monkeypatch.setattr(full_pipeline, "initialize_chromadb_client", lambda path: object())
    monkeypatch.setattr(full_pipeline, "generate_embeddings", lambda *_: embeddings)
    monkeypatch.setattr(full_pipeline, "recreate_collection", lambda *args, **kwargs: object())

    def fake_insert(collection, chunks_with_embeddings, batch_size=64, progress_callback=None):
        if progress_callback:
            progress_callback(len(chunks_with_embeddings), len(chunks_with_embeddings))
        return {"successful": 1, "failed": 1, "total_chunks": 1, "batches": 1, "errors": ["fail"]}

    monkeypatch.setattr(full_pipeline, "insert_chunks", fake_insert)

    result_chunks, result_embeddings, stats = full_pipeline.run_normal_pipeline(config, args, notes, start_time=0.0)
    assert result_chunks == chunks
    assert result_embeddings == embeddings
    assert stats["failed"] == 1
    captured = capsys.readouterr()
    assert "Storing in ChromaDB" in captured.out


def test_print_pipeline_summary_outputs(capsys):
    config = SimpleNamespace(collection_name="collection", description="desc", chromadb_path="/tmp")
    notes = [{}]
    chunks = [build_chunk(0)]
    embeddings = [build_chunk_with_embedding(0)]
    stats = {"successful": 1}
    full_pipeline.print_pipeline_summary(config, notes, chunks, embeddings, stats, processing_time=1.23)
    captured = capsys.readouterr()
    assert "Pipeline completed successfully" in captured.out


def test_handle_embedding_error_outputs(capsys):
    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.handle_embedding_error(RuntimeError("fail"), "config.json")

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "EMBEDDING GENERATION ERROR" in captured.err


def test_handle_file_not_found_error_outputs(capsys):
    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.handle_file_not_found_error(FileNotFoundError("missing"), "config.json")

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "FILE NOT FOUND ERROR" in captured.err


def test_handle_storage_error_outputs(capsys):
    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.handle_storage_error(RuntimeError("fail"), "collection", "config.json")

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "Storage Error" in captured.err


def test_handle_unexpected_error_outputs(capsys):
    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.handle_unexpected_error(RuntimeError("fail"), "config.json", is_dry_run=False)

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "UNEXPECTED ERROR" in captured.err


def test_execute_pipeline_mode_dry_run(monkeypatch: pytest.MonkeyPatch):
    config = SimpleNamespace()
    args = SimpleNamespace(dry_run=True)
    notes = []

    def fake_run(*_args, **_kwargs):
        raise SystemExit(0)

    monkeypatch.setattr(full_pipeline, "run_dry_run_mode", fake_run)

    with pytest.raises(SystemExit):
        full_pipeline.execute_pipeline_mode(config, args, notes, start_time=0.0)


def test_execute_pipeline_mode_normal(monkeypatch: pytest.MonkeyPatch):
    config = SimpleNamespace()
    args = SimpleNamespace(dry_run=False)
    notes = []

    monkeypatch.setattr(full_pipeline, "run_normal_pipeline", lambda *args, **kwargs: ([], [], {"successful": 0}))
    monkeypatch.setattr(full_pipeline, "print_pipeline_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(full_pipeline.time, "time", lambda: 10.0)

    full_pipeline.execute_pipeline_mode(config, args, notes, start_time=5.0)


def test_load_config_with_verbose_output(monkeypatch: pytest.MonkeyPatch, capsys):
    class DummyConfig:
        json_file = "notes.json"
        chunk_size = 500
        chromadb_path = "/tmp"
        collection_name = "collection"

    args = SimpleNamespace(config="config.json", verbose=True)
    monkeypatch.setattr(full_pipeline, "load_and_validate_config", lambda config, verbose: DummyConfig())

    config = full_pipeline.load_config_with_verbose_output(args)
    captured = capsys.readouterr()
    assert "Target chunk size" in captured.out
    assert isinstance(config, DummyConfig)


def test_load_notes_with_verbose_output(monkeypatch: pytest.MonkeyPatch, capsys):
    config = SimpleNamespace(json_file="notes.json")
    notes = [{"markdown": "text"}]
    monkeypatch.setattr(full_pipeline, "load_json_notes", lambda path: notes)

    result = full_pipeline.load_notes_with_verbose_output(config, verbose=True)
    captured = capsys.readouterr()
    assert "Loaded 1 notes" in captured.out
    assert result == notes


def test_main_keyboard_interrupt_during_config(monkeypatch: pytest.MonkeyPatch):
    args = SimpleNamespace(dry_run=False, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    def raise_keyboard_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(full_pipeline, "load_config_with_verbose_output", raise_keyboard_interrupt)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 130


def test_main_keyboard_interrupt_during_processing(monkeypatch: pytest.MonkeyPatch):
    args = SimpleNamespace(dry_run=False, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    monkeypatch.setattr(full_pipeline, "load_config_with_verbose_output", lambda _args: SimpleNamespace(json_file="notes.json"))
    def raise_keyboard_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(full_pipeline, "load_notes_with_verbose_output", raise_keyboard_interrupt)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 130


def test_main_storage_error(monkeypatch: pytest.MonkeyPatch):
    args = SimpleNamespace(dry_run=False, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    monkeypatch.setattr(full_pipeline, "load_config_with_verbose_output", lambda _args: SimpleNamespace(json_file="notes.json", collection_name="collection"))
    monkeypatch.setattr(full_pipeline, "load_notes_with_verbose_output", lambda config, verbose: [])
    def raise_storage_error(*_args, **_kwargs):
        raise StorageError("fail")

    def exit_with_55(*_args, **_kwargs):
        raise SystemExit(55)

    monkeypatch.setattr(full_pipeline, "execute_pipeline_mode", raise_storage_error)
    monkeypatch.setattr(full_pipeline, "handle_storage_error", exit_with_55)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 55


def test_main_embedding_error(monkeypatch: pytest.MonkeyPatch):
    args = SimpleNamespace(dry_run=False, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    monkeypatch.setattr(full_pipeline, "load_config_with_verbose_output", lambda _args: SimpleNamespace(json_file="notes.json"))
    monkeypatch.setattr(full_pipeline, "load_notes_with_verbose_output", lambda config, verbose: [])
    def raise_embedding_error(*_args, **_kwargs):
        raise EmbeddingError("fail")

    def exit_with_44(*_args, **_kwargs):
        raise SystemExit(44)

    monkeypatch.setattr(full_pipeline, "execute_pipeline_mode", raise_embedding_error)
    monkeypatch.setattr(full_pipeline, "handle_embedding_error", exit_with_44)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 44


def test_main_file_not_found_error(monkeypatch: pytest.MonkeyPatch):
    args = SimpleNamespace(dry_run=False, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    monkeypatch.setattr(full_pipeline, "load_config_with_verbose_output", lambda _args: SimpleNamespace(json_file="notes.json"))
    def raise_file_not_found(*_args, **_kwargs):
        raise FileNotFoundError("missing")

    def exit_with_33(*_args, **_kwargs):
        raise SystemExit(33)

    monkeypatch.setattr(full_pipeline, "load_notes_with_verbose_output", raise_file_not_found)
    monkeypatch.setattr(full_pipeline, "handle_file_not_found_error", exit_with_33)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 33


def test_main_unexpected_error(monkeypatch: pytest.MonkeyPatch):
    args = SimpleNamespace(dry_run=False, verbose=False, config="config.json")
    monkeypatch.setattr(full_pipeline, "parse_pipeline_args", lambda: args)
    monkeypatch.setattr(full_pipeline, "load_config_with_verbose_output", lambda _args: SimpleNamespace(json_file="notes.json"))
    def raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("fail")

    def exit_with_22(*_args, **_kwargs):
        raise SystemExit(22)

    monkeypatch.setattr(full_pipeline, "load_notes_with_verbose_output", raise_runtime_error)
    monkeypatch.setattr(full_pipeline, "handle_unexpected_error", exit_with_22)

    with pytest.raises(SystemExit) as exit_info:
        full_pipeline.main()

    assert exit_info.value.code == 22
