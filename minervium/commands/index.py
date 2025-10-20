"""
Index command - Index markdown notes into ChromaDB with embeddings.
"""

import sys
import time
from argparse import Namespace
from typing import Dict, Any, List

from minervium.common.config_loader import load_collection_config, ConfigError, CollectionConfig
from minervium.common.ai_provider import AIProvider, AIProviderError
from minervium.indexing.json_loader import load_json_notes
from minervium.indexing.chunking import create_chunks_from_notes
from minervium.indexing.embeddings import initialize_provider, generate_embeddings, EmbeddingError
from minervium.indexing.storage import (
    initialize_chromadb_client,
    create_collection,
    recreate_collection,
    insert_chunks,
    StorageError
)


def print_banner(is_dry_run: bool) -> None:
    """Print command banner."""
    print("\nMinervium Index Command")
    if is_dry_run:
        print("DRY-RUN MODE: Validation only, no data will be modified")
    print("=" * 60)


def load_and_print_config(config_path: str, verbose: bool) -> CollectionConfig:
    """Load configuration and optionally print details."""
    print(f"\nLoading configuration from: {config_path}")

    try:
        config = load_collection_config(str(config_path))

        if verbose:
            print(f"   Collection name: {config.collection_name}")
            print(f"   Description: {config.description[:80]}...")
            print(f"   ChromaDB path: {config.chromadb_path}")
            print(f"   JSON file: {config.json_file}")
            print(f"   Chunk size: {config.chunk_size} characters")
            print(f"   Force recreate: {config.force_recreate}")
            print(f"   Skip AI validation: {config.skip_ai_validation}")

            if config.ai_provider:
                provider_type = config.ai_provider.get('type', 'unknown')
                embedding_model = config.ai_provider.get('embedding', {}).get('model', 'unknown')
                llm_model = config.ai_provider.get('llm', {}).get('model', 'unknown')
                print(f"   AI provider: {provider_type}")
                print(f"   Embedding model: {embedding_model}")
                print(f"   LLM model: {llm_model}")

        print("   ✓ Configuration loaded successfully\n")
        return config

    except ConfigError as e:
        print(f"\n✗ Configuration Error:\n{e}", file=sys.stderr)
        sys.exit(1)


def load_and_print_notes(config: CollectionConfig, verbose: bool) -> List[Dict[str, Any]]:
    """Load notes from JSON file and optionally print statistics."""
    print("Loading notes from JSON file...")

    try:
        notes = load_json_notes(config.json_file)

        if verbose:
            total_chars = sum(len(note['markdown']) for note in notes)
            avg_chars = total_chars / len(notes) if notes else 0
            print(f"   Loaded {len(notes)} notes")
            print(f"   Total content: {total_chars:,} characters")
            print(f"   Average note size: {avg_chars:.0f} characters")
        else:
            print(f"   ✓ Loaded {len(notes)} notes")

        print()
        return notes

    except Exception as e:
        print(f"\n✗ Error loading notes: {e}", file=sys.stderr)
        sys.exit(1)


def initialize_and_validate_provider(config: CollectionConfig, verbose: bool) -> AIProvider:
    """Initialize AI provider and check availability."""
    print("Initializing AI provider...")

    try:
        provider = initialize_provider(config)

        # Check provider availability
        availability = provider.check_availability()
        if not availability['available']:
            error_msg = availability.get('error', 'Unknown error')
            print(f"\n{'=' * 60}", file=sys.stderr)
            print(f"PROVIDER UNAVAILABLE", file=sys.stderr)
            print(f"{'=' * 60}", file=sys.stderr)
            print(f"\nProvider: {provider.provider_type}", file=sys.stderr)
            print(f"Model: {provider.embedding_model}", file=sys.stderr)
            print(f"Error: {error_msg}", file=sys.stderr)
            print(f"\nSuggestion: Check that the provider service is running", file=sys.stderr)
            if provider.provider_type == 'ollama':
                print(f"  $ ollama serve", file=sys.stderr)
                print(f"  $ ollama pull {provider.embedding_model}", file=sys.stderr)
            sys.exit(1)

        # Print provider details
        dimension = availability.get('dimension', 'unknown')
        print(f"   Provider: {provider.provider_type}")
        print(f"   Embedding model: {provider.embedding_model}")
        print(f"   LLM model: {provider.llm_model}")
        print(f"   Embedding dimension: {dimension}")
        print(f"   Status: ✓ Available")

        # Validate description if not skipped
        if not config.skip_ai_validation:
            if verbose:
                print("\n   Validating collection description with AI...")
            validation_result = provider.validate_description(config.description)
            score = validation_result.get('score', 0)
            feedback = validation_result.get('feedback', 'No feedback available')

            if verbose:
                print(f"   Description score: {score}/10")
                print(f"   Feedback: {feedback}")

            if score < 7:
                print(f"   ⚠ Warning: Description score is below 7", file=sys.stderr)

        print()
        return provider

    except AIProviderError as e:
        print(f"\n✗ Provider initialization error: {e}", file=sys.stderr)
        sys.exit(1)


