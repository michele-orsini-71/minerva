#!/usr/bin/env python3
"""
ChromaDB Inspector Tool

A utility script to inspect ChromaDB collections and their metadata.
Provides a quick overview of all collections in a ChromaDB database.

Usage:
    python inspect_chromadb.py <chromadb_path>
    python inspect_chromadb.py <chromadb_path> --json
    python inspect_chromadb.py <chromadb_path> --collection <name>
    python inspect_chromadb.py <chromadb_path> --verbose

Examples:
    # Basic inspection
    python inspect_chromadb.py ../chromadb_data

    # JSON output for scripting
    python inspect_chromadb.py ../chromadb_data --json

    # Inspect specific collection
    python inspect_chromadb.py ../chromadb_data --collection alice-in-wonderland

    # Verbose mode with sample documents
    python inspect_chromadb.py ../chromadb_data --verbose
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "markdown-notes-cag-data-creator"))

try:
    import chromadb
except ImportError:
    print("Error: chromadb library not installed. Run: pip install chromadb", file=sys.stderr)
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def format_timestamp(timestamp: Optional[str]) -> str:
    """Format ISO timestamp to human-readable format."""
    if not timestamp:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return timestamp


def format_bytes(size: int) -> str:
    """Format byte size to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def get_collection_info(collection: Any, verbose: bool = False) -> Dict[str, Any]:
    """Extract detailed information from a ChromaDB collection."""
    metadata = collection.metadata or {}
    chunk_count = collection.count()

    info = {
        "name": collection.name,
        "chunk_count": chunk_count,
        "metadata": metadata,
        "created_at": metadata.get("created_at"),
        "description": metadata.get("description", "No description available"),
        "version": metadata.get("version"),
        "ai_provider": {
            "embedding_provider": metadata.get("embedding_provider"),
            "embedding_model": metadata.get("embedding_model"),
            "embedding_dimension": metadata.get("embedding_dimension"),
            "embedding_base_url": metadata.get("embedding_base_url"),
            "embedding_api_key_ref": metadata.get("embedding_api_key_ref"),
            "llm_model": metadata.get("llm_model"),
        },
        "index_config": {
            "hnsw_space": metadata.get("hnsw:space"),
        }
    }

    # Get sample documents if verbose mode
    if verbose and chunk_count > 0:
        try:
            sample_size = min(3, chunk_count)
            results = collection.get(limit=sample_size, include=['documents', 'metadatas'])
            info["sample_documents"] = {
                "documents": results.get('documents', []),
                "metadatas": results.get('metadatas', [])
            }
        except Exception as e:
            info["sample_documents_error"] = str(e)

    return info


def print_collection_summary(info: Dict[str, Any], use_colors: bool = True) -> None:
    """Print a formatted summary of a collection."""
    c = Colors if use_colors else type('NoColors', (), {attr: '' for attr in dir(Colors) if not attr.startswith('_')})()

    print(f"\n{c.BOLD}{c.CYAN}{'='*80}{c.END}")
    print(f"{c.BOLD}{c.HEADER}Collection: {info['name']}{c.END}")
    print(f"{c.CYAN}{'='*80}{c.END}")

    # Basic info
    print(f"\n{c.BOLD}Basic Information:{c.END}")
    print(f"  Chunk Count:  {c.GREEN}{info['chunk_count']:,}{c.END}")
    print(f"  Created At:   {format_timestamp(info['created_at'])}")
    if info.get('version'):
        print(f"  Version:      {info['version']}")

    # Description
    if info['description']:
        print(f"\n{c.BOLD}Description:{c.END}")
        desc = info['description']
        if len(desc) > 100:
            print(f"  {desc[:97]}...")
        else:
            print(f"  {desc}")

    # AI Provider info
    provider_info = info['ai_provider']
    if provider_info.get('embedding_provider'):
        print(f"\n{c.BOLD}AI Provider Configuration:{c.END}")
        print(f"  Provider:     {c.BLUE}{provider_info['embedding_provider']}{c.END}")
        print(f"  Embedding:    {provider_info['embedding_model']}")
        if provider_info.get('embedding_dimension'):
            print(f"  Dimension:    {provider_info['embedding_dimension']}")
        if provider_info.get('llm_model'):
            print(f"  LLM Model:    {provider_info['llm_model']}")
        if provider_info.get('embedding_base_url'):
            print(f"  Base URL:     {provider_info['embedding_base_url']}")
        if provider_info.get('embedding_api_key_ref'):
            print(f"  API Key Ref:  {provider_info['embedding_api_key_ref']}")

    # Index configuration
    index_config = info['index_config']
    if index_config.get('hnsw_space'):
        print(f"\n{c.BOLD}Index Configuration:{c.END}")
        print(f"  Distance:     {index_config['hnsw_space']}")

    # Sample documents (if verbose)
    if 'sample_documents' in info:
        print(f"\n{c.BOLD}Sample Documents:{c.END}")
        samples = info['sample_documents']
        for i, (doc, meta) in enumerate(zip(samples.get('documents', []), samples.get('metadatas', [])), 1):
            print(f"\n  {c.YELLOW}Sample {i}:{c.END}")
            print(f"    Title:    {meta.get('title', 'N/A')}")
            print(f"    Chunk:    {meta.get('chunkIndex', 'N/A')}")
            content_preview = doc[:100] + "..." if len(doc) > 100 else doc
            print(f"    Content:  {content_preview}")
    elif 'sample_documents_error' in info:
        print(f"\n{c.YELLOW}Note: Could not fetch sample documents: {info['sample_documents_error']}{c.END}")


