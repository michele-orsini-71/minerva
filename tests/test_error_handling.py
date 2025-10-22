import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from minervium.commands.validate import run_validate
from minervium.commands.index import run_index, initialize_and_validate_provider
from minervium.commands.peek import run_peek
from minervium.common.config_loader import load_collection_config, ConfigError
from minervium.common.schemas import validate_notes_file


class TestMissingFileErrors:
    """Test handling of missing files across the system"""

    def test_validate_nonexistent_json_file(self, temp_dir: Path):
        """Validate command should exit cleanly when JSON file doesn't exist"""
        nonexistent = temp_dir / "does_not_exist.json"
        args = Namespace(json_file=nonexistent, verbose=False)

        with pytest.raises(SystemExit) as exc_info:
            run_validate(args)

        assert exc_info.value.code == 1

    def test_index_nonexistent_config_file(self, temp_dir: Path):
        """Index command should exit cleanly when config file doesn't exist"""
        nonexistent = temp_dir / "does_not_exist.json"
        args = Namespace(config=nonexistent, verbose=False, dry_run=False)

        with pytest.raises(SystemExit) as exc_info:
            run_index(args)

        assert exc_info.value.code == 1

    @patch('minervium.commands.index.load_collection_config')
    @patch('minervium.commands.index.load_json_notes')
    def test_index_nonexistent_notes_file(self, mock_load_notes, mock_load_config, temp_dir: Path):
        """Index command should exit cleanly when referenced JSON notes file doesn't exist"""
        mock_config = Mock()
        mock_config.json_file = str(temp_dir / "does_not_exist.json")
        mock_load_config.return_value = mock_config
        mock_load_notes.side_effect = FileNotFoundError("File not found")

        args = Namespace(config=temp_dir / "config.json", verbose=False, dry_run=False)

        with pytest.raises(SystemExit) as exc_info:
            run_index(args)

        assert exc_info.value.code == 1

    @patch('minervium.commands.peek.initialize_chromadb_client')
    def test_peek_nonexistent_chromadb_directory(self, mock_init_client, temp_dir: Path):
        """Peek command should handle missing ChromaDB directory gracefully"""
        mock_init_client.side_effect = Exception("Directory does not exist")

        nonexistent_path = temp_dir / "does_not_exist_chromadb"
        args = Namespace(
            collection_name="test_collection",
            chromadb_path=nonexistent_path,
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1


class TestInvalidConfigErrors:
    """Test handling of invalid configuration files"""

    def test_load_malformed_json_config(self, temp_dir: Path):
        """Config loader should raise ConfigError for malformed JSON"""
        config_file = temp_dir / "bad_config.json"
        config_file.write_text("{ this is not valid json }")

        with pytest.raises(ConfigError) as exc_info:
            load_collection_config(str(config_file))

        assert "JSON" in str(exc_info.value) or "parse" in str(exc_info.value).lower()

    def test_load_config_missing_required_field(self, temp_dir: Path):
        """Config loader should raise ConfigError when required fields are missing"""
        config_file = temp_dir / "incomplete_config.json"
        config_data = {
            "collection_name": "test_collection"
            # Missing required fields: chromadb_path, json_file, description
        }
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigError) as exc_info:
            load_collection_config(str(config_file))

        assert "required" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    def test_load_config_with_invalid_chunk_size(self, temp_dir: Path):
        """Config loader should raise ConfigError for invalid chunk_size"""
        config_file = temp_dir / "bad_chunk_size.json"
        config_data = {
            "collection_name": "test",
            "description": "Test description",
            "chromadb_path": "./chromadb_data",
            "json_file": "notes.json",
            "chunk_size": -100  # Invalid negative value
        }
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigError) as exc_info:
            load_collection_config(str(config_file))

        assert "chunk_size" in str(exc_info.value).lower()

    def test_load_config_with_empty_collection_name(self, temp_dir: Path):
        """Config loader should raise ConfigError for empty collection_name"""
        config_file = temp_dir / "empty_name.json"
        config_data = {
            "collection_name": "",  # Empty string not allowed
            "description": "Test description",
            "chromadb_path": "./chromadb_data",
            "json_file": "notes.json"
        }
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigError) as exc_info:
            load_collection_config(str(config_file))

        assert "collection_name" in str(exc_info.value).lower()

    def test_index_with_invalid_ai_provider_config(self, temp_dir: Path):
        """Index should handle invalid AI provider configuration gracefully"""
        config_file = temp_dir / "bad_provider.json"
        config_data = {
            "collection_name": "test",
            "description": "Test description",
            "chromadb_path": "./chromadb_data",
            "json_file": "notes.json",
            "ai_provider": {
                "type": "invalid_provider_type",  # Invalid provider
                "embedding": {"model": "test"},
                "llm": {"model": "test"}
            }
        }
        config_file.write_text(json.dumps(config_data))

        args = Namespace(config=config_file, verbose=False, dry_run=False)

        # Should exit with error code 1
        with pytest.raises(SystemExit) as exc_info:
            run_index(args)

        assert exc_info.value.code == 1


