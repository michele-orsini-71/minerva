import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports from markdown-notes-cag-data-creator
sys.path.insert(0, str(Path(__file__).parent.parent / "markdown-notes-cag-data-creator"))

import chromadb
from embedding import generate_embedding, OllamaServiceError
from storage import initialize_chromadb_client, ChromaDBConnectionError

from context_retrieval import apply_context_mode


class SearchError(Exception):
    """Base exception for search-related errors."""
    pass


class CollectionNotFoundError(Exception):
    """Raised when the specified collection doesn't exist."""
    pass


def validate_collection_exists(
    client: chromadb.PersistentClient,
    collection_name: str
) -> chromadb.Collection:
    try:
        existing_collections = [col.name for col in client.list_collections()]

        if collection_name not in existing_collections:
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' not found.\n"
                f"Available collections: {', '.join(existing_collections) if existing_collections else 'none'}\n"
                f"Suggestion: Use the 'list_knowledge_bases' tool to see available collections."
            )

        return client.get_collection(collection_name)

    except CollectionNotFoundError:
        raise
    except Exception as error:
        raise SearchError(f"Failed to validate collection '{collection_name}': {error}")


def search_knowledge_base(
    query: str,
    collection_name: str,
    chromadb_path: str,
    context_mode: str = "enhanced",
    max_results: int = 5,
    embedding_model: str = "mxbai-embed-large:latest"
) -> List[Dict[str, Any]]:
    if not query or not query.strip():
        raise SearchError("Query cannot be empty")

    if max_results < 1 or max_results > 100:
        raise SearchError("max_results must be between 1 and 100")

    if context_mode not in ["chunk_only", "enhanced", "full_note"]:
        raise SearchError(
            f"Invalid context_mode '{context_mode}'. "
            f"Must be one of: chunk_only, enhanced, full_note"
        )

    try:
        # Step 1: Initialize ChromaDB client
        client = initialize_chromadb_client(chromadb_path)

        # Step 2: Validate collection exists
        collection = validate_collection_exists(client, collection_name)

        # Step 3: Generate query embedding
        try:
            query_embedding = generate_embedding(query, model=embedding_model)
        except OllamaServiceError as error:
            raise OllamaServiceError(
                f"Ollama service unavailable: {error}\n"
                f"Suggestion: Run 'ollama serve' to start the Ollama service."
            )

        # Step 4: Perform semantic search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max_results,
            include=["documents", "metadatas", "distances"]
        )

        # Step 5: Format results
        formatted_results = []

        if results and results['ids'] and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                result = {
                    'noteTitle': results['metadatas'][0][i].get('title', 'Unknown'),
                    'noteId': results['metadatas'][0][i].get('noteId', 'unknown'),
                    'chunkIndex': results['metadatas'][0][i].get('chunkIndex', 0),
                    'modificationDate': results['metadatas'][0][i].get('modificationDate', ''),
                    'collectionName': collection_name,
                    'similarityScore': 1.0 - results['distances'][0][i],  # Convert distance to similarity
                    'content': results['documents'][0][i],
                    'totalChunks': 1  # Will be updated by context retrieval
                }
                formatted_results.append(result)

        # Step 6: Apply context retrieval based on context_mode
        enhanced_results = apply_context_mode(collection, formatted_results, context_mode)

        return enhanced_results

    except (CollectionNotFoundError, OllamaServiceError):
        raise
    except ChromaDBConnectionError as error:
        raise SearchError(f"ChromaDB connection failed: {error}")
    except Exception as error:
        raise SearchError(f"Search failed: {error}")
