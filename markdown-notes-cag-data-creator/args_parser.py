#!/usr/bin/env python3
"""
Argument parsing for the Bear Notes RAG Pipeline.
Centralizes all CLI argument configuration and validation.
"""

import argparse
import sys
from storage import DEFAULT_CHROMADB_PATH


def parse_pipeline_args():
    """
    Parse and validate command-line arguments for the RAG pipeline.

    Returns:
        argparse.Namespace: Parsed and validated arguments containing:
            - json_file: Path to input JSON file
            - config: Path to collection configuration JSON
            - chunk_size: Target chunk size in characters
            - chromadb_path: ChromaDB storage path
            - verbose: Whether to enable verbose output

    Exits:
        sys.exit(1) if arguments are invalid
    """
    parser = argparse.ArgumentParser(
        description="Complete Bear Notes RAG pipeline: JSON → Chunks → Embeddings → ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config collections/bear_notes_config.json notes.json
  %(prog)s --config collections/wikipedia_history_config.json --chunk-size 800 --verbose wiki.json
  %(prog)s --config my_collection.json --chromadb-path ./my_db notes.json

This tool runs the complete multi-collection pipeline:
1. Loads and validates collection configuration
2. Validates collection name and description (with optional AI quality check)
3. Loads notes from JSON file
4. Creates semantic chunks
5. Generates embeddings using Ollama
6. Stores everything in ChromaDB with collection metadata
        """
    )

    parser.add_argument(
        "json_file",
        help="Path to Bear notes JSON file"
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to collection configuration JSON file (defines collection name, description, etc.)"
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1200,
        help="Target chunk size in characters (default: 1200)"
    )

    parser.add_argument(
        "--chromadb-path",
        default=DEFAULT_CHROMADB_PATH,
        help=f"ChromaDB storage path (default: {DEFAULT_CHROMADB_PATH})"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed progress"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.chunk_size <= 0:
        print("Error: Chunk size must be positive", file=sys.stderr)
        sys.exit(1)

    return args
