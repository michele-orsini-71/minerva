import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from typing import Any

from minerva.commands.peek import (
    run_peek,
    get_collection_info,
    format_collection_info_text,
    format_collection_info_json,
)


class TestGetCollectionInfo:
    def test_get_info_from_empty_collection(self):
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 0
        mock_collection.metadata = {"description": "Test collection"}

        info = get_collection_info(mock_collection)

        assert info["name"] == "test_collection"
        assert info["count"] == 0
        assert info["metadata"] == {"description": "Test collection"}

    def test_get_info_from_collection_with_data(self):
        mock_collection = Mock()
        mock_collection.name = "notes_collection"
        mock_collection.count.return_value = 10
        mock_collection.metadata = {
            "description": "My notes",
            "embedding_provider": "ollama",
            "embedding_model": "mxbai-embed-large:latest"
        }

        # Mock the get() method to return sample data
        mock_collection.get.return_value = {
            "ids": ["chunk_1", "chunk_2"],
            "documents": ["Document 1 content", "Document 2 content"],
            "metadatas": [
                {"title": "Note 1", "chunk_index": 0},
                {"title": "Note 2", "chunk_index": 0}
            ]
        }

        info = get_collection_info(mock_collection)

        assert info["name"] == "notes_collection"
        assert info["count"] == 10
        assert "samples" in info
        assert len(info["samples"]) == 2
        assert info["samples"][0]["id"] == "chunk_1"
        assert info["samples"][0]["document"] == "Document 1 content"

    def test_get_info_handles_get_error(self):
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 5
        mock_collection.metadata = {}
        mock_collection.get.side_effect = Exception("Database error")

        info = get_collection_info(mock_collection)

        assert info["name"] == "test_collection"
        assert "samples_error" in info
        assert "Database error" in info["samples_error"]

    def test_get_info_with_null_metadata(self):
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 0
        mock_collection.metadata = None

        info = get_collection_info(mock_collection)

        assert info["metadata"] == {}

    def test_get_info_limits_samples_to_five(self):
        mock_collection = Mock()
        mock_collection.name = "large_collection"
        mock_collection.count.return_value = 100
        mock_collection.metadata = {}

        # Mock get() with 5 samples even though collection has 100
        mock_collection.get.return_value = {
            "ids": [f"chunk_{i}" for i in range(5)],
            "documents": [f"Document {i}" for i in range(5)],
            "metadatas": [{"title": f"Note {i}"} for i in range(5)]
        }

        info = get_collection_info(mock_collection)

        # Should call get with limit=5
        assert mock_collection.get.call_args_list[-1] == call(limit=5, include=["documents", "metadatas"])
        assert len(info["samples"]) == 5
        assert info["note_count"] is None


class TestFormatCollectionInfoText:
    def test_format_text_basic_info(self):
        info = {
            "name": "test_collection",
            "count": 42,
            "metadata": {}
        }

        text = format_collection_info_text(info)

        assert "test_collection" in text
        assert "42" in text
        assert "Total chunks" in text

    def test_format_text_with_metadata(self):
        info = {
            "name": "test_collection",
            "count": 100,
            "metadata": {
                "description": "My test collection",
                "embedding_provider": "ollama",
                "embedding_model": "mxbai-embed-large:latest",
                "embedding_dimension": "1024"
            }
        }

        text = format_collection_info_text(info)

        assert "My test collection" in text
        assert "ollama" in text
        assert "mxbai-embed-large:latest" in text

    def test_format_text_with_samples(self):
        info = {
            "name": "test_collection",
            "count": 5,
            "metadata": {},
            "samples": [
                {
                    "id": "chunk_1",
                    "document": "Sample document content",
                    "metadata": {"title": "Note 1", "chunk_index": 0}
                }
            ]
        }

        text = format_collection_info_text(info)

        assert "chunk_1" in text
        assert "Note 1" in text
        assert "Sample document content" in text

    def test_format_text_truncates_long_document(self):
        long_doc = "x" * 500
        info = {
            "name": "test_collection",
            "count": 1,
            "metadata": {},
            "samples": [
                {
                    "id": "chunk_1",
                    "document": long_doc,
                    "metadata": {}
                }
            ]
        }

        text = format_collection_info_text(info)

        # Should truncate to 200 chars
        assert "..." in text

    def test_format_text_empty_collection(self):
        info = {
            "name": "empty_collection",
            "count": 0,
            "metadata": {}
        }

        text = format_collection_info_text(info)

        assert "empty" in text.lower() or "no chunks" in text.lower()

    def test_format_text_with_samples_error(self):
        info = {
            "name": "test_collection",
            "count": 5,
            "metadata": {},
            "samples_error": "Failed to retrieve samples"
        }

        text = format_collection_info_text(info)

        assert "Failed to retrieve samples" in text


