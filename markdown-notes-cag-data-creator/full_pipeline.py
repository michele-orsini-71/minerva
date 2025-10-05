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
from storage import collection_exists, initialize_chromadb_client, insert_chunks, get_or_create_collection, StorageError  # New immutable API


def main():
    args = parse_pipeline_args()

    # Start processing
    start_time = time.time()

    print("Markdown Notes Multi-Collection RAG Pipeline")
    print("=" * 60)

    try:
        config = load_and_validate_config(args.config, verbose=args.verbose)

        if args.verbose:
            print(f"   Input file: {config.json_file}")
            print(f"   Target chunk size: {config.chunk_size} characters")
            print(f"   ChromaDB path: {config.chromadb_path}")
            print(f"   Collection: {config.collection_name}")
            print()

    except KeyboardInterrupt:
        print("\n   Operation cancelled by user", file=sys.stderr)
        sys.exit(130)

    try:
        print("Loading notes JSON...")
        notes = load_json_notes(config.json_file)

        if args.verbose:
            total_chars = sum(len(note['markdown']) for note in notes)
            avg_chars = total_chars / len(notes) if notes else 0
            print(f"   Loaded {len(notes)} notes")
            print(f"   Total content: {total_chars:,} characters")
            print(f"   Average note size: {avg_chars:.0f} characters")
            print()

        try:
            client = initialize_chromadb_client(config.chromadb_path)

            if (collection_exists(client, config.collection_name) and not config.force_recreate):
                raise StorageError(
                    f"Collection '{config.collection_name}' already exists\n"
                    f"  Options:\n"
                    f"    1. Use a different collection name\n"
                    f"    2. Set 'forceRecreate': true in your configuration file to delete and recreate\n"
                    f"       (WARNING: This will permanently delete all existing data!)\n"
                    f"    3. Use the existing collection (not currently supported)\n"
                    f"  Note: force_recreate is a destructive operation - use with caution!"
                )

            # Step 2: Create chunks (immutable)
            print("Creating semantic chunks...")
            chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)
            print(f"   Created {len(chunks)} chunks from {len(notes)} notes")
            print()

            # Step 3: Generate embeddings (immutable)
            print("Generating embeddings with Ollama...")
            chunks_with_embeddings = generate_embeddings(chunks)
            print(f"   Generated {len(chunks_with_embeddings)} embeddings")
            print()

            # Step 4: Store in ChromaDB (immutable)
            print(f"Storing in ChromaDB collection '{config.collection_name}'...")

            collection = get_or_create_collection(
                client,
                collection_name=config.collection_name,
                description=config.description,
                force_recreate=config.force_recreate
            )

            def progress_callback(current, total):
                if args.verbose:
                    print(f"   Storing: {current}/{total} chunks ({current/total*100:.1f}%)")

            stats = insert_chunks(collection, chunks_with_embeddings, progress_callback=progress_callback)
            print(f"   Stored {stats['successful']} chunks in collection '{config.collection_name}'")
            if stats['failed'] > 0:
                print(f"   Failed to store {stats['failed']} chunks")
            print()
        except StorageError as e:
            print(f"\nStorage Error:\n{e}", file=sys.stderr)
            print(f"\nCollection: {config.collection_name}", file=sys.stderr)
            print(f"Configuration file: {args.config}", file=sys.stderr)
            sys.exit(1)

        # Final summary
        processing_time = time.time() - start_time
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

    except KeyboardInterrupt:
        print("\n   Operation cancelled by user", file=sys.stderr)
        sys.exit(130)

    except EmbeddingError as e:
        print(f"\nEmbedding generation failed: {e}", file=sys.stderr)
        print("   Make sure Ollama is running: ollama serve", file=sys.stderr)
        print("   And model is available: ollama pull mxbai-embed-large:latest", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()