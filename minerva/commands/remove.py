from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from minerva.common.exceptions import GracefulExit
from minerva.common.logger import get_logger
from minerva.indexing.storage import (
    ChromaDBConnectionError,
    StorageError,
    initialize_chromadb_client,
    remove_collection,
    ChromaDBLock,
)
from minerva.commands.peek import (
    format_collection_info_text,
    get_collection_info,
)

logger = get_logger(__name__, simple=True, mode="cli")


def _validate_chromadb_path(chromadb_path: Path) -> Path:
    resolved_path = chromadb_path.expanduser().resolve()

    if not resolved_path.exists():
        logger.error(f"ChromaDB path does not exist: {chromadb_path}")
        logger.error(f"   Absolute path: {resolved_path}")
        raise StorageError(f"ChromaDB path not found: {resolved_path}")

    if not resolved_path.is_dir():
        logger.error(f"ChromaDB path is not a directory: {chromadb_path}")
        raise StorageError(f"ChromaDB path is not a directory: {resolved_path}")

    return resolved_path


def _read_input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ""


def _require_yes_confirmation(collection_name: str, chromadb_path: Path) -> None:
    prompt = (
        "\nThis operation will permanently delete the entire collection and all of its chunks.\n"
        f"Type YES to continue deleting '{collection_name}' from '{chromadb_path}': "
    )

    response = _read_input(prompt).strip()
    if response != "YES":
        raise GracefulExit("Deletion cancelled before confirmation", exit_code=0)


def _require_collection_name_confirmation(collection_name: str) -> None:
    prompt = f"Re-type the collection name ('{collection_name}') to confirm: "
    response = _read_input(prompt).strip()
    if response != collection_name:
        raise GracefulExit("Deletion cancelled: collection name mismatch", exit_code=0)


def _describe_collection(collection, *, label: str = "") -> None:
    info = get_collection_info(collection)
    heading = label or "Collection details before deletion"
    logger.info("")
    logger.info(heading)
    logger.info("=" * len(heading))
    logger.info("")
    logger.info(format_collection_info_text(info))


def run_remove(args: Namespace) -> int:
    try:
        chromadb_path = Path(args.chromadb)
        collection_name = args.collection_name

        resolved_path = _validate_chromadb_path(chromadb_path)
        client = initialize_chromadb_client(str(resolved_path))

        collections = {collection.name: collection for collection in client.list_collections()}

        if not collections:
            logger.error("No collections found in ChromaDB")
            logger.error("   Suggestion: Use 'minerva index' to create collections")
            return 1

        if collection_name not in collections:
            logger.error(f"Collection '{collection_name}' not found")
            logger.error("Available collections:")
            for name in sorted(collections.keys()):
                logger.error(f"  • {name}")
            return 1

        collection = collections[collection_name]

        _describe_collection(collection)

        _require_yes_confirmation(collection_name, resolved_path)
        _require_collection_name_confirmation(collection_name)

        # Acquire lock for the deletion operation
        with ChromaDBLock(str(resolved_path)):
            remove_collection(client, collection_name)

        logger.success(f"✓ Collection '{collection_name}' deleted")
        logger.info("You can recreate it with 'minerva index --config <config-file>'.")
        return 0

    except GracefulExit:
        raise
    except ChromaDBConnectionError as error:
        logger.error(f"ChromaDB connection error: {error}")
        return 1
    except StorageError as error:
        logger.error(str(error))
        return 1
    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return 130
    except Exception as error:
        logger.error(f"Unexpected error: {error}")
        return 1