def run_dry_run(config: CollectionConfig, notes: List[Dict[str, Any]], verbose: bool) -> None:
    """Run dry-run validation mode."""
    print("Running dry-run validation...")
    print()

    # Validate provider (but don't generate embeddings)
    provider = initialize_and_validate_provider(config, verbose)

    # Create chunks to validate the chunking process
    print("Creating semantic chunks (validation only)...")
    chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
    print(f"   ✓ Would create {len(chunks)} chunks from {len(notes)} notes")
    print()

    # Estimate what would happen
    print("Dry-run summary:")
    print(f"   Collection: {config.collection_name}")
    print(f"   Notes to process: {len(notes)}")
    print(f"   Chunks to create: {len(chunks)}")
    print(f"   Embeddings to generate: {len(chunks)}")
    print(f"   ChromaDB location: {config.chromadb_path}")
    print(f"   Force recreate: {config.force_recreate}")
    print()
    print("✓ Dry-run validation completed successfully!")
    print("   Run without --dry-run to perform actual indexing")


def run_full_indexing(
    config: CollectionConfig,
    notes: List[Dict[str, Any]],
    verbose: bool,
    start_time: float
) -> None:
    """Run the full indexing pipeline."""

    # Initialize provider
    provider = initialize_and_validate_provider(config, verbose)
    embedding_metadata = provider.get_embedding_metadata()

    # Create chunks
    print("Creating semantic chunks...")
    chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
    print(f"   ✓ Created {len(chunks)} chunks from {len(notes)} notes")
    print()

    # Generate embeddings
    print("Generating embeddings...")
    try:
        chunks_with_embeddings = generate_embeddings(provider, chunks)
        print(f"   ✓ Generated {len(chunks_with_embeddings)} embeddings")
        print()
    except EmbeddingError as e:
        print(f"\n✗ Embedding generation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize ChromaDB
    print(f"Initializing ChromaDB at: {config.chromadb_path}")
    try:
        client = initialize_chromadb_client(config.chromadb_path)
        print(f"   ✓ ChromaDB client initialized")
        print()
    except Exception as e:
        print(f"\n✗ ChromaDB initialization error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create or recreate collection
    print(f"Preparing collection '{config.collection_name}'...")
    try:
        if config.force_recreate:
            collection = recreate_collection(
                client,
                collection_name=config.collection_name,
                description=config.description,
                embedding_metadata=embedding_metadata
            )
            print(f"   ✓ Collection recreated")
        else:
            collection = create_collection(
                client,
                collection_name=config.collection_name,
                description=config.description,
                embedding_metadata=embedding_metadata
            )
            print(f"   ✓ Collection ready")
        print()
    except StorageError as e:
        print(f"\n✗ Collection creation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Insert chunks
    print("Storing chunks in ChromaDB...")

    def progress_callback(current, total):
        if verbose:
            percentage = (current / total * 100) if total > 0 else 0
            print(f"   Progress: {current}/{total} chunks ({percentage:.1f}%)")

    try:
        stats = insert_chunks(collection, chunks_with_embeddings, progress_callback=progress_callback)
        print(f"   ✓ Stored {stats['successful']} chunks")
        if stats['failed'] > 0:
            print(f"   ⚠ Failed to store {stats['failed']} chunks", file=sys.stderr)
        print()
    except StorageError as e:
        print(f"\n✗ Storage error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print final summary
    processing_time = time.time() - start_time
    print_final_summary(config, notes, chunks, chunks_with_embeddings, stats, processing_time)


def print_final_summary(
    config: CollectionConfig,
    notes: List[Dict[str, Any]],
    chunks: List[Any],
    chunks_with_embeddings: List[Any],
    stats: Dict[str, int],
    processing_time: float
) -> None:
    """Print final indexing summary."""
    print("=" * 60)
    print("✓ Indexing completed successfully!")
    print("=" * 60)
    print(f"Collection: {config.collection_name}")
    print(f"Description: {config.description[:60]}...")
    print(f"Notes processed: {len(notes)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Embeddings generated: {len(chunks_with_embeddings)}")
    print(f"Chunks stored: {stats['successful']}")
    print(f"Processing time: {processing_time:.1f} seconds")

    if len(chunks) > 0 and processing_time > 0:
        print(f"Performance: {len(chunks) / processing_time:.1f} chunks/second")

    print()
    print(f"Collection '{config.collection_name}' is ready for queries")
    print(f"Database location: {config.chromadb_path}")
    print()


def run_index(args: Namespace) -> int:
    """
    Main entry point for the index command.

    Args:
        args: Parsed command-line arguments containing:
            - config: Path to configuration file
            - verbose: Enable verbose output
            - dry_run: Run validation only

    Returns:
        Exit code (0 for success, 1 for error)
    """
    start_time = time.time()

    try:
        # Print banner
        print_banner(args.dry_run)

        # Load configuration
        config = load_and_print_config(args.config, args.verbose)

        # Load notes
        notes = load_and_print_notes(config, args.verbose)

        # Run appropriate mode
        if args.dry_run:
            run_dry_run(config, notes, args.verbose)
        else:
            run_full_indexing(config, notes, args.verbose, start_time)

        return 0

    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
