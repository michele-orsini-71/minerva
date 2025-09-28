#!/usr/bin/env python3
"""
Chunk Creator module for Bear Notes.

Uses LangChain text splitters to create semantic chunks from Bear notes markdown content
with proper overlap and structure preservation.
"""

import sys
import hashlib
from typing import List, Dict, Any

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
except ImportError:
    print("Error: langchain-text-splitters library not installed. Run: pip install langchain-text-splitters", file=sys.stderr)
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


def create_langchain_chunker(target_chars: int = 1200, overlap_chars: int = 200):
    """
    Create configured LangChain text splitters for Bear notes.

    Args:
        target_chars: Target chunk size in characters
        overlap_chars: Overlap size in characters

    Returns:
        Tuple of (header_splitter, recursive_splitter)
    """
    # Configure header-based splitter
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
        ("######", "Header 6"),
    ]

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False  # Keep headers in content for context
    )

    # Configure recursive character splitter with overlap
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_chars,
        chunk_overlap=overlap_chars,
        length_function=len,
        is_separator_regex=False,
        separators=[
            "\n\n",  # Paragraph breaks (highest priority)
            "\n",    # Line breaks
            " ",     # Word breaks
            "",      # Character breaks (fallback)
        ]
    )

    return header_splitter, recursive_splitter


def chunk_markdown_content(markdown: str, target_chars: int = 1200, overlap_chars: int = 200) -> List[Dict[str, Any]]:
    """
    Chunk markdown content using combined LangChain approach.

    Args:
        markdown: Markdown content to chunk
        target_chars: Target chunk size in characters
        overlap_chars: Overlap size in characters

    Returns:
        List of chunk dictionaries with content, metadata, and size
    """
    header_splitter, recursive_splitter = create_langchain_chunker(target_chars, overlap_chars)

    # Step 1: Split by headers to preserve structure
    try:
        header_splits = header_splitter.split_text(markdown)
    except Exception as e:
        # Fallback to recursive splitting only if header splitting fails
        print(f"Warning: Header splitting failed, using recursive only: {e}", file=sys.stderr)
        header_splits = [type('obj', (object,), {
            'page_content': markdown,
            'metadata': {}
        })]

    # Step 2: Further split large sections with recursive splitter
    all_chunks = []
    for split in header_splits:
        content = split.page_content
        metadata = split.metadata if hasattr(split, 'metadata') else {}

        # If the header split is large, further split it with overlap
        if len(content) > target_chars:
            sub_chunks = recursive_splitter.split_text(content)
            for chunk_content in sub_chunks:
                all_chunks.append({
                    'content': chunk_content,
                    'metadata': metadata,
                    'size': len(chunk_content)
                })
        else:
            # Small enough to keep as-is
            all_chunks.append({
                'content': content,
                'metadata': metadata,
                'size': len(content)
            })

    return all_chunks


def create_chunks_for_notes(notes: List[Dict[str, Any]], target_chars: int = 1200, overlap_chars: int = 200) -> List[Dict[str, Any]]:
    """
    Create chunks for all notes using LangChain text splitters.

    Args:
        notes: List of note dictionaries from Bear JSON
        target_chars: Target chunk size in characters (default: 1200)
        overlap_chars: Overlap size in characters (default: 200)

    Returns:
        List of note dictionaries enriched with 'chunks' field containing chunk data
    """
    enriched_notes = []
    failed_notes = []

    print(f"🔄 Processing {len(notes)} notes with LangChain text splitters...")
    print(f"⚙️  Configuration: {target_chars} chars target, {overlap_chars} chars overlap")

    for i, note in enumerate(notes):
        try:
            # Generate stable note ID
            note_id = generate_note_id(note['title'], note.get('creationDate'))

            # Create chunks using LangChain
            chunk_data_list = chunk_markdown_content(
                note['markdown'],
                target_chars=target_chars,
                overlap_chars=overlap_chars
            )

            # Build enriched chunks with metadata
            chunks = []
            for chunk_index, chunk_data in enumerate(chunk_data_list):
                chunk_id = generate_chunk_id(note_id, note['modificationDate'], chunk_index)

                chunk_metadata = {
                    'id': chunk_id,
                    'content': chunk_data['content'],
                    'chunk_index': chunk_index,
                    'note_id': note_id,
                    'title': note['title'],
                    'modificationDate': note['modificationDate'],
                    'size': chunk_data['size']
                }

                # Add creation date if available
                if 'creationDate' in note:
                    chunk_metadata['creationDate'] = note['creationDate']

                # Add header metadata from LangChain
                if chunk_data['metadata']:
                    chunk_metadata['header_metadata'] = chunk_data['metadata']

                chunks.append(chunk_metadata)

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

    if enriched_notes:
        # Calculate chunk size statistics
        all_chunk_sizes = [
            chunk['size']
            for note in enriched_notes
            for chunk in note['chunks']
        ]
        avg_chunk_size = sum(all_chunk_sizes) / len(all_chunk_sizes)
        min_chunk_size = min(all_chunk_sizes)
        max_chunk_size = max(all_chunk_sizes)
    else:
        avg_chunk_size = min_chunk_size = max_chunk_size = 0

    print(f"✅ Chunking complete:")
    print(f"  Successfully processed: {len(enriched_notes)} notes")
    print(f"  Failed: {len(failed_notes)} notes")
    print(f"  Total chunks created: {total_chunks}")
    print(f"  Average chunks per note: {avg_chunks:.1f}")
    print(f"  Average chunk size: {avg_chunk_size:.0f} chars")
    print(f"  Chunk size range: {min_chunk_size}-{max_chunk_size} chars")

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

    # Example usage with LangChain
    test_notes = [
        {
            "title": "Test Note",
            "markdown": "# Test\n\nThis is a test note with some content.\n\n## Section\n\nMore content here that should be chunked properly with overlap.",
            "size": 100,
            "modificationDate": "2025-01-01T10:00:00Z"
        }
    ]

    result = create_chunks_for_notes(test_notes, target_chars=50, overlap_chars=10)
    print(f"Test result: {len(result[0]['chunks'])} chunks created")

    for i, chunk in enumerate(result[0]['chunks']):
        print(f"  Chunk {i+1}: {chunk['size']} chars - {chunk['content'][:50]}...")