def print_database_summary(collections: List[Dict[str, Any]], chromadb_path: str, use_colors: bool = True) -> None:
    """Print overall database summary."""
    c = Colors if use_colors else type('NoColors', (), {attr: '' for attr in dir(Colors) if not attr.startswith('_')})()

    total_chunks = sum(col['chunk_count'] for col in collections)

    print(f"\n{c.BOLD}{c.GREEN}{'='*80}{c.END}")
    print(f"{c.BOLD}ChromaDB Database Summary{c.END}")
    print(f"{c.GREEN}{'='*80}{c.END}")
    print(f"\n  Location:          {chromadb_path}")
    print(f"  Total Collections: {c.BOLD}{len(collections)}{c.END}")
    print(f"  Total Chunks:      {c.BOLD}{total_chunks:,}{c.END}")

    if collections:
        # Provider breakdown
        providers = {}
        for col in collections:
            provider = col['ai_provider'].get('embedding_provider') or 'Unknown'
            providers[provider] = providers.get(provider, 0) + 1

        print(f"\n  {c.BOLD}Providers:{c.END}")
        for provider, count in sorted(providers.items(), key=lambda x: (x[0] or 'zzz', x[1])):
            print(f"    {provider}: {count} collection(s)")


def inspect_chromadb(chromadb_path: str, collection_name: Optional[str] = None,
                     verbose: bool = False, output_json: bool = False) -> Dict[str, Any]:
    """
    Inspect ChromaDB database and return collection information.

    Args:
        chromadb_path: Path to ChromaDB database directory
        collection_name: Optional specific collection to inspect
        verbose: Include sample documents and detailed info
        output_json: Output results as JSON

    Returns:
        Dictionary containing collection information
    """
    # Validate path
    db_path = Path(chromadb_path).resolve()
    if not db_path.exists():
        print(f"Error: ChromaDB path does not exist: {chromadb_path}", file=sys.stderr)
        sys.exit(1)

    if not db_path.is_dir():
        print(f"Error: ChromaDB path is not a directory: {chromadb_path}", file=sys.stderr)
        sys.exit(1)

    # Initialize ChromaDB client
    try:
        client = chromadb.PersistentClient(path=str(db_path))
    except Exception as e:
        print(f"Error: Failed to connect to ChromaDB: {e}", file=sys.stderr)
        sys.exit(1)

    # Get collections
    try:
        all_collections = client.list_collections()
    except Exception as e:
        print(f"Error: Failed to list collections: {e}", file=sys.stderr)
        sys.exit(1)

    if not all_collections:
        print(f"No collections found in ChromaDB at: {chromadb_path}")
        return {"collections": [], "database_path": str(db_path)}

    # Filter by collection name if specified
    if collection_name:
        all_collections = [col for col in all_collections if col.name == collection_name]
        if not all_collections:
            print(f"Error: Collection '{collection_name}' not found", file=sys.stderr)
            sys.exit(1)

    # Extract information from each collection
    collections_info = []
    for collection in all_collections:
        try:
            info = get_collection_info(collection, verbose=verbose)
            collections_info.append(info)
        except Exception as e:
            print(f"Warning: Failed to extract info from collection '{collection.name}': {e}",
                  file=sys.stderr)

    result = {
        "database_path": str(db_path),
        "total_collections": len(collections_info),
        "collections": collections_info
    }

    # Output results
    if output_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        # Pretty print for terminal
        use_colors = sys.stdout.isatty()

        if not collection_name:
            print_database_summary(collections_info, str(db_path), use_colors)

        for col_info in collections_info:
            print_collection_summary(col_info, use_colors)

        print()  # Final newline

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Inspect ChromaDB collections and metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ../chromadb_data
  %(prog)s ../chromadb_data --json
  %(prog)s ../chromadb_data --collection alice-in-wonderland
  %(prog)s ../chromadb_data --verbose
        """
    )

    parser.add_argument(
        'chromadb_path',
        help='Path to ChromaDB database directory'
    )

    parser.add_argument(
        '-c', '--collection',
        help='Inspect specific collection only',
        metavar='NAME'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show sample documents and detailed information'
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        help='Output results as JSON (for scripting)'
    )

    args = parser.parse_args()

    inspect_chromadb(
        chromadb_path=args.chromadb_path,
        collection_name=args.collection,
        verbose=args.verbose,
        output_json=args.json
    )


if __name__ == "__main__":
    main()
