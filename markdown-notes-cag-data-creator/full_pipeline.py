#!/usr/bin/env python3
"""
Complete Bear Notes RAG Pipeline
Processes Bear notes JSON, creates chunks, generates embeddings, and stores in ChromaDB.
"""

import sys
import time

from ai_provider import AIProviderError
from args_parser import parse_pipeline_args
from chunk_creator import create_chunks_from_notes
from config_validator import load_and_validate_config
from dry_run import run_dry_run_mode
from embedding import (EmbeddingError, generate_embeddings,
                       initialize_provider)
from json_loader import load_json_notes
from storage import (StorageError, create_collection,
                     initialize_chromadb_client, insert_chunks,
                     recreate_collection)


def initialize_ai_provider(config, args):
    print("Initializing AI provider...")

    try:
        provider = initialize_provider(config)

        availability = provider.check_availability()
        if not availability['available']:
            error_msg = availability.get('error', 'Unknown error')
            print(f"\n{'=' * 60}", file=sys.stderr)
            print(f"PROVIDER UNAVAILABLE", file=sys.stderr)
            print(f"{'=' * 60}", file=sys.stderr)
            print(f"\nProvider: {provider.provider_type}", file=sys.stderr)
            print(f"Model: {provider.embedding_model}", file=sys.stderr)
            print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)

        provider_type = provider.provider_type
        embedding_model = provider.embedding_model
        llm_model = provider.llm_model
        dimension = availability.get('dimension', 'unknown')

        print(f"   Provider: {provider_type}")
        print(f"   Embedding model: {embedding_model}")
        print(f"   LLM model: {llm_model}")
        print(f"   Embedding dimension: {dimension}")
        print(f"   Status: Available")
        print()

        if not config.skip_ai_validation:
            print("Validating collection description...")
            validation_result = provider.validate_description(config.description)
            score = validation_result.get('score', 0)
            feedback = validation_result.get('feedback', 'No feedback available')

            print(f"   Description score: {score}/10")
            print(f"   Feedback: {feedback}")

            if score < 7:
                print(f"   WARNING: Description score is below 7. Consider improving the description.")
            print()

        return provider

    except AIProviderError as error:
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"PROVIDER INITIALIZATION ERROR", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
        print(f"\nError: {error}", file=sys.stderr)
        print(f"\nConfiguration file: {args.config}", file=sys.stderr)
        sys.exit(1)


def run_normal_pipeline(config, args, notes, start_time):
    # Initialize provider
    provider = initialize_ai_provider(config, args)

    # Get embedding metadata from provider instance
    embedding_metadata = provider.get_embedding_metadata()

    # Create chunks (immutable)
    print("Creating semantic chunks...")
    chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
    print(f"   Created {len(chunks)} chunks from {len(notes)} notes")
    print()

    # Initialize storage
    client = initialize_chromadb_client(config.chromadb_path)

    # Generate embeddings using provider instance
    print("Generating embeddings...")
    chunks_with_embeddings = generate_embeddings(provider, chunks)
    print(f"   Generated {len(chunks_with_embeddings)} embeddings")
    print()

    # Store in ChromaDB (immutable)
    print(f"Storing in ChromaDB collection '{config.collection_name}'...")

    # Use explicit function based on force_recreate flag
    if config.force_recreate:
        collection = recreate_collection(
            client,
            collection_name=config.collection_name,
            description=config.description,
            embedding_metadata=embedding_metadata
        )
    else:
        collection = create_collection(
            client,
            collection_name=config.collection_name,
            description=config.description,
            embedding_metadata=embedding_metadata
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


def handle_embedding_error(error, config_path, config):
    """Handle embedding generation errors with actionable guidance."""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"EMBEDDING GENERATION ERROR", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)
    print(f"\nError: {error}", file=sys.stderr)

    provider_type = config.ai_provider.get('type', 'unknown') if config.ai_provider else 'ollama'
    embedding_model = config.ai_provider.get('embedding', {}).get('model', 'unknown') if config.ai_provider else 'mxbai-embed-large:latest'

    print(f"\nProvider: {provider_type}", file=sys.stderr)
    print(f"Model: {embedding_model}", file=sys.stderr)
    print(f"\nActionable Steps:", file=sys.stderr)

    if provider_type == 'ollama':
        print(f"  1. Check if Ollama is running:", file=sys.stderr)
        print(f"     $ ollama serve", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  2. Verify the embedding model is available:", file=sys.stderr)
        print(f"     $ ollama list", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  3. If model is missing, pull it:", file=sys.stderr)
        print(f"     $ ollama pull {embedding_model}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  4. Test the model manually:", file=sys.stderr)
        print(f"     $ ollama run {embedding_model} \"test\"", file=sys.stderr)
    elif provider_type in ['openai', 'azure']:
        print(f"  1. Verify your API key is set correctly:", file=sys.stderr)
        print(f"     $ echo $OPENAI_API_KEY", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  2. Check API key has proper permissions", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  3. Verify the model name is correct: {embedding_model}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  4. Check your API quota and rate limits", file=sys.stderr)
    elif provider_type == 'gemini':
        print(f"  1. Verify your API key is set correctly:", file=sys.stderr)
        print(f"     $ echo $GEMINI_API_KEY", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  2. Check API key has proper permissions", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  3. Verify the model name is correct: {embedding_model}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  4. Check your API quota and rate limits", file=sys.stderr)
    else:
        print(f"  1. Verify your provider configuration is correct", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  2. Check API keys and credentials are set", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"  3. Verify the model name is correct: {embedding_model}", file=sys.stderr)

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

        if config.ai_provider:
            provider_type = config.ai_provider.get('type', 'unknown')
            embedding_model = config.ai_provider.get('embedding', {}).get('model', 'unknown')
            llm_model = config.ai_provider.get('llm', {}).get('model', 'unknown')
            base_url = config.ai_provider.get('embedding', {}).get('base_url')

            print(f"   AI Provider: {provider_type}")
            print(f"   Embedding model: {embedding_model}")
            print(f"   LLM model: {llm_model}")
            if base_url:
                print(f"   Base URL: {base_url}")
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
        handle_embedding_error(error, args.config, config)
    except FileNotFoundError as error:
        handle_file_not_found_error(error, args.config)
    except Exception as error:
        handle_unexpected_error(error, args.config, args.dry_run)


if __name__ == "__main__":
    main()