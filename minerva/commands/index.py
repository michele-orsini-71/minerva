import time
from argparse import Namespace
from typing import Any, Dict, List, Tuple

from minerva.common.ai_provider import AIProvider, AIProviderError
from minerva.common.config_loader import (
    IndexingCollectionConfig,
    UnifiedConfig,
    load_unified_config,
)
from minerva.indexing.json_loader import load_json_notes
from minerva.indexing.chunking import create_chunks_from_notes
from minerva.indexing.embeddings import initialize_provider, generate_embeddings, EmbeddingError
from minerva.indexing.storage import (
    initialize_chromadb_client,
    collection_exists,
    create_collection,
    recreate_collection,
    insert_chunks,
    StorageError,
)
from minerva.indexing.updater import (
    run_incremental_update,
    is_v1_collection,
    detect_config_changes,
    format_v1_collection_error,
    format_config_change_error
)
from minerva.common.logger import get_logger
from minerva.common.exceptions import (
    ConfigError,
    IncrementalUpdateError,
    IndexingError,
    JsonLoaderError,
    MinervaError,
    ProviderUnavailableError,
    resolve_exit_code,
)

logger = get_logger(__name__, simple=True, mode="cli")


def print_banner(is_dry_run: bool) -> None:
    logger.info("")
    logger.info("Minerva Index Command")
    if is_dry_run:
        logger.warning("DRY-RUN MODE: Validation only, no data will be modified")
    logger.info("=" * 60)


def load_and_print_config(
    config_path: str,
    verbose: bool
) -> Tuple[UnifiedConfig, IndexingCollectionConfig]:
    logger.info("")
    logger.info(f"Loading configuration from: {config_path}")

    try:
        unified_config = load_unified_config(str(config_path))
    except ConfigError as error:
        logger.error(f"Configuration Error:\n{error}")
        raise

    collections = list(unified_config.indexing.collections)
    if not collections:
        raise ConfigError("No collections defined in indexing.collections")

    if len(collections) > 1:
        raise ConfigError(
            "Configuration defines multiple collections. "
            "Specify a dedicated config or add a CLI option to select a collection."
        )

    collection = collections[0]
    provider = unified_config.get_provider(collection.ai_provider_id)

    logger.success("   ✓ Configuration loaded successfully")

    if verbose:
        logger.info(f"   Collection name: {collection.collection_name}")
        logger.info(f"   Description: {collection.description[:80]}...")
        logger.info(f"   ChromaDB path: {unified_config.indexing.chromadb_path}")
        logger.info(f"   JSON file: {collection.json_file}")
        logger.info(f"   Chunk size: {collection.chunk_size} characters")
        logger.info(f"   Force recreate: {collection.force_recreate}")
        logger.info(f"   Skip AI validation: {collection.skip_ai_validation}")
        logger.info(f"   AI provider: {provider.provider_type}")
        logger.info(f"   Embedding model: {provider.embedding_model}")
        logger.info(f"   LLM model: {provider.llm_model}")

    logger.info("")
    return unified_config, collection


def load_and_print_notes(collection: IndexingCollectionConfig, verbose: bool) -> List[Dict[str, Any]]:
    logger.info("Loading notes from JSON file...")

    try:
        notes = load_json_notes(collection.json_file)

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

    except JsonLoaderError as error:
        logger.error(f"Error loading notes: {error}")
        raise
    except Exception as error:
        message = f"Error loading notes: {error}"
        logger.error(message)
        raise JsonLoaderError(message) from error


def initialize_and_validate_provider(
    unified_config: UnifiedConfig,
    collection: IndexingCollectionConfig,
    verbose: bool
) -> AIProvider:
    logger.info("Initializing AI provider...")

    try:
        provider_config = unified_config.get_ai_provider_config(collection.ai_provider_id)
        provider = initialize_provider(provider_config)

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
            raise ProviderUnavailableError(error_msg)

        # Print provider details
        dimension = availability.get('dimension', 'unknown')
        logger.info(f"   Provider: {provider.provider_type}")
        logger.info(f"   Embedding model: {provider.embedding_model}")
        logger.info(f"   LLM model: {provider.llm_model}")
        logger.info(f"   Embedding dimension: {dimension}")
        logger.success("   Status: ✓ Available")

        if not collection.skip_ai_validation:
            if verbose:
                logger.info("")
                logger.info("   Validating collection description with AI...")
            validation_result = provider.validate_description(collection.description)
            score = validation_result.get('score', 0)
            feedback = validation_result.get('feedback', 'No feedback available')

            if verbose:
                logger.info(f"   Description score: {score}/10")
                logger.info(f"   Feedback: {feedback}")

            if score < 7:
                logger.warning("   ⚠ Warning: Description score is below 7")

        logger.info("")
        return provider

    except ProviderUnavailableError:
        raise
    except AIProviderError as error:
        logger.error(f"Provider initialization error: {error}")
        raise


