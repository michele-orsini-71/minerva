#!/usr/bin/env python3
"""
Multi-Collection MCP Server for Markdown Notes Search

This MCP server enables AI agents like Claude Desktop to perform semantic search
across multiple ChromaDB knowledge bases (Bear notes, Zim wikis, documentation, etc.).

The server exposes two main tools:
1. list_knowledge_bases - Discover all available collections
2. search_knowledge_base - Perform semantic search with configurable context modes

Architecture:
- FastMCP framework for declarative tool registration
- ChromaDB for vector storage and semantic search
- Ollama for local embedding generation
- Configuration-driven with comprehensive validation
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import FastMCP framework
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: FastMCP not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Import configuration and validation modules
from config import load_config, get_config_file_path, ConfigError, ConfigValidationError
from startup_validation import validate_server_prerequisites
from collection_discovery import discover_collections_with_providers, CollectionDiscoveryError
from search_tools import (
    search_knowledge_base as search_kb,
    SearchError,
    CollectionNotFoundError
)
from ai_provider import AIProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("markdown-notes-mcp-server")

# Global configuration (loaded at startup)
CONFIG: Dict[str, Any] = {}
PROVIDER_MAP: Dict[str, AIProvider] = {}
AVAILABLE_COLLECTIONS: List[Dict[str, Any]] = []

def initialize_server() -> None:
    global CONFIG, PROVIDER_MAP, AVAILABLE_COLLECTIONS

    try:
        logger.info("Loading configuration...")
        config_path = get_config_file_path()
        CONFIG = load_config(config_path)
        logger.info(f"✓ Configuration loaded from {config_path}")
        logger.info(f"  ChromaDB path: {CONFIG['chromadb_path']}")
        logger.info(f"  Default max results: {CONFIG['default_max_results']}")

    except (ConfigError, ConfigValidationError) as e:
        logger.error("Configuration loading failed:")
        logger.error(str(e))
        print(f"\n✗ Configuration Error:\n\n{e}\n", file=sys.stderr)
        sys.exit(1)

    try:
        logger.info("\nValidating server prerequisites...")
        success, error = validate_server_prerequisites(CONFIG)

        if not success:
            logger.error("Server validation failed:")
            logger.error(error)
            print(f"\n✗ Server Validation Failed:\n\n{error}\n", file=sys.stderr)
            sys.exit(1)

        logger.info("✓ All validation checks passed")

    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        print(f"\n✗ Validation Error:\n{e}\n", file=sys.stderr)
        sys.exit(1)

    try:
        logger.info("\nDiscovering collections and initializing AI providers...")
        PROVIDER_MAP, all_collections = discover_collections_with_providers(CONFIG['chromadb_path'])

        total_count = len(all_collections)
        available_count = sum(1 for c in all_collections if c['available'])
        unavailable_count = total_count - available_count

        AVAILABLE_COLLECTIONS = [c for c in all_collections if c['available']]

        logger.info(f"\n{'='*60}")
        logger.info("Collection Discovery Results")
        logger.info(f"{'='*60}")

        for collection in all_collections:
            status = "✓ AVAILABLE" if collection['available'] else "✗ UNAVAILABLE"
            logger.info(f"\n{status}: {collection['name']}")
            logger.info(f"  Description: {collection['description']}")
            logger.info(f"  Chunks: {collection['chunk_count']}")

            if collection['available']:
                logger.info(f"  Provider: {collection['provider_type']}")
                logger.info(f"  Embedding Model: {collection['embedding_model']}")
                logger.info(f"  LLM Model: {collection['llm_model']}")
                if collection.get('embedding_dimension'):
                    logger.info(f"  Embedding Dimension: {collection['embedding_dimension']}")
            else:
                logger.info(f"  Reason: {collection['unavailable_reason']}")

        logger.info(f"\n{'='*60}")
        logger.info(f"Summary: {total_count} total, {available_count} available, {unavailable_count} unavailable")
        logger.info(f"{'='*60}\n")

        if available_count == 0:
            error_msg = (
                "No collections are available!\n\n"
                "Troubleshooting:\n"
                "1. Ensure collections were created with the updated pipeline that includes AI provider metadata\n"
                "2. Check that required API keys are set as environment variables\n"
                "3. For Ollama collections, ensure the Ollama service is running: ollama serve\n"
                "4. Verify provider configurations in your collection metadata\n\n"
                "Run the pipeline with --verbose to create collections with proper metadata."
            )
            logger.error(error_msg)
            print(f"\n✗ {error_msg}\n", file=sys.stderr)
            sys.exit(1)

        logger.info("Server is ready to accept requests\n")

    except CollectionDiscoveryError as e:
        logger.error(f"Collection discovery failed: {e}")
        print(f"\n✗ Collection Discovery Error:\n\n{e}\n", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during collection discovery: {e}")
        print(f"\n✗ Collection Discovery Error:\n{e}\n", file=sys.stderr)
        sys.exit(1)


@mcp.tool(
    description="Discover all available knowledge bases (collections) in the system. "
                "Returns collection names, descriptions, and chunk counts to help users choose which knowledge base to search."
)
def list_knowledge_bases() -> List[Dict[str, Any]]:
    try:
        logger.info("Tool invoked: list_knowledge_bases")

        logger.info(f"✓ Returning {len(AVAILABLE_COLLECTIONS)} available collection(s)")
        for col in AVAILABLE_COLLECTIONS:
            logger.info(f"  - {col['name']}: {col['chunk_count']} chunks")

        return AVAILABLE_COLLECTIONS

    except Exception as e:
        logger.error(f"Unexpected error in list_knowledge_bases: {e}")
        raise CollectionDiscoveryError(f"Failed to list knowledge bases: {e}")


@mcp.tool(
    description="Perform semantic search across a knowledge base. "
                "IMPORTANT: Always cite sources by including the noteTitle field in your response to users. "
                "The noteTitle indicates where the information came from (e.g., note name, article title, or document reference). "
                "Format citations naturally, such as: 'According to [Note Title]...' or 'From [Note Title]: ...' "
                "This ensures users know the provenance of the information."
)
def search_knowledge_base(
    query: str,
    collection_name: str,
    context_mode: str = "enhanced",
    max_results: Optional[int] = None
) -> List[Dict[str, Any]]:
    try:
        # Use default max_results from config if not provided
        if max_results is None:
            max_results = CONFIG['default_max_results']

        logger.info(f"Tool invoked: search_knowledge_base")
        logger.info(f"  Query: {query[:80]}{'...' if len(query) > 80 else ''}")
        logger.info(f"  Collection: {collection_name}")
        logger.info(f"  Context mode: {context_mode}")
        logger.info(f"  Max results: {max_results}")

        # Look up provider for target collection
        if collection_name not in PROVIDER_MAP:
            available_collections = [col['name'] for col in AVAILABLE_COLLECTIONS]
            raise SearchError(
                f"Collection '{collection_name}' is not available. "
                f"Use list_knowledge_bases() to see available collections.\n"
                f"Available collections: {', '.join(available_collections) if available_collections else 'none'}"
            )

        provider = PROVIDER_MAP[collection_name]

        # Perform search with collection-specific provider
        results = search_kb(
            query=query,
            collection_name=collection_name,
            chromadb_path=CONFIG['chromadb_path'],
            provider=provider,
            context_mode=context_mode,
            max_results=max_results
        )

        logger.info(f"✓ Search completed: {len(results)} result(s)")
        for i, result in enumerate(results):
            logger.info(f"  {i+1}. {result['noteTitle']} (score: {result['similarityScore']:.3f})")

        return results

    except CollectionNotFoundError as e:
        logger.error(f"Collection not found: {e}")
        raise
    except SearchError as e:
        logger.error(f"Search error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in search_knowledge_base: {e}")
        raise SearchError(f"Search failed: {e}")


def main():
    logger.info("=" * 60)
    logger.info("Multi-Collection MCP Server for Markdown Notes")
    logger.info("=" * 60)

    # Initialize server (load config and validate prerequisites)
    initialize_server()

    # Run FastMCP server in stdio mode
    logger.info("Starting FastMCP server in stdio mode...")
    logger.info("Waiting for MCP protocol requests...\n")

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("\n\nServer shutting down (keyboard interrupt)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
