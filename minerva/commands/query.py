from argparse import Namespace
from pathlib import Path
import json

from minerva.common.logger import get_logger
from minerva.indexing.storage import initialize_chromadb_client, ChromaDBConnectionError
from minerva.server.search_tools import search_knowledge_base, CollectionNotFoundError
from minerva.server.collection_discovery import discover_collections_with_providers

logger = get_logger(__name__, simple=True, mode="cli")


def run_query(args: Namespace) -> int:
    chromadb_path = Path(args.chromadb_path).expanduser().resolve()
    query_text = args.query
    collection_name = args.collection if hasattr(args, 'collection') and args.collection else None
    max_results = args.max_results if hasattr(args, 'max_results') and args.max_results else 5
    output_format = args.format if hasattr(args, 'format') and args.format else 'text'
    verbose = args.verbose if hasattr(args, 'verbose') and args.verbose else False

    try:
        client = initialize_chromadb_client(str(chromadb_path))

        if collection_name:
            results = _query_single_collection(
                client, chromadb_path, collection_name, query_text, max_results, verbose
            )
            _print_results(results, collection_name, output_format)
        else:
            all_results = _query_all_collections(
                client, chromadb_path, query_text, max_results, verbose
            )
            _print_all_results(all_results, output_format)

        return 0

    except ChromaDBConnectionError as e:
        logger.error(f"ChromaDB connection error: {e}")
        return 1
    except CollectionNotFoundError as e:
        logger.error(str(e))
        return 1
    except KeyboardInterrupt:
        logger.error("\nQuery interrupted")
        return 130
    except Exception as e:
        logger.error(f"Query error: {e}")
        return 1


def _query_single_collection(client, chromadb_path, collection_name, query_text, max_results, verbose):
    provider_map, all_collections = discover_collections_with_providers(str(chromadb_path))

    available_collections = [c for c in all_collections if c['available']]

    matching = [c for c in available_collections if c['name'] == collection_name]
    if not matching:
        unavailable = [c for c in all_collections if c['name'] == collection_name]
        if unavailable:
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' exists but is unavailable\n"
                f"Reason: {unavailable[0]['unavailable_reason']}"
            )
        raise CollectionNotFoundError(
            f"Collection '{collection_name}' not found\n"
            f"Available collections: {', '.join(c['name'] for c in available_collections)}"
        )

    collection_info = matching[0]
    provider = provider_map[collection_name]

    results = search_knowledge_base(
        query=query_text,
        collection_name=collection_name,
        chromadb_path=str(chromadb_path),
        provider=provider,
        context_mode="enhanced",
        max_results=max_results,
        verbose=verbose
    )

    return results


def _query_all_collections(client, chromadb_path, query_text, max_results, verbose):
    provider_map, all_collections = discover_collections_with_providers(str(chromadb_path))

    available_collections = [c for c in all_collections if c['available']]

    if not available_collections:
        logger.error("No available collections found")
        return {}

    logger.info(f"Querying {len(available_collections)} collection(s)...\n")

    all_results = {}
    for collection_info in available_collections:
        collection_name = collection_info['name']

        try:
            provider = provider_map[collection_name]

            results = search_knowledge_base(
                query=query_text,
                collection_name=collection_name,
                chromadb_path=str(chromadb_path),
                provider=provider,
                context_mode="enhanced",
                max_results=max_results,
                verbose=verbose
            )

            all_results[collection_name] = results

        except Exception as e:
            logger.warning(f"Error querying {collection_name}: {e}")
            continue

    return all_results


def _print_results(results, collection_name, output_format):
    if output_format == 'json':
        print(json.dumps(results, indent=2))
    else:
        logger.info(f"\nResults from '{collection_name}':\n")
        logger.info(f"{'='*60}")

        if not results:
            logger.info("No results found")
            return

        for i, result in enumerate(results, 1):
            logger.info(f"\n[{i}] {result['noteTitle']}")
            logger.info(f"Score: {result.get('relevanceScore', result.get('similarityScore', 0)):.4f}")
            logger.info(f"\n{result.get('text', result.get('content', ''))}\n")
            logger.info(f"{'-'*60}")


def _print_all_results(all_results, output_format):
    if output_format == 'json':
        print(json.dumps(all_results, indent=2))
    else:
        for collection_name, results in all_results.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Collection: {collection_name}")
            logger.info(f"{'='*60}")

            if not results:
                logger.info("No results found\n")
                continue

            for i, result in enumerate(results, 1):
                logger.info(f"\n[{i}] {result['noteTitle']}")
                logger.info(f"Score: {result.get('relevanceScore', result.get('similarityScore', 0)):.4f}")
                logger.info(f"\n{result.get('text', result.get('content', ''))}\n")
                if i < len(results):
                    logger.info(f"{'-'*60}")
