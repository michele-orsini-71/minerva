import subprocess
from pathlib import Path

from chromadb import PersistentClient

from minerva_kb.constants import CHROMADB_DIR, MINERVA_KB_APP_DIR, PROVIDER_DISPLAY_NAMES
from minerva_kb.utils.collection_naming import sanitize_collection_name
from minerva_kb.utils.config_loader import save_index_config, save_watcher_config
from minerva_kb.utils.description_generator import generate_description
from minerva_kb.utils.provider_selection import interactive_select_provider

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_DEBOUNCE_SECONDS = 60.0
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
]
DEFAULT_SUBPROCESS_TIMEOUT = 600


def run_add(repo_path: str) -> int:
    repository = _resolve_repository_path(repo_path)
    if repository is None:
        return 2

    collection_name = _derive_collection_name(repository)
    if collection_name is None:
        return 2

    watcher_config_path = _watcher_config_path(collection_name)
    if watcher_config_path.exists():
        return _run_provider_update_flow(collection_name, repository, watcher_config_path)
    return _run_new_collection_flow(collection_name, repository)


def _resolve_repository_path(repo_path: str) -> Path | None:
    expanded = Path(repo_path).expanduser()
    if not expanded.exists():
        _display_error(f"Repository path does not exist: {expanded}")
        return None
    if not expanded.is_dir():
        _display_error(f"Repository path is not a directory: {expanded}")
        return None
    try:
        return expanded.resolve(strict=True)
    except FileNotFoundError:
        _display_error(f"Repository path is invalid: {expanded}")
        return None


def _derive_collection_name(repository: Path) -> str | None:
    try:
        return sanitize_collection_name(repository)
    except ValueError as exc:  # noqa: PERF203 - sanitization errors are expected
        _display_error(str(exc))
        return None


def _watcher_config_path(collection_name: str) -> Path:
    return MINERVA_KB_APP_DIR / f"{collection_name}-watcher.json"


def _run_provider_update_flow(collection_name: str, repository: Path, watcher_path: Path) -> int:
    _display_warning(
        f"Provider update flow for '{collection_name}' is not implemented yet (config: {watcher_path})."
    )
    return 2


def _run_new_collection_flow(collection_name: str, repository: Path) -> int:
    provider_config = interactive_select_provider()
    _display_provider_summary(provider_config)
    description = generate_description(repository, collection_name, provider_config)
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
    provider_entry = {
        "provider_type": provider_config.get("provider_type"),
        "embedding_model": provider_config.get("embedding_model"),
        "llm_model": provider_config.get("llm_model"),
    }
    key_name = provider_config.get("api_key_name")
    if key_name:
        provider_entry["api_key"] = f"${{{key_name}}}"

    return {
        "chromadb_path": str(CHROMADB_DIR),
        "collection": {
            "name": collection_name,
            "description": description,
            "json_file": str(extracted_json),
            "chunk_size": DEFAULT_CHUNK_SIZE,
        },
        "provider": provider_entry,
    }


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
        _display_error(f"{label} command not found: {command[0]}")
        return False
    except subprocess.TimeoutExpired:
        _display_error(f"{label} timed out after {DEFAULT_SUBPROCESS_TIMEOUT} seconds")
        return False
    except subprocess.CalledProcessError as exc:
        _display_error(f"{label} failed (exit code {exc.returncode})")
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
    print("Next steps:")
    print(f"  • Start watcher: minerva-kb watch {collection_name}")
    print(f"  • Inspect config: {index_config_path}")
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


def _display_error(message: str) -> None:
    print(f"❌ {message}")


def _display_warning(message: str) -> None:
    print(f"⚠️ {message}")
