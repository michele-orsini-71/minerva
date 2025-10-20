import time
from typing import List, Dict, Any, Optional, Callable
import sys

import numpy as np

from minervium.common.models import Chunk, ChunkWithEmbedding, ChunkList, ChunkWithEmbeddingList
from minervium.common.ai_provider import AIProvider, AIProviderError, ProviderUnavailableError
from minervium.common.ai_config import AIProviderConfig
from minervium.common.config_loader import CollectionConfig

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


class EmbeddingError(Exception):
    pass


def initialize_provider(config: CollectionConfig) -> AIProvider:
    ai_provider_config = config.ai_provider

    provider_config = AIProviderConfig(
        provider_type=ai_provider_config['type'],
        embedding_model=ai_provider_config['embedding']['model'],
        llm_model=ai_provider_config['llm']['model'],
        base_url=ai_provider_config['embedding'].get('base_url'),
        api_key=ai_provider_config['embedding'].get('api_key')
    )

    try:
        provider = AIProvider(provider_config)
        return provider
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
                print(f"Warning: Embedding attempt {attempt + 1} failed: {error}", file=sys.stderr)
                print(f"         Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise EmbeddingError(f"Failed to generate embedding after {max_retries + 1} attempts: {error}")
        except Exception as error:
            if attempt < max_retries:
                print(f"Warning: Embedding attempt {attempt + 1} failed: {error}", file=sys.stderr)
                print(f"         Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise EmbeddingError(f"Failed to generate embedding after {max_retries + 1} attempts: {error}")

    # Safety fallback - should never reach here due to exception handling above
    raise EmbeddingError("Failed to generate embedding: unexpected loop exit")

def validate_embedding_consistency(embeddings: List[List[float]]) -> bool:
    if not embeddings:
        return True

    expected_dim = len(embeddings[0])
    for i, emb in enumerate(embeddings):
        if len(emb) != expected_dim:
            print(f"Warning: Embedding {i} has dimension {len(emb)}, expected {expected_dim}", file=sys.stderr)
            return False

    for i, emb in enumerate(embeddings):
        norm = np.linalg.norm(emb)
        if not (0.99 <= norm <= 1.01):
            print(f"Warning: Embedding {i} is not normalized (norm: {norm:.4f})", file=sys.stderr)
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
    print(f"Generating embeddings for {len(chunks)} chunks using {provider_type}/{embedding_model}...")

    try:
        availability = provider.check_availability()
        if not availability['available']:
            raise EmbeddingError(f"Provider unavailable: {availability.get('error', 'Unknown error')}")
        print(f"   Provider ready: {provider_type}/{embedding_model}")
    except AIProviderError as error:
        raise EmbeddingError(f"Provider initialization check failed: {error}")

    chunks_with_embeddings = []
    failed_chunks = []

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
            print(f"   Failed to generate embedding for chunk {chunk.id}: {error}", file=sys.stderr)
            continue

        if (i + 1) % 25 == 0 or i == len(chunks) - 1:
            print(f"   Progress: {i + 1}/{len(chunks)} chunks ({(i + 1) / len(chunks) * 100:.1f}%)")

    if progress_callback:
        progress_callback(len(chunks), len(chunks))

    if chunks_with_embeddings:
        embedding_vectors = [cwe.embedding for cwe in chunks_with_embeddings]
        is_consistent = validate_embedding_consistency(embedding_vectors)
        if not is_consistent:
            print("   Warning: Embedding consistency check failed", file=sys.stderr)

    print(f"   Embedding generation complete:")
    print(f"  Successfully embedded: {len(chunks_with_embeddings)} chunks")
    print(f"  Failed: {len(failed_chunks)} chunks")

    if failed_chunks:
        print(f"\n   Failed chunks:")
        for failed in failed_chunks:
            print(f"  - {failed['chunk_id']} ({failed['title']}): {failed['error']}")

    if not chunks_with_embeddings:
        raise EmbeddingError("No embeddings were successfully generated")

    return chunks_with_embeddings
