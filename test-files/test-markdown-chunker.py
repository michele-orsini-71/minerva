#!/usr/bin/env python3
"""
Test CLI for evaluating markdown-chunker library with Bear notes data.

This script loads real Bear notes JSON data and tests the markdown-chunker
library to evaluate its chunking quality and configuration options.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

from markdown_chunker import MarkdownChunkingStrategy


def load_bear_notes(json_path: str) -> List[Dict[str, Any]]:
    """Load Bear notes from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        sys.exit(1)


def analyze_note_stats(notes: List[Dict[str, Any]]) -> None:
    """Analyze basic statistics about the notes."""
    total_notes = len(notes)
    total_chars = sum(len(note['markdown']) for note in notes)
    avg_chars = total_chars / total_notes if total_notes > 0 else 0

    # Find notes with interesting markdown structures
    notes_with_code = [n for n in notes if '```' in n['markdown']]
    notes_with_tables = [n for n in notes if '|' in n['markdown'] and '---' in n['markdown']]
    notes_with_lists = [n for n in notes if '\n-' in n['markdown'] or '\n*' in n['markdown']]
    notes_with_headings = [n for n in notes if '\n#' in n['markdown']]

    print(f"📊 Bear Notes Analysis:")
    print(f"  Total notes: {total_notes}")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Average characters per note: {avg_chars:.0f}")
    print(f"  Notes with code blocks: {len(notes_with_code)}")
    print(f"  Notes with tables: {len(notes_with_tables)}")
    print(f"  Notes with lists: {len(notes_with_lists)}")
    print(f"  Notes with headings: {len(notes_with_headings)}")
    print()


def test_chunking_strategy(note: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
    """Test markdown-chunker with a specific configuration."""
    strategy = MarkdownChunkingStrategy(**config)

    try:
        chunks = strategy.chunk_markdown(note['markdown'])
        return chunks
    except Exception as e:
        print(f"Error chunking note '{note['title']}': {e}")
        return []


def analyze_chunks(chunks: List[str], target_chars: int) -> Dict[str, Any]:
    """Analyze chunk statistics."""
    if not chunks:
        return {"count": 0, "total_chars": 0, "avg_chars": 0, "min_chars": 0, "max_chars": 0}

    char_counts = [len(chunk) for chunk in chunks]

    return {
        "count": len(chunks),
        "total_chars": sum(char_counts),
        "avg_chars": sum(char_counts) / len(char_counts),
        "min_chars": min(char_counts),
        "max_chars": max(char_counts),
        "target_chars": target_chars,
        "chunks_over_target": sum(1 for c in char_counts if c > target_chars)
    }


def print_chunk_analysis(note_title: str, chunks: List[str], stats: Dict[str, Any]) -> None:
    """Print detailed chunk analysis."""
    print(f"📝 Note: {note_title}")
    print(f"  Original length: {stats['total_chars']:,} chars")
    print(f"  Chunks created: {stats['count']}")
    print(f"  Avg chunk size: {stats['avg_chars']:.0f} chars")
    print(f"  Min/Max chunk: {stats['min_chars']}/{stats['max_chars']} chars")
    print(f"  Target: {stats['target_chars']} chars")
    print(f"  Chunks over target: {stats['chunks_over_target']}")
    print()


def print_chunk_samples(chunks: List[str], max_chunks: int = 3) -> None:
    """Print sample chunks for inspection."""
    print("🔍 Sample chunks:")
    for i, chunk in enumerate(chunks[:max_chunks]):
        preview = chunk.replace('\n', '\\n')[:100]
        print(f"  Chunk {i+1}: {preview}...")
        print(f"  Length: {len(chunk)} chars")
        print()


def main():
    parser = argparse.ArgumentParser(description="Test markdown-chunker with Bear notes")
    parser.add_argument(
        "--json-path",
        default="../test-data/Bear Notes 2025-09-20 at 08.49.json",
        help="Path to Bear notes JSON file"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of notes to test (default: 5)"
    )
    parser.add_argument(
        "--target-chars",
        type=int,
        default=1200,
        help="Target chunk size in characters (default: 1200)"
    )
    parser.add_argument(
        "--show-chunks",
        action="store_true",
        help="Show sample chunks for inspection"
    )

    args = parser.parse_args()

    # Load Bear notes
    print(f"🔄 Loading Bear notes from: {args.json_path}")
    notes = load_bear_notes(args.json_path)
    analyze_note_stats(notes)

    # Test different chunking configurations
    configs = [
        {
            "name": "Default",
            "config": {"add_metadata": True}
        },
        {
            "name": f"Target {args.target_chars} chars",
            "config": {
                "add_metadata": True,
                "min_chunk_len": args.target_chars // 4,  # 25% of target
                "soft_max_len": args.target_chars,
                "hard_max_len": args.target_chars * 2   # Allow 2x for structure preservation
            }
        },
        {
            "name": f"Strict {args.target_chars} chars",
            "config": {
                "add_metadata": True,
                "min_chunk_len": args.target_chars // 2,  # 50% of target
                "soft_max_len": args.target_chars,
                "hard_max_len": int(args.target_chars * 1.2)  # Only 20% over
            }
        }
    ]

    # Select interesting notes for testing
    sample_notes = notes[:args.sample_size]

    print(f"🧪 Testing {len(sample_notes)} notes with {len(configs)} configurations\n")

    for config_info in configs:
        print(f"⚙️  Configuration: {config_info['name']}")
        print("=" * 50)

        total_chunks = 0
        total_original_chars = 0
        total_chunk_chars = 0

        for note in sample_notes:
            chunks = test_chunking_strategy(note, config_info['config'])
            stats = analyze_chunks(chunks, args.target_chars)

            print_chunk_analysis(note['title'], chunks, stats)

            if args.show_chunks and chunks:
                print_chunk_samples(chunks)

            total_chunks += stats['count']
            total_original_chars += len(note['markdown'])
            total_chunk_chars += stats['total_chars']

        # Summary for this configuration
        print(f"📈 Configuration Summary:")
        print(f"  Total original chars: {total_original_chars:,}")
        print(f"  Total chunk chars: {total_chunk_chars:,}")
        print(f"  Total chunks created: {total_chunks}")
        print(f"  Avg chunks per note: {total_chunks / len(sample_notes):.1f}")
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()