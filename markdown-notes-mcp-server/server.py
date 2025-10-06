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
from collection_discovery import list_collections, CollectionDiscoveryError
from search_tools import (
    search_knowledge_base as search_kb,
    SearchError,
    CollectionNotFoundError
)
from embedding import OllamaServiceError

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

def initialize_server() -> None:
    global CONFIG

    try:
        # Step 1: Load configuration
        logger.info("Loading configuration...")
        config_path = get_config_file_path()
        CONFIG = load_config(config_path)
        logger.info(f"✓ Configuration loaded from {config_path}")
        logger.info(f"  ChromaDB path: {CONFIG['chromadb_path']}")
        logger.info(f"  Default max results: {CONFIG['default_max_results']}")
        logger.info(f"  Embedding model: {CONFIG['embedding_model']}")

    except (ConfigError, ConfigValidationError) as e:
        logger.error("Configuration loading failed:")
        logger.error(str(e))
        print(f"\n✗ Configuration Error:\n\n{e}\n", file=sys.stderr)
        sys.exit(1)

    try:
        # Step 2: Validate server prerequisites
        logger.info("\nValidating server prerequisites...")
        success, error = validate_server_prerequisites(CONFIG)

        if not success:
            logger.error("Server validation failed:")
            logger.error(error)
            print(f"\n✗ Server Validation Failed:\n\n{error}\n", file=sys.stderr)
            sys.exit(1)

        logger.info("✓ All validation checks passed")
        logger.info("\nServer is ready to accept requests\n")

    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        print(f"\n✗ Validation Error:\n{e}\n", file=sys.stderr)
        sys.exit(1)


@mcp.tool(
    description="Discover all available knowledge bases (collections) in the system. "
                "Returns collection names, descriptions, and chunk counts to help users choose which knowledge base to search."
)
def list_knowledge_bases() -> List[Dict[str, Any]]:
    try:
        logger.info("Tool invoked: list_knowledge_bases")
        chromadb_path = CONFIG['chromadb_path']

        collections = list_collections(chromadb_path)

        logger.info(f"✓ Found {len(collections)} collection(s)")
        for col in collections:
            logger.info(f"  - {col['name']}: {col['chunk_count']} chunks")

        return collections

    except CollectionDiscoveryError as e:
        logger.error(f"Collection discovery failed: {e}")
        raise
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

        # Perform search
        results = search_kb(
            query=query,
            collection_name=collection_name,
            chromadb_path=CONFIG['chromadb_path'],
            context_mode=context_mode,
            max_results=max_results,
            embedding_model=CONFIG['embedding_model']
        )

        logger.info(f"✓ Search completed: {len(results)} result(s)")
        for i, result in enumerate(results):
            logger.info(f"  {i+1}. {result['noteTitle']} (score: {result['similarityScore']:.3f})")

        return results

    except CollectionNotFoundError as e:
        logger.error(f"Collection not found: {e}")
        raise
    except OllamaServiceError as e:
        logger.error(f"Ollama service error: {e}")
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
