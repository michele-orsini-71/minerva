from typing import List, Dict, Any, Tuple
import chromadb
import time
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
    """
    Get enhanced content for a single result.

    NOTE: This function is kept for backward compatibility but is less efficient
    than batch_get_enhanced_content() when processing multiple results.
    """
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
            if surrounding_results['metadatas'] and surrounding_results['documents']:
                metadata = surrounding_results['metadatas'][i]
                chunks.append({
                    'index': metadata['chunkIndex'] if metadata else 0,
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


def batch_get_enhanced_content(
    collection: chromadb.Collection,
    results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if not results:
        return results

    try:
        # Step 1: Collect all (noteId, chunkIndex range) requirements
        start_time = time.time()
        query_conditions = []
        result_requirements = []  # Track what each result needs

        for result in results:
            note_id = result['noteId']
            matched_chunk_index = result['chunkIndex']
            start_index = max(0, matched_chunk_index - 2)
            end_index = matched_chunk_index + 2

            result_requirements.append({
                'result': result,
                'noteId': note_id,
                'matchedChunkIndex': matched_chunk_index,
                'startIndex': start_index,
                'endIndex': end_index
            })

            # Build query condition for this result
            query_conditions.append({
                "$and": [
                    {"noteId": {"$eq": note_id}},
                    {"chunkIndex": {"$gte": start_index}},
                    {"chunkIndex": {"$lte": end_index}}
                ]
            })

        # Step 2: Execute single batched query with $or
        batch_query = {"$or": query_conditions} if len(query_conditions) > 1 else query_conditions[0]

        all_chunks_results = collection.get(
            where=batch_query,
            include=["documents", "metadatas"]
        )

        query_time = time.time() - start_time
        console_logger.info(f"  → Batch query completed in {query_time*1000:.1f}ms ({len(results)} results)")

        if not all_chunks_results or not all_chunks_results['ids']:
            # Fallback to chunk_only for all results
            console_logger.warning("Batch query returned no results. Falling back to chunk_only mode.")
            return [get_chunk_only_content(collection, r) for r in results]

        # Step 3: Group chunks by (noteId, chunkIndex) for fast lookup
        group_start = time.time()
        chunks_map = {}  # {(noteId, chunkIndex): {'index': ..., 'content': ...}}

        for i in range(len(all_chunks_results['ids'])):
            if all_chunks_results['metadatas'] and i < len(all_chunks_results['metadatas']):
                metadata = all_chunks_results['metadatas'][i]
                note_id = metadata.get('noteId') if metadata else None
                chunk_index = metadata.get('chunkIndex') if metadata else None

                if note_id is not None and chunk_index is not None and all_chunks_results['documents']:
                    key = (note_id, chunk_index)
                    chunks_map[key] = {
                        'index': chunk_index,
                        'content': all_chunks_results['documents'][i]
                    }

        group_time = time.time() - group_start
        console_logger.info(f"  → Grouped {len(chunks_map)} chunks in {group_time*1000:.1f}ms")

        # Step 4: Distribute chunks back to their respective results
        distribute_start = time.time()
        enhanced_results = []

        for req in result_requirements:
            result = req['result']
            note_id = req['noteId']
            matched_chunk_index = req['matchedChunkIndex']
            start_index = req['startIndex']
            end_index = req['endIndex']

            # Collect chunks for this result
            relevant_chunks = []
            for chunk_index in range(start_index, end_index + 1):
                key = (note_id, chunk_index)
                if key in chunks_map:
                    relevant_chunks.append(chunks_map[key])

            if not relevant_chunks:
                # Fallback to chunk_only for this result
                enhanced_results.append(get_chunk_only_content(collection, result))
                continue

            # Sort chunks by index
            relevant_chunks.sort(key=lambda x: x['index'])

            # Build content with markers
            content_parts = []
            for chunk in relevant_chunks:
                if chunk['index'] == matched_chunk_index:
                    content_parts.append("[MATCH START]")
                    content_parts.append(chunk['content'])
                    content_parts.append("[MATCH END]")
                else:
                    content_parts.append(chunk['content'])

            result['content'] = "\n\n".join(content_parts)
            result['totalChunks'] = len(relevant_chunks)
            enhanced_results.append(result)

        distribute_time = time.time() - distribute_start
        console_logger.info(f"  → Distributed chunks in {distribute_time*1000:.1f}ms")

        total_time = time.time() - start_time
        console_logger.info(f"  → Total batch processing: {total_time*1000:.1f}ms")

        if total_time > 2.0:
            console_logger.warning(f"Batch context retrieval took {total_time:.2f}s - performance may need optimization")

        return enhanced_results

    except Exception as error:
        # Fallback to processing each result individually
        console_logger.warning(f"Batch enhanced context retrieval failed: {error}. Falling back to individual processing.")
        return [get_enhanced_content(collection, result) for result in results]


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
            if note_results['metadatas'] and note_results['documents']:
                metadata = note_results['metadatas'][i]
                chunks.append({
                    'index': metadata['chunkIndex'] if metadata else 0,
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

    # Use batch processing for enhanced mode (significant performance improvement)
    if context_mode == "enhanced":
        return batch_get_enhanced_content(collection, results)

    # For other modes, process individually
    enhanced_results = []
    for result in results:
        if context_mode == "chunk_only":
            enhanced_results.append(get_chunk_only_content(collection, result))
        elif context_mode == "full_note":
            enhanced_results.append(get_full_note_content(collection, result))
        else:
            # Default to chunk_only for unknown modes
            enhanced_results.append(get_chunk_only_content(collection, result))

    return enhanced_results
