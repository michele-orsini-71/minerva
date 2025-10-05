import importlib
import json
import runpy
from types import SimpleNamespace
from unittest import mock

import builtins
import pytest

import validation
from validation import ValidationError


def make_description(include_required: bool = True) -> str:
    base = "Architecture decision records and deployment playbooks for backend services are curated in this archive. "
    if include_required:
        guidance = "Use this collection when reviewing historical releases and preparing incident retrospectives."
    else:
        guidance = "The archive supports retrospective analysis of releases and incident preparedness without dictating when to query it."
    return base + guidance


def test_validate_collection_name_valid():
    validation.validate_collection_name("valid_name")


def test_validate_collection_name_empty():
    with pytest.raises(ValidationError):
        validation.validate_collection_name("")


def test_validate_collection_name_too_long():
    with pytest.raises(ValidationError):
        validation.validate_collection_name("a" * 64)


def test_validate_collection_name_invalid_pattern():
    with pytest.raises(ValidationError):
        validation.validate_collection_name("invalid name")


def test_validate_description_regex_valid():
    validation.validate_description_regex(make_description(include_required=True), "collection")


def test_validate_description_regex_too_short():
    short_description = "Use this collection when ready"  # < 50 chars
    with pytest.raises(ValidationError):
        validation.validate_description_regex(short_description, "collection")


def test_validate_description_regex_missing_required_phrase():
    description = make_description(include_required=False)
    with pytest.raises(ValidationError):
        validation.validate_description_regex(description, "collection")


def test_validate_description_regex_too_vague():
    description = (
        "Use this collection when general purpose documents data information content documents data"
        " fill the workspace and you need miscellaneous files."
    )
    with pytest.raises(ValidationError):
        validation.validate_description_regex(description, "collection")


def test_validate_description_regex_empty():
    with pytest.raises(ValidationError):
        validation.validate_description_regex("", "collection")


def test_validate_description_regex_too_long():
    long_description = (
        "Use this collection when analyzing comprehensive infrastructure change proposals and rollback procedures. "
        + "deployment patterns and resilience requirements " * 25
    )
    with pytest.raises(ValidationError):
        validation.validate_description_regex(long_description, "collection")


def test_validate_with_ai_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "check_model_availability_or_raise", lambda model: None)
    response = {"score": 8, "reasoning": "clear", "suggestions": ""}
    monkeypatch.setattr(validation, "call_ollama_ai", lambda description, collection_name, model: json.dumps(response))

    score, reasoning, suggestions = validation.validate_with_ai("desc", "collection", model="model")
    assert score == 8
    assert reasoning == "clear"
    assert suggestions == ""


def test_validate_with_ai_model_unavailable(monkeypatch: pytest.MonkeyPatch):
    def raise_missing(_model):
        raise ValidationError("missing")

    monkeypatch.setattr(validation, "check_model_availability_or_raise", raise_missing)
    with pytest.raises(ValidationError):
        validation.validate_with_ai("desc", "collection")


def test_validate_with_ai_invalid_response(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "check_model_availability_or_raise", lambda model: None)
    monkeypatch.setattr(validation, "call_ollama_ai", lambda description, collection_name, model: "not-json")
    with pytest.raises(ValidationError):
        validation.validate_with_ai("desc", "collection")


def test_validate_ai_score_invalid():
    with pytest.raises(ValidationError):
        validation.validate_ai_score(11)


def test_call_ollama_ai_uses_prompt(monkeypatch: pytest.MonkeyPatch):
    calls = {}

    def fake_chat(*, model, messages, options):
        calls["model"] = model
        calls["messages"] = messages
        calls["options"] = options
        return {"message": {"content": " {\"score\": 10}"}}

    monkeypatch.setattr(validation, "ollama_chat", fake_chat)
    result = validation.call_ollama_ai("description", "collection", model="model")
    assert "score" in result
    assert calls["model"] == "model"
    assert any("collection" in msg["content"] for msg in calls["messages"])


def test_check_model_availability_handles_empty_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "ollama_list", lambda: SimpleNamespace(models=[]))
    assert validation.check_model_availability("model") is False