def check_collection_early(
    chromadb_path: str,
    collection: IndexingCollectionConfig,
    provider: AIProvider
) -> tuple[bool, str]:
    logger.info("Checking ChromaDB collection status...")

    try:
        client = initialize_chromadb_client(chromadb_path)
        exists = collection_exists(client, collection.collection_name)

        if not exists:
            logger.success(f"   ✓ Collection '{collection.collection_name}' does not exist (will be created)")
            logger.info("")
            return False, "create"

        try:
            collection_obj = client.get_collection(collection.collection_name)
        except Exception as error:
            message = f"Failed to retrieve collection '{collection.collection_name}': {error}"
            logger.error(message)
            raise StorageError(message) from error

        if collection.force_recreate:
            logger.warning(f"   Collection '{collection.collection_name}' exists and will be recreated")
            logger.warning("   ⚠ WARNING: All existing data will be permanently deleted!")
            logger.info("")
            return True, "recreate"

        if is_v1_collection(collection_obj):
            error_msg = format_v1_collection_error(collection.collection_name, chromadb_path)
            logger.error(error_msg)
            raise IncrementalUpdateError(error_msg)

        config_change = detect_config_changes(
            collection_obj,
            current_embedding_model=provider.embedding_model,
            current_embedding_provider=provider.provider_type,
            current_chunk_size=collection.chunk_size
        )

        if config_change.has_changes:
            error_msg = format_config_change_error(collection.collection_name, config_change)
            logger.error(error_msg)
            raise IncrementalUpdateError(error_msg)

        logger.success(f"   ✓ Collection '{collection.collection_name}' exists (v2.0)")
        logger.info(f"   Will perform incremental update")
        logger.info("")
        return True, "incremental"

    except MinervaError:
        raise
    except Exception as error:
        message = f"ChromaDB check error: {error}"
        logger.error(message)
        raise IndexingError(message) from error


def run_dry_run(
    unified_config: UnifiedConfig,
    collection: IndexingCollectionConfig,
    notes: List[Dict[str, Any]],
    verbose: bool
) -> None:
    logger.info("Running dry-run validation...")
    logger.info("")

    provider = initialize_and_validate_provider(unified_config, collection, verbose)

    _, mode = check_collection_early(
        unified_config.indexing.chromadb_path,
        collection,
        provider
    )

    logger.info("Creating semantic chunks (validation only)...")
    chunks = create_chunks_from_notes(notes, target_chars=collection.chunk_size)
    logger.success(f"   ✓ Would create {len(chunks)} chunks from {len(notes)} notes")
    logger.info("")

    logger.info("Dry-run summary:")
    logger.info(f"   Collection: {collection.collection_name}")
    logger.info(f"   Mode: {mode}")
    logger.info(f"   Notes to process: {len(notes)}")
    logger.info(f"   Chunks to create: {len(chunks)}")
    logger.info(f"   Embeddings to generate: {len(chunks)}")
    logger.info(f"   ChromaDB location: {unified_config.indexing.chromadb_path}")
    logger.info(f"   Force recreate: {collection.force_recreate}")
    logger.info("")
    logger.success("✓ Dry-run validation completed successfully!")
    logger.info("   Run without --dry-run to perform actual indexing")


