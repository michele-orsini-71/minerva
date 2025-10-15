from typing import List, Dict, Any
import chromadb
from console_logger import get_logger

# Initialize console logger
console_logger = get_logger(__name__)


class ContextRetrievalError(Exception):
    """Base exception for context retrieval errors."""
    pass


def get_chunk_only_content(
    collection: chromadb.Collection,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    # Content is already in the result from initial search
    # Just ensure totalChunks is set correctly
    result['totalChunks'] = 1
    return result


def get_enhanced_content(
    collection: chromadb.Collection,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    note_id = result['noteId']
    matched_chunk_index = result['chunkIndex']

    # Calculate range of chunks to retrieve (±2 from matched chunk)
    start_index = max(0, matched_chunk_index - 2)
    end_index = matched_chunk_index + 2  # Will adjust based on actual chunks available

    try:
        # Query for chunks from the same note within the index range
        surrounding_results = collection.get(
            where={
                "$and": [
                    {"noteId": {"$eq": note_id}},
                    {"chunkIndex": {"$gte": start_index}},
                    {"chunkIndex": {"$lte": end_index}}
                ]
            },
            include=["documents", "metadatas"]
        )

        if not surrounding_results or not surrounding_results['ids']:
            # Fallback to chunk_only if we can't get surrounding chunks
            return get_chunk_only_content(collection, result)

        # Sort chunks by index
        chunks = []
        for i in range(len(surrounding_results['ids'])):
            chunks.append({
                'index': surrounding_results['metadatas'][i]['chunkIndex'],
                'content': surrounding_results['documents'][i]
            })

        chunks.sort(key=lambda x: x['index'])

        # Build content with markers
        content_parts = []
        for chunk in chunks:
            if chunk['index'] == matched_chunk_index:
                content_parts.append("[MATCH START]")
                content_parts.append(chunk['content'])
                content_parts.append("[MATCH END]")
            else:
                content_parts.append(chunk['content'])

        result['content'] = "\n\n".join(content_parts)
        result['totalChunks'] = len(chunks)

        return result

    except Exception as error:
        # Fallback to chunk_only on error
        console_logger.warning(f"Enhanced context retrieval failed: {error}. Falling back to chunk_only mode.")
        return get_chunk_only_content(collection, result)


def get_full_note_content(
    collection: chromadb.Collection,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    note_id = result['noteId']
    matched_chunk_index = result['chunkIndex']

    try:
        # Query for all chunks from the same note
        note_results = collection.get(
            where={"noteId": {"$eq": note_id}},
            include=["documents", "metadatas"]
        )

        if not note_results or not note_results['ids']:
            # Fallback to chunk_only if we can't get the full note
            return get_chunk_only_content(collection, result)

        # Sort chunks by index
        chunks = []
        for i in range(len(note_results['ids'])):
            chunks.append({
                'index': note_results['metadatas'][i]['chunkIndex'],
                'content': note_results['documents'][i]
            })

        chunks.sort(key=lambda x: x['index'])

        # Build content with match marker
        content_parts = []
        for chunk in chunks:
            if chunk['index'] == matched_chunk_index:
                content_parts.append(f"[MATCH AT CHUNK {matched_chunk_index}]")
            content_parts.append(chunk['content'])

        result['content'] = "\n\n".join(content_parts)
        result['totalChunks'] = len(chunks)

        return result

    except Exception as error:
        # Fallback to chunk_only on error
        console_logger.warning(f"Full note retrieval failed: {error}. Falling back to chunk_only mode.")
        return get_chunk_only_content(collection, result)


def apply_context_mode(
    collection: chromadb.Collection,
    results: List[Dict[str, Any]],
    context_mode: str
) -> List[Dict[str, Any]]:
    if not results:
        return results

    enhanced_results = []

    for result in results:
        if context_mode == "chunk_only":
            enhanced_results.append(get_chunk_only_content(collection, result))
        elif context_mode == "enhanced":
            enhanced_results.append(get_enhanced_content(collection, result))
        elif context_mode == "full_note":
            enhanced_results.append(get_full_note_content(collection, result))
        else:
            # Default to chunk_only for unknown modes
            enhanced_results.append(get_chunk_only_content(collection, result))

    return enhanced_results
