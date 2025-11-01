import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from minerva.commands.index import (
    run_index,
    print_banner,
    load_and_print_config,
    load_and_print_notes,
    print_final_summary,
)
from minerva.common.exceptions import JsonLoaderError, ProviderUnavailableError


class TestPrintBanner:
    def test_print_banner_normal_mode(self, capsys):
        print_banner(is_dry_run=False)
        # Should print without "DRY-RUN" warning

    def test_print_banner_dry_run_mode(self, capsys):
        print_banner(is_dry_run=True)
        # Should print with "DRY-RUN" warning


class TestLoadAndPrintConfig:
    @patch('minerva.commands.index.load_collection_config')
    def test_load_config_successful(self, mock_load, temp_dir: Path):
        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.description = "Test description for the collection"
        mock_config.chromadb_path = "./chromadb_data"
        mock_config.json_file = "notes.json"
        mock_config.chunk_size = 1200
        mock_config.force_recreate = False
        mock_config.skip_ai_validation = False
        mock_config.ai_provider = None
        mock_load.return_value = mock_config

        config_path = str(temp_dir / "config.json")
        result = load_and_print_config(config_path, verbose=False)

        assert result == mock_config
        mock_load.assert_called_once_with(config_path)

    @patch('minerva.commands.index.load_collection_config')
    def test_load_config_verbose(self, mock_load, temp_dir: Path):
        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.description = "A" * 100  # Long description
        mock_config.chromadb_path = "./chromadb_data"
        mock_config.json_file = "notes.json"
        mock_config.chunk_size = 1200
        mock_config.force_recreate = True
        mock_config.skip_ai_validation = True
        mock_config.ai_provider = {
            'type': 'ollama',
            'embedding': {'model': 'mxbai-embed-large:latest'},
            'llm': {'model': 'llama3.1:8b'}
        }
        mock_load.return_value = mock_config

        config_path = str(temp_dir / "config.json")
        result = load_and_print_config(config_path, verbose=True)

        assert result == mock_config

    @patch('minerva.commands.index.load_collection_config')
    def test_load_config_error_exits(self, mock_load, temp_dir: Path):
        from minerva.common.config_loader import ConfigError
        mock_load.side_effect = ConfigError("Invalid configuration")

        config_path = str(temp_dir / "config.json")

        with pytest.raises(ConfigError):
            load_and_print_config(config_path, verbose=False)


class TestLoadAndPrintNotes:
    @patch('minerva.commands.index.load_json_notes')
    def test_load_notes_successful(self, mock_load, valid_notes_list):
        mock_config = Mock()
        mock_config.json_file = "notes.json"
        mock_load.return_value = valid_notes_list

        result = load_and_print_notes(mock_config, verbose=False)

        assert result == valid_notes_list
        mock_load.assert_called_once_with("notes.json")

    @patch('minerva.commands.index.load_json_notes')
    def test_load_notes_verbose(self, mock_load, valid_notes_list):
        mock_config = Mock()
        mock_config.json_file = "notes.json"
        mock_load.return_value = valid_notes_list

        result = load_and_print_notes(mock_config, verbose=True)

        assert result == valid_notes_list

    @patch('minerva.commands.index.load_json_notes')
    def test_load_notes_error_exits(self, mock_load):
        mock_config = Mock()
        mock_config.json_file = "notes.json"
        mock_load.side_effect = Exception("File not found")

        with pytest.raises(JsonLoaderError):
            load_and_print_notes(mock_config, verbose=False)


class TestPrintFinalSummary:
    def test_print_summary_with_data(self, capsys):
        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.description = "Test description"
        mock_config.chromadb_path = "./chromadb_data"

        notes = [{"title": "Note 1"}, {"title": "Note 2"}]
        chunks = [{"chunk_id": "1"}, {"chunk_id": "2"}, {"chunk_id": "3"}]
        chunks_with_embeddings = chunks  # Same list for simplicity
        stats = {"successful": 3, "failed": 0}
        processing_time = 10.5

        print_final_summary(mock_config, notes, chunks, chunks_with_embeddings, stats, processing_time)
        # Should print summary without errors

    def test_print_summary_with_failures(self, capsys):
        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.description = "Test description"
        mock_config.chromadb_path = "./chromadb_data"

        notes = [{"title": "Note 1"}]
        chunks = [{"chunk_id": "1"}]
        chunks_with_embeddings = chunks
        stats = {"successful": 0, "failed": 1}
        processing_time = 1.0

        print_final_summary(mock_config, notes, chunks, chunks_with_embeddings, stats, processing_time)
        # Should print summary with failure info


