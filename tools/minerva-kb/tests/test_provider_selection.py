import os

from minerva_kb.utils import provider_selection


def test_interactive_select_provider_primes_env_from_keychain(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    secrets = {"OPENAI_API_KEY": "sk-openai"}
    reads = []

    def fake_read(key_name):
        reads.append(key_name)
        return secrets.get(key_name)

    def fake_shared_selector():
        assert os.environ["OPENAI_API_KEY"] == "sk-openai"
        return {"provider_type": "openai"}

    monkeypatch.setattr(provider_selection, "_read_keychain_secret", fake_read)
    monkeypatch.setattr(provider_selection, "_shared_select_provider", fake_shared_selector)

    result = provider_selection.interactive_select_provider()

    assert result == {"provider_type": "openai"}
    assert "OPENAI_API_KEY" in reads


def test_interactive_select_provider_preserves_existing_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-existing")

    calls = {"shared": 0}
    requested = []

    def fake_read(key_name):
        requested.append(key_name)
        return None

    def fake_shared_selector():
        calls["shared"] += 1
        assert os.environ["OPENAI_API_KEY"] == "sk-existing"
        return {"provider_type": "openai"}

    monkeypatch.setattr(provider_selection, "_read_keychain_secret", fake_read)
    monkeypatch.setattr(provider_selection, "_shared_select_provider", fake_shared_selector)

    result = provider_selection.interactive_select_provider()

    assert result["provider_type"] == "openai"
    assert calls["shared"] == 1
    assert "OPENAI_API_KEY" not in requested