class TestProviderUnavailableErrors:
    """Test handling of unavailable AI providers"""

    @patch('minervium.commands.index.initialize_provider')
    def test_ollama_server_not_running(self, mock_init_provider):
        """Index should handle Ollama server not running"""
        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.check_availability.return_value = {
            'available': False,
            'error': 'Connection refused - is Ollama running?'
        }
        mock_init_provider.return_value = mock_provider

        mock_config = Mock()
        mock_config.skip_ai_validation = False

        with pytest.raises(SystemExit) as exc_info:
            initialize_and_validate_provider(mock_config, verbose=False)

        assert exc_info.value.code == 1

    @patch('minervium.commands.index.initialize_provider')
    def test_invalid_api_key_for_openai(self, mock_init_provider):
        """Index should handle invalid OpenAI API key"""
        mock_provider = Mock()
        mock_provider.provider_type = "openai"
        mock_provider.embedding_model = "text-embedding-3-small"
        mock_provider.check_availability.return_value = {
            'available': False,
            'error': 'Invalid API key'
        }
        mock_init_provider.return_value = mock_provider

        mock_config = Mock()
        mock_config.skip_ai_validation = False

        with pytest.raises(SystemExit) as exc_info:
            initialize_and_validate_provider(mock_config, verbose=False)

        assert exc_info.value.code == 1

    @patch('minervium.commands.index.initialize_provider')
    def test_network_timeout_during_provider_check(self, mock_init_provider):
        """Index should handle network timeouts gracefully"""
        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "mxbai-embed-large:latest"
        mock_provider.check_availability.side_effect = TimeoutError("Connection timeout")

        mock_init_provider.return_value = mock_provider

        mock_config = Mock()
        mock_config.skip_ai_validation = False

        with pytest.raises((SystemExit, TimeoutError)):
            initialize_and_validate_provider(mock_config, verbose=False)

    @patch('minervium.commands.index.initialize_provider')
    def test_invalid_model_name(self, mock_init_provider):
        """Index should handle invalid/non-existent model names"""
        mock_provider = Mock()
        mock_provider.provider_type = "ollama"
        mock_provider.embedding_model = "nonexistent-model:latest"
        mock_provider.check_availability.return_value = {
            'available': False,
            'error': 'Model not found'
        }
        mock_init_provider.return_value = mock_provider

        mock_config = Mock()
        mock_config.skip_ai_validation = False

        with pytest.raises(SystemExit) as exc_info:
            initialize_and_validate_provider(mock_config, verbose=False)

        assert exc_info.value.code == 1


class TestSchemaViolationErrors:
    """Test handling of schema violations in real workflows"""

    def test_validate_file_with_wrong_root_type(self, temp_dir: Path):
        """Validate should reject files where root is not an array"""
        bad_file = temp_dir / "not_array.json"
        bad_file.write_text('{"title": "I am an object, not an array"}')

        with open(bad_file) as f:
            data = json.load(f)

        is_valid = validate_notes_file(data, str(bad_file))

        assert is_valid is False

    def test_validate_file_with_notes_missing_required_fields(self, temp_dir: Path):
        """Validate should reject notes missing required fields"""
        bad_file = temp_dir / "missing_fields.json"
        bad_data = [
            {
                "title": "Note with missing fields"
                # Missing: markdown, size, modificationDate
            }
        ]
        bad_file.write_text(json.dumps(bad_data))

        with open(bad_file) as f:
            data = json.load(f)

        is_valid = validate_notes_file(data, str(bad_file))

        assert is_valid is False

    def test_validate_file_with_invalid_date_format(self, temp_dir: Path):
        """Validate should reject notes with invalid date formats"""
        bad_file = temp_dir / "bad_dates.json"
        bad_data = [
            {
                "title": "Note with bad date",
                "markdown": "Content",
                "size": 100,
                "modificationDate": "2025/01/15 10:30:00"  # Wrong format
            }
        ]
        bad_file.write_text(json.dumps(bad_data))

        with open(bad_file) as f:
            data = json.load(f)

        is_valid = validate_notes_file(data, str(bad_file))

        assert is_valid is False

    def test_validate_file_with_negative_size(self, temp_dir: Path):
        """Validate should reject notes with negative size"""
        bad_file = temp_dir / "negative_size.json"
        bad_data = [
            {
                "title": "Note with negative size",
                "markdown": "Content",
                "size": -100,  # Invalid
                "modificationDate": "2025-01-15T10:30:00Z"
            }
        ]
        bad_file.write_text(json.dumps(bad_data))

        with open(bad_file) as f:
            data = json.load(f)

        is_valid = validate_notes_file(data, str(bad_file))

        assert is_valid is False


