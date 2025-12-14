import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from minerva_common.provider_setup import (
    build_provider_config,
    prompt_for_models,
    prompt_model_value,
    prompt_provider_choice,
    validate_provider_config,
)


def test_prompt_provider_choice_default():
    with patch("builtins.input", return_value=""):
        provider = prompt_provider_choice()
        assert provider == "openai"


def test_prompt_provider_choice_openai():
    with patch("builtins.input", return_value="1"):
        provider = prompt_provider_choice()
        assert provider == "openai"


def test_prompt_provider_choice_gemini():
    with patch("builtins.input", return_value="2"):
        provider = prompt_provider_choice()
        assert provider == "gemini"


def test_prompt_provider_choice_ollama():
    with patch("builtins.input", return_value="3"):
        provider = prompt_provider_choice()
        assert provider == "ollama"


def test_prompt_provider_choice_lmstudio():
    with patch("builtins.input", return_value="4"):
        provider = prompt_provider_choice()
        assert provider == "lmstudio"


def test_prompt_provider_choice_invalid_then_valid():
    with patch("builtins.input", side_effect=["5", "invalid", "1"]):
        provider = prompt_provider_choice()
        assert provider == "openai"


def test_prompt_model_value_with_input():
    with patch("builtins.input", return_value="my-model"):
        value = prompt_model_value("Model: ", None)
        assert value == "my-model"


def test_prompt_model_value_with_fallback():
    with patch("builtins.input", return_value=""):
        value = prompt_model_value("Model: ", "default-model")
        assert value == "default-model"


def test_prompt_model_value_empty_then_value():
    with patch("builtins.input", side_effect=["", "", "my-model"]):
        value = prompt_model_value("Model: ", None)
        assert value == "my-model"


def test_prompt_for_models_use_defaults():
    with patch("builtins.input", return_value=""):
        models = prompt_for_models("openai")
        assert models["embedding_model"] == "text-embedding-3-small"
        assert models["llm_model"] == "gpt-4o-mini"


def test_prompt_for_models_use_defaults_explicit_yes():
    with patch("builtins.input", return_value="y"):
        models = prompt_for_models("openai")
        assert models["embedding_model"] == "text-embedding-3-small"
        assert models["llm_model"] == "gpt-4o-mini"


def test_prompt_for_models_custom_models():
    with patch("builtins.input", side_effect=["n", "custom-embed", "custom-llm"]):
        models = prompt_for_models("openai")
        assert models["embedding_model"] == "custom-embed"
        assert models["llm_model"] == "custom-llm"


def test_prompt_for_models_ollama():
    with patch("builtins.input", return_value=""):
        models = prompt_for_models("ollama")
        assert models["embedding_model"] == "mxbai-embed-large:latest"
        assert models["llm_model"] == "llama3.1:8b"


def test_prompt_for_models_gemini():
    with patch("builtins.input", return_value=""):
        models = prompt_for_models("gemini")
        assert models["embedding_model"] == "text-embedding-004"
        assert models["llm_model"] == "gemini-1.5-flash"


def test_prompt_for_models_lmstudio_requires_input():
    with patch("builtins.input", side_effect=["", "", "embed-model", "llm-model"]):
        models = prompt_for_models("lmstudio")
        assert models["embedding_model"] == "embed-model"
        assert models["llm_model"] == "llm-model"


def test_prompt_for_models_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider type"):
        prompt_for_models("unknown")


def test_build_provider_config_openai():
    config = build_provider_config("openai", "text-embedding-3-small", "gpt-4o-mini")

    assert config["provider_type"] == "openai"
    assert config["embedding_model"] == "text-embedding-3-small"
    assert config["llm_model"] == "gpt-4o-mini"
    assert config["api_key"] == "${OPENAI_API_KEY}"
    assert "base_url" not in config


def test_build_provider_config_gemini():
    config = build_provider_config("gemini", "text-embedding-004", "gemini-1.5-flash")

    assert config["provider_type"] == "gemini"
    assert config["embedding_model"] == "text-embedding-004"
    assert config["llm_model"] == "gemini-1.5-flash"
    assert config["api_key"] == "${GEMINI_API_KEY}"
    assert "base_url" not in config


def test_build_provider_config_ollama():
    config = build_provider_config("ollama", "mxbai-embed-large:latest", "llama3.1:8b")

    assert config["provider_type"] == "ollama"
    assert config["embedding_model"] == "mxbai-embed-large:latest"
    assert config["llm_model"] == "llama3.1:8b"
    assert "api_key" not in config
    assert config["base_url"] == "http://localhost:11434"


def test_build_provider_config_lmstudio():
    config = build_provider_config("lmstudio", "embed-model", "llm-model")

    assert config["provider_type"] == "lmstudio"
    assert config["embedding_model"] == "embed-model"
    assert config["llm_model"] == "llm-model"
    assert "api_key" not in config
    assert config["base_url"] == "http://localhost:1234/v1"


def test_validate_provider_config_openai_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    config = {
        "provider_type": "openai",
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
    }

    valid, error = validate_provider_config(config)
    assert valid is True
    assert error is None


def test_validate_provider_config_openai_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config = {
        "provider_type": "openai",
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "api_key": "${OPENAI_API_KEY}",
    }

    valid, error = validate_provider_config(config)
    assert valid is False
    assert "OPENAI_API_KEY" in error


def test_validate_provider_config_gemini_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    config = {
        "provider_type": "gemini",
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
        "api_key": "${GEMINI_API_KEY}",
    }

    valid, error = validate_provider_config(config)
    assert valid is True
    assert error is None


def test_validate_provider_config_ollama_success():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        config = {
            "provider_type": "ollama",
            "embedding_model": "mxbai-embed-large:latest",
            "llm_model": "llama3.1:8b",
            "base_url": "http://localhost:11434",
        }

        valid, error = validate_provider_config(config)
        assert valid is True
        assert error is None


def test_validate_provider_config_ollama_connection_failed():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        config = {
            "provider_type": "ollama",
            "embedding_model": "mxbai-embed-large:latest",
            "llm_model": "llama3.1:8b",
            "base_url": "http://localhost:11434",
        }

        valid, error = validate_provider_config(config)
        assert valid is False
        assert "Cannot connect" in error
        assert "Ollama" in error


def test_validate_provider_config_lmstudio_success():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        config = {
            "provider_type": "lmstudio",
            "embedding_model": "model1",
            "llm_model": "model2",
            "base_url": "http://localhost:1234/v1",
        }

        valid, error = validate_provider_config(config)
        assert valid is True
        assert error is None


def test_validate_provider_config_missing_provider_type():
    config = {
        "embedding_model": "model",
        "llm_model": "model",
    }

    valid, error = validate_provider_config(config)
    assert valid is False
    assert "Missing provider_type" in error


def test_validate_provider_config_unknown_provider_type():
    config = {
        "provider_type": "unknown",
        "embedding_model": "model",
        "llm_model": "model",
    }

    valid, error = validate_provider_config(config)
    assert valid is False
    assert "Unknown provider type" in error


def test_validate_provider_config_missing_embedding_model():
    config = {
        "provider_type": "ollama",
        "llm_model": "model",
    }

    valid, error = validate_provider_config(config)
    assert valid is False
    assert "Missing embedding_model" in error


def test_validate_provider_config_missing_llm_model():
    config = {
        "provider_type": "ollama",
        "embedding_model": "model",
    }

    valid, error = validate_provider_config(config)
    assert valid is False
    assert "Missing llm_model" in error
