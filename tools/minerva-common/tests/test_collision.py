import json
from pathlib import Path
from unittest.mock import patch

import pytest

from minerva_common.collision import (
    check_collection_exists,
    check_registry_owner,
    find_collection_owner,
)


@pytest.fixture
def chromadb_path(tmp_path):
    chromadb_dir = tmp_path / "chromadb"
    chromadb_dir.mkdir()
    return chromadb_dir


@pytest.fixture
def apps_dir(tmp_path):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    return apps_dir


@pytest.fixture
def kb_registry(apps_dir):
    kb_dir = apps_dir / "minerva-kb"
    kb_dir.mkdir()

    registry_path = kb_dir / "collections.json"
    registry_data = {
        "collections": {
            "kb_collection": {
                "name": "kb_collection",
                "type": "repository",
            }
        }
    }

    with open(registry_path, "w") as f:
        json.dump(registry_data, f)

    return registry_path


@pytest.fixture
def doc_registry(apps_dir):
    doc_dir = apps_dir / "minerva-doc"
    doc_dir.mkdir()

    registry_path = doc_dir / "collections.json"
    registry_data = {
        "collections": {
            "doc_collection": {
                "name": "doc_collection",
                "type": "document",
            }
        }
    }

    with open(registry_path, "w") as f:
        json.dump(registry_data, f)

    return registry_path


def test_check_collection_exists_with_kb_owner(chromadb_path, apps_dir, kb_registry):
    with patch("minerva_common.collision.get_collection_count") as mock_count:
        with patch("minerva_common.collision.APPS_DIR", apps_dir):
            mock_count.return_value = 100

            exists, owner = check_collection_exists("kb_collection", chromadb_path)

            assert exists is True
            assert owner == "minerva-kb"


def test_check_collection_exists_with_doc_owner(chromadb_path, apps_dir, doc_registry):
    with patch("minerva_common.collision.get_collection_count") as mock_count:
        with patch("minerva_common.collision.APPS_DIR", apps_dir):
            mock_count.return_value = 200

            exists, owner = check_collection_exists("doc_collection", chromadb_path)

            assert exists is True
            assert owner == "minerva-doc"


def test_check_collection_exists_unmanaged(chromadb_path, apps_dir):
    with patch("minerva_common.collision.get_collection_count") as mock_count:
        with patch("minerva_common.collision.APPS_DIR", apps_dir):
            mock_count.return_value = 150

            exists, owner = check_collection_exists("unmanaged_collection", chromadb_path)

            assert exists is True
            assert owner is None


def test_check_collection_exists_not_found(chromadb_path, apps_dir):
    with patch("minerva_common.collision.get_collection_count") as mock_count:
        with patch("minerva_common.collision.APPS_DIR", apps_dir):
            mock_count.return_value = None

            exists, owner = check_collection_exists("nonexistent", chromadb_path)

            assert exists is False
            assert owner is None


def test_check_collection_exists_uses_default_chromadb_path():
    with patch("minerva_common.collision.get_collection_count") as mock_count:
        with patch("minerva_common.collision.CHROMADB_DIR") as mock_chromadb_dir:
            mock_chromadb_dir.return_value = Path("/default/chromadb")
            mock_count.return_value = None

            check_collection_exists("test")

            mock_count.assert_called_once()
            call_args = mock_count.call_args[0]
            assert call_args[1] == "test"


def test_check_collection_exists_accepts_string_path(apps_dir):
    with patch("minerva_common.collision.get_collection_count") as mock_count:
        with patch("minerva_common.collision.APPS_DIR", apps_dir):
            mock_count.return_value = None

            exists, owner = check_collection_exists("test", "/path/to/chromadb")

            assert exists is False
            assert owner is None


def test_find_collection_owner_in_kb(apps_dir, kb_registry):
    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = find_collection_owner("kb_collection")

        assert owner == "minerva-kb"


def test_find_collection_owner_in_doc(apps_dir, doc_registry):
    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = find_collection_owner("doc_collection")

        assert owner == "minerva-doc"


def test_find_collection_owner_not_found(apps_dir):
    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = find_collection_owner("nonexistent")

        assert owner is None


def test_find_collection_owner_kb_takes_precedence(apps_dir):
    kb_dir = apps_dir / "minerva-kb"
    kb_dir.mkdir()
    kb_registry = kb_dir / "collections.json"
    with open(kb_registry, "w") as f:
        json.dump({"collections": {"shared": {}}}, f)

    doc_dir = apps_dir / "minerva-doc"
    doc_dir.mkdir()
    doc_registry = doc_dir / "collections.json"
    with open(doc_registry, "w") as f:
        json.dump({"collections": {"shared": {}}}, f)

    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = find_collection_owner("shared")

        assert owner == "minerva-kb"


def test_check_registry_owner_found(apps_dir, kb_registry):
    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = check_registry_owner("kb_collection", "minerva-kb")

        assert owner == "minerva-kb"


def test_check_registry_owner_not_found(apps_dir, kb_registry):
    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = check_registry_owner("nonexistent", "minerva-kb")

        assert owner is None


def test_check_registry_owner_registry_not_exists(apps_dir):
    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = check_registry_owner("test", "minerva-kb")

        assert owner is None


def test_check_registry_owner_invalid_json(apps_dir):
    kb_dir = apps_dir / "minerva-kb"
    kb_dir.mkdir()
    registry_path = kb_dir / "collections.json"

    with open(registry_path, "w") as f:
        f.write("invalid json {{{")

    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = check_registry_owner("test", "minerva-kb")

        assert owner is None


def test_check_registry_owner_missing_collections_key(apps_dir):
    kb_dir = apps_dir / "minerva-kb"
    kb_dir.mkdir()
    registry_path = kb_dir / "collections.json"

    with open(registry_path, "w") as f:
        json.dump({"wrong_key": {}}, f)

    with patch("minerva_common.collision.APPS_DIR", apps_dir):
        owner = check_registry_owner("test", "minerva-kb")

        assert owner is None


def test_check_registry_owner_permission_error(apps_dir):
    kb_dir = apps_dir / "minerva-kb"
    kb_dir.mkdir()
    registry_path = kb_dir / "collections.json"

    with open(registry_path, "w") as f:
        json.dump({"collections": {"test": {}}}, f)

    with patch("builtins.open", side_effect=OSError("Permission denied")):
        with patch("minerva_common.collision.APPS_DIR", apps_dir):
            owner = check_registry_owner("test", "minerva-kb")

            assert owner is None
