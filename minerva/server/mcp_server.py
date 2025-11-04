#!/usr/bin/env python3
from typing import List, Dict, Any, Optional

from minerva.common.exceptions import (
    GracefulExit,
    ServerError,
    StartupValidationError,
    CollectionDiscoveryError,
)
from minerva.common.logger import get_logger

console_logger = get_logger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as error:
    message = "FastMCP not installed. Run: pip install mcp"
    console_logger.error(message)
    raise StartupValidationError(message) from error

# Import configuration and validation modules
from minerva.common.server_config import ServerConfig, load_server_config
from minerva.server.startup_validation import validate_server_prerequisites
from minerva.server.collection_discovery import discover_collections_with_providers
from minerva.server.search_tools import (
    search_knowledge_base as search_kb,
    SearchError,
    CollectionNotFoundError
)
from minerva.common.ai_provider import AIProvider

# Global configuration (loaded at startup)
SERVER_CONFIG: Optional[ServerConfig] = None
PROVIDER_MAP: Dict[str, AIProvider] = {}
AVAILABLE_COLLECTIONS: List[Dict[str, Any]] = []


def _ensure_server_config(config: ServerConfig | str) -> ServerConfig:
    if isinstance(config, ServerConfig):
        return config
    return load_server_config(config)


def initialize_server(server_config: ServerConfig) -> None:
    global SERVER_CONFIG, PROVIDER_MAP, AVAILABLE_COLLECTIONS

    SERVER_CONFIG = server_config
    PROVIDER_MAP = {}
    AVAILABLE_COLLECTIONS = []

    console_logger.info("Loading configuration...")
    source_display = server_config.source_path if server_config.source_path else "provided object"
    console_logger.success(f"✓ Configuration loaded from {source_display}")
    console_logger.info(f"  ChromaDB path: {server_config.chromadb_path}")
    console_logger.info(f"  Default max results: {server_config.default_max_results}")
    if server_config.host:
        console_logger.info(f"  Host override: {server_config.host}")
    if server_config.port:
        console_logger.info(f"  Port override: {server_config.port}")

    console_logger.info("\nValidating server prerequisites...")

    try:
        validate_server_prerequisites(server_config.chromadb_path)
        console_logger.success("✓ All validation checks passed")

    except StartupValidationError as error:
        console_logger.error(f"Server Validation Failed:\n\n{error}")
        raise
    except Exception as error:
        console_logger.error(f"Validation Error:\n{error}")
        raise StartupValidationError(str(error)) from error

    console_logger.info("\nDiscovering collections and initializing AI providers...")

    try:
        provider_map, all_collections = discover_collections_with_providers(server_config.chromadb_path)

        total_count = len(all_collections)
        available_count = sum(1 for c in all_collections if c['available'])
        unavailable_count = total_count - available_count

        available_collections = [c for c in all_collections if c['available']]

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
                embedding_dimension = collection.get('embedding_dimension')
                if embedding_dimension:
                    console_logger.info(f"  Embedding Dimension: {embedding_dimension}")
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
            raise CollectionDiscoveryError(error_msg)

        PROVIDER_MAP = provider_map
        AVAILABLE_COLLECTIONS = available_collections
        console_logger.info("Server is ready to accept requests\n")

    except CollectionDiscoveryError as error:
        console_logger.error(f"Collection Discovery Error:\n\n{error}")
        raise
    except Exception as error:
        console_logger.error(f"Collection Discovery Error:\n{error}")
        raise ServerError(f"Failed to discover collections: {error}") from error


def _register_tools(mcp_instance: FastMCP) -> None:
    """Register all MCP tools with their descriptions."""

    # Register list_knowledge_bases tool
    mcp_instance.tool(
        description="Discover all available knowledge bases (collections) in the system. "
                    "Returns collection names, descriptions, and chunk counts to help users choose which knowledge base to search. "
                    "Use this first to see what collections are available before calling search_knowledge_base. "
                    "\n\n"
                    "NOTE: When you later search these collections, you MUST cite sources using the 'noteTitle' field from search results."
    )(list_knowledge_bases)

    # Register search_knowledge_base tool
    mcp_instance.tool(
        description="Perform semantic search across indexed knowledge bases (documentation, notes, standards). "
                    "Use this for conceptual queries like 'what does the documentation say about X?', 'how should I implement Y?', 'what are the standards for Z?'. "
                    "This searches curated, indexed content and returns ranked results by relevance. "
                    "More efficient than Grep/Glob for semantic/documentation searches. Not for searching raw source code - use Grep/Glob for exact string matching in source files. "
                    "\n\n"
                    "⚠️ CITATION REQUIREMENT - YOU MUST FOLLOW THIS:\n"
                    "ALWAYS cite the source by including the 'noteTitle' field when presenting information to users. "
                    "Every single response that uses information from search results MUST include the note title. "
                    "Format: 'According to [noteTitle], ...' or 'From [noteTitle]: ...' or '[noteTitle] states that ...' "
                    "Do NOT present information without citing its source. The noteTitle indicates where the information came from. "
                    "\n\n"
                    "TOKEN LIMITS: Each result includes surrounding context (~1,500 tokens). "
                    "Start with max_results=3-5 (default: 5). If you get a token limit error, retry with fewer results. "
                    "The system will self-regulate through error responses. Max allowed: 15 results."
    )(search_knowledge_base)


