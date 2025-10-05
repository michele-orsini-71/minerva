"""
Unit tests for configuration management module.

Tests cover:
- Valid configuration loading
- Missing configuration file
- Invalid JSON syntax
- Missing required fields
- Invalid field types
- Out-of-range values
- Invalid path formats
- Invalid model naming
"""

import json
import os
import pytest
import tempfile
from pathlib import Path

# Add parent directory to path to import config module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    load_config,
    validate_config,
    validate_chromadb_path,
    validate_default_max_results,
    validate_embedding_model,
    ConfigError,
    ConfigValidationError
)


class TestLoadConfig:
    """Test configuration file loading."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "chromadb_path": "/absolute/path/to/chromadb",
            "default_max_results": 5,
            "embedding_model": "mxbai-embed-large:latest"
        }
        config_file.write_text(json.dumps(config_data))

        config = load_config(str(config_file))

        assert config == config_data
        assert config['chromadb_path'] == "/absolute/path/to/chromadb"
        assert config['default_max_results'] == 5
        assert config['embedding_model'] == "mxbai-embed-large:latest"

    def test_load_config_file_not_found(self):
        """Test error when configuration file does not exist."""
        with pytest.raises(ConfigError) as exc_info:
            load_config("/nonexistent/config.json")

        assert "Configuration file not found" in str(exc_info.value)
        assert "cp config.json.example" in str(exc_info.value)

    def test_load_invalid_json(self, tmp_path):
        """Test error when JSON syntax is invalid."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"invalid": json syntax}')

        with pytest.raises(ConfigError) as exc_info:
            load_config(str(config_file))

        assert "Invalid JSON" in str(exc_info.value)

    def test_load_empty_json_object(self, tmp_path):
        """Test error when config file is empty JSON object."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{}')

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "Missing required field" in str(exc_info.value)


class TestValidateChromadbPath:
    """Test chromadb_path validation."""

    def test_valid_absolute_path(self):
        """Test validation passes for valid absolute paths."""
        configs = [
            {"chromadb_path": "/usr/local/chromadb"},
            {"chromadb_path": "/home/user/data/chromadb"},
            {"chromadb_path": "/Users/username/chromadb_data"}
        ]

        for config in configs:
            validate_chromadb_path(config)  # Should not raise

    def test_missing_chromadb_path(self):
        """Test error when chromadb_path is missing."""
        config = {}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_chromadb_path(config)

        assert "Missing required field: 'chromadb_path'" in str(exc_info.value)

    def test_chromadb_path_not_string(self):
        """Test error when chromadb_path is not a string."""
        configs = [
            {"chromadb_path": 123},
            {"chromadb_path": ["path"]},
            {"chromadb_path": {"path": "/usr/local"}},
            {"chromadb_path": None}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_chromadb_path(config)

            assert "must be a string" in str(exc_info.value)

    def test_chromadb_path_empty(self):
        """Test error when chromadb_path is empty."""
        configs = [
            {"chromadb_path": ""},
            {"chromadb_path": "   "}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_chromadb_path(config)

            assert "cannot be empty" in str(exc_info.value)

    def test_chromadb_path_not_absolute(self):
        """Test error when chromadb_path is relative."""
        configs = [
            {"chromadb_path": "relative/path"},
            {"chromadb_path": "./chromadb"},
            {"chromadb_path": "../chromadb"},
            {"chromadb_path": "chromadb_data"}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_chromadb_path(config)

            assert "must be an absolute path" in str(exc_info.value)
            assert "Relative paths are not allowed" in str(exc_info.value)


class TestValidateDefaultMaxResults:
    """Test default_max_results validation."""

    def test_valid_max_results(self):
        """Test validation passes for valid values."""
        valid_values = [1, 5, 10, 25, 50, 100]

        for value in valid_values:
            config = {"default_max_results": value}
            validate_default_max_results(config)  # Should not raise

    def test_missing_default_max_results(self):
        """Test error when default_max_results is missing."""
        config = {}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_default_max_results(config)

        assert "Missing required field: 'default_max_results'" in str(exc_info.value)

    def test_default_max_results_not_integer(self):
        """Test error when default_max_results is not an integer."""
        configs = [
            {"default_max_results": "5"},
            {"default_max_results": 5.5},
            {"default_max_results": [5]},
            {"default_max_results": None}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_default_max_results(config)

            assert "must be an integer" in str(exc_info.value)

    def test_default_max_results_below_minimum(self):
        """Test error when value is below minimum (1)."""
        configs = [
            {"default_max_results": 0},
            {"default_max_results": -1},
            {"default_max_results": -100}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_default_max_results(config)

            assert "must be between 1 and 100" in str(exc_info.value)

    def test_default_max_results_above_maximum(self):
        """Test error when value is above maximum (100)."""
        configs = [
            {"default_max_results": 101},
            {"default_max_results": 200},
            {"default_max_results": 1000}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_default_max_results(config)

            assert "must be between 1 and 100" in str(exc_info.value)


class TestValidateEmbeddingModel:
    """Test embedding_model validation."""

    def test_valid_model_names(self):
        """Test validation passes for valid Ollama model names."""
        valid_models = [
            "mxbai-embed-large:latest",
            "nomic-embed-text:latest",
            "all-minilm:latest",
            "llama3.1:8b",
            "model-name",
            "model_name",
            "model.name",
            "model123:v1.0"
        ]

        for model in valid_models:
            config = {"embedding_model": model}
            validate_embedding_model(config)  # Should not raise

    def test_missing_embedding_model(self):
        """Test error when embedding_model is missing."""
        config = {}

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_embedding_model(config)

        assert "Missing required field: 'embedding_model'" in str(exc_info.value)
        assert "ollama pull" in str(exc_info.value)

    def test_embedding_model_not_string(self):
        """Test error when embedding_model is not a string."""
        configs = [
            {"embedding_model": 123},
            {"embedding_model": ["model"]},
            {"embedding_model": None}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_embedding_model(config)

            assert "must be a string" in str(exc_info.value)

    def test_embedding_model_empty(self):
        """Test error when embedding_model is empty."""
        configs = [
            {"embedding_model": ""},
            {"embedding_model": "   "}
        ]

        for config in configs:
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_embedding_model(config)

            assert "cannot be empty" in str(exc_info.value)

    def test_embedding_model_invalid_format(self):
        """Test error when model name doesn't match Ollama convention."""
        invalid_models = [
            "MODEL-NAME:latest",  # Uppercase not allowed
            "model name:latest",  # Spaces not allowed
            ":latest",  # Missing model name
            "model:",  # Missing version
            "model::version",  # Double colon
            "model:version:extra",  # Too many colons
            "-model:latest",  # Cannot start with hyphen
            ".model:latest",  # Cannot start with dot
            "_model:latest",  # Cannot start with underscore
        ]

        for model in invalid_models:
            config = {"embedding_model": model}
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_embedding_model(config)

            assert "does not match Ollama naming convention" in str(exc_info.value)


