import json
import sys
from argparse import Namespace
from typing import Dict, Any, List

from minerva.common.logger import get_logger
from minerva.indexing.storage import initialize_chromadb_client, ChromaDBConnectionError

logger = get_logger(__name__, simple=True, mode="cli")


def is_collection_usable(metadata: Dict[str, Any]) -> tuple[bool, str | None]:
    """
    Check if a collection has required metadata to be usable.
    Returns (is_usable, reason_if_not_usable)
    """
    provider_type = metadata.get('embedding_provider')
    embedding_model = metadata.get('embedding_model')
    llm_model = metadata.get('llm_model')

    if not provider_type or not embedding_model or not llm_model:
        return False, "Missing AI provider metadata (created with old pipeline)"

    return True, None


def _extract_unique_note_ids(metadatas: List[Dict[str, Any]]) -> set[str]:
    note_ids: set[str] = set()
    for meta in metadatas:
        if not meta:
            continue
        note_id = meta.get('noteId') or meta.get('note_id')
        if note_id:
            note_ids.add(str(note_id))
    return note_ids


def _compute_note_count(collection, chunk_count: int) -> tuple[int | None, str | None]:
    if chunk_count == 0:
        return 0, None

    batch_size = 1000
    unique_note_ids: set[str] = set()
    retrieved = 0

    try:
        while retrieved < chunk_count:
            limit = min(batch_size, chunk_count - retrieved)
            results = collection.get(
                include=["metadatas"],
                limit=limit,
                offset=retrieved
            )

            metadatas = results.get("metadatas") if results else None
            if not metadatas:
                break

            unique_note_ids.update(_extract_unique_note_ids(metadatas))
            retrieved += len(metadatas)

        if not unique_note_ids:
            return None, None

        return len(unique_note_ids), None

    except Exception as error:
        return None, str(error)


def get_collection_info(collection) -> Dict[str, Any]:

    # Get basic collection info
    metadata = collection.metadata or {}
    is_usable, unavailable_reason = is_collection_usable(metadata)

    chunk_count = collection.count()
    note_count, note_count_error = _compute_note_count(collection, chunk_count)

    info = {
        "name": collection.name,
        "count": chunk_count,
        "metadata": metadata,
        "is_usable": is_usable,
        "unavailable_reason": unavailable_reason,
        "note_count": note_count,
        "note_count_error": note_count_error,
    }

    # Get a few sample chunks (limit to 5 for inspection)
    try:
        if info["count"] > 0:
            limit = min(5, info["count"])
            results = collection.get(limit=limit, include=["documents", "metadatas"])

            info["samples"] = []
            if results and results.get("ids"):
                for i, chunk_id in enumerate(results["ids"]):
                    sample = {
                        "id": chunk_id,
                        "document": results["documents"][i] if results.get("documents") else None,
                        "metadata": results["metadatas"][i] if results.get("metadatas") else {}
                    }
                    info["samples"].append(sample)
    except Exception as e:
        info["samples_error"] = str(e)

    return info


