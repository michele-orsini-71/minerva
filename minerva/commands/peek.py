import json
import sys
from argparse import Namespace
from typing import Dict, Any, List

from minerva.common.logger import get_logger
from minerva.indexing.storage import initialize_chromadb_client, ChromaDBConnectionError

logger = get_logger(__name__, simple=True, mode="cli")


def get_collection_info(collection) -> Dict[str, Any]:

    # Get basic collection info
    info = {
        "name": collection.name,
        "count": collection.count(),
        "metadata": collection.metadata or {}
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

    # Basic stats
    lines.append(f"Total chunks: {info['count']}")
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

    for i, info in enumerate(collections_data, 1):
        lines.append(f"[{i}] {info['name']}")
        lines.append(f"    Total chunks: {info['count']}")

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
    lines.append("")
    lines.append("Tip: To inspect a specific collection, use:")
    lines.append("     minerva peek <chromadb_path> <collection_name>")
    lines.append("")

    return "\n".join(lines)


def format_all_collections_json(collections_data: List[Dict[str, Any]]) -> str:
    """Format summary of all collections in JSON format"""
    # For JSON output, we'll create a simpler structure without sample chunks
    summary = {
        "total_collections": len(collections_data),
        "collections": []
    }

    for info in collections_data:
        collection_summary = {
            "name": info["name"],
            "count": info["count"],
            "metadata": info.get("metadata", {})
        }
        summary["collections"].append(collection_summary)

    return json.dumps(summary, indent=2)


def run_peek(args: Namespace) -> int:
    try:
        chromadb_path = str(args.chromadb)
        output_format = args.format
        collection_name = args.collection_name

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
                info = {
                    "name": coll.name,
                    "count": coll.count(),
                    "metadata": coll.metadata or {}
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
                logger.error("Available collections:", print_to_stderr=False)
                for name in existing_collections:
                    logger.error(f"  • {name}", print_to_stderr=False)
            else:
                logger.error("No collections found in ChromaDB", print_to_stderr=False)
                logger.error("   Suggestion: Use 'minerva index' to create collections", print_to_stderr=False)
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