class TestRunIndex:
    @patch('minerva.commands.index.run_dry_run')
    @patch('minerva.commands.index.load_and_print_notes')
    @patch('minerva.commands.index.load_and_print_config')
    def test_index_dry_run_mode(self, mock_load_config, mock_load_notes, mock_dry_run, valid_notes_list, temp_dir: Path):
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_load_notes.return_value = valid_notes_list

        config_file = temp_dir / "config.json"
        args = Namespace(config=config_file, verbose=False, dry_run=True)

        exit_code = run_index(args)

        assert exit_code == 0
        mock_dry_run.assert_called_once_with(mock_config, valid_notes_list, False)

    @patch('minerva.commands.index.run_full_indexing')
    @patch('minerva.commands.index.check_collection_early', return_value=(False, "create"))
    @patch('minerva.commands.index.initialize_and_validate_provider')
    @patch('minerva.commands.index.load_and_print_notes')
    @patch('minerva.commands.index.load_and_print_config')
    def test_index_full_mode(
        self,
        mock_load_config,
        mock_load_notes,
        mock_init_provider,
        _mock_check_collection,
        mock_full_indexing,
        valid_notes_list,
        temp_dir: Path
    ):
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_load_notes.return_value = valid_notes_list
        mock_provider = Mock()
        mock_init_provider.return_value = mock_provider

        config_file = temp_dir / "config.json"
        args = Namespace(config=config_file, verbose=False, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 0
        assert mock_full_indexing.called

    @patch('minerva.commands.index.load_and_print_config')
    def test_index_keyboard_interrupt(self, mock_load_config, temp_dir: Path):
        mock_load_config.side_effect = KeyboardInterrupt()

        config_file = temp_dir / "config.json"
        args = Namespace(config=config_file, verbose=False, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 130

    @patch('minerva.commands.index.load_and_print_config')
    def test_index_unexpected_error(self, mock_load_config, temp_dir: Path):
        mock_load_config.side_effect = Exception("Unexpected error")

        config_file = temp_dir / "config.json"
        args = Namespace(config=config_file, verbose=False, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 1

    @patch('minerva.commands.index.load_and_print_config')
    def test_index_verbose_error_with_traceback(self, mock_load_config, temp_dir: Path):
        mock_load_config.side_effect = Exception("Unexpected error")

        config_file = temp_dir / "config.json"
        args = Namespace(config=config_file, verbose=True, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 1


class TestRunDryRun:
    @patch('minerva.commands.index.create_chunks_from_notes')
    @patch('minerva.commands.index.initialize_and_validate_provider')
    def test_dry_run_successful(self, mock_init_provider, mock_create_chunks, valid_notes_list):
        from minerva.commands.index import run_dry_run

        mock_provider = Mock()
        mock_init_provider.return_value = mock_provider

        mock_chunks = [{"chunk_id": f"chunk_{i}"} for i in range(10)]
        mock_create_chunks.return_value = mock_chunks

        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.chunk_size = 1200
        mock_config.chromadb_path = "./chromadb_data"
        mock_config.force_recreate = False

        run_dry_run(mock_config, valid_notes_list, verbose=False)

        mock_init_provider.assert_called_once_with(mock_config, False)
        mock_create_chunks.assert_called_once_with(valid_notes_list, target_chars=1200)

    @patch('minerva.commands.index.create_chunks_from_notes')
    @patch('minerva.commands.index.initialize_and_validate_provider')
    def test_dry_run_verbose(self, mock_init_provider, mock_create_chunks, valid_notes_list):
        from minerva.commands.index import run_dry_run

        mock_provider = Mock()
        mock_init_provider.return_value = mock_provider

        mock_chunks = [{"chunk_id": "1"}]
        mock_create_chunks.return_value = mock_chunks

        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.chunk_size = 1200
        mock_config.chromadb_path = "./chromadb_data"
        mock_config.force_recreate = True

        run_dry_run(mock_config, valid_notes_list, verbose=True)

        mock_init_provider.assert_called_once_with(mock_config, True)


class TestRunFullIndexing:
    @patch('minerva.commands.index.insert_chunks')
    @patch('minerva.commands.index.create_collection')
    @patch('minerva.commands.index.initialize_chromadb_client')
    @patch('minerva.commands.index.generate_embeddings')
    @patch('minerva.commands.index.create_chunks_from_notes')
    def test_full_indexing_successful(
        self,
        mock_create_chunks,
        mock_generate_embeddings,
        mock_init_chromadb,
        mock_create_collection,
        mock_insert_chunks,
        valid_notes_list
    ):
        from minerva.commands.index import run_full_indexing

        # Mock provider
        mock_provider = Mock()
        mock_provider.get_embedding_metadata.return_value = {
            'provider': 'ollama',
            'model': 'mxbai-embed-large:latest'
        }

        # Mock chunks
        mock_chunks = [{"chunk_id": "1"}, {"chunk_id": "2"}]
        mock_create_chunks.return_value = mock_chunks

        # Mock embeddings
        mock_chunks_with_embeddings = [
            {"chunk_id": "1", "embedding": [0.1] * 1024},
            {"chunk_id": "2", "embedding": [0.2] * 1024}
        ]
        mock_generate_embeddings.return_value = mock_chunks_with_embeddings

        # Mock ChromaDB
        mock_client = Mock()
        mock_client.list_collections.return_value = []  # Return empty list for collection_exists check
        mock_init_chromadb.return_value = mock_client

        mock_collection = Mock()
        mock_create_collection.return_value = mock_collection

        # Mock insertion stats
        mock_insert_chunks.return_value = {"successful": 2, "failed": 0}

        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.description = "Test description"
        mock_config.chromadb_path = "./chromadb_data"
        mock_config.chunk_size = 1200
        mock_config.force_recreate = False

        run_full_indexing(mock_config, valid_notes_list, False, 0.0, mock_provider)

        # Verify all steps were called
        mock_create_chunks.assert_called_once()
        mock_generate_embeddings.assert_called_once()
        # initialize_chromadb_client should be called once during indexing
        assert mock_init_chromadb.call_count == 1
        mock_create_collection.assert_called_once()
        mock_insert_chunks.assert_called_once()

    @patch('minerva.commands.index.recreate_collection')
    @patch('minerva.commands.index.initialize_chromadb_client')
    @patch('minerva.commands.index.generate_embeddings')
    @patch('minerva.commands.index.create_chunks_from_notes')
    def test_full_indexing_with_force_recreate(
        self,
        mock_create_chunks,
        mock_generate_embeddings,
        mock_init_chromadb,
        mock_recreate_collection,
        valid_notes_list
    ):
        from minerva.commands.index import run_full_indexing

        # Setup mocks
        mock_provider = Mock()
        mock_provider.get_embedding_metadata.return_value = {}

        mock_chunks = [{"chunk_id": "1"}]
        mock_create_chunks.return_value = mock_chunks

        mock_chunks_with_embeddings = [{"chunk_id": "1", "embedding": [0.1] * 1024}]
        mock_generate_embeddings.return_value = mock_chunks_with_embeddings

        mock_client = Mock()
        mock_client.list_collections.return_value = []  # Return empty list for collection_exists check
        mock_init_chromadb.return_value = mock_client

        mock_collection = Mock()
        mock_recreate_collection.return_value = mock_collection

        mock_config = Mock()
        mock_config.collection_name = "test_collection"
        mock_config.description = "Test description"
        mock_config.chromadb_path = "./chromadb_data"
        mock_config.chunk_size = 1200
        mock_config.force_recreate = True

        with patch('minerva.commands.index.insert_chunks') as mock_insert:
            mock_insert.return_value = {"successful": 1, "failed": 0}
            run_full_indexing(mock_config, valid_notes_list, False, 0.0, mock_provider)

        # Verify recreate was called instead of create
        mock_recreate_collection.assert_called_once()


class TestInitializeAndValidateProvider:
    @patch('minerva.commands.index.initialize_provider')
    def test_provider_available(self, mock_init):
        from minerva.commands.index import initialize_and_validate_provider

        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.llm_model = "llama3.1:8b"
        mock_provider.check_availability.return_value = {
            'available': True,
            'dimension': 1024
        }
        mock_provider.validate_description.return_value = {
            'score': 8,
            'feedback': 'Good description'
        }
        mock_init.return_value = mock_provider

        mock_config = Mock()
        mock_config.skip_ai_validation = False

        result = initialize_and_validate_provider(mock_config, verbose=False)

        assert result == mock_provider
        mock_provider.check_availability.assert_called_once()

    @patch('minerva.commands.index.initialize_provider')
    def test_provider_unavailable_exits(self, mock_init):
        from minerva.commands.index import initialize_and_validate_provider

        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.check_availability.return_value = {
            'available': False,
            'error': 'Connection refused'
        }
        mock_init.return_value = mock_provider

        mock_config = Mock()

        with pytest.raises(ProviderUnavailableError):
            initialize_and_validate_provider(mock_config, verbose=False)

    @patch('minerva.commands.index.initialize_provider')
    def test_provider_skip_validation(self, mock_init):
        from minerva.commands.index import initialize_and_validate_provider

        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.llm_model = "llama3.1:8b"
        mock_provider.check_availability.return_value = {
            'available': True,
            'dimension': 1024
        }
        mock_init.return_value = mock_provider

        mock_config = Mock()
        mock_config.skip_ai_validation = True

        result = initialize_and_validate_provider(mock_config, verbose=False)

        assert result == mock_provider
        # Should not call validate_description when skipped
        mock_provider.validate_description.assert_not_called()