class TestChromaDBErrors:
    """Test handling of ChromaDB-related errors"""

    @patch('minervium.commands.peek.initialize_chromadb_client')
    def test_peek_collection_not_found(self, mock_init_client):
        """Peek should handle non-existent collection gracefully"""
        mock_client = Mock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.list_collections.return_value = []
        mock_init_client.return_value = mock_client

        args = Namespace(
            collection_name="nonexistent_collection",
            chromadb_path=Path("./chromadb_data"),
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1

    @patch('minervium.commands.index.initialize_chromadb_client')
    def test_chromadb_permission_denied(self, mock_init_client):
        """Index should handle ChromaDB permission errors"""
        mock_init_client.side_effect = PermissionError("Permission denied")

        args = Namespace(
            config=Path("config.json"),
            verbose=False,
            dry_run=False
        )

        # Mock the config loading to get past that step
        with patch('minervium.commands.index.load_and_print_config') as mock_load_config:
            mock_config = Mock()
            mock_config.chromadb_path = "./chromadb_data"
            mock_load_config.return_value = mock_config

            with patch('minervium.commands.index.load_and_print_notes') as mock_load_notes:
                mock_load_notes.return_value = []

                with patch('minervium.commands.index.run_full_indexing') as mock_full:
                    mock_full.side_effect = PermissionError("Permission denied")

                    exit_code = run_index(args)

                    assert exit_code == 1

    @patch('minervium.commands.peek.initialize_chromadb_client')
    def test_chromadb_corrupted_database(self, mock_init_client):
        """Peek should handle corrupted ChromaDB database"""
        mock_init_client.side_effect = Exception("Database corrupted")

        args = Namespace(
            collection_name="test_collection",
            chromadb_path=Path("./chromadb_data"),
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 1


class TestEdgeCaseErrors:
    """Test handling of edge cases and unusual inputs"""

    def test_validate_empty_json_file(self, temp_dir: Path):
        """Validate should handle empty files gracefully"""
        empty_file = temp_dir / "empty.json"
        empty_file.write_text("")

        args = Namespace(json_file=empty_file, verbose=False)

        # Should exit with error for empty/invalid JSON
        with pytest.raises(SystemExit) as exc_info:
            run_validate(args)

        assert exc_info.value.code == 1

    def test_validate_json_file_with_only_whitespace(self, temp_dir: Path):
        """Validate should handle files with only whitespace"""
        whitespace_file = temp_dir / "whitespace.json"
        whitespace_file.write_text("   \n\n\t   ")

        args = Namespace(json_file=whitespace_file, verbose=False)

        with pytest.raises(SystemExit) as exc_info:
            run_validate(args)

        assert exc_info.value.code == 1

    def test_validate_extremely_large_note_title(self, temp_dir: Path):
        """Validate should handle notes with extremely large titles"""
        large_file = temp_dir / "large_title.json"
        huge_title = "A" * 1000000  # 1MB title
        large_data = [
            {
                "title": huge_title,
                "markdown": "Content",
                "size": 100,
                "modificationDate": "2025-01-15T10:30:00Z"
            }
        ]
        large_file.write_text(json.dumps(large_data))

        args = Namespace(json_file=large_file, verbose=False)

        # Should complete without crashing (may be slow)
        exit_code = run_validate(args)

        # Should succeed - no schema violation
        assert exit_code == 0

    def test_config_with_special_characters_in_paths(self, temp_dir: Path):
        """Config loader should handle special characters in paths"""
        config_file = temp_dir / "special_chars.json"
        config_data = {
            "collection_name": "test_collection",
            "description": "Test description",
            "chromadb_path": "./chromadb data with spaces/",
            "json_file": "notes with spaces.json",
            "ai_provider": {
                "type": "ollama",
                "embedding": {"model": "mxbai-embed-large:latest"},
                "llm": {"model": "llama3.1:8b"}
            }
        }
        config_file.write_text(json.dumps(config_data))

        # Should load without errors
        config = load_collection_config(str(config_file))

        assert config.chromadb_path == "./chromadb data with spaces/"
        assert config.json_file == "notes with spaces.json"

    def test_validate_json_file_not_readable(self, temp_dir: Path):
        """Validate should handle files that can't be read"""
        import os

        unreadable_file = temp_dir / "unreadable.json"
        unreadable_file.write_text("[]")

        # Make file unreadable (Unix only)
        if os.name != 'nt':  # Skip on Windows
            os.chmod(unreadable_file, 0o000)

            args = Namespace(json_file=unreadable_file, verbose=False)

            with pytest.raises(SystemExit) as exc_info:
                run_validate(args)

            # Restore permissions for cleanup
            os.chmod(unreadable_file, 0o644)

            assert exc_info.value.code == 1


class TestKeyboardInterruptHandling:
    """Test graceful handling of keyboard interrupts (Ctrl+C)"""

    @patch('minervium.commands.index.load_and_print_config')
    def test_index_handles_keyboard_interrupt(self, mock_load_config, temp_dir: Path):
        """Index command should exit cleanly on Ctrl+C"""
        mock_load_config.side_effect = KeyboardInterrupt()

        args = Namespace(
            config=temp_dir / "config.json",
            verbose=False,
            dry_run=False
        )

        exit_code = run_index(args)

        # Should exit with 130 (standard for SIGINT)
        assert exit_code == 130

    @patch('minervium.commands.validate.load_json_file')
    def test_validate_handles_keyboard_interrupt(self, mock_load, temp_dir: Path):
        """Validate command should exit cleanly on Ctrl+C"""
        mock_load.side_effect = KeyboardInterrupt()

        args = Namespace(json_file=temp_dir / "notes.json", verbose=False)

        exit_code = run_validate(args)

        assert exit_code == 130

    @patch('minervium.commands.peek.initialize_chromadb_client')
    def test_peek_handles_keyboard_interrupt(self, mock_init, temp_dir: Path):
        """Peek command should exit cleanly on Ctrl+C"""
        mock_init.side_effect = KeyboardInterrupt()

        args = Namespace(
            collection_name="test_collection",
            chromadb=temp_dir,  # Note: peek uses 'chromadb' not 'chromadb_path'
            format="text"
        )

        exit_code = run_peek(args)

        assert exit_code == 130


class TestCascadingErrors:
    """Test scenarios where one error leads to another"""

    @patch('minervium.commands.index.load_and_print_config')
    @patch('minervium.commands.index.load_and_print_notes')
    def test_config_loads_but_notes_file_invalid(self, mock_load_notes, mock_load_config, temp_dir: Path):
        """Test when config is valid but referenced notes file is invalid"""
        # Config loads successfully
        mock_config = Mock()
        mock_config.json_file = "notes.json"
        mock_load_config.return_value = mock_config

        # But notes file loading fails
        mock_load_notes.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        args = Namespace(
            config=temp_dir / "config.json",
            verbose=False,
            dry_run=False
        )

        exit_code = run_index(args)

        assert exit_code == 1

    @patch('minervium.commands.index.load_and_print_config')
    @patch('minervium.commands.index.load_and_print_notes')
    @patch('minervium.commands.index.run_full_indexing')
    def test_notes_load_but_chromadb_fails(
        self,
        mock_full_indexing,
        mock_load_notes,
        mock_load_config,
        temp_dir: Path
    ):
        """Test when notes load successfully but ChromaDB operations fail"""
        # Config and notes load successfully
        mock_config = Mock()
        mock_load_config.return_value = mock_config
        mock_load_notes.return_value = []

        # But ChromaDB operations fail
        mock_full_indexing.side_effect = Exception("ChromaDB connection failed")

        args = Namespace(
            config=temp_dir / "config.json",
            verbose=False,
            dry_run=False
        )

        exit_code = run_index(args)

        assert exit_code == 1
