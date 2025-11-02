import pytest

from minerva.common.exceptions import (
    CollectionDiscoveryError,
    StartupValidationError,
)
from minerva.indexing.storage import ChromaDBConnectionError


def test_discover_collections_connection_error(monkeypatch):
    from minerva.server import collection_discovery

    def fake_initialize(_path):
        raise ChromaDBConnectionError("boom")

    monkeypatch.setattr(collection_discovery, "initialize_chromadb_client", fake_initialize)

    with pytest.raises(CollectionDiscoveryError) as exc_info:
        collection_discovery.discover_collections_with_providers("/tmp/db")

    assert "Failed to connect" in str(exc_info.value)


def test_list_collections_unexpected_error(monkeypatch):
    from minerva.server import collection_discovery

    class FakeClient:
        def list_collections(self):
            raise RuntimeError("bad things")

    monkeypatch.setattr(collection_discovery, "initialize_chromadb_client", lambda _path: FakeClient())

    with pytest.raises(CollectionDiscoveryError) as exc_info:
        collection_discovery.list_collections("/tmp/db")

    assert "Failed to list collections" in str(exc_info.value)


def test_validate_chromadb_path_empty():
    from minerva.server import startup_validation

    with pytest.raises(StartupValidationError):
        startup_validation.validate_chromadb_path("")


def test_validate_collection_availability_requires_collections(monkeypatch):
    from minerva.server import startup_validation

    class FakeClient:
        def list_collections(self):
            return []

    monkeypatch.setattr(startup_validation, "initialize_chromadb_client", lambda _path: FakeClient())

    with pytest.raises(StartupValidationError) as exc_info:
        startup_validation.validate_collection_availability("/tmp/db")

    assert "No collections found" in str(exc_info.value)


def test_initialize_server_raises_when_no_available_collections(monkeypatch):
    from pathlib import Path
    from minerva.server import mcp_server
    from minerva.common.server_config import ServerConfig

    server_config = ServerConfig(
        chromadb_path="/tmp/db",
        default_max_results=5,
        host=None,
        port=None,
        source_path=Path("config.json")
    )

    monkeypatch.setattr(mcp_server, "validate_server_prerequisites", lambda _cfg: None)

    unavailable = {
        "name": "test",
        "description": "desc",
        "chunk_count": 0,
        "created_at": "now",
        "available": False,
        "provider_type": None,
        "embedding_model": None,
        "llm_model": None,
        "embedding_dimension": None,
        "unavailable_reason": "no provider",
    }

    monkeypatch.setattr(
        mcp_server,
        "discover_collections_with_providers",
        lambda _path: ({}, [unavailable]),
    )

    with pytest.raises(CollectionDiscoveryError) as exc_info:
        mcp_server.initialize_server(server_config)

    assert "No collections are available" in str(exc_info.value)
