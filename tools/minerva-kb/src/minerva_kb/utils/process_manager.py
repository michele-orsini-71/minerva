import os
import signal
import subprocess
import time
from pathlib import Path


def find_watcher_pid(config_path: Path | str) -> int | None:
    target = str(config_path)
    try:
        result = subprocess.run(
            ["ps", "-ax", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    for line in result.stdout.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if "local-repo-watcher" not in normalized:
            continue
        if target not in normalized:
            continue
        parts = normalized.split(None, 1)
        if not parts:
            continue
        try:
            return int(parts[0])
        except ValueError:
            continue
    return None


def stop_watcher(pid: int, timeout: float = 5.0) -> bool:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False

    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if not _process_exists(pid):
            return True
        time.sleep(0.2)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return not _process_exists(pid)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
