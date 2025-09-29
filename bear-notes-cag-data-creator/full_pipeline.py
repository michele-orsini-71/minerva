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
from storage import initialize_chromadb_client, insert_chunks, get_or_create_collection, DEFAULT_CHROMADB_PATH  # New immutable API


def main():
    """Main pipeline entry point."""
    parser = argparse.ArgumentParser(
        description="Complete Bear Notes RAG pipeline: JSON → Chunks → Embeddings → ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ../test-data/Bear\\ Notes\\ 2025-09-20\\ at\\ 08.49.json
  %(prog)s --chunk-size 800 --verbose notes.json
  %(prog)s --chromadb-path ./my_db notes.json

This tool runs the complete pipeline: loads Bear notes, creates chunks,
generates embeddings using Ollama, and stores everything in ChromaDB.
        """
    )

    parser.add_argument(
        "json_file",
        help="Path to Bear notes JSON file"
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

    print("🚀 Bear Notes Complete RAG Pipeline")
    print("=" * 60)

    if args.verbose:
        print(f"📁 Input file: {args.json_file}")
        print(f"📏 Target chunk size: {args.chunk_size} characters")
        print(f"🗄️  ChromaDB path: {args.chromadb_path}")
        print()

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
        print("🗄️  Storing in ChromaDB...")
        client = initialize_chromadb_client(args.chromadb_path)
        collection = get_or_create_collection(client, reset_collection=True)  # Clean rebuild

        def progress_callback(current, total):
            if args.verbose:
                print(f"   📥 Storing: {current}/{total} chunks ({current/total*100:.1f}%)")

        stats = insert_chunks(collection, chunks_with_embeddings, progress_callback=progress_callback)
        print(f"   ✅ Stored {stats['successful']} chunks in ChromaDB")
        if stats['failed'] > 0:
            print(f"   ⚠️  Failed to store {stats['failed']} chunks")
        print()

        # Final summary
        processing_time = time.time() - start_time
        print("🎉 Pipeline completed successfully!")
        print("=" * 60)
        print(f"📊 Notes processed: {len(notes)}")
        print(f"📦 Chunks created: {len(chunks)}")
        print(f"🧠 Embeddings generated: {len(chunks_with_embeddings)}")
        print(f"🗄️  Chunks stored in ChromaDB: {stats['successful']}")
        print(f"⏱️  Total processing time: {processing_time:.1f} seconds")
        print(f"🚀 Performance: {len(chunks) / processing_time:.1f} chunks/second")
        print()
        print(f"💡 Database ready for RAG queries at: {args.chromadb_path}")

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