from pathlib import Path

from minerva_kb.commands import run_add, run_remove


def _confirm_yes(prompt=""):
    if "Type YES" in prompt:
        return "YES"
    return "y"


def test_remove_deletes_managed_collection(kb_env, monkeypatch):
    repo = kb_env.create_repo("alpha")
    kb_env.queue_provider()
    run_add(str(repo))

    monkeypatch.setattr("builtins.input", _confirm_yes)
    assert run_remove("alpha") == 0
    assert not (kb_env.app_dir / "alpha-index.json").exists()


def test_remove_reports_unmanaged_collection(kb_env):
    client = kb_env.chroma_client()
    client.get_or_create_collection("orphan")
    assert run_remove("orphan") == 1


def test_remove_handles_missing_chromadb_collection(kb_env, monkeypatch):
    repo = kb_env.create_repo("bravo")
    kb_env.queue_provider()
    run_add(str(repo))
    client = kb_env.chroma_client()
    client.delete_collection("bravo")

    responses = iter(["y", "YES"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))

    assert run_remove("bravo") == 0


def test_remove_stops_running_watcher(kb_env, monkeypatch):
    repo = kb_env.create_repo("charlie")
    kb_env.queue_provider()
    run_add(str(repo))
    kb_env.set_watcher_pid("charlie", 9999)

    monkeypatch.setattr("builtins.input", _confirm_yes)
    assert run_remove("charlie") == 0
    assert not kb_env.running_watchers


def test_remove_cancelled_by_user(kb_env, monkeypatch):
    repo = kb_env.create_repo("delta")
    kb_env.queue_provider()
    run_add(str(repo))
    client = kb_env.chroma_client()
    client.delete_collection("delta")

    responses = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    assert run_remove("delta") == 2
    assert (kb_env.app_dir / "delta-index.json").exists()


def test_remove_requires_exact_confirmation(kb_env, monkeypatch):
    repo = kb_env.create_repo("echo")
    kb_env.queue_provider()
    run_add(str(repo))

    responses = iter(["NO"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
    assert run_remove("echo") == 2
    assert (kb_env.app_dir / "echo-index.json").exists()


def test_remove_handles_permission_error(kb_env, monkeypatch):
    repo = kb_env.create_repo("foxtrot")
    kb_env.queue_provider()
    run_add(str(repo))

    original_unlink = Path.unlink

    def flaky_unlink(path, *args, **kwargs):  # noqa: ARG001
        if path.name.endswith("index.json"):
            raise PermissionError("denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    monkeypatch.setattr("builtins.input", _confirm_yes)
    assert run_remove("foxtrot") == 0
