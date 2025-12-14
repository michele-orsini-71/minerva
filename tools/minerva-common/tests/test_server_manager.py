import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from minerva_common.server_manager import (
    display_server_info,
    list_available_collections,
    start_server,
)


@pytest.fixture
def server_config(tmp_path):
    config = {
        "chromadb_path": "/path/to/chromadb",
        "default_max_results": 5,
        "host": "127.0.0.1",
        "port": 8337,
    }

    config_file = tmp_path / "server.json"
    with open(config_file, "w") as f:
        json.dump(config, f)

    return config_file


@pytest.fixture
def chromadb_path(tmp_path):
    chromadb_dir = tmp_path / "chromadb"
    chromadb_dir.mkdir()
    return chromadb_dir


def test_start_server_success(server_config, chromadb_path):
    with patch("minerva_common.server_manager.list_available_collections") as mock_list:
        with patch("minerva_common.server_manager.display_server_info") as mock_display:
            with patch("minerva_common.server_manager.run_serve") as mock_serve:
                mock_list.return_value = [{"name": "test", "count": 100}]
                mock_process = MagicMock(spec=subprocess.Popen)
                mock_serve.return_value = mock_process

                result = start_server(server_config, chromadb_path)

                assert result == mock_process
                mock_list.assert_called_once()
                mock_display.assert_called_once()
                mock_serve.assert_called_once_with(str(server_config))


def test_start_server_config_not_found(tmp_path, chromadb_path):
    nonexistent = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Server config not found"):
        start_server(nonexistent, chromadb_path)


def test_start_server_accepts_string_paths(server_config, chromadb_path):
    with patch("minerva_common.server_manager.list_available_collections") as mock_list:
        with patch("minerva_common.server_manager.display_server_info"):
            with patch("minerva_common.server_manager.run_serve") as mock_serve:
                mock_list.return_value = []
                mock_serve.return_value = MagicMock()

                start_server(str(server_config), str(chromadb_path))

                assert True


def test_list_available_collections_success(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_collection1 = MagicMock()
        mock_collection1.name = "collection1"
        mock_collection1.count.return_value = 150

        mock_collection2 = MagicMock()
        mock_collection2.name = "collection2"
        mock_collection2.count.return_value = 300

        mock_client.list_collections.return_value = [mock_collection1, mock_collection2]

        result = list_available_collections(chromadb_path)

        assert len(result) == 2
        assert result[0] == {"name": "collection1", "count": 150}
        assert result[1] == {"name": "collection2", "count": 300}
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_list_available_collections_empty(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_collections.return_value = []

        result = list_available_collections(chromadb_path)

        assert result == []


def test_list_available_collections_chromadb_not_exists(tmp_path):
    nonexistent = tmp_path / "nonexistent"

    result = list_available_collections(nonexistent)

    assert result == []


def test_list_available_collections_chromadb_error(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client_class.side_effect = Exception("ChromaDB connection error")

        result = list_available_collections(chromadb_path)

        assert result == []


def test_list_available_collections_accepts_string_path(chromadb_path):
    with patch("chromadb.PersistentClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.list_collections.return_value = []

        result = list_available_collections(str(chromadb_path))

        assert result == []
        mock_client_class.assert_called_once_with(path=str(chromadb_path))


def test_display_server_info_with_collections(capsys):
    config = {
        "chromadb_path": "/path/to/chromadb",
        "default_max_results": 6,
        "host": "127.0.0.1",
        "port": 8337,
    }

    collections = [
        {"name": "collection1", "count": 1500},
        {"name": "collection2", "count": 2345},
    ]

    display_server_info(config, collections)

    captured = capsys.readouterr()

    assert "Starting Minerva MCP Server" in captured.out
    assert "/path/to/chromadb" in captured.out
    assert "6" in captured.out
    assert "http://127.0.0.1:8337" in captured.out
    assert "Available Collections: 2" in captured.out
    assert "collection1: 1,500 chunks" in captured.out
    assert "collection2: 2,345 chunks" in captured.out


def test_display_server_info_without_collections(capsys):
    config = {
        "chromadb_path": "/path/to/chromadb",
        "default_max_results": 5,
    }

    collections = []

    display_server_info(config, collections)

    captured = capsys.readouterr()

    assert "Starting Minerva MCP Server" in captured.out
    assert "Available Collections: 0" in captured.out
    assert "(No collections found)" in captured.out


def test_display_server_info_without_host_port(capsys):
    config = {
        "chromadb_path": "/path/to/chromadb",
        "default_max_results": 5,
    }

    collections = []

    display_server_info(config, collections)

    captured = capsys.readouterr()

    assert "Server URL" not in captured.out


def test_display_server_info_missing_config_fields(capsys):
    config = {}

    collections = []

    display_server_info(config, collections)

    captured = capsys.readouterr()

    assert "ChromaDB Path: N/A" in captured.out
    assert "Default Max Results: N/A" in captured.out
