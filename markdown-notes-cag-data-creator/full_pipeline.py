#!/usr/bin/env python3
"""
Complete Bear Notes RAG Pipeline
Processes Bear notes JSON, creates chunks, generates embeddings, and stores in ChromaDB.
"""

import sys
import time

# Import our modules
from args_parser import parse_pipeline_args
from config_validator import load_and_validate_config
from json_loader import load_json_notes
from chunk_creator import create_chunks_from_notes  # New immutable API
from embedding import generate_embeddings, EmbeddingError  # New immutable API
from storage import collection_exists, initialize_chromadb_client, insert_chunks, create_collection, recreate_collection, StorageError  # New immutable API


def calculate_dry_run_estimates(notes, config):
    """Calculate rough estimates for dry-run mode without actual chunking."""
    total_chars = sum(len(note['markdown']) for note in notes)
    avg_note_size = total_chars / len(notes) if notes else 0

    # Rough estimate: assume each chunk is target_chars size
    estimated_chunks = total_chars // config.chunk_size
    # Account for overlap and header boundaries (roughly +20% chunks)
    estimated_chunks = int(estimated_chunks * 1.2)

    # Estimate: ~4 bytes per dimension for embeddings (1024 dimensions typical)
    estimated_embedding_size = estimated_chunks * 1024 * 4 / (1024 * 1024)  # MB
    estimated_metadata_size = estimated_chunks * 0.001  # Rough estimate: 1KB per chunk metadata
    total_estimated_size = estimated_embedding_size + estimated_metadata_size

    return {
        'total_chars': total_chars,
        'avg_note_size': avg_note_size,
        'estimated_chunks': estimated_chunks,
        'total_estimated_size': total_estimated_size
    }


def print_dry_run_summary(config, notes, estimates, exists):
    """Print comprehensive dry-run summary."""
    print(f"Collection Configuration:")
    print(f"   Name: {config.collection_name}")
    print(f"   Description: {config.description}")
    print(f"   Force Recreate: {config.force_recreate}")
    print()
    print(f"Data Analysis:")
    print(f"   Source file: {config.json_file}")
    print(f"   Notes loaded: {len(notes)}")
    print(f"   Total content: {estimates['total_chars']:,} characters")
    print(f"   Average note size: {estimates['avg_note_size']:.0f} characters")
    print(f"   Target chunk size: {config.chunk_size} characters")
    print()
    print(f"Estimates (without actual chunking):")
    print(f"   Estimated chunks: ~{estimates['estimated_chunks']:,}")
    print(f"   Estimated storage: ~{estimates['total_estimated_size']:.2f} MB")
    print(f"   Note: Actual values may vary by ±20% depending on content structure")
    print()
    print(f"Collection Status:")
    print(f"   ChromaDB path: {config.chromadb_path}")
    print(f"   Collection exists: {'YES' if exists else 'NO'}")


def validate_dry_run_config(config, exists):
    """Validate configuration in dry-run mode and exit if invalid."""
    if exists and config.force_recreate:
        print(f"   Action: Will DELETE and recreate (WARNING: destructive!)")
    elif exists and not config.force_recreate:
        print(f"   Action: Will FAIL (collection exists, forceRecreate=false)")
        print(f"   ERROR: Configuration would fail in real run!")
        print(f"   Fix: Set 'forceRecreate': true or use different collection name")
        print()
        print("=" * 60)
        print("DRY-RUN VALIDATION FAILED")
        sys.exit(1)
    else:
        print(f"   Action: Will create new collection")


def run_dry_run_mode(config, args, notes):
    """Execute dry-run validation mode."""
    print("DRY-RUN PREVIEW (fast validation mode)")
    print("=" * 60)

    # Check if collection exists
    client = initialize_chromadb_client(config.chromadb_path)
    exists = collection_exists(client, config.collection_name)

    # Calculate estimates
    estimates = calculate_dry_run_estimates(notes, config)

    # Print summary
    print_dry_run_summary(config, notes, estimates, exists)

    # Validate and potentially exit
    validate_dry_run_config(config, exists)

    print()
    print("=" * 60)
    print("DRY-RUN VALIDATION SUCCESSFUL")
    print("Configuration is valid and ready for processing")
    print(f"Run without --dry-run to execute the pipeline")
    sys.exit(0)


