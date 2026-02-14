import subprocess
from pathlib import Path

from chromadb import PersistentClient

from minerva_common.collision import check_collection_exists
from minerva_kb.constants import (
    CHROMADB_DIR,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_SUBPROCESS_TIMEOUT,
    MINERVA_KB_APP_DIR,
    PROVIDER_DISPLAY_NAMES,
)
from minerva_kb.utils.collection_naming import sanitize_collection_name
from minerva_kb.utils.config_helpers import ensure_server_config
from minerva_kb.utils.config_loader import (
    load_index_config,
    load_watcher_config,
    save_index_config,
    save_watcher_config,
)
from minerva_kb.utils.description_generator_repo import generate_description
from minerva_kb.utils.display import display_error, display_success, display_warning
from minerva_kb.utils.provider_selection import interactive_select_provider
from minerva_kb.utils.process_manager import find_watcher_pid, stop_watcher

INCLUDE_EXTENSIONS = [".md", ".mdx", ".markdown", ".rst", ".txt"]
IGNORE_PATTERNS = [
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".tox",
    "*.egg-info",
]


def run_add(repo_path: str) -> int:
    try:
        return _execute_add(repo_path)
    except KeyboardInterrupt:
        print("Operation cancelled by user")
        return 130


def _execute_add(repo_path: str) -> int:
    repository = _resolve_repository_path(repo_path)
    if repository is None:
        return 2

    collection_name = _derive_collection_name(repository)
    if collection_name is None:
        return 2

    watcher_config_path = _watcher_config_path(collection_name)
    if watcher_config_path.exists():
        return _run_provider_update_flow(collection_name, repository, watcher_config_path)

    conflict_result = _handle_unmanaged_collection_conflict(collection_name)
    if conflict_result == "abort":
        return 1
    if conflict_result == "error":
        return 3

    return _run_new_collection_flow(collection_name, repository)


def _resolve_repository_path(repo_path: str) -> Path | None:
    expanded = Path(repo_path).expanduser()
    if not expanded.exists():
        _display_repository_hint(f"Repository path does not exist: {expanded}")
        return None
    if not expanded.is_dir():
        _display_repository_hint(f"Repository path is not a directory: {expanded}")
        return None
    try:
        resolved = expanded.resolve(strict=True)
    except FileNotFoundError:
        _display_repository_hint(f"Repository path is invalid: {expanded}")
        return None
    if not resolved.is_absolute():
        _display_repository_hint(f"Repository path must be absolute: {resolved}")
        return None
    return resolved


def _derive_collection_name(repository: Path) -> str | None:
    try:
        return sanitize_collection_name(repository)
    except ValueError as exc:  # noqa: PERF203 - sanitization errors are expected
        display_error(str(exc))
        return None


def _watcher_config_path(collection_name: str) -> Path:
    return MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"


def _index_config_path(collection_name: str) -> Path:
    return MINERVA_KB_APP_DIR / f"{collection_name}-index.json"


def _run_provider_update_flow(collection_name: str, repository: Path, watcher_path: Path) -> int:
    try:
        watcher_config = load_watcher_config(collection_name)
    except ValueError as exc:
        display_error(f"Invalid watcher config: {exc}")
        return 3

    try:
        index_config = load_index_config(collection_name)
    except ValueError as exc:
        display_error(f"Invalid index config: {exc}")
        return 3

    _display_current_provider(index_config.get("provider", {}))

    confirm = input("Change AI provider? [y/N]: ").strip().lower()
    if confirm not in {"y", "yes"}:
        print("No changes made.")
        return 0

    provider_config = interactive_select_provider()
    _display_provider_summary(provider_config)

    updated_index_config = dict(index_config)
    updated_index_config["provider"] = _provider_entry_from_config(provider_config)
    updated_index_config.setdefault("collection", {})["force_recreate"] = True
    index_config_path = save_index_config(collection_name, updated_index_config)

    pid = find_watcher_pid(watcher_path)
    if pid is not None:
        print(f"Stopping watcher (PID {pid})...")
        if not stop_watcher(pid):
            display_warning("Failed to stop watcher cleanly. Proceeding with reindexing.")

    repo_path = Path(watcher_config.get("repository_path", str(repository))).expanduser()
    extracted_path = Path(
        watcher_config.get(
            "extracted_json_path",
            str(MINERVA_KB_APP_DIR / f"{collection_name}-extracted.json"),
        )
    ).expanduser()

    if not _run_repository_extractor(repo_path, extracted_path):
        return 3
    if not _run_indexing(index_config_path):
        return 3

    # Remove force_recreate so future incremental updates work normally
    updated_index_config["collection"].pop("force_recreate", None)
    save_index_config(collection_name, updated_index_config)

    _display_update_summary(collection_name, provider_config)
    return 0


