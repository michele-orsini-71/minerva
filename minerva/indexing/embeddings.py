import time
from typing import List, Dict, Any, Optional, Callable
import sys

import numpy as np

from minerva.common.exceptions import EmbeddingError
from minerva.common.logger import get_logger
from minerva.common.models import Chunk, ChunkWithEmbedding, ChunkList, ChunkWithEmbeddingList
from minerva.common.ai_provider import AIProvider, AIProviderError, ProviderUnavailableError
from minerva.common.ai_config import AIProviderConfig

logger = get_logger(__name__, mode="cli")

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0

# Provider-specific batch sizes for embeddings
# Based on official API limits (as of 2025)
BATCH_SIZES = {
    'openai': 2048,      # OpenAI supports up to 2048 inputs per request
    'gemini': 250,       # Gemini Vertex AI supports up to 250 inputs
    'ollama': 1,         # Local Ollama - no batching needed (already fast)
    'lmstudio': 1,       # LM Studio - no batching needed (local)
}


def initialize_provider(provider_config: AIProviderConfig) -> AIProvider:
    try:
        return AIProvider(provider_config)
    except AIProviderError as error:
        raise EmbeddingError(f"Failed to initialize AI provider: {error}")


def generate_embedding(
    provider: AIProvider,
    text: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY
) -> List[float]:

    if not text or not text.strip():
        raise ValueError(
            "Cannot generate embedding for empty text\n"
            "  Received: empty or whitespace-only string\n"
            "  Suggestion: Filter out empty chunks before embedding generation"
        )

    for attempt in range(max_retries + 1):
        try:
            return provider.generate_embedding(text)

        except AIProviderError as error:
            if attempt < max_retries:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {error}")
                logger.warning(f"         Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise EmbeddingError(f"Failed to generate embedding after {max_retries + 1} attempts: {error}")
        except Exception as error:
            if attempt < max_retries:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {error}")
                logger.warning(f"         Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise EmbeddingError(f"Failed to generate embedding after {max_retries + 1} attempts: {error}")

    # Safety fallback - should never reach here due to exception handling above
    raise EmbeddingError("Failed to generate embedding: unexpected loop exit")

def generate_embeddings_batch(
    provider: AIProvider,
    texts: List[str],
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY
) -> List[List[float]]:
    if not texts:
        return []

    # Validate all texts are non-empty
    for i, text in enumerate(texts):
        if not text or not text.strip():
            raise ValueError(
                f"Cannot generate embedding for empty text at batch index {i}\n"
                f"  Received: empty or whitespace-only string\n"
                f"  Suggestion: Filter out empty chunks before embedding generation"
            )

    for attempt in range(max_retries + 1):
        try:
            return provider.generate_embeddings_batch(texts)

        except AIProviderError as error:
            if attempt < max_retries:
                logger.warning(f"Batch embedding attempt {attempt + 1} failed: {error}")
                logger.warning(f"         Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise EmbeddingError(
                    f"Failed to generate batch embeddings after {max_retries + 1} attempts: {error}"
                )
        except Exception as error:
            if attempt < max_retries:
                logger.warning(f"Batch embedding attempt {attempt + 1} failed: {error}")
                logger.warning(f"         Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise EmbeddingError(
                    f"Failed to generate batch embeddings after {max_retries + 1} attempts: {error}"
                )

    # Safety fallback
    raise EmbeddingError("Failed to generate batch embeddings: unexpected loop exit")


def validate_embedding_consistency(embeddings: List[List[float]]) -> bool:
    if not embeddings:
        return True

    expected_dim = len(embeddings[0])
    for i, emb in enumerate(embeddings):
        if len(emb) != expected_dim:
            logger.warning(f"Embedding {i} has dimension {len(emb)}, expected {expected_dim}")
            return False

    for i, emb in enumerate(embeddings):
        norm = np.linalg.norm(emb)
        if not (0.99 <= norm <= 1.01):
            logger.warning(f"Embedding {i} is not normalized (norm: {norm:.4f})")
            return False

    return True


def generate_embeddings(
    provider: AIProvider,
    chunks: ChunkList,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> ChunkWithEmbeddingList:
    if not chunks:
        return []

    provider_type = provider.provider_type
    embedding_model = provider.embedding_model

    # Determine batch size for this provider
    batch_size = BATCH_SIZES.get(provider_type, 1)

    if batch_size > 1:
        logger.info(
            f"Generating embeddings for {len(chunks)} chunks using {provider_type}/{embedding_model} "
            f"(batch size: {batch_size})..."
        )
    else:
        logger.info(f"Generating embeddings for {len(chunks)} chunks using {provider_type}/{embedding_model}...")

    try:
        availability = provider.check_availability()
        if not availability['available']:
            raise EmbeddingError(f"Provider unavailable: {availability.get('error', 'Unknown error')}")
        logger.info(f"   Provider ready: {provider_type}/{embedding_model}")
    except AIProviderError as error:
        raise EmbeddingError(f"Provider initialization check failed: {error}")

    chunks_with_embeddings = []
    failed_chunks = []
    processed_count = 0

    # Process chunks in batches
    if batch_size > 1:
        # Batch processing mode
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        logger.info(f"   Processing {len(chunks)} chunks in {total_batches} batch(es)...")

        for batch_idx in range(0, len(chunks), batch_size):
            batch_chunks = chunks[batch_idx:batch_idx + batch_size]
            batch_texts = [chunk.content for chunk in batch_chunks]

            current_batch_num = (batch_idx // batch_size) + 1

            try:
                # Generate embeddings for entire batch
                embeddings = generate_embeddings_batch(
                    provider=provider,
                    texts=batch_texts,
                    max_retries=max_retries,
                    retry_delay=retry_delay
                )

                # Pair chunks with their embeddings
                for chunk, embedding in zip(batch_chunks, embeddings):
                    chunk_with_embedding = ChunkWithEmbedding(
                        chunk=chunk,
                        embedding=embedding
                    )
                    chunks_with_embeddings.append(chunk_with_embedding)

                processed_count += len(batch_chunks)

                # Progress reporting
                if progress_callback:
                    progress_callback(processed_count, len(chunks))

                logger.info(
                    f"   Batch {current_batch_num}/{total_batches} complete: "
                    f"{processed_count}/{len(chunks)} chunks ({processed_count / len(chunks) * 100:.1f}%)"
                )

            except Exception as error:
                # If batch fails, fall back to processing chunks individually
                logger.warning(f"   Batch {current_batch_num} failed: {error}")
                logger.warning(f"   Falling back to individual processing for this batch...")

                for chunk in batch_chunks:
                    try:
                        embedding = generate_embedding(
                            provider=provider,
                            text=chunk.content,
                            max_retries=max_retries,
                            retry_delay=retry_delay
                        )

                        chunk_with_embedding = ChunkWithEmbedding(
                            chunk=chunk,
                            embedding=embedding
                        )
                        chunks_with_embeddings.append(chunk_with_embedding)

                    except Exception as individual_error:
                        failed_chunks.append({
                            'chunk_id': chunk.id,
                            'title': chunk.title,
                            'error': str(individual_error)
                        })
                        logger.error(f"   Failed to generate embedding for chunk {chunk.id}: {individual_error}")

                processed_count += len(batch_chunks)
                if progress_callback:
                    progress_callback(processed_count, len(chunks))

    else:
        # Sequential processing mode (for local providers)
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(i, len(chunks))

            try:
                embedding = generate_embedding(
                    provider=provider,
                    text=chunk.content,
                    max_retries=max_retries,
                    retry_delay=retry_delay
                )

                chunk_with_embedding = ChunkWithEmbedding(
                    chunk=chunk,
                    embedding=embedding
                )

                chunks_with_embeddings.append(chunk_with_embedding)

            except Exception as error:
                failed_chunks.append({
                    'chunk_id': chunk.id,
                    'title': chunk.title,
                    'error': str(error)
                })
                logger.error(f"   Failed to generate embedding for chunk {chunk.id}: {error}")
                continue

            if (i + 1) % 25 == 0 or i == len(chunks) - 1:
                logger.info(f"   Progress: {i + 1}/{len(chunks)} chunks ({(i + 1) / len(chunks) * 100:.1f}%)")

        if progress_callback:
            progress_callback(len(chunks), len(chunks))

    # Validate embedding consistency
    if chunks_with_embeddings:
        embedding_vectors = [cwe.embedding for cwe in chunks_with_embeddings]
        is_consistent = validate_embedding_consistency(embedding_vectors)
        if not is_consistent:
            logger.warning("   Embedding consistency check failed")

    # Report final results
    logger.info(f"   Embedding generation complete:")
    logger.info(f"  Successfully embedded: {len(chunks_with_embeddings)} chunks")
    logger.info(f"  Failed: {len(failed_chunks)} chunks")

    if failed_chunks:
        logger.warning(f"\n   Failed chunks:")
        for failed in failed_chunks:
            logger.warning(f"  - {failed['chunk_id']} ({failed['title']}): {failed['error']}")

    if not chunks_with_embeddings:
        raise EmbeddingError("No embeddings were successfully generated")

    return chunks_with_embeddings