def run_normal_pipeline(config, args, notes, start_time):
    """Execute the normal RAG pipeline with chunking, embedding, and storage."""
    # Create chunks (immutable)
    print("Creating semantic chunks...")
    chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
    print(f"   Created {len(chunks)} chunks from {len(notes)} notes")
    print()

    # Initialize storage
    client = initialize_chromadb_client(config.chromadb_path)

    # Generate embeddings (immutable)
    print("Generating embeddings with Ollama...")
    chunks_with_embeddings = generate_embeddings(chunks)
    print(f"   Generated {len(chunks_with_embeddings)} embeddings")
    print()

    # Store in ChromaDB (immutable)
    print(f"Storing in ChromaDB collection '{config.collection_name}'...")

    # Use explicit function based on force_recreate flag
    if config.force_recreate:
        collection = recreate_collection(
            client,
            collection_name=config.collection_name,
            description=config.description
        )
    else:
        collection = create_collection(
            client,
            collection_name=config.collection_name,
            description=config.description
        )

    def progress_callback(current, total):
        if args.verbose:
            print(f"   Storing: {current}/{total} chunks ({current/total*100:.1f}%)")

    stats = insert_chunks(collection, chunks_with_embeddings, progress_callback=progress_callback)
    print(f"   Stored {stats['successful']} chunks in collection '{config.collection_name}'")
    if stats['failed'] > 0:
        print(f"   Failed to store {stats['failed']} chunks")
    print()

    return chunks, chunks_with_embeddings, stats


def print_pipeline_summary(config, notes, chunks, chunks_with_embeddings, stats, processing_time):
    """Print final pipeline execution summary."""
    print("Pipeline completed successfully!")
    print("=" * 60)
    print(f"Collection: {config.collection_name}")
    print(f"Description: {config.description[:60]}...")
    print(f"Notes processed: {len(notes)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Embeddings generated: {len(chunks_with_embeddings)}")
    print(f"Chunks stored: {stats['successful']}")
    print(f"Processing time: {processing_time:.1f} seconds")
    print(f"Performance: {len(chunks) / processing_time:.1f} chunks/second")
    print()
    print(f"Collection '{config.collection_name}' ready for RAG queries")
    print(f"   Database location: {config.chromadb_path}")


