from minerva_kb.commands import run_add, run_status


def test_status_displays_collection_details(kb_env, capsys):
    repo = kb_env.create_repo("alpha")
    kb_env.queue_provider()
    run_add(str(repo))
    collection_name = kb_env.collection_name(repo)

    assert run_status(collection_name) == 0
    output = capsys.readouterr().out
    assert collection_name in output
    assert "Repository" in output


def test_status_handles_missing_collection(kb_env):
    assert run_status("missing") == 1


def test_status_detects_missing_chromadb_collection(kb_env):
    repo = kb_env.create_repo("bravo")
    kb_env.queue_provider()
    run_add(str(repo))
    collection_name = kb_env.collection_name(repo)
    client = kb_env.chroma_client()
    client.delete_collection(collection_name)

    assert run_status(collection_name) == 2


def test_status_reports_stopped_watcher(kb_env, capsys):
    repo = kb_env.create_repo("charlie")
    kb_env.queue_provider()
    run_add(str(repo))
    collection_name = kb_env.collection_name(repo)

    assert run_status(collection_name) == 0
    output = capsys.readouterr().out
    assert "Watcher: ⚠ Not running" in output
