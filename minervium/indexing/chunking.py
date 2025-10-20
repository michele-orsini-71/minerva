import sys
import hashlib
from typing import List, Dict, Any
from minervium.common.logger import get_logger

logger = get_logger(__name__, mode="cli")

# Import our immutable models
from minervium.common.models import Chunk, ChunkList

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
except ImportError:
    logger.error("langchain-text-splitters library not installed. Run: pip install langchain-text-splitters")
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


def build_text_splitters(target_chars: int = 1200, overlap_chars: int = 200):
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


class FallbackDocument:
    """Simple document wrapper for fallback when header splitting fails."""
    def __init__(self, page_content: str):
        self.page_content = page_content
        self.metadata = {}


def chunk_markdown_content(markdown: str, target_chars: int = 1200, overlap_chars: int = 200) -> List[Dict[str, Any]]:
    header_splitter, recursive_splitter = build_text_splitters(target_chars, overlap_chars)

    # Step 1: Split by headers to preserve structure
    try:
        header_splits = header_splitter.split_text(markdown)
    except Exception as error:
        # Fallback to recursive splitting only if header splitting fails
        logger.warning(f"Header splitting failed, using recursive only: {error}")
        header_splits = [FallbackDocument(markdown)]

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


def calculate_chunk_statistics(chunks: List[Chunk]) -> Dict[str, Any]:
    """Calculate comprehensive statistics about created chunks."""
    if not chunks:
        return {
            'avg_chunk_size': 0,
            'min_chunk_size': 0,
            'max_chunk_size': 0,
            'unique_note_ids': 0,
            'avg_chunks_per_note': 0
        }

    all_chunk_sizes = [chunk.size for chunk in chunks]
    unique_note_ids = len(set(chunk.noteId for chunk in chunks))

    return {
        'avg_chunk_size': sum(all_chunk_sizes) / len(all_chunk_sizes),
        'min_chunk_size': min(all_chunk_sizes),
        'max_chunk_size': max(all_chunk_sizes),
        'unique_note_ids': unique_note_ids,
        'avg_chunks_per_note': len(chunks) / unique_note_ids if unique_note_ids else 0
    }


def log_chunking_progress(current: int, total: int, chunks_created: int) -> None:
    """Log progress during chunking operation."""
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"  Progress: {current}/{total} notes ({percentage:.1f}%) - {chunks_created} chunks created")


def print_chunking_summary(stats: Dict[str, Any], failed_notes: List[Dict[str, str]], total_chunks: int) -> None:
    """Print comprehensive summary of chunking operation."""
    logger.info(f"   Chunking complete:")
    logger.info(f"  Successfully processed: {stats['unique_note_ids']} notes")
    logger.info(f"  Failed: {len(failed_notes)} notes")
    logger.info(f"  Total chunks created: {total_chunks}")
    logger.info(f"  Average chunks per note: {stats['avg_chunks_per_note']:.1f}")
    logger.info(f"  Average chunk size: {stats['avg_chunk_size']:.0f} chars")
    logger.info(f"  Chunk size range: {stats['min_chunk_size']}-{stats['max_chunk_size']} chars")

    if failed_notes:
        logger.warning(f"\n   Failed notes:")
        for failed in failed_notes:
            logger.warning(f"  - {failed['title']}: {failed['error']}")


def build_chunks_from_note(note: Dict[str, Any], target_chars: int, overlap_chars: int) -> List[Chunk]:
    """Build immutable Chunk objects from a single note."""
    note_id = generate_note_id(note['title'], note.get('creationDate'))

    markdown_chunks = chunk_markdown_content(
        note['markdown'],
        target_chars=target_chars,
        overlap_chars=overlap_chars
    )

    chunks = []
    for chunk_index, chunk_data in enumerate(markdown_chunks):
        chunk_id = generate_chunk_id(note_id, note['modificationDate'], chunk_index)

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

    return chunks


def should_report_progress(current_index: int, total_count: int) -> bool:
    """Determine if progress should be reported at this iteration."""
    return (current_index + 1) % 50 == 0 or current_index == total_count - 1


def create_chunks_from_notes(notes: List[Dict[str, Any]], target_chars: int = 1200, overlap_chars: int = 200) -> ChunkList:
    chunks = []
    failed_notes = []

    logger.info(f"Processing {len(notes)} notes with LangChain text splitters...")
    logger.info(f"   Configuration: {target_chars} chars target, {overlap_chars} chars overlap")

    for i, note in enumerate(notes):
        try:
            note_chunks = build_chunks_from_note(note, target_chars, overlap_chars)
            chunks.extend(note_chunks)

            if should_report_progress(i, len(notes)):
                log_chunking_progress(i + 1, len(notes), len(chunks))
        except Exception as error:
            failed_notes.append({
                'title': note.get('title', 'Unknown'),
                'error': str(error)
            })
            logger.error(f"   Failed to process note '{note.get('title', 'Unknown')}': {error}")

    # Calculate statistics and print summary
    stats = calculate_chunk_statistics(chunks)
    print_chunking_summary(stats, failed_notes, len(chunks))

    if not chunks:
        logger.error("No chunks were successfully created")
        sys.exit(1)

    return chunks
