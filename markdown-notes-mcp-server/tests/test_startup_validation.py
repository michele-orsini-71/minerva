import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from startup_validation import (
    validate_chromadb_path,
    validate_collection_availability,
    validate_server_prerequisites,
    ValidationError
)


class TestValidateChromaDBPath:
    """Test ChromaDB path validation."""

    def test_empty_path(self):
        """Test validation fails for empty path."""
        success, error = validate_chromadb_path("")
        assert success is False
        assert "ChromaDB path is empty" in error
        assert "config.json" in error

    def test_whitespace_path(self):
        """Test validation fails for whitespace-only path."""
        success, error = validate_chromadb_path("   ")
        assert success is False
        assert "ChromaDB path is empty" in error

    def test_nonexistent_path(self):
        """Test validation fails for nonexistent path."""
        nonexistent = "/this/path/does/not/exist/chromadb"
        success, error = validate_chromadb_path(nonexistent)
        assert success is False
        assert "does not exist" in error
        assert nonexistent in error
        assert "full_pipeline.py" in error  # Remediation step

    def test_path_is_file_not_directory(self):
        """Test validation fails when path points to a file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            success, error = validate_chromadb_path(tmp_path)
            assert success is False
            assert "not a directory" in error
            assert tmp_path in error
        finally:
            os.unlink(tmp_path)

    def test_unreadable_directory(self):
        """Test validation fails for directory without read permissions."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Remove read permissions
            os.chmod(tmp_dir, 0o000)

            try:
                success, error = validate_chromadb_path(tmp_dir)
                assert success is False
                assert "not readable" in error
                assert "Permission denied" in error
                assert "chmod" in error  # Remediation step
            finally:
                # Restore permissions for cleanup
                os.chmod(tmp_dir, 0o755)

    def test_valid_directory(self):
        """Test validation passes for valid readable directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            success, error = validate_chromadb_path(tmp_dir)
            assert success is True
            assert error is None


class TestValidateCollectionAvailability:
    """Test collection availability validation."""

    @patch('startup_validation.initialize_chromadb_client')
    def test_no_collections(self, mock_init_client):
        """Test validation fails when no collections exist."""
        # Mock client with empty collection list
        mock_client = MagicMock()
        mock_client.list_collections.return_value = []
        mock_init_client.return_value = mock_client

        success, error = validate_collection_availability("/mock/path")
        assert success is False
        assert "No collections found" in error
        assert "full_pipeline.py" in error  # Remediation step

    @patch('startup_validation.initialize_chromadb_client')
    def test_collections_exist(self, mock_init_client):
        """Test validation passes when collections exist."""
        # Mock client with collections
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_client = MagicMock()
        mock_client.list_collections.return_value = [mock_collection]
        mock_init_client.return_value = mock_client

        success, error = validate_collection_availability("/mock/path")
        assert success is True
        assert error is None

    @patch('startup_validation.initialize_chromadb_client')
    def test_multiple_collections(self, mock_init_client):
        """Test validation passes with multiple collections."""
        # Mock client with multiple collections
        mock_collections = [
            MagicMock(name="collection1"),
            MagicMock(name="collection2"),
            MagicMock(name="collection3")
        ]
        mock_client = MagicMock()
        mock_client.list_collections.return_value = mock_collections
        mock_init_client.return_value = mock_client

        success, error = validate_collection_availability("/mock/path")
        assert success is True
        assert error is None

    @patch('startup_validation.initialize_chromadb_client')
    def test_chromadb_connection_error(self, mock_init_client):
        """Test validation fails gracefully on ChromaDB connection error."""
        # Mock client initialization failure
        mock_init_client.side_effect = Exception("Connection refused")

        success, error = validate_collection_availability("/mock/path")
        assert success is False
        assert "Failed to connect" in error
        assert "Connection refused" in error

    @patch('startup_validation.initialize_chromadb_client')
    def test_list_collections_error(self, mock_init_client):
        """Test validation fails gracefully when list_collections raises error."""
        # Mock client that fails on list_collections
        mock_client = MagicMock()
        mock_client.list_collections.side_effect = Exception("Database corrupted")
        mock_init_client.return_value = mock_client

        success, error = validate_collection_availability("/mock/path")
        assert success is False
        assert "Failed to connect" in error
        assert "Database corrupted" in error


class TestValidateServerPrerequisites:
    """Test complete server prerequisite validation."""

    @patch('startup_validation.validate_collection_availability')
    @patch('startup_validation.validate_chromadb_path')
    def test_all_validations_pass(self, mock_path, mock_collections):
        """Test validation passes when all checks succeed."""
        mock_path.return_value = (True, None)
        mock_collections.return_value = (True, None)

        config = {
            'chromadb_path': '/mock/chromadb'
        }

        success, error = validate_server_prerequisites(config)
        assert success is True
        assert error is None

        mock_path.assert_called_once_with('/mock/chromadb')
        mock_collections.assert_called_once_with('/mock/chromadb')

    @patch('startup_validation.validate_chromadb_path')
    def test_chromadb_path_fails_early_exit(self, mock_path):
        """Test validation exits early when ChromaDB path validation fails."""
        mock_path.return_value = (False, "Path does not exist")

        config = {
            'chromadb_path': '/invalid/path'
        }

        success, error = validate_server_prerequisites(config)
        assert success is False
        assert "ChromaDB Path Validation Failed" in error
        assert "Path does not exist" in error

    @patch('startup_validation.validate_collection_availability')
    @patch('startup_validation.validate_chromadb_path')
    def test_collection_check_fails(self, mock_path, mock_collections):
        """Test validation fails when collection check fails."""
        mock_path.return_value = (True, None)
        mock_collections.return_value = (False, "No collections found")

        config = {
            'chromadb_path': '/mock/chromadb'
        }

        success, error = validate_server_prerequisites(config)
        assert success is False
        assert "Collection Availability Check Failed" in error
        assert "No collections found" in error

    @patch('startup_validation.validate_collection_availability')
    @patch('startup_validation.validate_chromadb_path')
    def test_validation_order(self, mock_path, mock_collections):
        """Test validations run in the correct order and stop at first failure."""
        mock_path.return_value = (False, "Path error")

        config = {
            'chromadb_path': '/mock/chromadb'
        }

        success, error = validate_server_prerequisites(config)

        assert success is False
        assert "ChromaDB Path Validation Failed" in error

        mock_path.assert_called_once()
        mock_collections.assert_not_called()

    @patch('startup_validation.validate_collection_availability')
    @patch('startup_validation.validate_chromadb_path')
    def test_config_missing_fields(self, mock_path, mock_collections):
        """Test validation handles missing config fields gracefully."""
        mock_path.return_value = (True, None)
        mock_collections.return_value = (False, "Empty path")

        config = {'chromadb_path': '/mock/chromadb'}

        success, error = validate_server_prerequisites(config)

        mock_path.assert_called_once_with('/mock/chromadb')
        mock_collections.assert_called_once_with('/mock/chromadb')


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_fresh_installation_scenario(self):
        """Test error messages for a fresh installation without setup."""
        success, error = validate_chromadb_path("")
        assert success is False
        assert "config.json" in error

    @patch('startup_validation.initialize_chromadb_client')
    def test_chromadb_exists_but_empty(self, mock_init):
        """Test scenario where ChromaDB exists but has no collections."""
        mock_client = MagicMock()
        mock_client.list_collections.return_value = []
        mock_init.return_value = mock_client

        success, error = validate_collection_availability("/mock/path")
        assert success is False
        assert "No collections found" in error
        assert "full_pipeline.py" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
