from dataclasses import replace
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from minerva.commands.index import (
    run_index,
    print_banner,
    load_and_print_config,
    load_and_print_notes,
    print_final_summary,
    run_dry_run,
    run_full_indexing,
    initialize_and_validate_provider,
)
from minerva.common.exceptions import ConfigError, JsonLoaderError, ProviderUnavailableError
from tests.helpers.config_builders import make_index_config


class TestPrintBanner:
    def test_print_banner_normal_mode(self, capsys):
        print_banner(is_dry_run=False)

    def test_print_banner_dry_run_mode(self, capsys):
        print_banner(is_dry_run=True)


class TestLoadAndPrintConfig:
    @patch('minerva.commands.index.load_index_config')
    def test_load_config_successful(self, mock_load, temp_dir: Path):
        index_config, config_path = make_index_config(temp_dir)
        mock_load.return_value = index_config

        config = load_and_print_config(str(config_path), verbose=False)

        assert config == index_config
        mock_load.assert_called_once_with(str(config_path))

    @patch('minerva.commands.index.load_index_config')
    def test_load_config_verbose(self, mock_load, temp_dir: Path):
        long_description = "A" * 120
        index_config, config_path = make_index_config(
            temp_dir,
            collection_overrides={
                "description": long_description,
                "skip_ai_validation": True,
                "force_recreate": True,
            },
        )
        mock_load.return_value = index_config

        config = load_and_print_config(str(config_path), verbose=True)

        assert config.collection.description == long_description

    @patch('minerva.commands.index.load_index_config')
    def test_load_config_error_exits(self, mock_load, temp_dir: Path):
        mock_load.side_effect = ConfigError("Invalid configuration")

        config_path = temp_dir / "missing.json"

        with pytest.raises(ConfigError):
            load_and_print_config(str(config_path), verbose=False)


class TestLoadAndPrintNotes:
    @patch('minerva.commands.index.load_json_notes')
    def test_load_notes_successful(self, mock_load, valid_notes_list, temp_dir: Path):
        index_config, _ = make_index_config(temp_dir)
        collection = index_config.collection
        mock_load.return_value = valid_notes_list

        result = load_and_print_notes(collection, verbose=False)

        assert result == valid_notes_list
        mock_load.assert_called_once_with(collection.json_file)

    @patch('minerva.commands.index.load_json_notes')
    def test_load_notes_verbose(self, mock_load, valid_notes_list, temp_dir: Path):
        index_config, _ = make_index_config(temp_dir)
        collection = index_config.collection
        mock_load.return_value = valid_notes_list

        result = load_and_print_notes(collection, verbose=True)

        assert result == valid_notes_list

    @patch('minerva.commands.index.load_json_notes')
    def test_load_notes_error_exits(self, mock_load, temp_dir: Path):
        index_config, _ = make_index_config(temp_dir)
        collection = index_config.collection
        mock_load.side_effect = Exception("File not found")

        with pytest.raises(JsonLoaderError):
            load_and_print_notes(collection, verbose=False)


class TestPrintFinalSummary:
    def test_print_summary_with_data(self, temp_dir: Path):
        index_config, _ = make_index_config(temp_dir)

        notes = [{"title": "Note 1"}, {"title": "Note 2"}]
        chunks = [{"chunk_id": "1"}, {"chunk_id": "2"}, {"chunk_id": "3"}]
        stats = {"successful": 3, "failed": 0}
        processing_time = 10.5

        print_final_summary(index_config, notes, chunks, chunks, stats, processing_time)

    def test_print_summary_with_failures(self, temp_dir: Path):
        index_config, _ = make_index_config(temp_dir)

        notes = [{"title": "Note 1"}]
        chunks = [{"chunk_id": "1"}]
        stats = {"successful": 0, "failed": 1}
        processing_time = 1.0

        print_final_summary(index_config, notes, chunks, chunks, stats, processing_time)


