#!/usr/bin/env python3
"""
Bear Notes Embeddings Creator - CLI tool for processing Bear notes and creating chunks.

This is the main entry point for the Bear Notes RAG pipeline. It loads Bear notes
from JSON, creates semantic chunks using markdown-chunker, and prepares data for
vector embedding and storage.
"""

import argparse
import sys
import time
from pathlib import Path

from json_loader import load_bear_notes_json
from chunk_creator import create_chunks_for_notes


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create semantic chunks from Bear notes JSON for RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s notes.json
  %(prog)s --chunk-size 800 notes.json
  %(prog)s --verbose ../test-data/Bear\\ Notes\\ 2025-09-20\\ at\\ 08.49.json

The tool loads Bear notes from JSON, creates semantic chunks using markdown-chunker,
and outputs statistics about the chunking process. This prepares the data for
embedding generation and vector storage in the RAG pipeline.
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
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed progress"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file path for enriched notes with chunks (optional)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.chunk_size <= 0:
        print("Error: Chunk size must be positive", file=sys.stderr)
        sys.exit(1)

    if args.chunk_size < 100:
        print("Warning: Very small chunk size may produce poor results", file=sys.stderr)

    if args.chunk_size > 5000:
        print("Warning: Very large chunk size may exceed model limits", file=sys.stderr)

    # Start processing
    start_time = time.time()

    print("🚀 Bear Notes Embeddings Creator")
    print("=" * 50)

    if args.verbose:
        print(f"📁 Input file: {args.json_file}")
        print(f"📏 Target chunk size: {args.chunk_size} characters")
        print()

    try:
        # Step 1: Load JSON
        print("📖 Loading Bear notes JSON...")
        notes = load_bear_notes_json(args.json_file)

        if args.verbose:
            total_chars = sum(len(note['markdown']) for note in notes)
            avg_chars = total_chars / len(notes) if notes else 0
            print(f"   Loaded {len(notes)} notes")
            print(f"   Total content: {total_chars:,} characters")
            print(f"   Average note size: {avg_chars:.0f} characters")
            print()

        # Step 2: Create chunks
        print("✂️  Creating semantic chunks...")
        enriched_notes = create_chunks_for_notes(notes, target_chars=args.chunk_size)

        # Step 3: Summary statistics
        total_chunks = sum(len(note['chunks']) for note in enriched_notes)
        total_chunk_chars = sum(
            sum(chunk['size'] for chunk in note['chunks'])
            for note in enriched_notes
        )
        avg_chunk_size = total_chunk_chars / total_chunks if total_chunks else 0

        processing_time = time.time() - start_time

        print()
        print("📊 Processing Summary:")
        print("=" * 50)
        print(f"✅ Successfully processed: {len(enriched_notes)} notes")
        print(f"📦 Total chunks created: {total_chunks}")
        print(f"📏 Average chunk size: {avg_chunk_size:.0f} characters")
        print(f"⏱️  Processing time: {processing_time:.1f} seconds")
        print(f"🚀 Chunks per second: {total_chunks / processing_time:.1f}")

        if args.verbose:
            # Detailed statistics
            chunk_sizes = [
                chunk['size']
                for note in enriched_notes
                for chunk in note['chunks']
            ]
            chunk_sizes.sort()

            min_size = min(chunk_sizes) if chunk_sizes else 0
            max_size = max(chunk_sizes) if chunk_sizes else 0
            median_size = chunk_sizes[len(chunk_sizes) // 2] if chunk_sizes else 0

            print()
            print("📈 Detailed Chunk Statistics:")
            print(f"   Minimum chunk size: {min_size} characters")
            print(f"   Maximum chunk size: {max_size} characters")
            print(f"   Median chunk size: {median_size} characters")
            print(f"   Target chunk size: {args.chunk_size} characters")

            over_target = sum(1 for size in chunk_sizes if size > args.chunk_size)
            print(f"   Chunks over target: {over_target} ({over_target / len(chunk_sizes) * 100:.1f}%)")

        # Step 4: Optional output file
        if args.output:
            import json
            output_path = Path(args.output)
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(enriched_notes, f, indent=2, ensure_ascii=False)
                print(f"💾 Enriched notes saved to: {output_path}")
            except Exception as e:
                print(f"Warning: Could not save output file: {e}", file=sys.stderr)

        print()
        print("🎉 Chunking completed successfully!")
        print("   Ready for embedding generation and vector storage.")

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user", file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        print(f"\n💥 Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()