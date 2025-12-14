from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minerva_common.collection_ops import (
    get_collection_count,
    list_chromadb_collections,
    remove_chromadb_collection,
)


@pytest.fixture
def chromadb_path(tmp_path):
    chromadb_dir = tmp_path / "chromadb"
    chromadb_dir.mkdir()
    return chromadb_dir


def test_list_chromadb_collections_success(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_collection1 = MagicMock()
        mock_collection1.name = "collection1"
        mock_collection1.count.return_value = 100

        mock_collection2 = MagicMock()
        mock_collection2.name = "collection2"
        mock_collection2.count.return_value = 200

        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]

        result = list_chromadb_collections(chromadb_path)

        assert len(result) == 2
        assert result[0] == {"name": "collection1", "count": 100}
        assert result[1] == {"name": "collection2", "count": 200}
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_list_chromadb_collections_empty(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_collections.return_value = []

        result = list_chromadb_collections(chromadb_path)

        assert result == []


def test_list_chromadb_collections_path_not_exists(tmp_path):
    nonexistent = tmp_path / "nonexistent"

    result = list_chromadb_collections(nonexistent)

    assert result == []


def test_list_chromadb_collections_exception(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client_class.side_effect = Exception("ChromaDB error")

        result = list_chromadb_collections(chromadb_path)

        assert result == []


def test_list_chromadb_collections_accepts_string_path(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_collections.return_value = []

        result = list_chromadb_collections(str(chromadb_path))

        assert result == []
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_remove_chromadb_collection_success(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = remove_chromadb_collection(chromadb_path, "test_collection")

        assert result is True
        mock_client.delete_collection.assert_called_once_with(name="test_collection")
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_remove_chromadb_collection_not_exists(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.delete_collection.side_effect = ValueError("Collection not found")

        result = remove_chromadb_collection(chromadb_path, "nonexistent")

        assert result is False


def test_remove_chromadb_collection_path_not_exists(tmp_path):
    nonexistent = tmp_path / "nonexistent"

    result = remove_chromadb_collection(nonexistent, "test_collection")

    assert result is False


def test_remove_chromadb_collection_exception(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client_class.side_effect = Exception("ChromaDB error")

        result = remove_chromadb_collection(chromadb_path, "test_collection")

        assert result is False


def test_remove_chromadb_collection_accepts_string_path(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = remove_chromadb_collection(str(chromadb_path), "test_collection")

        assert result is True
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_get_collection_count_success(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.count.return_value = 500
        mock_client.get_collection.return_value = mock_collection

        result = get_collection_count(chromadb_path, "test_collection")

        assert result == 500
        mock_client.get_collection.assert_called_once_with(name="test_collection")
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_get_collection_count_not_exists(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_collection.side_effect = ValueError("Collection not found")

        result = get_collection_count(chromadb_path, "nonexistent")

        assert result is None


def test_get_collection_count_path_not_exists(tmp_path):
    nonexistent = tmp_path / "nonexistent"

    result = get_collection_count(nonexistent, "test_collection")

    assert result is None


def test_get_collection_count_exception(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client_class.side_effect = Exception("ChromaDB error")

        result = get_collection_count(chromadb_path, "test_collection")

        assert result is None


def test_get_collection_count_accepts_string_path(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.count.return_value = 300
        mock_client.get_collection.return_value = mock_collection

        result = get_collection_count(str(chromadb_path), "test_collection")

        assert result == 300
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_get_collection_count_zero(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.get_collection.return_value = mock_collection

        result = get_collection_count(chromadb_path, "empty_collection")

        assert result == 0
