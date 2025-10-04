import sys
import hashlib
from typing import List, Dict, Any

# Import our immutable models
from models import Chunk, ChunkList

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
except ImportError:
    print("Error: langchain-text-splitters library not installed. Run: pip install langchain-text-splitters", file=sys.stderr)
    sys.exit(1)


def generate_note_id(title: str, creation_date: str = None) -> str:
    # Use title + creation date if available, otherwise just title
    id_source = title
    if creation_date:
        id_source = f"{title}|{creation_date}"

    return hashlib.sha1(id_source.encode('utf-8')).hexdigest()


def generate_chunk_id(note_id: str, modification_date: str, chunk_index: int) -> str:
    chunk_source = f"{note_id}|{modification_date}|{chunk_index}"
    return hashlib.sha256(chunk_source.encode('utf-8')).hexdigest()


def create_langchain_chunker(target_chars: int = 1200, overlap_chars: int = 200):
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
    enriched_notes = []
    failed_notes = []

    print(f"Processing {len(notes)} notes with LangChain text splitters...")
    print(f"   Configuration: {target_chars} chars target, {overlap_chars} chars overlap")

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
            print(f"   Failed to process note '{note.get('title', 'Unknown')}': {e}", file=sys.stderr)
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

    print(f"   Chunking complete:")
    print(f"  Successfully processed: {len(enriched_notes)} notes")
    print(f"  Failed: {len(failed_notes)} notes")
    print(f"  Total chunks created: {total_chunks}")
    print(f"  Average chunks per note: {avg_chunks:.1f}")
    print(f"  Average chunk size: {avg_chunk_size:.0f} chars")
    print(f"  Chunk size range: {min_chunk_size}-{max_chunk_size} chars")

    if failed_notes:
        print(f"\n   Failed notes:")
        for failed in failed_notes:
            print(f"  - {failed['title']}: {failed['error']}")

    if not enriched_notes:
        print("Error: No notes were successfully processed", file=sys.stderr)
        sys.exit(1)

    return enriched_notes


def create_chunks_from_notes(notes: List[Dict[str, Any]], target_chars: int = 1200, overlap_chars: int = 200) -> ChunkList:
    chunks = []
    failed_notes = []

    print(f"Processing {len(notes)} notes with LangChain text splitters...")
    print(f"   Configuration: {target_chars} chars target, {overlap_chars} chars overlap")

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

            # Build immutable Chunk objects
            for chunk_index, chunk_data in enumerate(chunk_data_list):
                chunk_id = generate_chunk_id(note_id, note['modificationDate'], chunk_index)

                # Create immutable Chunk
                chunk = Chunk(
                    id=chunk_id,
                    content=chunk_data['content'],
                    noteId=note_id,
                    title=note['title'],
                    modificationDate=note['modificationDate'],
                    creationDate=note.get('creationDate', ''),
                    size=chunk_data['size'],
                    chunkIndex=chunk_index
                )

                chunks.append(chunk)

            # Progress feedback
            if (i + 1) % 50 == 0 or i == len(notes) - 1:
                print(f"  Progress: {i + 1}/{len(notes)} notes ({(i + 1) / len(notes) * 100:.1f}%) - {len(chunks)} chunks created")

        except Exception as e:
            failed_notes.append({
                'title': note.get('title', 'Unknown'),
                'error': str(e)
            })
            print(f"   Failed to process note '{note.get('title', 'Unknown')}': {e}", file=sys.stderr)
            continue

    # Summary statistics
    if chunks:
        # Calculate chunk size statistics
        all_chunk_sizes = [chunk.size for chunk in chunks]
        avg_chunk_size = sum(all_chunk_sizes) / len(all_chunk_sizes)
        min_chunk_size = min(all_chunk_sizes)
        max_chunk_size = max(all_chunk_sizes)

        # Calculate notes processed
        unique_note_ids = len(set(chunk.noteId for chunk in chunks))
        avg_chunks_per_note = len(chunks) / unique_note_ids if unique_note_ids else 0
    else:
        avg_chunk_size = min_chunk_size = max_chunk_size = 0
        unique_note_ids = 0
        avg_chunks_per_note = 0

    print(f"   Chunking complete:")
    print(f"  Successfully processed: {unique_note_ids} notes")
    print(f"  Failed: {len(failed_notes)} notes")
    print(f"  Total chunks created: {len(chunks)}")
    print(f"  Average chunks per note: {avg_chunks_per_note:.1f}")
    print(f"  Average chunk size: {avg_chunk_size:.0f} chars")
    print(f"  Chunk size range: {min_chunk_size}-{max_chunk_size} chars")

    if failed_notes:
        print(f"\n   Failed notes:")
        for failed in failed_notes:
            print(f"  - {failed['title']}: {failed['error']}")

    if not chunks:
        print("Error: No chunks were successfully created", file=sys.stderr)
        sys.exit(1)

    return chunks