def format_collection_info_text(info: Dict[str, Any]) -> str:

    lines = []
    lines.append("=" * 70)
    lines.append(f"Collection: {info['name']}")
    lines.append("=" * 70)
    lines.append("")

    # Legacy/unusable warning (prominent)
    if not info.get("is_usable", True):
        lines.append("⚠️  WARNING: LEGACY COLLECTION - CANNOT BE USED")
        lines.append("━" * 70)
        lines.append(f"   Reason: {info.get('unavailable_reason', 'Unknown')}")
        lines.append("")
        lines.append("   This collection was created with an older version of Minerva")
        lines.append("   and is missing required AI provider metadata.")
        lines.append("")
        lines.append("   To fix: Re-index this collection using 'minerva index'")
        lines.append("━" * 70)
        lines.append("")

    # Basic stats
    lines.append(f"Total chunks: {info['count']}")
    if info.get("note_count") is not None:
        lines.append(f"Total notes: {info['note_count']}")
    elif info.get("note_count_error"):
        lines.append(f"Total notes: unavailable (error: {info['note_count_error']})")
    else:
        lines.append("Total notes: unavailable (note metadata missing)")
    lines.append("")

    # Metadata section
    if info.get("metadata"):
        lines.append("Metadata:")
        lines.append("-" * 70)

        # Provider information
        if "embedding_provider" in info["metadata"]:
            lines.append(f"  Provider: {info['metadata']['embedding_provider']}")
        if "embedding_model" in info["metadata"]:
            lines.append(f"  Embedding model: {info['metadata']['embedding_model']}")
        if "embedding_dimension" in info["metadata"]:
            lines.append(f"  Embedding dimension: {info['metadata']['embedding_dimension']}")
        if "llm_model" in info["metadata"]:
            lines.append(f"  LLM model: {info['metadata']['llm_model']}")

        # Description
        if "description" in info["metadata"]:
            desc = info["metadata"]["description"]
            lines.append(f"  Description: {desc[:100]}..." if len(desc) > 100 else f"  Description: {desc}")

        # Other metadata
        other_keys = [k for k in info["metadata"].keys()
                      if k not in ["embedding_provider", "embedding_model", "embedding_dimension",
                                   "llm_model", "description", "hnsw:space"]]
        if other_keys:
            lines.append("")
            lines.append("  Additional metadata:")
            for key in sorted(other_keys):
                value = info["metadata"][key]
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 60:
                    value_str = value_str[:57] + "..."
                lines.append(f"    {key}: {value_str}")

        lines.append("")

    # Sample chunks
    if "samples" in info and info["samples"]:
        lines.append(f"Sample chunks (showing {len(info['samples'])} of {info['count']}):")
        lines.append("-" * 70)

        for i, sample in enumerate(info["samples"], 1):
            lines.append(f"\n[{i}] ID: {sample['id']}")

            # Show metadata
            if sample.get("metadata"):
                meta = sample["metadata"]
                if "title" in meta:
                    lines.append(f"    Title: {meta['title']}")
                if "chunk_index" in meta:
                    lines.append(f"    Chunk index: {meta['chunk_index']}")
                if "modificationDate" in meta:
                    lines.append(f"    Modified: {meta['modificationDate']}")

            # Show document content (truncated)
            if sample.get("document"):
                doc = sample["document"]
                if len(doc) > 200:
                    doc = doc[:197] + "..."
                lines.append(f"    Content: {doc}")

        lines.append("")
    elif "samples_error" in info:
        lines.append(f"⚠ Could not retrieve sample chunks: {info['samples_error']}")
        lines.append("")
    elif info["count"] == 0:
        lines.append("⚠ Collection is empty (no chunks)")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def format_collection_info_json(info: Dict[str, Any]) -> str:
    return json.dumps(info, indent=2)