def run_incremental_indexing(
    unified_config: UnifiedConfig,
    collection: IndexingCollectionConfig,
    notes: List[Dict[str, Any]],
    verbose: bool,
    start_time: float,
    provider: AIProvider
) -> None:

    chromadb_path = unified_config.indexing.chromadb_path

    logger.info(f"Initializing ChromaDB at: {chromadb_path}")
    client = initialize_chromadb_client(chromadb_path)
    logger.success("   ✓ ChromaDB client initialized")
    logger.info("")

    try:
        collection_obj = client.get_collection(collection.collection_name)
        logger.success(f"   ✓ Retrieved collection '{collection.collection_name}'")
        logger.info("")
    except Exception as error:
        message = f"Failed to retrieve collection: {error}"
        logger.error(message)
        raise StorageError(message) from error

    try:
        stats = run_incremental_update(
            collection=collection_obj,
            new_notes=notes,
            provider=provider,
            new_description=collection.description,
            target_chars=collection.chunk_size
        )
    except MinervaError as error:
        logger.error(f"Incremental update error: {error}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise
    except Exception as error:
        logger.error(f"Incremental update error: {error}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise IndexingError(f"Incremental update error: {error}") from error


def run_full_indexing(
    unified_config: UnifiedConfig,
    collection: IndexingCollectionConfig,
    notes: List[Dict[str, Any]],
    verbose: bool,
    start_time: float,
    provider: AIProvider
) -> None:
    embedding_metadata = provider.get_embedding_metadata()

    logger.info("Creating semantic chunks...")
    chunks = create_chunks_from_notes(notes, target_chars=collection.chunk_size)
    logger.success(f"   ✓ Created {len(chunks)} chunks from {len(notes)} notes")
    logger.info("")

    logger.info("Generating embeddings...")
    try:
        chunks_with_embeddings = generate_embeddings(provider, chunks)
        logger.success(f"   ✓ Generated {len(chunks_with_embeddings)} embeddings")
        logger.info("")
    except EmbeddingError as error:
        logger.error(f"Embedding generation error: {error}")
        raise

    chromadb_path = unified_config.indexing.chromadb_path
    logger.info(f"Initializing ChromaDB at: {chromadb_path}")
    client = initialize_chromadb_client(chromadb_path)
    logger.success("   ✓ ChromaDB client initialized")
    logger.info("")

    logger.info(f"Preparing collection '{collection.collection_name}'...")
    try:
        if collection.force_recreate:
            collection_obj = recreate_collection(
                client,
                collection_name=collection.collection_name,
                description=collection.description,
                embedding_metadata=embedding_metadata,
                chunk_size=collection.chunk_size
            )
            logger.success("   ✓ Collection recreated")
        else:
            collection_obj = create_collection(
                client,
                collection_name=collection.collection_name,
                description=collection.description,
                embedding_metadata=embedding_metadata,
                chunk_size=collection.chunk_size
            )
            logger.success("   ✓ Collection ready")
        logger.info("")
    except StorageError as error:
        logger.error(f"Collection creation error: {error}")
        raise

    logger.info("Storing chunks in ChromaDB...")

    def progress_callback(current, total):
        if verbose:
            percentage = (current / total * 100) if total > 0 else 0
            logger.info(f"   Progress: {current}/{total} chunks ({percentage:.1f}%)")

    try:
        stats = insert_chunks(collection_obj, chunks_with_embeddings, progress_callback=progress_callback)
        logger.success(f"   ✓ Stored {stats['successful']} chunks")
        if stats['failed'] > 0:
            logger.warning(f"   ⚠ Failed to store {stats['failed']} chunks")
        logger.info("")
    except StorageError as error:
        logger.error(f"Storage error: {error}")
        raise

    processing_time = time.time() - start_time
    print_final_summary(
        unified_config,
        collection,
        notes,
        chunks,
        chunks_with_embeddings,
        stats,
        processing_time
    )


def print_final_summary(
    unified_config: UnifiedConfig,
    collection: IndexingCollectionConfig,
    notes: List[Dict[str, Any]],
    chunks: List[Any],
    chunks_with_embeddings: List[Any],
    stats: Dict[str, int],
    processing_time: float
) -> None:
    logger.info("=" * 60)
    logger.success("✓ Indexing completed successfully!")
    logger.info("=" * 60)
    logger.info(f"Collection: {collection.collection_name}")
    logger.info(f"Description: {collection.description[:60]}...")
    logger.info(f"Notes processed: {len(notes)}")
    logger.info(f"Chunks created: {len(chunks)}")
    logger.info(f"Embeddings generated: {len(chunks_with_embeddings)}")
    logger.info(f"Chunks stored: {stats['successful']}")
    logger.info(f"Processing time: {processing_time:.1f} seconds")

    if len(chunks) > 0 and processing_time > 0:
        logger.info(f"Performance: {len(chunks) / processing_time:.1f} chunks/second")

    logger.info("")
    logger.info(f"Collection '{collection.collection_name}' is ready for queries")
    logger.info(f"Database location: {unified_config.indexing.chromadb_path}")
    logger.info("")


def run_index(args: Namespace) -> int:
    start_time = time.time()

    try:
        print_banner(args.dry_run)

        unified_config, collection = load_and_print_config(args.config, args.verbose)

        notes = load_and_print_notes(collection, args.verbose)

        if args.dry_run:
            run_dry_run(unified_config, collection, notes, args.verbose)
        else:
            provider = initialize_and_validate_provider(unified_config, collection, args.verbose)

            _, mode = check_collection_early(
                unified_config.indexing.chromadb_path,
                collection,
                provider
            )

            if mode == "incremental":
                run_incremental_indexing(
                    unified_config,
                    collection,
                    notes,
                    args.verbose,
                    start_time,
                    provider
                )
            else:
                run_full_indexing(
                    unified_config,
                    collection,
                    notes,
                    args.verbose,
                    start_time,
                    provider
                )

        return 0

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return 130

    except MinervaError as error:
        message = str(error).strip()
        if message:
            logger.error(message)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return resolve_exit_code(error)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
