import json

from minerva_kb.commands import run_add, run_list


def test_list_shows_managed_collections(kb_env, capsys):
    repo = kb_env.create_repo("alpha")
    kb_env.queue_provider()
    run_add(str(repo))
    kb_env.set_watcher_pid("alpha", 4321)

    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert "Collections (1)" in output
    assert "alpha" in output
    assert "PID 4321" in output


def test_list_outputs_json_format(kb_env, capsys):
    repo = kb_env.create_repo("bravo")
    kb_env.queue_provider()
    run_add(str(repo))
    capsys.readouterr()
    assert run_list("json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["managed_collections"][0]["name"] == "bravo"


def test_list_includes_unmanaged_collections(kb_env, capsys):
    client = kb_env.chroma_client()
    client.get_or_create_collection("orphan")

    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert "Unmanaged collections" in output
    assert "orphan" in output


def test_list_flags_broken_collections(kb_env, capsys):
    repo = kb_env.create_repo("broken")
    kb_env.queue_provider()
    run_add(str(repo))
    client = kb_env.chroma_client()
    client.delete_collection("broken")

    capsys.readouterr()
    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert "⚠ Not indexed" in output


def test_list_shows_stopped_watcher(kb_env, capsys):
    repo = kb_env.create_repo("idle")
    kb_env.queue_provider()
    run_add(str(repo))

    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert "⚠ Not running" in output


def test_list_handles_chromadb_error(kb_env, capsys):
    def boom():
        raise RuntimeError("boom")

    kb_env.fake_client.list_collections = boom
    assert run_list("table") == 0
    output = capsys.readouterr().out
    assert "Collections" in output
