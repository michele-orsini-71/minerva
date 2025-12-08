import json
import threading

from minerva_kb.commands import run_add
from minerva_kb.utils import config_helpers


def test_add_creates_new_collection(kb_env):
    repo = kb_env.create_repo("alpha")
    kb_env.queue_provider()

    result = run_add(str(repo))
    assert result == 0

    index_path = kb_env.app_dir / "alpha-index.json"
    watcher_path = kb_env.app_dir / "alpha-watcher.json"
    server_path = kb_env.app_dir / "server.json"

    assert index_path.exists()
    assert watcher_path.exists()
    assert server_path.exists()

    config = json.loads(index_path.read_text())
    assert config["collection"]["name"] == "alpha"


def test_add_existing_collection_enters_provider_update_flow(kb_env, monkeypatch):
    repo = kb_env.create_repo("bravo")
    kb_env.queue_provider()
    assert run_add(str(repo)) == 0

    def fake_input(prompt=""):
        return "y"

    monkeypatch.setattr("builtins.input", fake_input)
    kb_env.queue_provider({
        "provider_type": "gemini",
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
    })

    assert run_add(str(repo)) == 0
    updated = json.loads((kb_env.app_dir / "bravo-index.json").read_text())
    assert updated["provider"]["provider_type"] == "gemini"


def test_add_aborts_on_unmanaged_conflict(kb_env, monkeypatch):
    client = kb_env.chroma_client()
    client.get_or_create_collection("charlie")

    def fake_input(prompt=""):
        return "1"

    monkeypatch.setattr("builtins.input", fake_input)
    repo = kb_env.create_repo("charlie")
    kb_env.queue_provider()

    result = run_add(str(repo))
    assert result == 1
    assert not (kb_env.app_dir / "charlie-index.json").exists()


def test_add_wipes_unmanaged_conflict_when_requested(kb_env, monkeypatch):
    client = kb_env.chroma_client()
    client.get_or_create_collection("delta")

    responses = iter(["2"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    repo = kb_env.create_repo("delta")
    kb_env.queue_provider()

    result = run_add(str(repo))
    assert result == 0
    assert (kb_env.app_dir / "delta-index.json").exists()


def test_add_handles_missing_readme_by_prompting(kb_env, monkeypatch):
    repo = kb_env.create_repo("echo", with_readme=False)
    kb_env.queue_provider()

    prompts = []

    def fake_input(prompt=""):
        prompts.append(prompt)
        return "Manual repo description"

    monkeypatch.setattr("builtins.input", fake_input)
    assert run_add(str(repo)) == 0
    assert any("Brief description" in prompt for prompt in prompts)


def test_add_supports_parallel_operations(kb_env):
    results: list[int] = []
    config_helpers.ensure_server_config()

    def worker(repo_name: str):
        repo = kb_env.create_repo(repo_name)
        kb_env.queue_provider()
        results.append(run_add(str(repo)))

    thread_a = threading.Thread(target=worker, args=("parallel-a",))
    thread_b = threading.Thread(target=worker, args=("parallel-b",))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert results.count(0) == 2
