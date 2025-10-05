from types import SimpleNamespace

import pytest

import config_validator
from config_loader import ConfigError
from validation import ValidationError


def build_config(skip_ai: bool = False):
    return SimpleNamespace(
        collection_name="collection",
        description="Use this collection when reviewing backend releases and retrospectives for deployments.",
        chromadb_path="/tmp/chroma",
        json_file="notes.json",
        chunk_size=1200,
        force_recreate=False,
        skip_ai_validation=skip_ai,
    )


def test_load_and_validate_config_skip_ai(monkeypatch: pytest.MonkeyPatch, capsys):
    config = build_config(skip_ai=True)
    monkeypatch.setattr(config_validator, "load_collection_config", lambda path: config)
    monkeypatch.setattr(config_validator, "validate_collection_name", lambda name: None)
    monkeypatch.setattr(config_validator, "validate_description_regex_only", lambda description, collection_name: None)

    result = config_validator.load_and_validate_config("config.json")

    assert result is config
    captured = capsys.readouterr()
    assert "AI validation was skipped" in captured.out


def test_load_and_validate_config_with_ai(monkeypatch: pytest.MonkeyPatch, capsys):
    config = build_config(skip_ai=False)
    monkeypatch.setattr(config_validator, "load_collection_config", lambda path: config)
    monkeypatch.setattr(config_validator, "validate_collection_name", lambda name: None)
    monkeypatch.setattr(config_validator, "validate_description_with_ai", lambda description, collection_name: {"score": 9, "reasoning": "ok", "suggestions": ""})

    result = config_validator.load_and_validate_config("config.json")

    assert result is config
    captured = capsys.readouterr()
    assert "AI Quality Score" in captured.out


def test_load_and_validate_config_config_error(monkeypatch: pytest.MonkeyPatch):
    def raise_config_error(path):
        raise ConfigError("bad config")

    monkeypatch.setattr(config_validator, "load_collection_config", raise_config_error)

    with pytest.raises(SystemExit) as exit_info:
        config_validator.load_and_validate_config("config.json")

    assert exit_info.value.code == 1


def test_load_and_validate_config_validation_error(monkeypatch: pytest.MonkeyPatch):
    config = build_config(skip_ai=False)
    monkeypatch.setattr(config_validator, "load_collection_config", lambda path: config)
    monkeypatch.setattr(config_validator, "validate_collection_name", lambda name: None)

    def raise_validation(description, collection_name):
        raise ValidationError("invalid description")

    monkeypatch.setattr(config_validator, "validate_description_with_ai", raise_validation)

    with pytest.raises(SystemExit) as exit_info:
        config_validator.load_and_validate_config("config.json")

    assert exit_info.value.code == 1
