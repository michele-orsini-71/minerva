#!/usr/bin/env python3
"""
Chunk Creator module for Bear Notes.

Uses markdown-chunker library to create semantic chunks from Bear notes markdown content.
"""

import sys
import hashlib
from typing import List, Dict, Any

try:
    from markdown_chunker import MarkdownChunkingStrategy
except ImportError:
    print("Error: markdown-chunker library not installed. Run: pip install markdown-chunker", file=sys.stderr)
    sys.exit(1)


def generate_note_id(title: str, creation_date: str = None) -> str:
    """
    Generate a stable note ID using SHA1 hash of title and creation date.

    Args:
        title: Note title
        creation_date: Optional creation date for uniqueness

    Returns:
        SHA1 hex digest as note ID
    """
    # Use title + creation date if available, otherwise just title
    id_source = title
    if creation_date:
        id_source = f"{title}|{creation_date}"

    return hashlib.sha1(id_source.encode('utf-8')).hexdigest()


def generate_chunk_id(note_id: str, modification_date: str, chunk_index: int) -> str:
    """
    Generate a stable chunk ID using SHA256 hash.

    Args:
        note_id: Parent note ID
        modification_date: Note modification date
        chunk_index: Index of chunk within note

    Returns:
        SHA256 hex digest as chunk ID
    """
    chunk_source = f"{note_id}|{modification_date}|{chunk_index}"
    return hashlib.sha256(chunk_source.encode('utf-8')).hexdigest()


def create_chunks_for_notes(notes: List[Dict[str, Any]], target_chars: int = 1200) -> List[Dict[str, Any]]:
    """
    Create chunks for all notes using markdown-chunker library.

    Args:
        notes: List of note dictionaries from Bear JSON
        target_chars: Target chunk size in characters (default: 1200)

    Returns:
        List of note dictionaries enriched with 'chunks' field containing chunk data
    """
    # Configure markdown-chunker for optimal Bear notes processing
    strategy = MarkdownChunkingStrategy(
        add_metadata=False,              # No YAML front matter overhead
        soft_max_len=target_chars,       # Target size (1200 chars)
        hard_max_len=int(target_chars * 1.5),  # Allow 50% over for structure preservation
        min_chunk_len=target_chars // 4,       # Minimum 25% of target
        heading_based_chunking=True,            # Preserve semantic structure
        remove_duplicates=False,               # Avoid content loss warnings
        detect_headers_footers=False           # Bear notes don't have these
    )

    enriched_notes = []
    failed_notes = []

    print(f"🔄 Processing {len(notes)} notes with markdown-chunker...")

    for i, note in enumerate(notes):
        try:
            # Generate stable note ID
            note_id = generate_note_id(note['title'], note.get('creationDate'))

            # Create chunks using markdown-chunker
            chunks_text = strategy.chunk_markdown(note['markdown'])

            # Build chunk metadata
            chunks = []
            for chunk_index, chunk_content in enumerate(chunks_text):
                chunk_id = generate_chunk_id(note_id, note['modificationDate'], chunk_index)

                chunk_data = {
                    'id': chunk_id,
                    'content': chunk_content,
                    'chunk_index': chunk_index,
                    'note_id': note_id,
                    'title': note['title'],
                    'modificationDate': note['modificationDate'],
                    'size': len(chunk_content)
                }

                # Add creation date if available
                if 'creationDate' in note:
                    chunk_data['creationDate'] = note['creationDate']

                chunks.append(chunk_data)

            # Create enriched note
            enriched_note = note.copy()
            enriched_note['note_id'] = note_id
            enriched_note['chunks'] = chunks

            enriched_notes.append(enriched_note)

            # Progress feedback
            if (i + 1) % 50 == 0 or i == len(notes) - 1:
                total_chunks = sum(len(n['chunks']) for n in enriched_notes)
                print(f"  Progress: {i + 1}/{len(notes)} notes ({(i + 1) / len(notes) * 100:.1f}%) - {total_chunks} chunks created")

        except Exception as e:
            failed_notes.append({
                'title': note.get('title', 'Unknown'),
                'error': str(e)
            })
            print(f"⚠️  Failed to process note '{note.get('title', 'Unknown')}': {e}", file=sys.stderr)
            continue

    # Summary
    total_chunks = sum(len(note['chunks']) for note in enriched_notes)
    avg_chunks = total_chunks / len(enriched_notes) if enriched_notes else 0

    print(f"✅ Chunking complete:")
    print(f"  Successfully processed: {len(enriched_notes)} notes")
    print(f"  Failed: {len(failed_notes)} notes")
    print(f"  Total chunks created: {total_chunks}")
    print(f"  Average chunks per note: {avg_chunks:.1f}")

    if failed_notes:
        print(f"\n❌ Failed notes:")
        for failed in failed_notes:
            print(f"  - {failed['title']}: {failed['error']}")

    if not enriched_notes:
        print("Error: No notes were successfully processed", file=sys.stderr)
        sys.exit(1)

    return enriched_notes


if __name__ == "__main__":
    # Simple test when run directly
    print("Chunk Creator module - use via embeddings_creator.py CLI")

    # Example usage
    test_notes = [
        {
            "title": "Test Note",
            "markdown": "# Test\n\nThis is a test note with some content.\n\n## Section\n\nMore content here.",
            "size": 100,
            "modificationDate": "2025-01-01T10:00:00Z"
        }
    ]

    result = create_chunks_for_notes(test_notes, target_chars=100)
    print(f"Test result: {len(result[0]['chunks'])} chunks created")