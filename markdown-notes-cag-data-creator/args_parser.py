import argparse
import sys
from storage import DEFAULT_CHROMADB_PATH

def parse_pipeline_args():
    parser = argparse.ArgumentParser(
        description="Complete Markdown Notes RAG pipeline: JSON → Chunks → Embeddings → ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter
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
