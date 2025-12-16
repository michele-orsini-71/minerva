import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from minerva_common.collision import check_collection_exists
from minerva_common.config_builder import build_index_config, save_index_config
from minerva_common.description_generator import prompt_for_description
from minerva_common.init import ensure_server_config
from minerva_common.minerva_runner import run_index, run_validate
from minerva_common.paths import CHROMADB_DIR
from minerva_common.provider_setup import select_provider_interactive
from minerva_common.registry import Registry

from minerva_doc.constants import COLLECTIONS_REGISTRY_PATH, MINERVA_DOC_APP_DIR
from minerva_doc.utils.init import ensure_registry


def run_add(json_file: str, collection_name: str) -> int:
    try:
        return execute_add(json_file, collection_name)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


def execute_add(json_file: str, collection_name: str) -> int:
    json_path = validate_json_file(json_file)
    if json_path is None:
        return 1

    if not validate_collection_name(collection_name):
        return 1

    if not check_collision(collection_name):
        return 1

    if not validate_json_content(json_path):
        return 1

    provider_config = select_provider_interactive()
    if provider_config is None:
        print("Error: Provider selection cancelled")
        return 1

    display_provider_summary(provider_config)

    description = prompt_for_description(json_path, provider_config)
    if description is None:
        print("Error: Description generation failed")
        return 1

    ensure_shared_infrastructure()

    index_config = build_index_config(
        collection_name=collection_name,
        json_file=str(json_path),
        chromadb_path=str(CHROMADB_DIR),
        provider=provider_config,
        description=description,
        chunk_size=1200,
        force_recreate=False,
    )

    temp_config_path = create_temp_index_config(index_config)
    if temp_config_path is None:
        return 1

    try:
        if not run_indexing(temp_config_path):
            return 1

        register_collection(collection_name, json_path, provider_config, description)
        display_success(collection_name)
        return 0

    finally:
        cleanup_temp_file(temp_config_path)


def validate_json_file(json_file: str) -> Path | None:
    path = Path(json_file).expanduser()

    if not path.exists():
        print(f"Error: JSON file does not exist: {path}")
        return None

    if not path.is_file():
        print(f"Error: Path is not a file: {path}")
        return None

    if not path.suffix == ".json":
        print(f"Warning: File does not have .json extension: {path}")

    try:
        resolved = path.resolve(strict=True)
    except Exception as e:
        print(f"Error: Cannot resolve path {path}: {e}")
        return None

    return resolved


def validate_collection_name(name: str) -> bool:
    if not name:
        print("Error: Collection name cannot be empty")
        return False

    if len(name) > 100:
        print("Error: Collection name too long (max 100 characters)")
        return False

    invalid_chars = set('<>:"/\\|?*')
    if any(c in name for c in invalid_chars):
        print(f"Error: Collection name contains invalid characters: {invalid_chars}")
        return False

    return True


def check_collision(collection_name: str) -> bool:
    exists, owner = check_collection_exists(collection_name)

    if not exists:
        return True

    if owner == "minerva-kb":
        print(f"Error: Collection '{collection_name}' already exists")
        print(f"  Owner: minerva-kb (repository-based collection)")
        print(f"  Action: Use a different name or remove the existing collection with:")
        print(f"    minerva-kb remove {collection_name}")
        return False

    if owner == "minerva-doc":
        print(f"Error: Collection '{collection_name}' already exists")
        print(f"  Owner: minerva-doc (document-based collection)")
        print(f"  Action: Use a different name, update it, or remove it with:")
        print(f"    minerva-doc update {collection_name} <new-json-file>")
        print(f"    minerva-doc remove {collection_name}")
        return False

    print(f"Error: Collection '{collection_name}' already exists")
    print(f"  Owner: unknown (unmanaged collection)")
    print(f"  Action: Use a different name or remove it manually using minerva CLI")
    return False


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


def display_provider_summary(provider_config: dict) -> None:
    provider_type = provider_config.get("provider_type", "unknown")
    embedding_model = provider_config.get("embedding_model", "unknown")
    llm_model = provider_config.get("llm_model", "unknown")

    print()
    print("Selected AI Provider:")
    print(f"  Provider: {provider_type}")
    print(f"  Embedding model: {embedding_model}")
    print(f"  LLM model: {llm_model}")
    print()


def ensure_shared_infrastructure() -> None:
    ensure_server_config()
    ensure_registry()


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

    except Exception as e:
        print(f"Error: Failed to create temp config file: {e}")
        return None


def run_indexing(config_path: Path) -> bool:
    print(f"Indexing collection (this may take a few minutes)...")

    success, output = run_index(str(config_path))

    if success:
        print("✓ Collection indexed successfully")
        return True
    else:
        print("✗ Indexing failed:")
        print(output)
        return False


def register_collection(
    collection_name: str,
    json_path: Path,
    provider_config: dict,
    description: str,
) -> None:
    registry = Registry(COLLECTIONS_REGISTRY_PATH)

    metadata = {
        "collection_name": collection_name,
        "records_path": str(json_path),
        "description": description,
        "provider": provider_config,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }

    registry.add_collection(collection_name, metadata)


def display_success(collection_name: str) -> None:
    print()
    print("=" * 60)
    print("✓ Collection created successfully!")
    print("=" * 60)
    print(f"  Collection name: {collection_name}")
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
