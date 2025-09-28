#!/usr/bin/env python3
"""
Embedding generation module for Bear Notes RAG system.

Handles embedding generation using Ollama's mxbai-embed-large model with L2 normalization
for ChromaDB cosine similarity compatibility. Includes service discovery, error handling,
and retry logic for robust operation.
"""

import time
from typing import List, Dict, Any, Optional
import sys

import numpy as np
from ollama import embeddings as ollama_embeddings
import ollama


# Configuration constants
EMBED_MODEL = "mxbai-embed-large:latest"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""
    pass


class OllamaServiceError(Exception):
    """Exception raised when Ollama service is unavailable."""
    pass


def check_ollama_service() -> bool:
    """
    Check if Ollama service is available and responsive.

    Returns:
        True if service is available, False otherwise
    """
    try:
        # Try to get list of models as a health check
        ollama.list()
        return True
    except Exception:
        return False


def check_model_availability(model_name: str = EMBED_MODEL) -> bool:
    """
    Check if the required embedding model is available locally.

    Args:
        model_name: Name of the model to check

    Returns:
        True if model is available, False otherwise
    """
    try:
        models = ollama.list()
        model_names = [model.model for model in models.models]
        return model_name in model_names
    except Exception:
        return False


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """
    Apply L2 normalization to vectors for cosine similarity compatibility.

    Args:
        vectors: Input vectors as numpy array (shape: [n_vectors, embedding_dim])

    Returns:
        L2-normalized vectors with same shape
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Avoid division by zero for zero vectors
    norms[norms == 0] = 1.0
    return vectors / norms


def generate_embedding(
    text: str,
    model: str = EMBED_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY
) -> List[float]:
    """
    Generate embedding for a single text using Ollama.

    Args:
        text: Input text to embed
        model: Ollama model name to use
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        L2-normalized embedding vector as list of floats

    Raises:
        EmbeddingError: If embedding generation fails after retries
        OllamaServiceError: If Ollama service is not available
    """
    if not text.strip():
        # Return zero vector for empty text
        return [0.0] * 1024  # mxbai-embed-large has 1024 dimensions

    for attempt in range(max_retries + 1):
        try:
            response = ollama_embeddings(model=model, prompt=text)

            if 'embedding' not in response:
                raise EmbeddingError("Invalid response from Ollama: missing 'embedding' field")

            # Convert to numpy array and normalize
            vector = np.array(response['embedding'], dtype=np.float32)

            if vector.size == 0:
                raise EmbeddingError("Received empty embedding vector")

            # Apply L2 normalization
            normalized = l2_normalize(vector.reshape(1, -1))
            return normalized.flatten().tolist()

        except Exception as e:
            if attempt < max_retries:
                print(f"Warning: Embedding attempt {attempt + 1} failed: {e}", file=sys.stderr)
                print(f"         Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
            else:
                if "connection" in str(e).lower() or "refused" in str(e).lower():
                    raise OllamaServiceError(f"Ollama service unavailable: {e}")
                else:
                    raise EmbeddingError(f"Failed to generate embedding after {max_retries + 1} attempts: {e}")


def generate_embeddings_batch(
    texts: List[str],
    model: str = EMBED_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    progress_callback: Optional[callable] = None
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts with progress tracking.

    Args:
        texts: List of input texts to embed
        model: Ollama model name to use
        max_retries: Maximum number of retry attempts per text
        retry_delay: Initial delay between retries in seconds
        progress_callback: Optional callback function(current, total) for progress updates

    Returns:
        List of L2-normalized embedding vectors

    Raises:
        EmbeddingError: If any embedding generation fails after retries
        OllamaServiceError: If Ollama service is not available
    """
    if not texts:
        return []

    embeddings = []

    for i, text in enumerate(texts):
        if progress_callback:
            progress_callback(i, len(texts))

        embedding = generate_embedding(
            text=text,
            model=model,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        embeddings.append(embedding)

    if progress_callback:
        progress_callback(len(texts), len(texts))

    return embeddings


def validate_embedding_consistency(embeddings: List[List[float]]) -> bool:
    """
    Validate that all embeddings have consistent dimensions and are properly normalized.

    Args:
        embeddings: List of embedding vectors to validate

    Returns:
        True if all embeddings are consistent, False otherwise
    """
    if not embeddings:
        return True

    # Check dimension consistency
    expected_dim = len(embeddings[0])
    for i, emb in enumerate(embeddings):
        if len(emb) != expected_dim:
            print(f"Warning: Embedding {i} has dimension {len(emb)}, expected {expected_dim}", file=sys.stderr)
            return False

    # Check normalization (L2 norm should be approximately 1.0)
    for i, emb in enumerate(embeddings):
        norm = np.linalg.norm(emb)
        if not (0.99 <= norm <= 1.01):  # Allow small floating point errors
            print(f"Warning: Embedding {i} is not normalized (norm: {norm:.4f})", file=sys.stderr)
            return False

    return True


def initialize_embedding_service(model: str = EMBED_MODEL) -> Dict[str, Any]:
    """
    Initialize and validate the embedding service.

    Args:
        model: Model name to validate

    Returns:
        Dictionary with service status information

    Raises:
        OllamaServiceError: If service initialization fails
    """
    status = {
        'service_available': False,
        'model_available': False,
        'model_name': model,
        'ready': False
    }

    # Check service availability
    if not check_ollama_service():
        raise OllamaServiceError(
            "Ollama service is not available. Please ensure:\n"
            "1. Ollama is installed\n"
            "2. Run 'ollama serve' to start the service\n"
            "3. Check that the service is accessible"
        )

    status['service_available'] = True

    # Check model availability
    if not check_model_availability(model):
        raise OllamaServiceError(
            f"Model '{model}' is not available. Please run:\n"
            f"ollama pull {model}"
        )

    status['model_available'] = True
    status['ready'] = True

    return status


if __name__ == "__main__":
    # Simple test when run directly
    print("🧪 Testing embedding.py module")
    print("=" * 50)

    try:
        # Initialize service
        print("🔍 Checking Ollama service...")
        status = initialize_embedding_service()
        print(f"✅ Service status: {status}")
        print()

        # Test single embedding
        print("📝 Testing single embedding generation...")
        test_text = "This is a test sentence for embedding generation."
        embedding = generate_embedding(test_text)

        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        print(f"   L2 norm: {np.linalg.norm(embedding):.4f}")
        print()

        # Test batch embeddings
        print("📦 Testing batch embedding generation...")
        test_texts = [
            "First test document for batch processing.",
            "Second document with different content.",
            "Third document to complete the batch test."
        ]

        def progress_cb(current, total):
            print(f"   Progress: {current}/{total} ({current/total*100:.1f}%)")

        embeddings = generate_embeddings_batch(test_texts, progress_callback=progress_cb)
        print(f"✅ Generated {len(embeddings)} embeddings")

        # Validate consistency
        print("✅ Validating embedding consistency...")
        is_consistent = validate_embedding_consistency(embeddings)
        print(f"   Consistency check: {'✅ PASSED' if is_consistent else '❌ FAILED'}")

        print()
        print("🎉 All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}", file=sys.stderr)
        sys.exit(1)