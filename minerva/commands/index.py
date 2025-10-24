import sys
import time
from argparse import Namespace
from typing import Dict, Any, List

from minerva.common.config_loader import load_collection_config, ConfigError, CollectionConfig
from minerva.common.ai_provider import AIProvider, AIProviderError
from minerva.indexing.json_loader import load_json_notes
from minerva.indexing.chunking import create_chunks_from_notes
from minerva.indexing.embeddings import initialize_provider, generate_embeddings, EmbeddingError
from minerva.indexing.storage import (
    initialize_chromadb_client,
    create_collection,
    recreate_collection,
    insert_chunks,
    StorageError
)
from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")


def print_banner(is_dry_run: bool) -> None:
    logger.info("")
    logger.info("Minervium Index Command")
    if is_dry_run:
        logger.warning("DRY-RUN MODE: Validation only, no data will be modified")
    logger.info("=" * 60)


def load_and_print_config(config_path: str, verbose: bool) -> CollectionConfig:
    logger.info("")
    logger.info(f"Loading configuration from: {config_path}")

    try:
        config = load_collection_config(str(config_path))

        if verbose:
            logger.info(f"   Collection name: {config.collection_name}")
            logger.info(f"   Description: {config.description[:80]}...")
            logger.info(f"   ChromaDB path: {config.chromadb_path}")
            logger.info(f"   JSON file: {config.json_file}")
            logger.info(f"   Chunk size: {config.chunk_size} characters")
            logger.info(f"   Force recreate: {config.force_recreate}")
            logger.info(f"   Skip AI validation: {config.skip_ai_validation}")

            if config.ai_provider:
                provider_type = config.ai_provider.get('type', 'unknown')
                embedding_model = config.ai_provider.get('embedding', {}).get('model', 'unknown')
                llm_model = config.ai_provider.get('llm', {}).get('model', 'unknown')
                logger.info(f"   AI provider: {provider_type}")
                logger.info(f"   Embedding model: {embedding_model}")
                logger.info(f"   LLM model: {llm_model}")

        logger.success("   ✓ Configuration loaded successfully")
        logger.info("")
        return config

    except ConfigError as e:
        logger.error(f"Configuration Error:\n{e}")
        sys.exit(1)


def load_and_print_notes(config: CollectionConfig, verbose: bool) -> List[Dict[str, Any]]:
    logger.info("Loading notes from JSON file...")

    try:
        notes = load_json_notes(config.json_file)

        if verbose:
            total_chars = sum(len(note['markdown']) for note in notes)
            avg_chars = total_chars / len(notes) if notes else 0
            logger.info(f"   Loaded {len(notes)} notes")
            logger.info(f"   Total content: {total_chars:,} characters")
            logger.info(f"   Average note size: {avg_chars:.0f} characters")
        else:
            logger.success(f"   ✓ Loaded {len(notes)} notes")

        logger.info("")
        return notes

    except Exception as e:
        logger.error(f"Error loading notes: {e}")
        sys.exit(1)


def initialize_and_validate_provider(config: CollectionConfig, verbose: bool) -> AIProvider:
    logger.info("Initializing AI provider...")

    try:
        provider = initialize_provider(config)

        # Check provider availability
        availability = provider.check_availability()
        if not availability['available']:
            error_msg = availability.get('error', 'Unknown error')
            logger.error("")
            logger.error("=" * 60)
            logger.error("PROVIDER UNAVAILABLE")
            logger.error("=" * 60)
            logger.error("")
            logger.error(f"Provider: {provider.provider_type}")
            logger.error(f"Model: {provider.embedding_model}")
            logger.error(f"Error: {error_msg}")
            logger.error("")
            logger.error("Suggestion: Check that the provider service is running")
            if provider.provider_type == 'ollama':
                logger.error("  $ ollama serve")
                logger.error(f"  $ ollama pull {provider.embedding_model}")
            sys.exit(1)

        # Print provider details
        dimension = availability.get('dimension', 'unknown')
        logger.info(f"   Provider: {provider.provider_type}")
        logger.info(f"   Embedding model: {provider.embedding_model}")
        logger.info(f"   LLM model: {provider.llm_model}")
        logger.info(f"   Embedding dimension: {dimension}")
        logger.success("   Status: ✓ Available")

        if not config.skip_ai_validation:
            if verbose:
                logger.info("")
                logger.info("   Validating collection description with AI...")
            validation_result = provider.validate_description(config.description)
            score = validation_result.get('score', 0)
            feedback = validation_result.get('feedback', 'No feedback available')

            if verbose:
                logger.info(f"   Description score: {score}/10")
                logger.info(f"   Feedback: {feedback}")

            if score < 7:
                logger.warning("   ⚠ Warning: Description score is below 7")

        logger.info("")
        return provider

    except AIProviderError as e:
        logger.error(f"Provider initialization error: {e}")
        sys.exit(1)