def _run_new_collection_flow(collection_name: str, repository: Path) -> int:
    provider_config = interactive_select_provider()
    _display_provider_summary(provider_config)
    description = generate_description(repository, collection_name, provider_config)
    _ensure_server_config()
    config_paths = _create_collection_configs(collection_name, description, repository, provider_config)
    if not _run_repository_extractor(repository, config_paths["extracted_json"]):
        return 3
    if not _run_indexing(config_paths["index_config"]):
        return 3
    _display_success_summary(collection_name, repository, provider_config, config_paths["index_config"])
    return 0


def _create_collection_configs(
    collection_name: str,
    description: str,
    repository: Path,
    provider_config: dict[str, str],
) -> dict[str, Path]:
    MINERVA_KB_APP_DIR.mkdir(parents=True, exist_ok=True)
    extracted_json = MINERVA_KB_APP_DIR / f"{collection_name}-extracted.json"
    index_config_path = save_index_config(
        collection_name,
        _build_index_config(collection_name, description, extracted_json, provider_config),
    )
    watcher_config_path = save_watcher_config(
        collection_name,
        _build_watcher_config(collection_name, repository, extracted_json, index_config_path),
    )
    return {
        "index_config": index_config_path,
        "watcher_config": watcher_config_path,
        "extracted_json": extracted_json,
    }


def _build_index_config(
    collection_name: str,
    description: str,
    extracted_json: Path,
    provider_config: dict[str, str],
) -> dict[str, object]:
    return {
        "chromadb_path": str(CHROMADB_DIR),
        "collection": {
            "name": collection_name,
            "description": description,
            "json_file": str(extracted_json),
            "chunk_size": DEFAULT_CHUNK_SIZE,
        },
        "provider": _provider_entry_from_config(provider_config),
    }


def _provider_entry_from_config(provider_config: dict[str, str]) -> dict[str, str]:
    entry = {
        "provider_type": provider_config.get("provider_type"),
        "embedding_model": provider_config.get("embedding_model"),
        "llm_model": provider_config.get("llm_model"),
    }
    api_key_reference = provider_config.get("api_key")
    if api_key_reference:
        entry["api_key"] = api_key_reference
    else:
        key_name = provider_config.get("api_key_name")
        if key_name:
            entry["api_key"] = f"${{{key_name}}}"
    base_url = provider_config.get("base_url")
    if base_url:
        entry["base_url"] = base_url
    return entry


def _build_watcher_config(
    collection_name: str,
    repository: Path,
    extracted_json: Path,
    index_config_path: Path,
) -> dict[str, object]:
    return {
        "repository_path": str(repository),
        "collection_name": collection_name,
        "extracted_json_path": str(extracted_json),
        "index_config_path": str(index_config_path),
        "debounce_seconds": DEFAULT_DEBOUNCE_SECONDS,
        "include_extensions": INCLUDE_EXTENSIONS,
        "ignore_patterns": IGNORE_PATTERNS,
    }


def _run_repository_extractor(repository: Path, output_path: Path) -> bool:
    print("📚 Extracting repository contents...")
    command = ["repository-doc-extractor", str(repository), "-o", str(output_path)]
    return _run_command(command, "Extraction")


def _run_indexing(index_config_path: Path) -> bool:
    print("🔍 Indexing collection (this may take a few minutes)...")
    command = ["minerva", "index", "--config", str(index_config_path)]
    return _run_command(command, "Indexing")


def _run_command(command: list[str], label: str) -> bool:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
            check=True,
        )
        _print_command_output(result.stdout, result.stderr)
        return True
    except FileNotFoundError:
        display_error(f"{label} command not found: {command[0]}")
        return False
    except subprocess.TimeoutExpired:
        display_error(f"{label} timed out after {DEFAULT_SUBPROCESS_TIMEOUT} seconds")
        return False
    except subprocess.CalledProcessError as exc:
        error_details = _extract_error_line(exc.stdout, exc.stderr)
        display_error(f"{label} failed: {error_details}")
        _print_command_output(exc.stdout, exc.stderr)
        return False


def _print_command_output(stdout: str | None, stderr: str | None) -> None:
    if stdout:
        print(stdout.strip())
    if stderr:
        print(stderr.strip())


def _display_success_summary(
    collection_name: str,
    repository: Path,
    provider_config: dict[str, str],
    index_config_path: Path,
) -> None:
    chunk_count = _fetch_chunk_count(collection_name)
    formatted_chunks = _format_chunk_count(chunk_count)
    print()
    print(f"✅ Collection '{collection_name}' indexed successfully!")
    print(f"   Repository: {repository}")
    print(f"   Provider:   {PROVIDER_DISPLAY_NAMES.get(provider_config.get('provider_type'), 'Unknown')}")
    print(f"   Chunks:     {formatted_chunks}")
    print()
    print("Next steps: start watcher with the command minerva-kb watch {collection_name}")
    print()


def _fetch_chunk_count(collection_name: str) -> int | None:
    try:
        client = PersistentClient(path=str(CHROMADB_DIR))
        collection = client.get_collection(collection_name)
        return collection.count()
    except Exception:  # noqa: BLE001 - chunk count is best-effort
        return None


