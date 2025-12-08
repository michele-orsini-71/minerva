import subprocess
from pathlib import Path

from chromadb import PersistentClient

from minerva_kb.constants import CHROMADB_DIR, MINERVA_KB_APP_DIR
from minerva_kb.utils.collection_naming import validate_collection_name_format
from minerva_kb.utils.config_loader import load_index_config, load_watcher_config
from minerva_kb.utils.display import display_error
from minerva_kb.utils.process_manager import find_watcher_pid, stop_watcher

DEFAULT_TIMEOUT = 600


def run_remove(collection_name: str) -> int:
    if not _validate_collection_argument(collection_name):
        return 2
    try:
        return _execute_remove(collection_name)
    except KeyboardInterrupt:
        print("Deletion cancelled")
        return 130


def _execute_remove(collection_name: str) -> int:
    watcher_path = MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"
    index_path = MINERVA_KB_APP_DIR / f"{collection_name}-index.json"
    extracted_path = MINERVA_KB_APP_DIR / f"{collection_name}-extracted.json"

    managed = watcher_path.exists() or index_path.exists()
    if not managed:
        display_error(f"Collection '{collection_name}' is not managed by minerva-kb")
        print("Collection exists in ChromaDB but has no config files.")
        print("Remove manually with:")
        print(f"  minerva remove {CHROMADB_DIR} {collection_name}")
        return 1

    watcher_config = _safe_load(load_watcher_config, collection_name)
    index_config = _safe_load(load_index_config, collection_name)
    chroma_state = _get_chroma_state(collection_name)

    _print_summary(collection_name, watcher_config, index_config, chroma_state)

    if not chroma_state.get("exists", False):
        if not _prompt_yes_no("ChromaDB collection not found. Delete configs anyway? [y/N]: "):
            print("Deletion cancelled")
            return 2

    _print_deletion_plan(collection_name, chroma_state.get("exists", False), watcher_path, index_path, extracted_path)

    if not _confirm_deletion(collection_name):
        print("Deletion cancelled (type YES to confirm)")
        return 2

    pid = find_watcher_pid(watcher_path)
    if pid is not None:
        print(f"Stopping watcher (PID {pid})...")
        if stop_watcher(pid):
            print("Watcher stopped")
        else:
            print("Watcher may still be running; continuing")

    _delete_file(watcher_path)
    _delete_file(index_path)
    _delete_file(extracted_path)

    if chroma_state.get("exists", False):
        if not _remove_chroma_collection(collection_name):
            return 3

    _print_api_key_hint(index_config)
    print(f"✓ Collection '{collection_name}' removed")
    return 0


def _safe_load(loader, collection_name: str) -> dict | None:
    try:
        return loader(collection_name)
    except ValueError as exc:
        display_error(str(exc))
        return None


def _get_chroma_state(collection_name: str) -> dict:
    if not CHROMADB_DIR.exists():
        return {"exists": False, "error": "ChromaDB directory missing"}
    try:
        client = PersistentClient(path=str(CHROMADB_DIR))
        collection = client.get_collection(collection_name)
        return {"exists": True, "count": collection.count()}
    except Exception as exc:  # noqa: BLE001
        return {"exists": False, "error": str(exc)}


def _print_summary(collection_name: str, watcher_config: dict | None, index_config: dict | None, chroma_state: dict) -> None:
    print(f"Collection: {collection_name}")
    if watcher_config:
        print(f"  Repository: {watcher_config.get('repository_path', 'unknown')}")
    if index_config:
        provider = index_config.get("provider", {})
        print(
            "  Provider: {0} ({1} + {2})".format(
                provider.get("provider_type", "unknown"),
                provider.get("llm_model", "unknown"),
                provider.get("embedding_model", "unknown"),
            )
        )
    if chroma_state.get("exists"):
        count = chroma_state.get("count")
        formatted = f"{count:,}" if isinstance(count, int) else "unknown"
        print(f"  ChromaDB: ✓ Present ({formatted} chunks)")
    else:
        print("  ChromaDB: ⚠ Not found")
        if chroma_state.get("error"):
            print(f"    {chroma_state['error']}")


def _print_deletion_plan(collection_name: str, chroma_exists: bool, watcher_path: Path, index_path: Path, extracted_path: Path) -> None:
    print()
    print("This will delete:")
    if chroma_exists:
        print(f"  • ChromaDB collection '{collection_name}'")
    print(f"  • {watcher_path}")
    print(f"  • {index_path}")
    print(f"  • {extracted_path}")
    print("Repository files will NOT be affected.")


def _confirm_deletion(collection_name: str) -> bool:
    prompt = f"Type YES to confirm deletion of '{collection_name}': "
    response = input(prompt).strip()
    return response == "YES"


def _prompt_yes_no(prompt: str) -> bool:
    return input(prompt).strip().lower() in {"y", "yes"}


def _delete_file(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
            print(f"Deleted {path}")
        except OSError as exc:
            display_error(f"Failed to delete {path}: {exc}")


def _remove_chroma_collection(collection_name: str) -> bool:
    confirmation = f"YES\n{collection_name}\n"
    try:
        subprocess.run(
            ["minerva", "remove", str(CHROMADB_DIR), collection_name],
            input=confirmation,
            text=True,
            check=True,
            timeout=DEFAULT_TIMEOUT,
        )
        return True
    except subprocess.CalledProcessError as exc:
        display_error(f"Failed to remove Chroma collection (exit {exc.returncode})")
        return False
    except FileNotFoundError:
        display_error("'minerva' command not found")
        return False
    except subprocess.TimeoutExpired:
        display_error("Chroma removal timed out")
        return False


def _print_api_key_hint(index_config: dict | None) -> None:
    if not index_config:
        return
    provider = index_config.get("provider", {})
    key_ref = provider.get("api_key")
    if not key_ref:
        return
    key_name = key_ref.strip()
    if key_name.startswith("${") and key_name.endswith("}"):
        key_name = key_name[2:-1]
    print()
    print("API key remains in keychain.")
    print(f"To remove: minerva keychain delete {key_name}")


def _validate_collection_argument(collection_name: str) -> bool:
    try:
        validate_collection_name_format(collection_name)
        return True
    except ValueError as exc:
        display_error(str(exc))
        return False