def test_check_model_availability_or_raise(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "check_model_availability", lambda model: False)
    with pytest.raises(ValidationError):
        validation.check_model_availability_or_raise("model")


def test_wrap_generic_ai_error(monkeypatch: pytest.MonkeyPatch):
    error = ValidationError("already handled")
    assert validation.wrap_generic_ai_error(error) is error

    wrapped = validation.wrap_generic_ai_error(RuntimeError("boom"))
    assert isinstance(wrapped, ValidationError)


def test_validate_description_regex_only_outputs(capsys):
    validation.validate_description_regex_only(make_description(include_required=True), "collection")
    captured = capsys.readouterr()
    assert "AI validation was skipped" in captured.out


def test_validate_description_with_ai_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "validate_with_ai", lambda description, collection_name, model: (5, "needs work", "add detail"))
    with pytest.raises(ValidationError) as error_info:
        validation.validate_description_with_ai(make_description(include_required=True), "collection", model="model")

    assert "below threshold" in str(error_info.value)


def test_validate_description_with_ai_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "validate_with_ai", lambda description, collection_name, model: (9, "clear", ""))
    result = validation.validate_description_with_ai(make_description(include_required=True), "collection", model="model")
    assert result["score"] == 9


def test_validate_description_hybrid_skip_ai_runs_real_function(monkeypatch: pytest.MonkeyPatch, capsys):
    result = validation.validate_description_hybrid(make_description(include_required=True), "collection", skip_ai_validation=True)
    captured = capsys.readouterr()
    assert result is None
    assert "Description validated" in captured.out


def test_validate_description_hybrid_with_ai_invokes_real_flow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "validate_with_ai", lambda description, collection_name, model: (8, "clear", ""))
    result = validation.validate_description_hybrid(make_description(include_required=True), "collection", skip_ai_validation=False, model="model")
    assert result["score"] == 8


def test_validation_import_missing_ollama(monkeypatch: pytest.MonkeyPatch):
    module = importlib.import_module("validation")
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ollama" or name.startswith("ollama."):
            raise ImportError("missing ollama")
        return original_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(SystemExit):
            importlib.reload(module)

    importlib.reload(module)


def test_validate_description_hybrid_skip_ai(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "validate_description_regex_only", lambda description, collection_name: None)
    result = validation.validate_description_hybrid("desc", "collection", skip_ai_validation=True)
    assert result is None


def test_validate_description_hybrid_with_ai(monkeypatch: pytest.MonkeyPatch):
    expected = {"score": 9}
    monkeypatch.setattr(validation, "validate_description_with_ai", lambda description, collection_name, model: expected)
    result = validation.validate_description_hybrid("desc", "collection", skip_ai_validation=False)
    assert result is expected


def test_extract_models_list_and_name():
    models_obj = SimpleNamespace(models=[SimpleNamespace(model='model-a:latest')])
    assert validation.extract_models_list(models_obj) == models_obj.models
    assert validation.extract_models_list({"models": ["model-b"]}) == ["model-b"]
    assert validation.extract_models_list(42) is None
    assert validation.extract_model_name(SimpleNamespace(model='model-c')) == "model-c"
    assert validation.extract_model_name({"name": "model-d"}) == "model-d"
    assert validation.extract_model_name({}) is None


def test_is_model_match():
    assert validation.is_model_match("mxbai-embed-large", "mxbai-embed-large:latest")
    assert validation.is_model_match("model:latest", "model")
    assert not validation.is_model_match("foo", "bar")


def test_check_model_availability(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(validation, "ollama_list", lambda: SimpleNamespace(models=[SimpleNamespace(model="test:1.0")]))
    assert validation.check_model_availability("test") is True


def test_check_model_availability_handles_exception(monkeypatch: pytest.MonkeyPatch):
    def raise_error():
        raise RuntimeError("boom")

    monkeypatch.setattr(validation, "ollama_list", lambda: raise_error())
    assert validation.check_model_availability("test") is False


def test_validation_main_block(capsys):
    # Ensure running the module as __main__ does not raise
    runpy.run_module("validation", run_name="__main__")
    captured = capsys.readouterr()
    assert "Testing validation.py module" in captured.out
