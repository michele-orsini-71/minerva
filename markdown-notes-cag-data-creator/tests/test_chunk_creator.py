import hashlib
from typing import Any, Dict, List

import pytest

import chunk_creator
from models import Chunk


class StubSplit:
    def __init__(self, content: str, metadata: Dict[str, Any] | None = None):
        self.page_content = content
        self.metadata = metadata or {}


class DummyRecursiveSplitter:
    def __init__(self, target_size: int):
        self.target_size = target_size
        self.calls: List[str] = []

    def split_text(self, text: str) -> List[str]:
        self.calls.append(text)
        chunks = []
        for start in range(0, len(text), self.target_size):
            chunks.append(text[start:start + self.target_size])
        return chunks or [""]


def stub_build_text_splitters(monkeypatch: pytest.MonkeyPatch, splits: List[StubSplit], recursive: DummyRecursiveSplitter | None = None):
    if recursive is None:
        recursive = DummyRecursiveSplitter(target_size=9999)

    class HeaderSplitter:
        def split_text(self, markdown: str):
            return splits

    monkeypatch.setattr(chunk_creator, "build_text_splitters", lambda *args, **kwargs: (HeaderSplitter(), recursive))
    return recursive


def test_generate_note_id_with_creation_date():
    expected = hashlib.sha1("Title|2024-01-01".encode("utf-8")).hexdigest()
    assert chunk_creator.generate_note_id("Title", "2024-01-01") == expected


def test_generate_note_id_without_creation_date():
    expected = hashlib.sha1("Solo Title".encode("utf-8")).hexdigest()
    assert chunk_creator.generate_note_id("Solo Title") == expected


def test_generate_chunk_id_is_deterministic():
    note_id = "note123"
    modification_date = "2024-02-02"
    chunk_index = 3
    first = chunk_creator.generate_chunk_id(note_id, modification_date, chunk_index)
    second = chunk_creator.generate_chunk_id(note_id, modification_date, chunk_index)
    assert first == second


def test_chunk_markdown_content_basic(monkeypatch: pytest.MonkeyPatch):
    markdown = "Just a simple paragraph"
    splits = [StubSplit(markdown, {"header": "root"})]
    recursive = DummyRecursiveSplitter(target_size=10)
    recursive.split_text = lambda text: pytest.fail("Recursive splitter should not be used for small content")

    stub_build_text_splitters(monkeypatch, splits, recursive=recursive)

    chunks = chunk_creator.chunk_markdown_content(markdown, target_chars=100, overlap_chars=20)

    assert len(chunks) == 1
    assert chunks[0]["content"] == markdown
    assert chunks[0]["metadata"] == {"header": "root"}
    assert chunks[0]["size"] == len(markdown)


def test_chunk_markdown_content_with_headers(monkeypatch: pytest.MonkeyPatch):
    splits = [
        StubSplit("# Header\nSection one", {"header": "h1"}),
        StubSplit("## Subheader\nSection two", {"header": "h2"}),
    ]
    stub_build_text_splitters(monkeypatch, splits)

    chunks = chunk_creator.chunk_markdown_content("irrelevant")

    assert [chunk["metadata"]["header"] for chunk in chunks] == ["h1", "h2"]
    assert chunks[0]["content"].startswith("# Header")


def test_chunk_markdown_content_empty_input(monkeypatch: pytest.MonkeyPatch):
    splits = [StubSplit("")]
    stub_build_text_splitters(monkeypatch, splits)

    chunks = chunk_creator.chunk_markdown_content("")

    assert len(chunks) == 1
    assert chunks[0]["content"] == ""
    assert chunks[0]["size"] == 0


def test_chunk_markdown_content_very_long_content(monkeypatch: pytest.MonkeyPatch):
    long_text = "a" * 35
    splits = [StubSplit(long_text)]
    recursive = DummyRecursiveSplitter(target_size=10)
    stub_build_text_splitters(monkeypatch, splits, recursive=recursive)

    chunks = chunk_creator.chunk_markdown_content(long_text, target_chars=10, overlap_chars=2)

    # Expect 4 chunks of length 10,10,10,5
    sizes = [chunk["size"] for chunk in chunks]
    assert sizes == [10, 10, 10, 5]
    assert "".join(chunk["content"] for chunk in chunks) == long_text


def test_create_chunks_from_notes_success(monkeypatch: pytest.MonkeyPatch, sample_notes):
    def fake_chunk_markdown_content(markdown: str, target_chars: int = 1200, overlap_chars: int = 200):
        return [
            {"content": markdown, "metadata": {}, "size": len(markdown)}
        ]

    monkeypatch.setattr(chunk_creator, "chunk_markdown_content", fake_chunk_markdown_content)

    chunks = chunk_creator.create_chunks_from_notes(sample_notes[:1], target_chars=256, overlap_chars=0)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, Chunk)
    assert chunk.title == sample_notes[0]["title"]
    assert chunk.size == len(sample_notes[0]["markdown"])
    assert chunk.chunkIndex == 0


def test_create_chunks_from_notes_with_failures(monkeypatch: pytest.MonkeyPatch, sample_notes, capsys):
    def fake_chunk_markdown_content(markdown: str, target_chars: int = 1200, overlap_chars: int = 200):
        return [
            {"content": markdown, "metadata": {}, "size": len(markdown)}
        ]

    real_builder = chunk_creator.build_chunks_from_note

    def fake_builder(note: Dict[str, Any], target_chars: int, overlap_chars: int):
        if note["title"] == "Another Note":
            raise ValueError("Simulated failure")
        return real_builder(note, target_chars, overlap_chars)

    monkeypatch.setattr(chunk_creator, "chunk_markdown_content", fake_chunk_markdown_content)
    monkeypatch.setattr(chunk_creator, "build_chunks_from_note", fake_builder)

    chunks = chunk_creator.create_chunks_from_notes(sample_notes, target_chars=256, overlap_chars=0)

    captured = capsys.readouterr()
    assert "Failed to process note" in captured.err
    assert len(chunks) >= 1
    titles = {chunk.title for chunk in chunks}
    assert "Test Note" in titles
    assert "Another Note" not in titles


def test_create_chunks_from_notes_empty_list():
    with pytest.raises(SystemExit) as exit_info:
        chunk_creator.create_chunks_from_notes([])

    assert exit_info.value.code == 1
