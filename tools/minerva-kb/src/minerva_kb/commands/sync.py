import subprocess
from pathlib import Path

from minerva_kb.constants import MINERVA_KB_APP_DIR
from minerva_kb.utils.config_loader import load_watcher_config

DEFAULT_TIMEOUT = 600


def run_sync(collection_name: str) -> int:
    watcher_path = MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"
    if not watcher_path.exists():
        _display_error(f"Collection '{collection_name}' not found")
        return 1

    try:
        watcher_config = load_watcher_config(collection_name)
    except ValueError as exc:
        _display_error(f"Watcher config is invalid: {exc}")
        return 2

    repo_path = Path(watcher_config["repository_path"]).expanduser()
    extracted_path = Path(watcher_config["extracted_json_path"]).expanduser()
    index_config_path = Path(watcher_config["index_config_path"]).expanduser()

    print(f"Syncing collection '{collection_name}'...")

    if not _run_command(
        ["repository-doc-extractor", str(repo_path), "-o", str(extracted_path)],
        label="Extraction",
    ):
        return 2

    if not _run_command([
        "minerva",
        "index",
        "--config",
        str(index_config_path),
    ], label="Indexing"):
        return 3

    print("✓ Sync completed successfully")
    return 0


def _run_command(command: list[str], *, label: str) -> bool:
    print(f"▶ {label}...")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT,
            check=True,
        )
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        return True
    except FileNotFoundError:
        _display_error(f"{label} command not found: {command[0]}")
        return False
    except subprocess.CalledProcessError as exc:
        _display_error(f"{label} failed (exit {exc.returncode})")
        if exc.stdout:
            print(exc.stdout.strip())
        if exc.stderr:
            print(exc.stderr.strip())
        return False
    except subprocess.TimeoutExpired:
        _display_error(f"{label} timed out after {DEFAULT_TIMEOUT} seconds")
        return False


def _display_error(message: str) -> None:
    print(f"❌ {message}")
