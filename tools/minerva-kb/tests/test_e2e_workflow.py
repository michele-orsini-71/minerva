from minerva_kb.commands import (
    run_add,
    run_list,
    run_remove,
    run_status,
    run_sync,
    run_watch,
)


def test_end_to_end_workflow(kb_env, monkeypatch):
    repo = kb_env.create_repo("omega")
    kb_env.queue_provider()
    collection_name = kb_env.collection_name(repo)

    assert run_add(str(repo)) == 0
    assert run_list("table") == 0
    assert run_status(collection_name) == 0
    assert run_sync(collection_name) == 0
    assert run_watch(collection_name) == 0

    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")
    assert run_remove(collection_name) == 0

    assert not (kb_env.app_dir / f"{collection_name}-index.json").exists()


def test_multi_collection_workflow(kb_env, monkeypatch, capsys):
    repo_a = kb_env.create_repo("alpha")
    repo_b = kb_env.create_repo("beta")
    collection_a = kb_env.collection_name(repo_a)
    collection_b = kb_env.collection_name(repo_b)
    kb_env.queue_provider()
    run_add(str(repo_a))
    kb_env.queue_provider()
    run_add(str(repo_b))

    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert collection_a in output and collection_b in output

    confirmations = iter(["YES"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(confirmations))
    assert run_remove(collection_a) == 0
    confirmations = iter(["YES"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(confirmations))
    assert run_remove(collection_b) == 0


def test_provider_update_workflow(kb_env, monkeypatch, capsys):
    repo = kb_env.create_repo("gamma")
    kb_env.queue_provider()
    run_add(str(repo))
    collection_name = kb_env.collection_name(repo)

    prompts = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(prompts))
    kb_env.queue_provider({
        "provider_type": "gemini",
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
        "api_key": "${GEMINI_API_KEY}",
    })
    run_add(str(repo))

    assert run_status(collection_name) == 0
    output = capsys.readouterr().out
    assert "Gemini" in output