class TestFormatCollectionInfoJson:
    def test_format_json_basic(self):
        info = {
            "name": "test_collection",
            "count": 42,
            "metadata": {}
        }

        json_output = format_collection_info_json(info)

        assert '"name": "test_collection"' in json_output
        assert '"count": 42' in json_output

    def test_format_json_with_samples(self):
        info = {
            "name": "test_collection",
            "count": 2,
            "metadata": {},
            "samples": [
                {
                    "id": "chunk_1",
                    "document": "Content",
                    "metadata": {"title": "Note"}
                }
            ]
        }

        json_output = format_collection_info_json(info)

        assert '"samples"' in json_output
        assert '"chunk_1"' in json_output

    def test_format_json_is_valid_json(self):
        import json
        info = {
            "name": "test_collection",
            "count": 0,
            "metadata": {"key": "value"}
        }

        json_output = format_collection_info_json(info)

        # Should be parseable JSON
        parsed = json.loads(json_output)
        assert parsed["name"] == "test_collection"


class TestRunPeek:
    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_successful_text_format(self, mock_init_client, temp_chromadb_dir: Path):
        # Mock ChromaDB client and collection
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 10
        mock_collection.metadata = {"description": "Test"}
        mock_collection.get.return_value = {
            "ids": ["chunk_1"],
            "documents": ["Content"],
            "metadatas": [{"title": "Note"}]
        }

        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="test_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 0
        mock_init_client.assert_called_once_with(str(temp_chromadb_dir))
        mock_client.get_collection.assert_called_once_with("test_collection")

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_successful_json_format(self, mock_init_client, temp_chromadb_dir: Path):
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 5
        mock_collection.metadata = {}
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="test_collection",
            format="json"
        )

        exit_code = run_peek(args)

        assert exit_code == 0

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_collection_not_found(self, mock_init_client, temp_chromadb_dir: Path):
        mock_client = Mock()
        mock_other_collection = Mock()
        mock_other_collection.name = "other_collection"

        mock_client.list_collections.return_value = [mock_other_collection]
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="nonexistent_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1
        mock_client.get_collection.assert_not_called()

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_no_collections_exist(self, mock_init_client, temp_chromadb_dir: Path):
        mock_client = Mock()
        mock_client.list_collections.return_value = []
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="any_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_chromadb_connection_error(self, mock_init_client, temp_chromadb_dir: Path):
        from minerva.indexing.storage import ChromaDBConnectionError
        mock_init_client.side_effect = ChromaDBConnectionError("Connection failed")

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="test_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_keyboard_interrupt(self, mock_init_client, temp_chromadb_dir: Path):
        mock_init_client.side_effect = KeyboardInterrupt()

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="test_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 130

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_unexpected_error(self, mock_init_client, temp_chromadb_dir: Path):
        mock_init_client.side_effect = Exception("Unexpected error")

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="test_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_shows_available_collections_on_not_found(self, mock_init_client, temp_chromadb_dir: Path):
        mock_client = Mock()
        mock_col1 = Mock()
        mock_col1.name = "collection_1"
        mock_col2 = Mock()
        mock_col2.name = "collection_2"

        mock_client.list_collections.return_value = [mock_col1, mock_col2]
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="wrong_name",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1


class TestIntegrationScenarios:
    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_large_collection(self, mock_init_client, temp_chromadb_dir: Path):
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "large_collection"
        mock_collection.count.return_value = 10000
        mock_collection.metadata = {
            "description": "Large dataset",
            "embedding_provider": "ollama"
        }

        # Return 5 samples even though collection is large
        mock_collection.get.return_value = {
            "ids": [f"chunk_{i}" for i in range(5)],
            "documents": [f"Document {i}" for i in range(5)],
            "metadatas": [{"title": f"Note {i}"} for i in range(5)]
        }

        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="large_collection",
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 0
        # Should limit samples to 5
        assert mock_collection.get.call_args_list[-1] == call(limit=5, include=["documents", "metadatas"])

    @patch('minerva.commands.peek.initialize_chromadb_client')
    def test_peek_collection_with_unicode(self, mock_init_client, temp_chromadb_dir: Path):
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "unicode_collection"
        mock_collection.count.return_value = 2
        mock_collection.metadata = {"description": "日本語のコレクション"}

        mock_collection.get.return_value = {
            "ids": ["chunk_1"],
            "documents": ["これはテストです 🎉"],
            "metadatas": [{"title": "日本語のノート"}]
        }

        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_init_client.return_value = mock_client

        args = Namespace(
            chromadb=temp_chromadb_dir,
            collection_name="unicode_collection",
            format="json"
        )

        exit_code = run_peek(args)

        assert exit_code == 0
