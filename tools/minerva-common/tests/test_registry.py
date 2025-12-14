import json
from pathlib import Path

import pytest

from minerva_common.registry import Registry


@pytest.fixture
def temp_registry(tmp_path):
    registry_path = tmp_path / "registry.json"
    return Registry(registry_path)


@pytest.fixture
def populated_registry(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry = Registry(registry_path)
    registry.add_collection(
        "collection1",
        {
            "description": "Test collection 1",
            "provider": "ollama",
            "created_at": "2024-01-01T00:00:00Z",
        },
    )
    registry.add_collection(
        "collection2",
        {
            "description": "Test collection 2",
            "provider": "openai",
            "created_at": "2024-01-02T00:00:00Z",
        },
    )
    return registry


def test_load_empty_registry(temp_registry):
    data = temp_registry.load()
    assert data == {"collections": {}}
    assert isinstance(data["collections"], dict)


def test_load_nonexistent_registry(tmp_path):
    registry_path = tmp_path / "nonexistent" / "registry.json"
    registry = Registry(registry_path)
    data = registry.load()
    assert data == {"collections": {}}


def test_save_creates_registry(temp_registry):
    data = {"collections": {"test": {"description": "Test"}}}
    temp_registry.save(data)

    assert temp_registry.registry_path.exists()
    with temp_registry.registry_path.open("r") as f:
        saved_data = json.load(f)
    assert saved_data == data


def test_save_creates_parent_directory(tmp_path):
    registry_path = tmp_path / "nested" / "dirs" / "registry.json"
    registry = Registry(registry_path)

    data = {"collections": {}}
    registry.save(data)

    assert registry_path.exists()
    assert registry_path.parent.exists()


def test_save_uses_atomic_write(temp_registry):
    data = {"collections": {"test": {"description": "Test"}}}
    temp_registry.save(data)

    temp_path = temp_registry.registry_path.with_suffix(".tmp")
    assert not temp_path.exists()
    assert temp_registry.registry_path.exists()


def test_save_sets_permissions(temp_registry):
    data = {"collections": {}}
    temp_registry.save(data)

    stat = temp_registry.registry_path.stat()
    assert oct(stat.st_mode)[-3:] == "600"


def test_add_collection(temp_registry):
    metadata = {
        "description": "My collection",
        "provider": "ollama",
        "created_at": "2024-01-01T00:00:00Z",
    }
    temp_registry.add_collection("my_collection", metadata)

    data = temp_registry.load()
    assert "my_collection" in data["collections"]
    assert data["collections"]["my_collection"] == metadata


def test_add_multiple_collections(temp_registry):
    temp_registry.add_collection("coll1", {"description": "Collection 1"})
    temp_registry.add_collection("coll2", {"description": "Collection 2"})

    data = temp_registry.load()
    assert len(data["collections"]) == 2
    assert "coll1" in data["collections"]
    assert "coll2" in data["collections"]


def test_get_collection_existing(populated_registry):
    collection = populated_registry.get_collection("collection1")
    assert collection is not None
    assert collection["description"] == "Test collection 1"
    assert collection["provider"] == "ollama"


def test_get_collection_nonexistent(populated_registry):
    collection = populated_registry.get_collection("nonexistent")
    assert collection is None


def test_get_collection_from_empty_registry(temp_registry):
    collection = temp_registry.get_collection("any")
    assert collection is None


def test_update_collection_existing(populated_registry):
    populated_registry.update_collection(
        "collection1", {"description": "Updated description", "indexed_at": "2024-01-03T00:00:00Z"}
    )

    collection = populated_registry.get_collection("collection1")
    assert collection["description"] == "Updated description"
    assert collection["indexed_at"] == "2024-01-03T00:00:00Z"
    assert collection["provider"] == "ollama"


def test_update_collection_nonexistent(temp_registry):
    temp_registry.update_collection("nonexistent", {"description": "Updated"})
    data = temp_registry.load()
    assert "nonexistent" not in data["collections"]


def test_update_collection_partial(populated_registry):
    original = populated_registry.get_collection("collection1")
    populated_registry.update_collection("collection1", {"new_field": "new_value"})

    updated = populated_registry.get_collection("collection1")
    assert updated["description"] == original["description"]
    assert updated["provider"] == original["provider"]
    assert updated["new_field"] == "new_value"


def test_remove_collection_existing(populated_registry):
    assert populated_registry.collection_exists("collection1")

    populated_registry.remove_collection("collection1")

    assert not populated_registry.collection_exists("collection1")
    data = populated_registry.load()
    assert "collection1" not in data["collections"]
    assert "collection2" in data["collections"]


def test_remove_collection_nonexistent(populated_registry):
    data_before = populated_registry.load()
    populated_registry.remove_collection("nonexistent")
    data_after = populated_registry.load()

    assert data_before == data_after


def test_list_collections_empty(temp_registry):
    collections = temp_registry.list_collections()
    assert collections == []


def test_list_collections_populated(populated_registry):
    collections = populated_registry.list_collections()
    assert len(collections) == 2

    names = [c["name"] for c in collections]
    assert "collection1" in names
    assert "collection2" in names

    coll1 = next(c for c in collections if c["name"] == "collection1")
    assert coll1["description"] == "Test collection 1"
    assert coll1["provider"] == "ollama"


def test_list_collections_includes_name(populated_registry):
    collections = populated_registry.list_collections()
    for collection in collections:
        assert "name" in collection


def test_collection_exists_true(populated_registry):
    assert populated_registry.collection_exists("collection1")
    assert populated_registry.collection_exists("collection2")


def test_collection_exists_false(populated_registry):
    assert not populated_registry.collection_exists("nonexistent")


def test_collection_exists_empty_registry(temp_registry):
    assert not temp_registry.collection_exists("any")


def test_roundtrip_persistence(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry1 = Registry(registry_path)

    registry1.add_collection("test", {"description": "Test collection"})

    registry2 = Registry(registry_path)
    collection = registry2.get_collection("test")

    assert collection is not None
    assert collection["description"] == "Test collection"
