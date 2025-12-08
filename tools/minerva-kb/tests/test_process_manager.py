from types import SimpleNamespace

import pytest

from minerva_kb.utils import process_manager


def test_find_watcher_pid_parses_ps_output(monkeypatch):
    sample = "1234 local-repo-watcher --config /tmp/alpha-watcher.json"

    def fake_run(*args, **kwargs):  # noqa: ARG001
        return SimpleNamespace(stdout=sample, returncode=0)

    monkeypatch.setattr(process_manager.subprocess, "run", fake_run)
    assert (
        process_manager.find_watcher_pid("/tmp/alpha-watcher.json") == 1234
    )


def test_find_watcher_pid_returns_none_when_not_found(monkeypatch):
    def fake_run(*args, **kwargs):  # noqa: ARG001
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(process_manager.subprocess, "run", fake_run)
    assert process_manager.find_watcher_pid("/tmp/missing.json") is None


def test_stop_watcher_terminates_after_sigterm(monkeypatch):
    kills = []

    def fake_kill(pid, sig):  # noqa: ARG001
        kills.append(sig)

    states = iter([True, False])

    monkeypatch.setattr(process_manager.os, "kill", fake_kill)
    monkeypatch.setattr(process_manager, "_process_exists", lambda pid: next(states))
    assert process_manager.stop_watcher(1000) is True
    assert kills[0] == process_manager.signal.SIGTERM


def test_stop_watcher_uses_sigkill_when_needed(monkeypatch):
    kills = []

    def fake_kill(pid, sig):  # noqa: ARG001
        kills.append(sig)

    current_time = {"value": 0.0}

    def fake_monotonic():
        return current_time["value"]

    def fake_sleep(amount):
        current_time["value"] += amount

    monkeypatch.setattr(process_manager.os, "kill", fake_kill)
    monkeypatch.setattr(process_manager, "_process_exists", lambda pid: True)
    monkeypatch.setattr(process_manager.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(process_manager.time, "sleep", fake_sleep)

    result = process_manager.stop_watcher(2000, timeout=0.1)
    assert result is False
    assert process_manager.signal.SIGKILL in kills
