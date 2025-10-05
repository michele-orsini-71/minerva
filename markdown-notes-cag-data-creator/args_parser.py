import argparse
import sys

def parse_pipeline_args():
    parser = argparse.ArgumentParser(
        description="Complete Markdown Notes RAG pipeline: JSON → Chunks → Embeddings → ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to collection configuration JSON file (defines collection name, description, etc.)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed progress"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validation-only mode: validates configuration and analyzes notes without creating embeddings or modifying ChromaDB"
    )

    args = parser.parse_args()

    return args
