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
from chunk_creator import create_chunks_for_notes
from embedding import generate_embeddings_batch, EmbeddingError
from storage import initialize_chromadb_client, insert_chunks_batch, get_or_create_collection, DEFAULT_CHROMADB_PATH


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

        # Step 2: Create chunks
        print("✂️  Creating semantic chunks...")
        enriched_notes = create_chunks_for_notes(notes, target_chars=args.chunk_size)

        total_chunks = sum(len(note['chunks']) for note in enriched_notes)
        print(f"   ✅ Created {total_chunks} chunks from {len(enriched_notes)} notes")
        print()

        # Step 3: Generate embeddings
        print("🧠 Generating embeddings with Ollama...")

        # Collect all chunks with metadata
        all_chunks = []
        for note in enriched_notes:
            for chunk in note['chunks']:
                chunk_data = {
                    'text': chunk['content'],  # Fix: use 'content' field
                    'metadata': {
                        'note_id': chunk['note_id'],  # Use chunk's note_id
                        'title': chunk['title'],      # Use chunk's title
                        'modificationDate': chunk['modificationDate'],
                        'creationDate': chunk['creationDate'],
                        'size': chunk['size'],
                        'chunk_index': chunk['chunk_index'],
                        'chunk_id': chunk['id']       # Fix: use 'id' field
                    }
                }
                all_chunks.append(chunk_data)

        # Generate embeddings in batches
        embeddings = generate_embeddings_batch([chunk['text'] for chunk in all_chunks])
        print(f"   ✅ Generated {len(embeddings)} embeddings")
        print()

        # Step 4: Store in ChromaDB
        print("🗄️  Storing in ChromaDB...")
        client = initialize_chromadb_client(args.chromadb_path)
        collection = get_or_create_collection(client)

        chunks_data = []
        for i, chunk in enumerate(all_chunks):
            # Flatten all metadata as direct fields (storage module extracts everything except content/embedding as metadata)
            chunks_data.append({
                'id': chunk['metadata']['chunk_id'],
                'content': chunk['text'],
                'embedding': embeddings[i],
                # Metadata fields as direct properties
                'note_id': chunk['metadata']['note_id'],
                'title': chunk['metadata']['title'],
                'modificationDate': chunk['metadata']['modificationDate'],
                'creationDate': chunk['metadata']['creationDate'],
                'size': chunk['metadata']['size'],
                'chunk_index': chunk['metadata']['chunk_index']
            })

        def progress_callback(current, total):
            if args.verbose:
                print(f"   📥 Storing: {current}/{total} chunks ({current/total*100:.1f}%)")

        stats = insert_chunks_batch(collection, chunks_data, progress_callback=progress_callback)
        print(f"   ✅ Stored {stats['successful']} chunks in ChromaDB")
        if stats['failed'] > 0:
            print(f"   ⚠️  Failed to store {stats['failed']} chunks")
        print()

        # Final summary
        processing_time = time.time() - start_time
        print("🎉 Pipeline completed successfully!")
        print("=" * 60)
        print(f"📊 Notes processed: {len(enriched_notes)}")
        print(f"📦 Chunks created: {total_chunks}")
        print(f"🧠 Embeddings generated: {len(embeddings)}")
        print(f"🗄️  Chunks stored in ChromaDB: {stats['successful']}")
        print(f"⏱️  Total processing time: {processing_time:.1f} seconds")
        print(f"🚀 Performance: {total_chunks / processing_time:.1f} chunks/second")
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