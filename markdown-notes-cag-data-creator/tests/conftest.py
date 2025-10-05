import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

import pytest

# Provide lightweight fallbacks for optional third-party dependencies used during imports.
if "langchain_text_splitters" not in sys.modules:
    splitter_module = types.ModuleType("langchain_text_splitters")

    class _StubSplitter:
        def __init__(self, *args, **kwargs):
            pass

        def split_text(self, text):
            return []

    splitter_module.MarkdownHeaderTextSplitter = _StubSplitter
    splitter_module.RecursiveCharacterTextSplitter = _StubSplitter
    sys.modules["langchain_text_splitters"] = splitter_module

if "chromadb" not in sys.modules:
    chromadb_module = types.ModuleType("chromadb")

    class _StubClient:
        def __init__(self, *args, **kwargs):
            pass

        def heartbeat(self):
            return None

        def list_collections(self):
            return []

        def delete_collection(self, *_args, **_kwargs):
            return None

        def create_collection(self, *args, **kwargs):
            return SimpleNamespace(name=kwargs.get("name"), metadata=kwargs.get("metadata", {}))

    chromadb_module.PersistentClient = _StubClient
    chromadb_module.Collection = SimpleNamespace
    sys.modules["chromadb"] = chromadb_module

    config_module = types.ModuleType("chromadb.config")

    class _StubSettings:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    config_module.Settings = _StubSettings
    sys.modules["chromadb.config"] = config_module

if "ollama" not in sys.modules:
    ollama_module = types.ModuleType("ollama")

    class _StubModels(SimpleNamespace):
        pass

    def _stub_list():
        return SimpleNamespace(models=[_StubModels(model="mxbai-embed-large:latest")])

    def _stub_embeddings(*_args, **_kwargs):
        raise RuntimeError("ollama stub: embeddings not patched")

    def _stub_chat(*_args, **_kwargs):
        raise RuntimeError("ollama stub: chat not patched")

    ollama_module.list = _stub_list
    ollama_module.embeddings = _stub_embeddings
    ollama_module.chat = _stub_chat
    sys.modules["ollama"] = ollama_module

import embedding


@pytest.fixture
def fixtures_path() -> Path:
    """Return the absolute path to the shared test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_notes(fixtures_path: Path) -> List[Dict[str, object]]:
    """Load representative Bear-exported notes for chunking tests."""
    with (fixtures_path / "sample_notes.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def temp_chromadb_path(tmp_path: Path) -> str:
    """Provide a temporary ChromaDB directory path for storage tests."""
    path = tmp_path / "chromadb_test"
    path.mkdir()
    return str(path)


@pytest.fixture
def mock_ollama_service(monkeypatch: pytest.MonkeyPatch):
    """Stub the Ollama client so embedding tests run offline."""
    calls: Dict[str, List[Dict[str, object]]] = {"embeddings": []}

    class _MockOllama:
        def list(self):
            return SimpleNamespace(
                models=[SimpleNamespace(model=embedding.EMBED_MODEL)]
            )

    def fake_embeddings(model: str, prompt: str) -> Dict[str, List[float]]:
        vector = [0.0, 0.1, 0.2]
        calls["embeddings"].append({"model": model, "prompt": prompt, "vector": vector})
        return {"embedding": vector}

    monkeypatch.setattr(embedding, "ollama", _MockOllama())
    monkeypatch.setattr(embedding, "ollama_embeddings", fake_embeddings)

    yield calls

    # No teardown necessary; monkeypatch fixture handles cleanup.
