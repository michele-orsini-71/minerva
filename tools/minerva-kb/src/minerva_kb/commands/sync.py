import subprocess
from pathlib import Path

from minerva_kb.constants import DEFAULT_SUBPROCESS_TIMEOUT, MINERVA_KB_APP_DIR
from minerva_kb.utils.collection_naming import validate_collection_name_format
from minerva_kb.utils.config_helpers import list_managed_collections
from minerva_kb.utils.config_loader import load_watcher_config
from minerva_kb.utils.display import display_collection_not_found, display_error


def run_sync(collection_name: str) -> int:
    try:
        return _execute_sync(collection_name)
    except KeyboardInterrupt:
        print("Sync cancelled by user")
        return 130


def _execute_sync(collection_name: str) -> int:
    if not _validate_collection_argument(collection_name):
        return 2
    watcher_path = MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"
    if not watcher_path.exists():
        display_collection_not_found(collection_name, list_managed_collections())
        return 1

    try:
        watcher_config = load_watcher_config(collection_name)
    except ValueError as exc:
        display_error(f"Watcher config is invalid: {exc}")
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
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
            check=True,
        )
        _print_output(result.stdout, result.stderr)
        return True
    except FileNotFoundError:
        display_error(f"{label} command not found: {command[0]}")
        return False
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or exc.stdout or "").strip()
        summary = output.splitlines()[-1] if output else f"exit {exc.returncode}"
        display_error(f"{label} failed: {summary}")
        _print_output(exc.stdout, exc.stderr)
        return False
    except subprocess.TimeoutExpired:
        display_error(f"{label} timed out after {DEFAULT_SUBPROCESS_TIMEOUT} seconds")
        return False


def _print_output(stdout: str | None, stderr: str | None) -> None:
    if stdout:
        print(stdout.strip())
    if stderr:
        print(stderr.strip())


def _validate_collection_argument(collection_name: str) -> bool:
    try:
        validate_collection_name_format(collection_name)
        return True
    except ValueError as exc:
        display_error(str(exc))
        return False
