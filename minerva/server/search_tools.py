import sys
from typing import List, Dict, Any
from pathlib import Path

import chromadb
from minerva.indexing.storage import initialize_chromadb_client, ChromaDBConnectionError
from minerva.common.ai_provider import AIProvider, AIProviderError, ProviderUnavailableError

from minerva.server.context_retrieval import apply_context_mode
from minerva.common.logger import get_logger

console_logger = get_logger(__name__)


class SearchError(Exception):
    pass


class CollectionNotFoundError(Exception):
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
    provider: AIProvider,
    context_mode: str = "enhanced",
    max_results: int = 5
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
        client = initialize_chromadb_client(chromadb_path)

        collection = validate_collection_exists(client, collection_name)

        collection_metadata = collection.metadata
        if not collection_metadata:
            raise SearchError(
                f"Collection '{collection_name}' has no metadata. "
                f"This collection was created with an old pipeline version and is not compatible. "
                f"Please recreate the collection using the updated pipeline with AI provider metadata."
            )

        expected_dimension = collection_metadata.get('embedding_dimension')

        console_logger.info("  → Generating query embedding...")
        try:
            query_embedding = provider.generate_embedding(query)
            console_logger.info(f"  ✓ Embedding generated (dimension: {len(query_embedding)})")
        except ProviderUnavailableError as error:
            raise SearchError(
                f"AI provider unavailable: {error}\n"
                f"Suggestion: Ensure the provider service is running and accessible."
            )
        except AIProviderError as error:
            raise SearchError(f"Failed to generate query embedding: {error}")

        actual_dimension = len(query_embedding)
        if expected_dimension is not None and actual_dimension != expected_dimension:
            raise SearchError(
                f"Embedding dimension mismatch! Query: {actual_dimension}, Collection: {expected_dimension}\n"
                f"The collection was created with a different embedding model.\n"
                f"Collection provider: {collection_metadata.get('embedding_provider')}\n"
                f"Collection model: {collection_metadata.get('embedding_model')}"
            )

        console_logger.info(f"  → Querying ChromaDB (max_results: {max_results})...")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max_results,
            include=["documents", "metadatas", "distances"]
        )

        # Log how many results were found
        num_results = len(results['ids'][0]) if results and results['ids'] else 0
        console_logger.info(f"  ✓ ChromaDB query completed ({num_results} results found)")

        formatted_results = []

        if results and results['ids'] and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                result = {
                    'chunkId': results['ids'][0][i],  # Include chunk ID for Strategy 4
                    'noteTitle': results['metadatas'][0][i].get('title', 'Unknown'),
                    'noteId': results['metadatas'][0][i].get('noteId', 'unknown'),
                    'chunkIndex': results['metadatas'][0][i].get('chunkIndex', 0),
                    'modificationDate': results['metadatas'][0][i].get('modificationDate', ''),
                    'collectionName': collection_name,
                    'similarityScore': 1.0 - results['distances'][0][i],
                    'content': results['documents'][0][i],
                    'totalChunks': 1
                }
                formatted_results.append(result)

        console_logger.info(f"  → Applying context mode: {context_mode}...")
        enhanced_results = apply_context_mode(collection, formatted_results, context_mode)
        console_logger.info(f"  ✓ Context retrieval completed")

        return enhanced_results

    except CollectionNotFoundError:
        raise
    except SearchError:
        raise
    except ChromaDBConnectionError as error:
        raise SearchError(f"ChromaDB connection failed: {error}")
    except Exception as error:
        raise SearchError(f"Search failed: {error}")
