import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from github_webhook_orchestrator.validation import (
    validate_prerequisites,
    _validate_required_tools,
    _validate_required_env_vars,
    _extract_env_vars_from_string,
    _extract_env_vars_from_index_config
)
from github_webhook_orchestrator.config import WebhookConfig, RepositoryConfig


class TestExtractEnvVarsFromString:
    def test_single_env_var(self):
        result = _extract_env_vars_from_string("${API_KEY}")
        assert result == {"API_KEY"}

    def test_multiple_env_vars(self):
        result = _extract_env_vars_from_string("${VAR1} and ${VAR2}")
        assert result == {"VAR1", "VAR2"}

    def test_no_env_vars(self):
        result = _extract_env_vars_from_string("plain text")
        assert result == set()

    def test_env_var_in_middle(self):
        result = _extract_env_vars_from_string("prefix ${MY_VAR} suffix")
        assert result == {"MY_VAR"}

    def test_duplicate_env_vars(self):
        result = _extract_env_vars_from_string("${VAR} and ${VAR}")
        assert result == {"VAR"}

    def test_empty_string(self):
        result = _extract_env_vars_from_string("")
        assert result == set()


class TestExtractEnvVarsFromIndexConfig:
    def test_extract_from_provider_config(self, tmp_path):
        config_file = tmp_path / "index.json"
        config_data = {
            "chromadb_path": "/path/to/chromadb",
            "collection": {
                "name": "test",
                "json_file": "/path/to/notes.json"
            },
            "provider": {
                "provider_type": "openai",
                "api_key": "${OPENAI_API_KEY}",
                "embedding_model": "text-embedding-3-small"
            }
        }
        config_file.write_text(json.dumps(config_data))

        result = _extract_env_vars_from_index_config(str(config_file))
        assert "OPENAI_API_KEY" in result

    def test_extract_multiple_env_vars(self, tmp_path):
        config_file = tmp_path / "index.json"
        config_data = {
            "chromadb_path": "${CHROMA_PATH}",
            "provider": {
                "api_key": "${API_KEY}",
                "base_url": "${BASE_URL}"
            }
        }
        config_file.write_text(json.dumps(config_data))

        result = _extract_env_vars_from_index_config(str(config_file))
        assert result == {"CHROMA_PATH", "API_KEY", "BASE_URL"}

    def test_no_env_vars_in_config(self, tmp_path):
        config_file = tmp_path / "index.json"
        config_data = {
            "chromadb_path": "/path/to/chromadb",
            "provider": {
                "api_key": "hardcoded-key"
            }
        }
        config_file.write_text(json.dumps(config_data))

        result = _extract_env_vars_from_index_config(str(config_file))
        assert result == set()

    def test_nested_env_vars(self, tmp_path):
        config_file = tmp_path / "index.json"
        config_data = {
            "level1": {
                "level2": {
                    "level3": "${DEEP_VAR}"
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        result = _extract_env_vars_from_index_config(str(config_file))
        assert "DEEP_VAR" in result

    def test_env_vars_in_lists(self, tmp_path):
        config_file = tmp_path / "index.json"
        config_data = {
            "items": ["${VAR1}", "plain", "${VAR2}"]
        }
        config_file.write_text(json.dumps(config_data))

        result = _extract_env_vars_from_index_config(str(config_file))
        assert result == {"VAR1", "VAR2"}


class TestValidateRequiredTools:
    @patch('shutil.which')
    def test_all_tools_available(self, mock_which):
        mock_which.return_value = '/usr/bin/tool'
        _validate_required_tools()

    @patch('shutil.which')
    def test_missing_git(self, mock_which):
        def which_side_effect(tool):
            return None if tool == 'git' else '/usr/bin/tool'
        mock_which.side_effect = which_side_effect

        with pytest.raises(RuntimeError) as exc_info:
            _validate_required_tools()
        assert 'git' in str(exc_info.value)

    @patch('shutil.which')
    def test_missing_repository_doc_extractor(self, mock_which):
        def which_side_effect(tool):
            return None if tool == 'repository-doc-extractor' else '/usr/bin/tool'
        mock_which.side_effect = which_side_effect

        with pytest.raises(RuntimeError) as exc_info:
            _validate_required_tools()
        assert 'repository-doc-extractor' in str(exc_info.value)

    @patch('shutil.which')
    def test_missing_minerva(self, mock_which):
        def which_side_effect(tool):
            return None if tool == 'minerva' else '/usr/bin/tool'
        mock_which.side_effect = which_side_effect

        with pytest.raises(RuntimeError) as exc_info:
            _validate_required_tools()
        assert 'minerva' in str(exc_info.value)

    @patch('shutil.which')
    def test_multiple_missing_tools(self, mock_which):
        mock_which.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            _validate_required_tools()
        error_msg = str(exc_info.value)
        assert 'git' in error_msg
        assert 'repository-doc-extractor' in error_msg
        assert 'minerva' in error_msg


class TestValidateRequiredEnvVars:
    def test_all_env_vars_set(self, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({
            "provider": {"api_key": "${OPENAI_API_KEY}"}
        }))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="${WEBHOOK_SECRET}",
            github_token="${GITHUB_TOKEN}",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with patch.dict(os.environ, {
            'WEBHOOK_SECRET': 'secret',
            'GITHUB_TOKEN': 'token',
            'OPENAI_API_KEY': 'key'
        }):
            _validate_required_env_vars(config)

    def test_missing_webhook_secret(self, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({}))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="${WEBHOOK_SECRET}",
            github_token="token",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                _validate_required_env_vars(config)
            assert 'WEBHOOK_SECRET' in str(exc_info.value)

    def test_missing_github_token(self, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({}))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="secret",
            github_token="${GITHUB_TOKEN}",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                _validate_required_env_vars(config)
            assert 'GITHUB_TOKEN' in str(exc_info.value)

    def test_missing_provider_api_key(self, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({
            "provider": {"api_key": "${OPENAI_API_KEY}"}
        }))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="secret",
            github_token="token",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                _validate_required_env_vars(config)
            assert 'OPENAI_API_KEY' in str(exc_info.value)

    def test_multiple_missing_env_vars(self, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({
            "provider": {"api_key": "${OPENAI_API_KEY}"}
        }))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="${WEBHOOK_SECRET}",
            github_token="${GITHUB_TOKEN}",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                _validate_required_env_vars(config)
            error_msg = str(exc_info.value)
            assert 'WEBHOOK_SECRET' in error_msg
            assert 'GITHUB_TOKEN' in error_msg
            assert 'OPENAI_API_KEY' in error_msg

    def test_hardcoded_values_no_env_vars(self, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({
            "provider": {"api_key": "hardcoded-key"}
        }))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="hardcoded-secret",
            github_token="hardcoded-token",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with patch.dict(os.environ, {}, clear=True):
            _validate_required_env_vars(config)


class TestValidatePrerequisites:
    @patch('github_webhook_orchestrator.validation._validate_required_tools')
    @patch('github_webhook_orchestrator.validation._validate_required_env_vars')
    def test_all_validations_pass(self, mock_env_vars, mock_tools, tmp_path):
        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({}))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="secret",
            github_token="token",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        validate_prerequisites(config)
        mock_tools.assert_called_once()
        mock_env_vars.assert_called_once_with(config)

    @patch('github_webhook_orchestrator.validation._validate_required_tools')
    def test_tools_validation_fails(self, mock_tools, tmp_path):
        mock_tools.side_effect = RuntimeError("Missing tools")

        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({}))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="secret",
            github_token="token",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with pytest.raises(RuntimeError) as exc_info:
            validate_prerequisites(config)
        assert "Missing tools" in str(exc_info.value)

    @patch('github_webhook_orchestrator.validation._validate_required_tools')
    @patch('github_webhook_orchestrator.validation._validate_required_env_vars')
    def test_env_vars_validation_fails(self, mock_env_vars, mock_tools, tmp_path):
        mock_env_vars.side_effect = RuntimeError("Missing env vars")

        index_config = tmp_path / "index.json"
        index_config.write_text(json.dumps({}))

        repo = RepositoryConfig(
            name="test",
            github_url="https://github.com/test/repo",
            local_path=str(tmp_path),
            index_config=str(index_config)
        )

        config = WebhookConfig(
            webhook_secret="secret",
            github_token="token",
            repositories=[repo],
            log_file="/tmp/test.log"
        )

        with pytest.raises(RuntimeError) as exc_info:
            validate_prerequisites(config)
        assert "Missing env vars" in str(exc_info.value)