def list_knowledge_bases() -> List[Dict[str, Any]]:
    try:
        console_logger.info("Tool invoked: list_knowledge_bases")

        console_logger.success(f"✓ Returning {len(AVAILABLE_COLLECTIONS)} available collection(s)")
        for col in AVAILABLE_COLLECTIONS:
            console_logger.info(f"  - {col['name']}: {col['chunk_count']} chunks")

        return AVAILABLE_COLLECTIONS

    except Exception as e:
        console_logger.error(f"Unexpected error in list_knowledge_bases: {e}")
        raise CollectionDiscoveryError(f"Failed to list knowledge bases: {e}")


def search_knowledge_base(
    query: str,
    collection_name: str,
    context_mode: str = "enhanced",
    max_results: Optional[int] = None
) -> List[Dict[str, Any]]:
    try:
        # Use default max_results from config if not provided
        if SERVER_CONFIG is None:
            raise ServerError("Server configuration not initialized")

        effective_max_results: int = max_results if max_results is not None else SERVER_CONFIG.default_max_results

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
            chromadb_path=SERVER_CONFIG.chromadb_path,
            provider=provider,
            context_mode=context_mode,
            max_results=effective_max_results
        )

        console_logger.success(f"✓ Search completed: {len(results)} result(s)")
        for i, result in enumerate(results):
            console_logger.info(f"  {i+1}. {result['noteTitle']} (score: {result['similarityScore']:.3f})")

        return results

    except CollectionNotFoundError as e:
        console_logger.error(f"Collection not found: {e}")
        raise
    except SearchError as e:
        console_logger.error(f"Search error: {e}")
        raise
    except Exception as e:
        console_logger.error(f"Unexpected error in search_knowledge_base: {e}")
        raise SearchError(f"Search failed: {e}")


def main(config: ServerConfig | str):
    console_logger.info("=" * 60)
    console_logger.info("Multi-Collection MCP Server for Markdown Notes")
    console_logger.info("=" * 60)

    server_config = _ensure_server_config(config)
    initialize_server(server_config)

    # Create FastMCP instance (stdio mode doesn't need host/port)
    mcp = FastMCP("minerva-mcp-server")

    # Register all tools
    _register_tools(mcp)

    console_logger.info("Starting FastMCP server in stdio mode...")
    console_logger.info("Waiting for MCP protocol requests...\n")

    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        console_logger.info("\n\nServer shutting down (keyboard interrupt)")
        raise GracefulExit("Server shutdown requested", exit_code=0)
    except Exception as error:
        console_logger.error(f"Server error: {error}")
        raise ServerError(f"Server encountered an error: {error}") from error


def main_http(config: ServerConfig | str):
    console_logger.info("=" * 60)
    console_logger.info("Multi-Collection MCP Server for Markdown Notes")
    console_logger.info("=" * 60)

    server_config = _ensure_server_config(config)
    initialize_server(server_config)

    host = server_config.host or "localhost"
    port = server_config.port or 8000

    # Create FastMCP instance with config from file
    mcp = FastMCP("minerva-mcp-server", host=host, port=port)

    # Register all tools
    _register_tools(mcp)

    console_logger.info(f"Starting FastMCP server in HTTP mode on http://{host}:{port}...")
    console_logger.info(f"MCP endpoint will be available at: http://{host}:{port}/mcp/")
    console_logger.info("Waiting for HTTP requests...\n")

    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        console_logger.info("\n\nServer shutting down (keyboard interrupt)")
        raise GracefulExit("Server shutdown requested", exit_code=0)
    except Exception as error:
        console_logger.error(f"Server error: {error}")
        raise ServerError(f"Server encountered an error: {error}") from error