class TestRunIndex:
    @patch('minerva.commands.index.run_dry_run')
    @patch('minerva.commands.index.load_and_print_notes')
    @patch('minerva.commands.index.load_and_print_config')
    def test_index_dry_run_mode(self, mock_load_config, mock_load_notes, mock_dry_run, valid_notes_list, temp_dir: Path):
        index_config, config_path = make_index_config(temp_dir)
        mock_load_config.return_value = index_config
        mock_load_notes.return_value = valid_notes_list

        args = Namespace(config=config_path, verbose=False, dry_run=True)

        exit_code = run_index(args)

        assert exit_code == 0
        mock_dry_run.assert_called_once_with(index_config, valid_notes_list, False)

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
        temp_dir: Path,
    ):
        index_config, config_path = make_index_config(temp_dir)
        mock_load_config.return_value = index_config
        mock_load_notes.return_value = valid_notes_list
        mock_provider = Mock()
        mock_init_provider.return_value = mock_provider

        args = Namespace(config=config_path, verbose=False, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 0
        assert mock_full_indexing.called

    @patch('minerva.commands.index.load_and_print_config')
    def test_index_keyboard_interrupt(self, mock_load_config, temp_dir: Path):
        mock_load_config.side_effect = KeyboardInterrupt()

        args = Namespace(config=temp_dir / "config.json", verbose=False, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 130

    @patch('minerva.commands.index.load_and_print_config')
    def test_index_unexpected_error(self, mock_load_config, temp_dir: Path):
        mock_load_config.side_effect = Exception("Unexpected error")

        args = Namespace(config=temp_dir / "config.json", verbose=False, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 1

    @patch('minerva.commands.index.load_and_print_config')
    def test_index_verbose_error_with_traceback(self, mock_load_config, temp_dir: Path):
        mock_load_config.side_effect = Exception("Unexpected error")

        args = Namespace(config=temp_dir / "config.json", verbose=True, dry_run=False)

        exit_code = run_index(args)

        assert exit_code == 1


class TestRunDryRun:
    @patch('minerva.commands.index.check_collection_early', return_value=(False, "create"))
    @patch('minerva.commands.index.create_chunks_from_notes')
    @patch('minerva.commands.index.initialize_and_validate_provider')
    def test_dry_run_successful(self, mock_init_provider, mock_create_chunks, _mock_check_collection, valid_notes_list, temp_dir: Path):
        mock_provider = Mock()
        mock_init_provider.return_value = mock_provider
        mock_chunks = [{"chunk_id": f"chunk_{i}"} for i in range(3)]
        mock_create_chunks.return_value = mock_chunks

        index_config, _ = make_index_config(temp_dir)

        run_dry_run(index_config, valid_notes_list, verbose=False)

        mock_init_provider.assert_called_once_with(index_config, False)
        mock_create_chunks.assert_called_once_with(valid_notes_list, target_chars=index_config.collection.chunk_size)

    @patch('minerva.commands.index.check_collection_early', return_value=(True, "incremental"))
    @patch('minerva.commands.index.create_chunks_from_notes')
    @patch('minerva.commands.index.initialize_and_validate_provider')
    def test_dry_run_verbose(self, mock_init_provider, mock_create_chunks, mock_check_collection, valid_notes_list, temp_dir: Path):
        mock_provider = Mock()
        mock_init_provider.return_value = mock_provider
        mock_chunks = [{"chunk_id": "1"}]
        mock_create_chunks.return_value = mock_chunks

        index_config, _ = make_index_config(
            temp_dir,
            collection_overrides={"force_recreate": True},
        )

        run_dry_run(index_config, valid_notes_list, verbose=True)

        mock_init_provider.assert_called_once_with(index_config, True)
        mock_check_collection.assert_called_once_with(
            index_config.chromadb_path,
            index_config.collection,
            mock_provider,
        )


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
        valid_notes_list,
        temp_dir: Path,
    ):
        mock_provider = Mock()
        mock_provider.get_embedding_metadata.return_value = {
            'provider': 'ollama',
            'model': 'mxbai-embed-large:latest',
        }

        mock_chunks = [{"chunk_id": "1"}, {"chunk_id": "2"}]
        mock_create_chunks.return_value = mock_chunks

        mock_chunks_with_embeddings = [
            {"chunk_id": "1", "embedding": [0.1] * 4},
            {"chunk_id": "2", "embedding": [0.2] * 4},
        ]
        mock_generate_embeddings.return_value = mock_chunks_with_embeddings

        mock_client = Mock()
        mock_init_chromadb.return_value = mock_client

        mock_collection = Mock()
        mock_create_collection.return_value = mock_collection

        mock_insert_chunks.return_value = {"successful": 2, "failed": 0}

        index_config, _ = make_index_config(temp_dir)

        run_full_indexing(index_config, valid_notes_list, False, 0.0, mock_provider)

        mock_create_chunks.assert_called_once()
        mock_generate_embeddings.assert_called_once()
        mock_init_chromadb.assert_called_once_with(index_config.chromadb_path)
        mock_create_collection.assert_called_once()
        mock_insert_chunks.assert_called_once()

    @patch('minerva.commands.index.insert_chunks')
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
        mock_insert_chunks,
        valid_notes_list,
        temp_dir: Path,
    ):
        mock_provider = Mock()
        mock_provider.get_embedding_metadata.return_value = {}

        mock_chunks = [{"chunk_id": "1"}]
        mock_create_chunks.return_value = mock_chunks

        mock_generate_embeddings.return_value = [{"chunk_id": "1", "embedding": [0.1] * 4}]

        mock_client = Mock()
        mock_init_chromadb.return_value = mock_client

        mock_collection = Mock()
        mock_recreate_collection.return_value = mock_collection

        mock_insert_chunks.return_value = {"successful": 1, "failed": 0}

        index_config, _ = make_index_config(
            temp_dir,
            collection_overrides={"force_recreate": True},
        )

        run_full_indexing(index_config, valid_notes_list, False, 0.0, mock_provider)

        mock_recreate_collection.assert_called_once()


class TestInitializeAndValidateProvider:
    @patch('minerva.commands.index.initialize_provider')
    def test_provider_available(self, mock_init, temp_dir: Path):
        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.llm_model = "llama3.1:8b"
        mock_provider.check_availability.return_value = {
            'available': True,
            'dimension': 1024,
        }
        mock_provider.validate_description.return_value = {
            'score': 8,
            'feedback': 'Good description',
        }
        mock_init.return_value = mock_provider

        index_config, _ = make_index_config(temp_dir)

        result = initialize_and_validate_provider(index_config, verbose=False)

        assert result == mock_provider
        mock_provider.check_availability.assert_called_once()
        mock_provider.validate_description.assert_called_once()

    @patch('minerva.commands.index.initialize_provider')
    def test_provider_unavailable_exits(self, mock_init, temp_dir: Path):
        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.check_availability.return_value = {
            'available': False,
            'error': 'Connection refused',
        }
        mock_init.return_value = mock_provider

        index_config, _ = make_index_config(temp_dir)

        with pytest.raises(ProviderUnavailableError):
            initialize_and_validate_provider(index_config, verbose=False)

    @patch('minerva.commands.index.initialize_provider')
    def test_provider_skip_validation(self, mock_init, temp_dir: Path):
        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.llm_model = "llama3.1:8b"
        mock_provider.check_availability.return_value = {
            'available': True,
            'dimension': 1024,
        }
        mock_init.return_value = mock_provider

        index_config, _ = make_index_config(temp_dir)
        index_config = replace(
            index_config,
            collection=replace(index_config.collection, skip_ai_validation=True),
        )

        result = initialize_and_validate_provider(index_config, verbose=False)

        assert result == mock_provider
        mock_provider.validate_description.assert_not_called()
