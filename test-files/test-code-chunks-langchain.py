#!/usr/bin/env python3
"""
Test LangChain text splitters with Bear notes data.

This script tests LangChain's MarkdownHeaderTextSplitter and RecursiveCharacterTextSplitter
to evaluate their chunking quality compared to markdown-chunker.
"""

import json
import sys
from pathlib import Path

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
except ImportError:
    print("Error: langchain-text-splitters not installed. Run: pip install langchain-text-splitters")
    sys.exit(1)


def load_bear_notes(json_path: str):
    """Load Bear notes from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        sys.exit(1)


def test_markdown_header_splitter(markdown_content: str, note_title: str):
    """Test LangChain's MarkdownHeaderTextSplitter."""
    print(f"\n🔗 Testing MarkdownHeaderTextSplitter with: {note_title}")
    print("=" * 60)

    # Define headers to split on
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
        ("######", "Header 6"),
    ]

    # Create splitter
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False  # Keep headers in content
    )

    # Split the content
    md_header_splits = markdown_splitter.split_text(markdown_content)

    print(f"📦 Created {len(md_header_splits)} header-based splits:")
    for i, split in enumerate(md_header_splits):
        content_preview = split.page_content.replace('\n', '\\n')[:100]
        metadata = split.metadata if hasattr(split, 'metadata') else {}
        print(f"  Split {i+1}: {len(split.page_content)} chars")
        print(f"    Content: {content_preview}...")
        print(f"    Metadata: {metadata}")
        print()

    return md_header_splits


def test_recursive_character_splitter(markdown_content: str, note_title: str, target_chars: int = 1200, overlap_chars: int = 200):
    """Test LangChain's RecursiveCharacterTextSplitter."""
    print(f"\n🔀 Testing RecursiveCharacterTextSplitter with: {note_title}")
    print(f"Target: {target_chars} chars, Overlap: {overlap_chars} chars")
    print("=" * 60)

    # Create recursive splitter with overlap
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_chars,
        chunk_overlap=overlap_chars,
        length_function=len,
        is_separator_regex=False,
        separators=[
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            " ",     # Word breaks
            "",      # Character breaks
        ]
    )

    # Split the content
    splits = text_splitter.split_text(markdown_content)

    print(f"📦 Created {len(splits)} chunks:")
    for i, chunk in enumerate(splits):
        chunk_preview = chunk.replace('\n', '\\n')[:100]
        print(f"  Chunk {i+1}: {len(chunk)} chars")
        print(f"    Content: {chunk_preview}...")

        # Check for overlap with previous chunk
        if i > 0:
            prev_chunk = splits[i-1]
            # Look for overlap by finding common ending/beginning
            overlap_found = False
            for overlap_len in range(min(len(prev_chunk), len(chunk), overlap_chars), 10, -1):
                if prev_chunk[-overlap_len:] == chunk[:overlap_len]:
                    print(f"    ✅ Overlap detected: {overlap_len} chars")
                    overlap_found = True
                    break
            if not overlap_found:
                print(f"    ❌ No overlap detected")
        print()

    return splits


def test_combined_approach(markdown_content: str, note_title: str, target_chars: int = 1200, overlap_chars: int = 200):
    """Test combined approach: MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter."""
    print(f"\n🔄 Testing Combined Approach with: {note_title}")
    print("=" * 60)

    # Step 1: Split by headers
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    md_header_splits = markdown_splitter.split_text(markdown_content)

    # Step 2: Further split large sections with RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_chars,
        chunk_overlap=overlap_chars,
        length_function=len,
    )

    all_chunks = []
    for split in md_header_splits:
        # If the header split is large, further split it
        if len(split.page_content) > target_chars:
            sub_chunks = text_splitter.split_text(split.page_content)
            for chunk in sub_chunks:
                all_chunks.append({
                    'content': chunk,
                    'metadata': split.metadata if hasattr(split, 'metadata') else {},
                    'size': len(chunk)
                })
        else:
            all_chunks.append({
                'content': split.page_content,
                'metadata': split.metadata if hasattr(split, 'metadata') else {},
                'size': len(split.page_content)
            })

    print(f"📦 Created {len(all_chunks)} final chunks:")
    for i, chunk in enumerate(all_chunks):
        content_preview = chunk['content'].replace('\n', '\\n')[:100]
        print(f"  Chunk {i+1}: {chunk['size']} chars")
        print(f"    Content: {content_preview}...")
        print(f"    Metadata: {chunk['metadata']}")
        print()

    return all_chunks


def main():
    # Load Bear notes
    json_path = "../test-data/Bear Notes 2025-09-20 at 08.49.json"
    print(f"🔄 Loading Bear notes from: {json_path}")
    notes = load_bear_notes(json_path)

    # Find a note with code blocks for testing
    test_note = None
    for note in notes:
        if '```' in note['markdown'] and len(note['markdown']) > 1000:
            test_note = note
            break

    if not test_note:
        # Fallback to first substantial note
        test_note = next((note for note in notes if len(note['markdown']) > 500), notes[0])

    print(f"📝 Testing with note: '{test_note['title']}'")
    print(f"📏 Original length: {len(test_note['markdown'])} characters")

    # Test different approaches
    markdown_content = test_note['markdown']
    note_title = test_note['title']

    # Test 1: Header-based splitting
    header_splits = test_markdown_header_splitter(markdown_content, note_title)

    # Test 2: Recursive character splitting with overlap
    recursive_splits = test_recursive_character_splitter(markdown_content, note_title, target_chars=1200, overlap_chars=200)

    # Test 3: Combined approach
    combined_chunks = test_combined_approach(markdown_content, note_title, target_chars=1200, overlap_chars=200)

    # Summary comparison
    print("\n📊 Summary Comparison:")
    print("=" * 60)
    print(f"Original content: {len(markdown_content)} chars")
    print(f"Header-based splits: {len(header_splits)} chunks")
    print(f"Recursive splits: {len(recursive_splits)} chunks")
    print(f"Combined approach: {len(combined_chunks)} chunks")

    # Verify no content loss
    header_total = sum(len(split.page_content) for split in header_splits)
    recursive_total = sum(len(chunk) for chunk in recursive_splits)
    combined_total = sum(chunk['size'] for chunk in combined_chunks)

    print(f"\nContent preservation check:")
    print(f"Header approach: {header_total} chars ({header_total/len(markdown_content)*100:.1f}%)")
    print(f"Recursive approach: {recursive_total} chars ({recursive_total/len(markdown_content)*100:.1f}%)")
    print(f"Combined approach: {combined_total} chars ({combined_total/len(markdown_content)*100:.1f}%)")


if __name__ == "__main__":
    main()