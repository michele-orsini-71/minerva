#!/usr/bin/env python3
"""
Complete Bear Notes RAG Pipeline
Processes Bear notes JSON, creates chunks, generates embeddings, and stores in ChromaDB.
"""

import argparse
import sys
import time
from pathlib import Path

# Import our modules
from json_loader import load_bear_notes_json
from chunk_creator import create_chunks_from_notes  # New immutable API
from embedding import generate_embeddings, EmbeddingError  # New immutable API
from storage import initialize_chromadb_client, insert_chunks, get_or_create_collection, DEFAULT_CHROMADB_PATH, StorageError  # New immutable API
from config_loader import load_collection_config, ConfigError
from validation import validate_collection_name, validate_description_hybrid, ValidationError


def main():
    """Main pipeline entry point."""
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

    # Start processing
    start_time = time.time()

    print("🚀 Markdown Notes Multi-Collection RAG Pipeline")
    print("=" * 60)

    try:
        # Step 0: Load and validate configuration
        print("⚙️  Loading collection configuration...")
        try:
            config = load_collection_config(args.config)
            print(f"   ✅ Configuration loaded from: {args.config}")
            print(f"   Collection name: {config.collection_name}")
            print(f"   Description: {config.description[:80]}...")
            print(f"   Force recreate: {config.force_recreate}")
            print(f"   Skip AI validation: {config.skip_ai_validation}")
            print()
        except ConfigError as e:
            print(f"\n❌ Configuration Error:\n{e}", file=sys.stderr)
            print(f"\nConfiguration file: {args.config}", file=sys.stderr)
            sys.exit(1)

        # Step 0.5: Validate collection name and description
        print("✅ Validating collection metadata...")
        try:
            # Validate collection name
            validate_collection_name(config.collection_name)
            print(f"   ✅ Collection name validated: {config.collection_name}")

            # Validate description (hybrid: regex + optional AI)
            validation_result = validate_description_hybrid(
                config.description,
                config.collection_name,
                skip_ai_validation=config.skip_ai_validation
            )
            print(f"   ✅ Description validated successfully")
            if validation_result:
                print(f"   AI Quality Score: {validation_result['score']}/10")
            print()
        except ValidationError as e:
            print(f"\n❌ Validation Error:\n{e}", file=sys.stderr)
            print(f"\nConfiguration file: {args.config}", file=sys.stderr)
            print(f"Collection name: {config.collection_name}", file=sys.stderr)
            sys.exit(1)

        if args.verbose:
            print(f"📁 Input file: {args.json_file}")
            print(f"📏 Target chunk size: {args.chunk_size} characters")
            print(f"🗄️  ChromaDB path: {args.chromadb_path}")
            print(f"📦 Collection: {config.collection_name}")
            print()

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user", file=sys.stderr)
        sys.exit(130)

    try:
        # Step 1: Load JSON
        print("📖 Loading Bear notes JSON...")
        notes = load_bear_notes_json(args.json_file)

        if args.verbose:
            total_chars = sum(len(note['markdown']) for note in notes)
            avg_chars = total_chars / len(notes) if notes else 0
            print(f"   ✅ Loaded {len(notes)} notes")
            print(f"   📊 Total content: {total_chars:,} characters")
            print(f"   📊 Average note size: {avg_chars:.0f} characters")
            print()

        # Step 2: Create chunks (immutable)
        print("✂️  Creating semantic chunks...")
        chunks = create_chunks_from_notes(notes, target_chars=args.chunk_size)
        print(f"   ✅ Created {len(chunks)} chunks from {len(notes)} notes")
        print()

        # Step 3: Generate embeddings (immutable)
        print("🧠 Generating embeddings with Ollama...")
        chunks_with_embeddings = generate_embeddings(chunks)
        print(f"   ✅ Generated {len(chunks_with_embeddings)} embeddings")
        print()

        # Step 4: Store in ChromaDB (immutable)
        print(f"🗄️  Storing in ChromaDB collection '{config.collection_name}'...")
        try:
            client = initialize_chromadb_client(args.chromadb_path)
            collection = get_or_create_collection(
                client,
                collection_name=config.collection_name,
                description=config.description,
                force_recreate=config.force_recreate
            )

            def progress_callback(current, total):
                if args.verbose:
                    print(f"   📥 Storing: {current}/{total} chunks ({current/total*100:.1f}%)")

            stats = insert_chunks(collection, chunks_with_embeddings, progress_callback=progress_callback)
            print(f"   ✅ Stored {stats['successful']} chunks in collection '{config.collection_name}'")
            if stats['failed'] > 0:
                print(f"   ⚠️  Failed to store {stats['failed']} chunks")
            print()
        except StorageError as e:
            print(f"\n❌ Storage Error:\n{e}", file=sys.stderr)
            print(f"\nCollection: {config.collection_name}", file=sys.stderr)
            print(f"Configuration file: {args.config}", file=sys.stderr)
            sys.exit(1)

        # Final summary
        processing_time = time.time() - start_time
        print("🎉 Pipeline completed successfully!")
        print("=" * 60)
        print(f"📦 Collection: {config.collection_name}")
        print(f"📝 Description: {config.description[:60]}...")
        print(f"📊 Notes processed: {len(notes)}")
        print(f"✂️  Chunks created: {len(chunks)}")
        print(f"🧠 Embeddings generated: {len(chunks_with_embeddings)}")
        print(f"🗄️  Chunks stored: {stats['successful']}")
        print(f"⏱️  Processing time: {processing_time:.1f} seconds")
        print(f"🚀 Performance: {len(chunks) / processing_time:.1f} chunks/second")
        print()
        print(f"💡 Collection '{config.collection_name}' ready for RAG queries")
        print(f"   Database location: {args.chromadb_path}")

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user", file=sys.stderr)
        sys.exit(130)

    except EmbeddingError as e:
        print(f"\n💥 Embedding generation failed: {e}", file=sys.stderr)
        print("   Make sure Ollama is running: ollama serve", file=sys.stderr)
        print("   And model is available: ollama pull mxbai-embed-large:latest", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"\n💥 Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()