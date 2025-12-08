from types import SimpleNamespace

import pytest

from minerva_kb.utils import provider_selection


def test_check_api_key_exists_true(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(provider_selection.subprocess, "run", fake_run)
    assert provider_selection.check_api_key_exists("openai") is True


def test_check_api_key_exists_false(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(provider_selection.subprocess, "run", fake_run)
    assert provider_selection.check_api_key_exists("openai") is False


def test_prompt_for_models_accepts_defaults(monkeypatch):
    inputs = iter([""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    result = provider_selection.prompt_for_models("openai")
    assert result == {
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
    }


def test_prompt_for_models_requires_explicit_values(monkeypatch):
    inputs = iter(["", "embed-model", "", "llm-model"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    result = provider_selection.prompt_for_models("lmstudio")
    assert result == {
        "embedding_model": "embed-model",
        "llm_model": "llm-model",
    }


class FakeResponse:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_validate_local_provider_success(monkeypatch):
    monkeypatch.setattr(
        provider_selection.urllib.request,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(200),
    )

    assert provider_selection.validate_local_provider("ollama") is True


def test_validate_local_provider_failure(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise provider_selection.urllib.error.URLError("down")

    monkeypatch.setattr(provider_selection.urllib.request, "urlopen", fake_urlopen)

    assert provider_selection.validate_local_provider("ollama") is False


def test_validate_api_key_success(monkeypatch):
    monkeypatch.setattr(provider_selection, "_read_api_key", lambda _: "secret")
    called = {}

    def fake_validate(provider_type, api_key):
        called["value"] = (provider_type, api_key)

    monkeypatch.setattr(provider_selection, "_perform_remote_validation", fake_validate)

    assert provider_selection.validate_api_key("openai") is True
    assert called["value"] == ("openai", "secret")


def test_validate_api_key_failure(monkeypatch):
    monkeypatch.setattr(provider_selection, "_read_api_key", lambda _: "secret")

    def fake_validate(provider_type, api_key):  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(provider_selection, "_perform_remote_validation", fake_validate)
    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    assert provider_selection.validate_api_key("openai") is False
