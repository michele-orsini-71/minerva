import subprocess
from pathlib import Path

from minerva_kb.constants import MINERVA_KB_APP_DIR
from minerva_kb.utils.collection_naming import validate_collection_name_format
from minerva_kb.utils.config_helpers import list_managed_collections
from minerva_kb.utils.config_loader import load_watcher_config
from minerva_kb.utils.display import display_collection_not_found, display_error
from minerva_kb.utils.process_manager import find_watcher_pid

DEFAULT_TIMEOUT = 600


def run_watch(collection_name: str | None) -> int:
    if collection_name is None:
        collection_name = _interactive_select_collection()
        if collection_name is None:
            return 1
    elif not _validate_collection_argument(collection_name):
        return 2
    else:
        collection_name = collection_name.strip()

    watcher_path = MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"
    if not watcher_path.exists():
        display_collection_not_found(collection_name, list_managed_collections())
        return 1

    pid = find_watcher_pid(watcher_path)
    if pid is not None:
        print(f"⚠️ Watcher already running for '{collection_name}' (PID {pid})")
        print(f"To stop the watcher: kill {pid}")
        return 2

    config = _load_watcher_config(collection_name)
    if config is None:
        return 2

    watcher_bin = _ensure_watcher_binary()
    if watcher_bin is None:
        return 2

    print(f"▶️ Starting watcher for '{collection_name}'... Press Ctrl+C to stop.")
    return _run_watcher_process(watcher_bin, watcher_path)


def _interactive_select_collection() -> str | None:
    configs = sorted(MINERVA_KB_APP_DIR.glob("*-watcher.json"))
    if not configs:
        display_error("No collections available")
        return None

    print("Select a collection to watch:")
    for idx, path in enumerate(configs, start=1):
        print(f"  {idx}) {path.stem.replace('-watcher', '')}")

    while True:
        choice = input("Choice [number]: ").strip()
        if not choice:
            return None
        try:
            value = int(choice)
        except ValueError:
            print("❌ Invalid choice")
            continue
        if 1 <= value <= len(configs):
            selected = configs[value - 1].stem.replace("-watcher", "")
            if _validate_collection_argument(selected):
                return selected
            return None
        print("❌ Choice out of range")


def _load_watcher_config(collection_name: str) -> dict | None:
    try:
        return load_watcher_config(collection_name)
    except ValueError as exc:
        display_error(f"Watcher config invalid: {exc}")
        return None


def _ensure_watcher_binary() -> str | None:
    result = subprocess.run(
        ["which", "local-repo-watcher"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        display_error("local-repo-watcher not found in PATH")
        print("Install via: pipx install tools/local-repo-watcher")
        return None
    return result.stdout.strip()


def _run_watcher_process(watcher_bin: str, config_path: Path) -> int:
    try:
        process = subprocess.Popen(
            [watcher_bin, "--config", str(config_path)],
        )
        process.wait()
        return process.returncode or 0
    except KeyboardInterrupt:
        print("Watcher stopped by user")
        return 130
    except FileNotFoundError:
        display_error("Watcher binary not found")
        return 2


def _validate_collection_argument(collection_name: str) -> bool:
    try:
        validate_collection_name_format(collection_name)
        return True
    except ValueError as exc:
        display_error(str(exc))
        return False