class TestValidateConfig:
    """Test complete configuration validation."""

    def test_validate_complete_valid_config(self):
        """Test validation of a complete valid configuration."""
        config = {
            "chromadb_path": "/absolute/path/to/chromadb",
            "default_max_results": 5,
            "embedding_model": "mxbai-embed-large:latest"
        }

        validate_config(config)  # Should not raise

    def test_validate_config_with_unexpected_fields(self):
        """Test error when config contains unexpected fields."""
        config = {
            "chromadb_path": "/absolute/path/to/chromadb",
            "default_max_results": 5,
            "embedding_model": "mxbai-embed-large:latest",
            "unexpected_field": "value",
            "another_field": 123
        }

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)

        error_msg = str(exc_info.value)
        assert "Unexpected field(s)" in error_msg
        assert "unexpected_field" in error_msg or "another_field" in error_msg
        assert "check for typos" in error_msg.lower()

    def test_validate_config_multiple_errors(self):
        """Test that validation reports the first error encountered."""
        config = {
            "chromadb_path": "relative/path",  # Invalid: relative path
            "default_max_results": 0,  # Invalid: below minimum
            "embedding_model": "INVALID:MODEL"  # Invalid: uppercase
        }

        # Should raise on first validation error (chromadb_path)
        with pytest.raises(ConfigValidationError):
            validate_config(config)


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_results_boundary_values(self):
        """Test boundary values for max_results."""
        # Test minimum valid value
        config_min = {
            "chromadb_path": "/path",
            "default_max_results": 1,
            "embedding_model": "model:latest"
        }
        validate_config(config_min)

        # Test maximum valid value
        config_max = {
            "chromadb_path": "/path",
            "default_max_results": 100,
            "embedding_model": "model:latest"
        }
        validate_config(config_max)

    def test_model_name_without_version(self):
        """Test that model names without version are valid."""
        config = {
            "chromadb_path": "/path",
            "default_max_results": 5,
            "embedding_model": "model-name"
        }
        validate_config(config)

    def test_model_name_with_dots_and_underscores(self):
        """Test model names with dots and underscores."""
        config = {
            "chromadb_path": "/path",
            "default_max_results": 5,
            "embedding_model": "model.name_123:v1.0"
        }
        validate_config(config)

    def test_very_long_absolute_path(self):
        """Test very long absolute paths are accepted."""
        long_path = "/" + "/".join(["very"] * 50 + ["long", "path", "to", "chromadb"])
        config = {
            "chromadb_path": long_path,
            "default_max_results": 5,
            "embedding_model": "model:latest"
        }
        validate_config(config)


class TestConfigIntegration:
    """Integration tests for complete configuration workflow."""

    def test_full_config_load_and_validate(self, tmp_path):
        """Test complete workflow: write config -> load -> validate."""
        config_file = tmp_path / "config.json"
        config_data = {
            "chromadb_path": "/Users/test/chromadb_data",
            "default_max_results": 10,
            "embedding_model": "mxbai-embed-large:latest"
        }

        # Write config file
        config_file.write_text(json.dumps(config_data, indent=2))

        # Load and validate
        loaded_config = load_config(str(config_file))

        # Verify all fields are correct
        assert loaded_config == config_data
        assert isinstance(loaded_config['chromadb_path'], str)
        assert isinstance(loaded_config['default_max_results'], int)
        assert isinstance(loaded_config['embedding_model'], str)

    def test_error_messages_are_helpful(self, tmp_path):
        """Test that error messages include remediation steps."""
        # Test missing file error
        with pytest.raises(ConfigError) as exc_info:
            load_config("/nonexistent/config.json")
        assert "cp config.json.example" in str(exc_info.value)

        # Test relative path error
        config_file = tmp_path / "config.json"
        config_data = {
            "chromadb_path": "relative/path",
            "default_max_results": 5,
            "embedding_model": "model:latest"
        }
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))
        assert "absolute path" in str(exc_info.value)
        assert "pwd" in str(exc_info.value)  # Suggests how to get absolute path


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
