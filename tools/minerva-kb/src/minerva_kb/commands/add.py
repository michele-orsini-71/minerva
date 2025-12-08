from pathlib import Path

from minerva_kb.constants import MINERVA_KB_APP_DIR, PROVIDER_DISPLAY_NAMES
from minerva_kb.utils.collection_naming import sanitize_collection_name
from minerva_kb.utils.description_generator import generate_description
from minerva_kb.utils.provider_selection import interactive_select_provider


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
    generate_description(repository, collection_name, provider_config)
    _display_warning(
        f"New collection flow for '{collection_name}' at '{repository}' is not implemented yet."
    )
    return 2


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
