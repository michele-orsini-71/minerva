from minerva_kb.commands import run_add, run_watch
from minerva_kb.commands import watch as watch_cmd


def test_watch_interactive_selection(kb_env, monkeypatch):
    repo = kb_env.create_repo("alpha")
    kb_env.queue_provider()
    run_add(str(repo))

    inputs = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert run_watch(None) == 0


def test_watch_reports_existing_process(kb_env):
    repo = kb_env.create_repo("bravo")
    kb_env.queue_provider()
    run_add(str(repo))
    kb_env.set_watcher_pid("bravo", 9001)

    assert run_watch("bravo") == 2


def test_watch_reports_missing_binary(kb_env):
    repo = kb_env.create_repo("charlie")
    kb_env.queue_provider()
    run_add(str(repo))
    kb_env.subprocess_runner.watcher_available = False

    assert run_watch("charlie") == 2


def test_watch_handles_keyboard_interrupt(kb_env, monkeypatch):
    repo = kb_env.create_repo("delta")
    kb_env.queue_provider()
    run_add(str(repo))

    class InterruptWatcher:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

        def wait(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(
        watch_cmd.subprocess,
        "Popen",
        lambda *args, **kwargs: InterruptWatcher(),
    )

    assert run_watch("delta") == 130