def format_all_collections_text(collections_data: List[Dict[str, Any]]) -> str:
    """Format summary of all collections in text format"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"ChromaDB Collections Summary ({len(collections_data)} total)")
    lines.append("=" * 70)
    lines.append("")

    if not collections_data:
        lines.append("⚠ No collections found in ChromaDB")
        lines.append("")
        lines.append("Suggestion: Use 'minerva index' to create collections")
        lines.append("=" * 70)
        return "\n".join(lines)

    # Count legacy collections for summary
    legacy_count = sum(1 for info in collections_data if not info.get("is_usable", True))

    for i, info in enumerate(collections_data, 1):
        # Add warning indicator for legacy collections
        status_indicator = " ⚠️ LEGACY" if not info.get("is_usable", True) else ""
        lines.append(f"[{i}] {info['name']}{status_indicator}")
        lines.append(f"    Total chunks: {info['count']}")
        if info.get("note_count") is not None:
            lines.append(f"    Total notes: {info['note_count']}")
        elif info.get("note_count_error"):
            lines.append(f"    Total notes: unavailable (error)")
        else:
            lines.append("    Total notes: unavailable")

        # Show unavailable reason for legacy collections
        if not info.get("is_usable", True):
            lines.append(f"    ⚠️  Status: CANNOT BE USED - {info.get('unavailable_reason', 'Unknown reason')}")

        if info.get("metadata"):
            meta = info["metadata"]
            if "description" in meta:
                desc = meta["description"]
                # Truncate long descriptions
                if len(desc) > 70:
                    desc = desc[:67] + "..."
                lines.append(f"    Description: {desc}")

            if "embedding_model" in meta:
                lines.append(f"    Model: {meta['embedding_model']}")

        lines.append("")

    lines.append("=" * 70)

    # Add summary warning if there are legacy collections
    if legacy_count > 0:
        lines.append("")
        lines.append(f"⚠️  WARNING: {legacy_count} legacy collection(s) found")
        lines.append("   These collections cannot be used and must be re-indexed.")
        lines.append("   Use 'minerva peek <chromadb_path> <collection_name>' for details.")
        lines.append("")
    lines.append("")
    lines.append("Tip: To inspect a specific collection, use:")
    lines.append("     minerva peek <chromadb_path> <collection_name>")
    lines.append("")

    return "\n".join(lines)


def format_all_collections_json(collections_data: List[Dict[str, Any]]) -> str:
    """Format summary of all collections in JSON format"""
    # For JSON output, we'll create a simpler structure without sample chunks
    legacy_count = sum(1 for info in collections_data if not info.get("is_usable", True))

    summary = {
        "total_collections": len(collections_data),
        "legacy_collections": legacy_count,
        "collections": []
    }

    for info in collections_data:
        collection_summary = {
            "name": info["name"],
            "count": info["count"],
            "is_usable": info.get("is_usable", True),
            "unavailable_reason": info.get("unavailable_reason"),
            "metadata": info.get("metadata", {})
        }
        summary["collections"].append(collection_summary)

    return json.dumps(summary, indent=2)


def run_peek(args: Namespace) -> int:
    try:
        chromadb_path = str(args.chromadb)
        output_format = args.format
        collection_name = args.collection_name

        # Validate that ChromaDB path exists
        from pathlib import Path
        db_path = Path(chromadb_path)

        if not db_path.exists():
            logger.error(f"ChromaDB path does not exist: {chromadb_path}")
            logger.error(f"   Absolute path: {db_path.absolute()}")
            logger.error("")
            logger.error("Suggestion: Check the path and try again")
            logger.error("   Example: minerva peek ./chromadb_data")
            return 1

        if not db_path.is_dir():
            logger.error(f"ChromaDB path is not a directory: {chromadb_path}")
            logger.error(f"   Found: {db_path.absolute()}")
            return 1

        logger.info(f"Connecting to ChromaDB at: {chromadb_path}")
        logger.info("")
        client = initialize_chromadb_client(chromadb_path)

        existing_collections = [c.name for c in client.list_collections()]

        # If no collection name provided, list all collections
        if collection_name is None:
            if not existing_collections:
                logger.error("No collections found in ChromaDB")
                logger.error("   Suggestion: Use 'minerva index' to create collections")
                return 1

            # Get basic info for all collections
            collections_data = []
            for coll in client.list_collections():
                metadata = coll.metadata or {}
                is_usable, unavailable_reason = is_collection_usable(metadata)

                info = {
                    "name": coll.name,
                    "count": coll.count(),
                    "metadata": metadata,
                    "is_usable": is_usable,
                    "unavailable_reason": unavailable_reason
                }
                collections_data.append(info)

            # Format and print
            if output_format == "json":
                logger.info(format_all_collections_json(collections_data))
            else:
                logger.info(format_all_collections_text(collections_data))

            return 0

        # Collection name provided - show detailed info for specific collection
        if collection_name not in existing_collections:
            logger.error(f"Collection '{collection_name}' not found")
            if existing_collections:
                logger.error("Available collections:")
                for name in existing_collections:
                    logger.error(f"  • {name}")
            else:
                logger.error("No collections found in ChromaDB")
                logger.error("   Suggestion: Use 'minerva index' to create collections")
            return 1

        # Get the collection
        collection = client.get_collection(collection_name)

        # Get collection info
        info = get_collection_info(collection)

        # Format and print
        if output_format == "json":
            logger.info(format_collection_info_json(info))
        else:
            logger.info(format_collection_info_text(info))

        return 0

    except ChromaDBConnectionError as e:
        logger.error(f"ChromaDB connection error: {e}")
        return 1

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
