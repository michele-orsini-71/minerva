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
from typing import List, Dict, Any, Optional

# Import FastMCP framework
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Use print here as ConsoleLogger isn't available yet
    print("Error: FastMCP not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Import configuration and validation modules
from minervium.common.config import load_config, ConfigError, ConfigValidationError
from minervium.server.startup_validation import validate_server_prerequisites
from minervium.server.collection_discovery import discover_collections_with_providers, CollectionDiscoveryError
from minervium.server.search_tools import (
    search_knowledge_base as search_kb,
    SearchError,
    CollectionNotFoundError
)
from minervium.common.ai_provider import AIProvider
from minervium.common.logger import get_logger

# Initialize console logger
console_logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("markdown-notes-mcp-server")

# Global configuration (loaded at startup)
CONFIG: Dict[str, Any] = {}
PROVIDER_MAP: Dict[str, AIProvider] = {}
AVAILABLE_COLLECTIONS: List[Dict[str, Any]] = []

def initialize_server(config_path: str) -> None:
    global CONFIG, PROVIDER_MAP, AVAILABLE_COLLECTIONS

    try:
        console_logger.info("Loading configuration...")
        CONFIG = load_config(config_path)
        console_logger.success(f"✓ Configuration loaded from {config_path}")
        console_logger.info(f"  ChromaDB path: {CONFIG['chromadb_path']}")
        console_logger.info(f"  Default max results: {CONFIG['default_max_results']}")

    except (ConfigError, ConfigValidationError) as e:
        console_logger.error(f"Configuration Error:\n\n{e}")
        sys.exit(1)

    try:
        console_logger.info("\nValidating server prerequisites...")
        success, error = validate_server_prerequisites(CONFIG)

        if not success:
            console_logger.error(f"Server Validation Failed:\n\n{error}")
            sys.exit(1)

        console_logger.success("✓ All validation checks passed")

    except Exception as e:
        console_logger.error(f"Validation Error:\n{e}")
        sys.exit(1)

    try:
        console_logger.info("\nDiscovering collections and initializing AI providers...")
        PROVIDER_MAP, all_collections = discover_collections_with_providers(CONFIG['chromadb_path'])

        total_count = len(all_collections)
        available_count = sum(1 for c in all_collections if c['available'])
        unavailable_count = total_count - available_count

        AVAILABLE_COLLECTIONS = [c for c in all_collections if c['available']]

        console_logger.info(f"\n{'='*60}")
        console_logger.info("Collection Discovery Results")
        console_logger.info(f"{'='*60}")

        for collection in all_collections:
            status = "✓ AVAILABLE" if collection['available'] else "✗ UNAVAILABLE"
            console_logger.info(f"\n{status}: {collection['name']}")
            console_logger.info(f"  Description: {collection['description']}")
            console_logger.info(f"  Chunks: {collection['chunk_count']}")

            if collection['available']:
                console_logger.info(f"  Provider: {collection['provider_type']}")
                console_logger.info(f"  Embedding Model: {collection['embedding_model']}")
                console_logger.info(f"  LLM Model: {collection['llm_model']}")
                if collection.get('embedding_dimension'):
                    console_logger.info(f"  Embedding Dimension: {collection['embedding_dimension']}")
            else:
                console_logger.info(f"  Reason: {collection['unavailable_reason']}")

        console_logger.info(f"\n{'='*60}")
        console_logger.info(f"Summary: {total_count} total, {available_count} available, {unavailable_count} unavailable")
        console_logger.info(f"{'='*60}\n")

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
            console_logger.error(error_msg)
            sys.exit(1)

        console_logger.info("Server is ready to accept requests\n")

    except CollectionDiscoveryError as e:
        console_logger.error(f"Collection Discovery Error:\n\n{e}")
        sys.exit(1)
    except Exception as e:
        console_logger.error(f"Collection Discovery Error:\n{e}")
        sys.exit(1)


@mcp.tool(
    description="Discover all available knowledge bases (collections) in the system. "
                "Returns collection names, descriptions, and chunk counts to help users choose which knowledge base to search."
)
def list_knowledge_bases() -> List[Dict[str, Any]]:
    try:
        console_logger.info("Tool invoked: list_knowledge_bases")

        console_logger.success(f"✓ Returning {len(AVAILABLE_COLLECTIONS)} available collection(s)")
        for col in AVAILABLE_COLLECTIONS:
            console_logger.info(f"  - {col['name']}: {col['chunk_count']} chunks")

        return AVAILABLE_COLLECTIONS

    except Exception as e:
        console_logger.error(f"Unexpected error in list_knowledge_bases: {e}", print_to_stderr=False)
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
        effective_max_results: int = max_results if max_results is not None else CONFIG['default_max_results']

        console_logger.info(f"Tool invoked: search_knowledge_base")
        console_logger.info(f"  Query: {query[:80]}{'...' if len(query) > 80 else ''}")
        console_logger.info(f"  Collection: {collection_name}")
        console_logger.info(f"  Context mode: {context_mode}")
        console_logger.info(f"  Max results: {effective_max_results}")

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
            max_results=effective_max_results
        )

        console_logger.success(f"✓ Search completed: {len(results)} result(s)")
        for i, result in enumerate(results):
            console_logger.info(f"  {i+1}. {result['noteTitle']} (score: {result['similarityScore']:.3f})")

        return results

    except CollectionNotFoundError as e:
        console_logger.error(f"Collection not found: {e}", print_to_stderr=False)
        raise
    except SearchError as e:
        console_logger.error(f"Search error: {e}", print_to_stderr=False)
        raise
    except Exception as e:
        console_logger.error(f"Unexpected error in search_knowledge_base: {e}", print_to_stderr=False)
        raise SearchError(f"Search failed: {e}")


def main(config_path: str):
    console_logger.info("=" * 60)
    console_logger.info("Multi-Collection MCP Server for Markdown Notes")
    console_logger.info("=" * 60)

    # Initialize server (load config and validate prerequisites)
    initialize_server(config_path)

    # Run FastMCP server in stdio mode
    console_logger.info("Starting FastMCP server in stdio mode...")
    console_logger.info("Waiting for MCP protocol requests...\n")

    try:
        mcp.run()
    except KeyboardInterrupt:
        console_logger.info("\n\nServer shutting down (keyboard interrupt)")
        sys.exit(0)
    except Exception as e:
        console_logger.error(f"Server error: {e}")
        sys.exit(1)