def run_dry_run(config: CollectionConfig, notes: List[Dict[str, Any]], verbose: bool) -> None:
    logger.info("Running dry-run validation...")
    logger.info("")

    _ = initialize_and_validate_provider(config, verbose)

    logger.info("Creating semantic chunks (validation only)...")
    chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
    logger.success(f"   ✓ Would create {len(chunks)} chunks from {len(notes)} notes")
    logger.info("")

    # Estimate what would happen
    logger.info("Dry-run summary:")
    logger.info(f"   Collection: {config.collection_name}")
    logger.info(f"   Notes to process: {len(notes)}")
    logger.info(f"   Chunks to create: {len(chunks)}")
    logger.info(f"   Embeddings to generate: {len(chunks)}")
    logger.info(f"   ChromaDB location: {config.chromadb_path}")
    logger.info(f"   Force recreate: {config.force_recreate}")
    logger.info("")
    logger.success("✓ Dry-run validation completed successfully!")
    logger.info("   Run without --dry-run to perform actual indexing")


def run_full_indexing(
    config: CollectionConfig,
    notes: List[Dict[str, Any]],
    verbose: bool,
    start_time: float
) -> None:

    provider = initialize_and_validate_provider(config, verbose)
    embedding_metadata = provider.get_embedding_metadata()

    logger.info("Creating semantic chunks...")
    chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
    logger.success(f"   ✓ Created {len(chunks)} chunks from {len(notes)} notes")
    logger.info("")

    logger.info("Generating embeddings...")
    try:
        chunks_with_embeddings = generate_embeddings(provider, chunks)
        logger.success(f"   ✓ Generated {len(chunks_with_embeddings)} embeddings")
        logger.info("")
    except EmbeddingError as e:
        logger.error(f"Embedding generation error: {e}")
        sys.exit(1)

    logger.info(f"Initializing ChromaDB at: {config.chromadb_path}")
    try:
        client = initialize_chromadb_client(config.chromadb_path)
        logger.success("   ✓ ChromaDB client initialized")
        logger.info("")
    except Exception as e:
        logger.error(f"ChromaDB initialization error: {e}")
        sys.exit(1)

    logger.info(f"Preparing collection '{config.collection_name}'...")
    try:
        if config.force_recreate:
            collection = recreate_collection(
                client,
                collection_name=config.collection_name,
                description=config.description,
                embedding_metadata=embedding_metadata
            )
            logger.success("   ✓ Collection recreated")
        else:
            collection = create_collection(
                client,
                collection_name=config.collection_name,
                description=config.description,
                embedding_metadata=embedding_metadata
            )
            logger.success("   ✓ Collection ready")
        logger.info("")
    except StorageError as e:
        logger.error(f"Collection creation error: {e}")
        sys.exit(1)

    # Insert chunks
    logger.info("Storing chunks in ChromaDB...")

    def progress_callback(current, total):
        if verbose:
            percentage = (current / total * 100) if total > 0 else 0
            logger.info(f"   Progress: {current}/{total} chunks ({percentage:.1f}%)")

    try:
        stats = insert_chunks(collection, chunks_with_embeddings, progress_callback=progress_callback)
        logger.success(f"   ✓ Stored {stats['successful']} chunks")
        if stats['failed'] > 0:
            logger.warning(f"   ⚠ Failed to store {stats['failed']} chunks")
        logger.info("")
    except StorageError as e:
        logger.error(f"Storage error: {e}")
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
    logger.info("=" * 60)
    logger.success("✓ Indexing completed successfully!")
    logger.info("=" * 60)
    logger.info(f"Collection: {config.collection_name}")
    logger.info(f"Description: {config.description[:60]}...")
    logger.info(f"Notes processed: {len(notes)}")
    logger.info(f"Chunks created: {len(chunks)}")
    logger.info(f"Embeddings generated: {len(chunks_with_embeddings)}")
    logger.info(f"Chunks stored: {stats['successful']}")
    logger.info(f"Processing time: {processing_time:.1f} seconds")

    if len(chunks) > 0 and processing_time > 0:
        logger.info(f"Performance: {len(chunks) / processing_time:.1f} chunks/second")

    logger.info("")
    logger.info(f"Collection '{config.collection_name}' is ready for queries")
    logger.info(f"Database location: {config.chromadb_path}")
    logger.info("")


def run_index(args: Namespace) -> int:
    start_time = time.time()

    try:
        # Print banner
        print_banner(args.dry_run)

        config = load_and_print_config(args.config, args.verbose)

        notes = load_and_print_notes(config, args.verbose)

        # Run appropriate mode
        if args.dry_run:
            run_dry_run(config, notes, args.verbose)
        else:
            run_full_indexing(config, notes, args.verbose, start_time)

        return 0

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
