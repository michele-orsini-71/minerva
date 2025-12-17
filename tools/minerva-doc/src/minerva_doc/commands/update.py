import tempfile
from datetime import datetime, timezone
from pathlib import Path

from minerva_common.config_builder import build_index_config, save_index_config
from minerva_common.description_generator import prompt_for_description
from minerva_common.minerva_runner import run_index, run_validate
from minerva_common.paths import CHROMADB_DIR
from minerva_common.provider_setup import select_provider_interactive
from minerva_common.registry import Registry

from minerva_doc.constants import COLLECTIONS_REGISTRY_PATH, MINERVA_DOC_APP_DIR


def run_update(collection_name: str, json_file: str) -> int:
    try:
        return execute_update(collection_name, json_file)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


def execute_update(collection_name: str, json_file: str) -> int:
    registry = Registry(COLLECTIONS_REGISTRY_PATH)

    collection = registry.get_collection(collection_name)
    if collection is None:
        print(f"Error: Collection '{collection_name}' not found")
        print(f"  This collection is not managed by minerva-doc")
        print()
        print("Actions:")
        print(f"  - List all collections: minerva-doc list")
        print(f"  - Create new collection: minerva-doc add {json_file} --name {collection_name}")
        return 1

    json_path = validate_json_file(json_file)
    if json_path is None:
        return 1

    if not validate_json_content(json_path):
        return 1

    current_provider = collection.get("provider", {})
    display_current_provider(current_provider)

    provider_changed = prompt_provider_change()

    if provider_changed:
        new_provider = select_provider_interactive()
        if new_provider is None:
            print("Error: Provider selection cancelled")
            return 1

        display_provider_summary(new_provider)

        description = prompt_for_description(json_path, new_provider)
        if description is None:
            print("Error: Description generation failed")
            return 1

        provider_config = new_provider
        force_recreate = True
    else:
        provider_config = current_provider
        description = collection.get("description", "Document collection")
        force_recreate = False

    index_config = build_index_config(
        collection_name=collection_name,
        json_file=str(json_path),
        chromadb_path=str(CHROMADB_DIR),
        provider=provider_config,
        description=description,
        chunk_size=1200,
        force_recreate=force_recreate,
    )

    temp_config_path = create_temp_index_config(index_config)
    if temp_config_path is None:
        return 1

    try:
        if not run_indexing(temp_config_path, force_recreate):
            return 1

        update_registry(registry, collection_name, json_path, provider_config, description)
        display_success(collection_name, provider_changed)
        return 0

    finally:
        cleanup_temp_file(temp_config_path)


def validate_json_file(json_file: str) -> Path | None:
    path = Path(json_file).expanduser()

    if not path.exists():
        print(f"Error: JSON file does not exist: {path}")
        print(f"  Check that the path is correct and the file exists")
        print(f"  Hint: Use an absolute path or ensure you're in the right directory")
        return None

    if not path.is_file():
        print(f"Error: Path is not a file: {path}")
        print(f"  The path exists but points to a directory, not a file")
        return None

    if not path.suffix == ".json":
        print(f"Warning: File does not have .json extension: {path}")

    try:
        resolved = path.resolve(strict=True)
    except Exception as e:
        print(f"Error: Cannot resolve path {path}: {e}")
        print(f"  Check file permissions and that the path is accessible")
        return None

    return resolved


def validate_json_content(json_path: Path) -> bool:
    print(f"Validating JSON file: {json_path.name}")

    success, output = run_validate(str(json_path))

    if success:
        print("✓ JSON file is valid")
        return True
    else:
        print("✗ JSON file validation failed:")
        print(output)
        return False


def display_current_provider(provider_config: dict) -> None:
    provider_type = provider_config.get("provider_type", "unknown")
    embedding_model = provider_config.get("embedding_model", "unknown")
    llm_model = provider_config.get("llm_model", "unknown")

    print()
    print("Current AI Provider:")
    print(f"  Provider: {provider_type}")
    print(f"  Embedding model: {embedding_model}")
    print(f"  LLM model: {llm_model}")
    print()


def prompt_provider_change() -> bool:
    while True:
        response = input("Change AI provider? [y/N]: ").strip().lower()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no", ""}:
            return False
        print("Please enter 'y' for yes or 'n' for no")


def display_provider_summary(provider_config: dict) -> None:
    provider_type = provider_config.get("provider_type", "unknown")
    embedding_model = provider_config.get("embedding_model", "unknown")
    llm_model = provider_config.get("llm_model", "unknown")

    print()
    print("New AI Provider:")
    print(f"  Provider: {provider_type}")
    print(f"  Embedding model: {embedding_model}")
    print(f"  LLM model: {llm_model}")
    print()


def create_temp_index_config(config: dict) -> Path | None:
    try:
        MINERVA_DOC_APP_DIR.mkdir(parents=True, exist_ok=True)

        temp_fd, temp_path_str = tempfile.mkstemp(
            suffix=".json",
            prefix="minerva-doc-index-",
            dir=MINERVA_DOC_APP_DIR,
        )

        temp_path = Path(temp_path_str)

        import os
        os.close(temp_fd)

        save_index_config(config, temp_path)
        return temp_path

    except PermissionError as e:
        print(f"Error: Permission denied creating temp config file: {e}")
        print(f"  Check that you have write permissions to: {MINERVA_DOC_APP_DIR}")
        print(f"  Try: chmod 700 {MINERVA_DOC_APP_DIR}")
        return None
    except Exception as e:
        print(f"Error: Failed to create temp config file: {e}")
        print(f"  This may be due to disk space or filesystem issues")
        return None


def run_indexing(config_path: Path, force_recreate: bool) -> bool:
    if force_recreate:
        print("Re-indexing collection with new provider (this may take a few minutes)...")
    else:
        print("Updating collection (this may take a few minutes)...")

    success, output = run_index(str(config_path))

    if success:
        print("✓ Collection updated successfully")
        return True
    else:
        print("✗ Update failed:")
        print(output)
        return False


def update_registry(
    registry: Registry,
    collection_name: str,
    json_path: Path,
    provider_config: dict,
    description: str,
) -> None:
    existing = registry.get_collection(collection_name)

    updated_metadata = {
        "collection_name": collection_name,
        "records_path": str(json_path),
        "description": description,
        "provider": provider_config,
        "created_at": existing.get("created_at", datetime.now(timezone.utc).isoformat()),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }

    registry.update_collection(collection_name, updated_metadata)


def display_success(collection_name: str, provider_changed: bool) -> None:
    print()
    print("=" * 60)
    print("✓ Collection updated successfully!")
    print("=" * 60)
    print(f"  Collection name: {collection_name}")
    if provider_changed:
        print(f"  AI provider: Changed (collection re-indexed)")
    else:
        print(f"  AI provider: Unchanged")
    print()
    print("Next steps:")
    print(f"  1. Check status:   minerva-doc status {collection_name}")
    print(f"  2. List all:       minerva-doc list")
    print(f"  3. Start server:   minerva-doc serve")
    print()


def cleanup_temp_file(temp_path: Path | None) -> None:
    if temp_path and temp_path.exists():
        try:
            temp_path.unlink()
        except Exception:
            pass