def _format_chunk_count(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:,}"


def _display_update_summary(collection_name: str, provider_config: dict[str, str]) -> None:
    chunk_count = _fetch_chunk_count(collection_name)
    formatted_chunks = _format_chunk_count(chunk_count)
    provider_name = PROVIDER_DISPLAY_NAMES.get(provider_config.get("provider_type"), "Unknown")
    print()
    print(f"✓ Collection '{collection_name}' reindexed with {provider_name}")
    print(f"  Chunks: {formatted_chunks}")
    print(f"  Watcher stopped. Restart with: minerva-kb watch {collection_name}")
    print()


def _display_current_provider(provider: dict[str, str]) -> None:
    provider_name = PROVIDER_DISPLAY_NAMES.get(provider.get("provider_type"), "Unknown")
    print()
    print("Current provider configuration:")
    print(f"  • Provider:  {provider_name}")
    print(f"  • Embedding: {provider.get('embedding_model', 'unknown')}")
    print(f"  • LLM:       {provider.get('llm_model', 'unknown')}")
    print()


def _display_provider_summary(provider_config: dict[str, str]) -> None:
    provider_type = provider_config.get("provider_type", "unknown")
    provider_name = PROVIDER_DISPLAY_NAMES.get(provider_type, provider_type)
    embedding = provider_config.get("embedding_model", "unknown")
    llm_model = provider_config.get("llm_model", "unknown")
    print()
    print("✓ AI provider configured")
    print(f"  • Provider:  {provider_name}")
    print(f"  • Embedding: {embedding}")
    print(f"  • LLM:       {llm_model}")
    print()


def _handle_unmanaged_collection_conflict(collection_name: str) -> str:
    index_exists = _index_config_path(collection_name).exists()
    watcher_exists = _watcher_config_path(collection_name).exists()
    if index_exists or watcher_exists:
        return "ok"

    exists, owner = check_collection_exists(collection_name, CHROMADB_DIR)
    if not exists:
        return "ok"

    if owner and owner != "minerva-kb":
        _display_cross_tool_collision(collection_name, owner)
        return "abort"

    return _prompt_unmanaged_collision_resolution(collection_name)


def _prompt_unmanaged_collision_resolution(collection_name: str) -> str:
    collections = _list_chromadb_collections()
    display_error(f"Collection '{collection_name}' already exists in ChromaDB")
    print("This collection was not created by minerva-kb, so it cannot be managed.")
    print()
    print("Options:")
    print("  1) Abort (keep existing collection)")
    print("  2) Wipe and recreate (delete existing collection)")

    while True:
        choice = input("Choice [1-2]: ").strip()
        if choice == "1":
            _print_available_collections(collections)
            return "abort"
        if choice == "2":
            if _wipe_existing_collection(collection_name):
                return "ok"
            return "error"
        print("❌ Invalid choice. Enter 1 or 2.")


def _display_cross_tool_collision(collection_name: str, owner: str) -> None:
    display_error(
        f"Collection '{collection_name}' is already managed by {owner}."
    )
    if owner == "minerva-doc":
        print("Use minerva-doc to update or remove this collection (e.g. 'minerva-doc remove').")
    else:
        print(f"Use the {owner} tool to manage or delete this collection before retrying.")
    print()


def _list_chromadb_collections() -> list[str]:
    try:
        client = PersistentClient(path=str(CHROMADB_DIR))
        return sorted(collection.name for collection in client.list_collections())
    except Exception:  # noqa: BLE001 - listing is best effort
        return []


def _print_available_collections(collections: list[str]) -> None:
    if not collections:
        print("No collections currently in ChromaDB.")
        return
    print("Existing collections:")
    for name in collections:
        print(f"  • {name}")


def _wipe_existing_collection(collection_name: str) -> bool:
    print()
    print(f"⚠️  Wiping existing ChromaDB collection '{collection_name}'...")
    confirmation = f"YES\n{collection_name}\n"
    try:
        subprocess.run(
            ["minerva", "remove", str(CHROMADB_DIR), collection_name],
            input=confirmation,
            text=True,
            check=True,
            timeout=DEFAULT_SUBPROCESS_TIMEOUT,
        )
        print("✓ Existing collection removed")
        print()
        return True
    except FileNotFoundError:
        display_error("'minerva' command not found while removing collection")
    except subprocess.TimeoutExpired:
        display_error("Collection removal timed out")
    except subprocess.CalledProcessError as exc:
        display_error(f"Failed to remove collection (exit code {exc.returncode})")
    return False


def _display_repository_hint(message: str) -> None:
    display_error(message)
    print("Please provide a valid directory path.")


def _extract_error_line(stdout: str | None, stderr: str | None) -> str:
    data = (stderr or stdout or "").strip()
    if data:
        return data.splitlines()[-1]
    return "see logs for details"


def _ensure_server_config() -> None:
    _, created = ensure_server_config()
    if created:
        display_success("Created server config with defaults")