def handle_embedding_error(error, config_path):
    """Handle embedding generation errors with actionable guidance."""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"EMBEDDING GENERATION ERROR", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"\nError: {error}", file=sys.stderr)
    print(f"\nActionable Steps:", file=sys.stderr)
    print(f"  1. Check if Ollama is running:", file=sys.stderr)
    print(f"     $ ollama serve", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  2. Verify the embedding model is available:", file=sys.stderr)
    print(f"     $ ollama list", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  3. If model is missing, pull it:", file=sys.stderr)
    print(f"     $ ollama pull mxbai-embed-large:latest", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  4. Test the model manually:", file=sys.stderr)
    print(f"     $ ollama run mxbai-embed-large:latest \"test\"", file=sys.stderr)
    print(f"\nConfiguration file: {config_path}", file=sys.stderr)
    sys.exit(1)


def handle_file_not_found_error(error, config_path):
    """Handle file not found errors with actionable guidance."""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"FILE NOT FOUND ERROR", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"\nError: {error}", file=sys.stderr)
    print(f"\nActionable Steps:", file=sys.stderr)
    print(f"  1. Check the file path in your configuration:", file=sys.stderr)
    print(f"     Configuration file: {config_path}", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  2. Verify the JSON file exists:", file=sys.stderr)
    print(f"     $ ls -la <json_file_path>", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  3. Use absolute paths or verify relative paths are correct", file=sys.stderr)
    print(f"\nTip: Use --dry-run to validate configuration before processing", file=sys.stderr)
    sys.exit(1)


def handle_storage_error(error, collection_name, config_path):
    """Handle storage errors with actionable guidance."""
    print(f"\nStorage Error:\n{error}", file=sys.stderr)
    print(f"\nCollection: {collection_name}", file=sys.stderr)
    print(f"Configuration file: {config_path}", file=sys.stderr)
    sys.exit(1)


def handle_unexpected_error(error, config_path, is_dry_run):
    """Handle unexpected errors with actionable guidance."""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"UNEXPECTED ERROR", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"\nError: {error}", file=sys.stderr)
    print(f"\nDebug Information:", file=sys.stderr)
    print(f"  Configuration file: {config_path}", file=sys.stderr)
    print(f"  Mode: {'DRY-RUN' if is_dry_run else 'NORMAL'}", file=sys.stderr)
    print(f"\nActionable Steps:", file=sys.stderr)
    print(f"  1. Try running with --dry-run to identify issues:", file=sys.stderr)
    print(f"     $ python full_pipeline.py --config {config_path} --dry-run", file=sys.stderr)
    print(f"", file=sys.stderr)
    print(f"  2. Check the configuration file format", file=sys.stderr)
    print(f"  3. Verify all required dependencies are installed:", file=sys.stderr)
    print(f"     $ pip list | grep -E '(chromadb|ollama|langchain)'", file=sys.stderr)
    print(f"\nIf the issue persists, please report it with the full error message", file=sys.stderr)
    sys.exit(1)


def execute_pipeline_mode(config, args, notes, start_time):
    """Execute either dry-run or normal pipeline mode."""
    if args.dry_run:
        run_dry_run_mode(config, args, notes)
        return  # dry_run_mode calls sys.exit, but this helps clarity

    chunks, chunks_with_embeddings, stats = run_normal_pipeline(config, args, notes, start_time)
    processing_time = time.time() - start_time
    print_pipeline_summary(config, notes, chunks, chunks_with_embeddings, stats, processing_time)


def load_config_with_verbose_output(args):
    """Load and optionally print configuration details."""
    config = load_and_validate_config(args.config, verbose=args.verbose)

    if args.verbose:
        print(f"   Input file: {config.json_file}")
        print(f"   Target chunk size: {config.chunk_size} characters")
        print(f"   ChromaDB path: {config.chromadb_path}")
        print(f"   Collection: {config.collection_name}")
        print()

    return config


def load_notes_with_verbose_output(config, verbose):
    """Load notes and optionally print statistics."""
    print("Loading notes JSON...")
    notes = load_json_notes(config.json_file)

    if verbose:
        total_chars = sum(len(note['markdown']) for note in notes)
        avg_chars = total_chars / len(notes) if notes else 0
        print(f"   Loaded {len(notes)} notes")
        print(f"   Total content: {total_chars:,} characters")
        print(f"   Average note size: {avg_chars:.0f} characters")
        print()

    return notes


def main():
    args = parse_pipeline_args()
    start_time = time.time()

    print("Markdown Notes Multi-Collection RAG Pipeline")
    if args.dry_run:
        print("DRY-RUN MODE: Validation only, no data will be modified")
    print("=" * 60)

    try:
        config = load_config_with_verbose_output(args)
    except KeyboardInterrupt:
        print("\n   Operation cancelled by user", file=sys.stderr)
        sys.exit(130)

    try:
        notes = load_notes_with_verbose_output(config, args.verbose)
        execute_pipeline_mode(config, args, notes, start_time)
    except KeyboardInterrupt:
        print("\n   Operation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except StorageError as error:
        handle_storage_error(error, config.collection_name, args.config)
    except EmbeddingError as error:
        handle_embedding_error(error, args.config)
    except FileNotFoundError as error:
        handle_file_not_found_error(error, args.config)
    except Exception as error:
        handle_unexpected_error(error, args.config, args.dry_run)


if __name__ == "__main__":
    main()