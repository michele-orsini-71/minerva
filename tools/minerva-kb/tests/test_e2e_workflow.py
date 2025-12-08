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

    assert run_add(str(repo)) == 0
    assert run_list("table") == 0
    assert run_status("omega") == 0
    assert run_sync("omega") == 0
    assert run_watch("omega") == 0

    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")
    assert run_remove("omega") == 0

    assert not (kb_env.app_dir / "omega-index.json").exists()


def test_multi_collection_workflow(kb_env, monkeypatch, capsys):
    repo_a = kb_env.create_repo("alpha")
    repo_b = kb_env.create_repo("beta")
    kb_env.queue_provider()
    run_add(str(repo_a))
    kb_env.queue_provider()
    run_add(str(repo_b))

    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert "alpha" in output and "beta" in output

    confirmations = iter(["YES"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(confirmations))
    assert run_remove("alpha") == 0
    confirmations = iter(["YES"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(confirmations))
    assert run_remove("beta") == 0


def test_provider_update_workflow(kb_env, monkeypatch, capsys):
    repo = kb_env.create_repo("gamma")
    kb_env.queue_provider()
    run_add(str(repo))

    prompts = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(prompts))
    kb_env.queue_provider({
        "provider_type": "gemini",
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
    })
    run_add(str(repo))

    assert run_status("gamma") == 0
    output = capsys.readouterr().out
    assert "Gemini" in output
