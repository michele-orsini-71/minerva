from typing import List, Dict, Any
from minerva.server.collection_discovery import list_collections, CollectionDiscoveryError
from minerva.server.search_tools import search_knowledge_base, SearchError, CollectionNotFoundError
from minerva.common.logger import get_logger

logger = get_logger(__name__)


TOOL_LIST_KNOWLEDGE_BASES = {
    "type": "function",
    "function": {
        "name": "list_knowledge_bases",
        "description": "List all available knowledge bases (collections) in the system. Returns information about each collection including name, description, chunk count, and availability status.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

TOOL_SEARCH_KNOWLEDGE_BASE = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Search a specific knowledge base using semantic search. Returns relevant chunks of information ranked by similarity to the query. Use this to find information from a user's personal notes and knowledge.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query in natural language"
                },
                "collection_name": {
                    "type": "string",
                    "description": "The name of the knowledge base to search"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-15, default: 3)",
                    "minimum": 1,
                    "maximum": 15,
                    "default": 3
                },
                "context_mode": {
                    "type": "string",
                    "description": "Context retrieval mode: 'chunk_only' (just matching chunk), 'enhanced' (matching chunk + surrounding chunks), 'full_note' (entire note)",
                    "enum": ["chunk_only", "enhanced", "full_note"],
                    "default": "enhanced"
                }
            },
            "required": ["query", "collection_name"]
        }
    }
}


def get_tool_definitions() -> List[Dict]:
    return [TOOL_LIST_KNOWLEDGE_BASES, TOOL_SEARCH_KNOWLEDGE_BASE]


def _execute_list_knowledge_bases(context: Dict) -> Dict:
    chromadb_path = context.get('chromadb_path')
    if not chromadb_path:
        return {
            'success': False,
            'error': 'chromadb_path not provided in context'
        }

    try:
        collections = list_collections(chromadb_path)
        return {
            'success': True,
            'collections': collections,
            'count': len(collections)
        }
    except CollectionDiscoveryError as e:
        logger.error(f"Collection discovery failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error listing collections: {e}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def _execute_search_knowledge_base(arguments: Dict, context: Dict) -> Dict:
    chromadb_path = context.get('chromadb_path')
    provider = context.get('provider')

    if not chromadb_path:
        return {
            'success': False,
            'error': 'chromadb_path not provided in context'
        }

    if not provider:
        return {
            'success': False,
            'error': 'AI provider not provided in context'
        }

    query = arguments.get('query')
    collection_name = arguments.get('collection_name')
    max_results = arguments.get('max_results', 3)
    context_mode = arguments.get('context_mode', 'enhanced')

    if not query:
        return {
            'success': False,
            'error': 'query parameter is required'
        }

    if not collection_name:
        return {
            'success': False,
            'error': 'collection_name parameter is required'
        }

    try:
        results = search_knowledge_base(
            query=query,
            collection_name=collection_name,
            chromadb_path=chromadb_path,
            provider=provider,
            context_mode=context_mode,
            max_results=max_results
        )

        return {
            'success': True,
            'results': results,
            'count': len(results),
            'query': query,
            'collection_name': collection_name
        }
    except CollectionNotFoundError as e:
        logger.error(f"Collection not found: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    except SearchError as e:
        logger.error(f"Search failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error during search: {e}")
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def execute_tool(tool_name: str, arguments: Dict, context: Dict) -> Dict:
    if tool_name == "list_knowledge_bases":
        return _execute_list_knowledge_bases(context)
    elif tool_name == "search_knowledge_base":
        return _execute_search_knowledge_base(arguments, context)
    else:
        return {
            'success': False,
            'error': f"Unknown tool: {tool_name}"
        }


def format_tool_result(tool_name: str, result: Dict) -> str:
    if not result.get('success'):
        error_msg = result.get('error', 'Unknown error')
        return f"❌ Tool execution failed: {error_msg}"

    if tool_name == "list_knowledge_bases":
        return _format_list_knowledge_bases_result(result)
    elif tool_name == "search_knowledge_base":
        return _format_search_result(result)
    else:
        return f"✓ Tool '{tool_name}' executed successfully"


def _format_list_knowledge_bases_result(result: Dict) -> str:
    collections = result.get('collections', [])
    count = result.get('count', 0)

    if count == 0:
        return "No knowledge bases found in the system."

    lines = [f"Found {count} knowledge base(s):\n"]

    for coll in collections:
        name = coll.get('name', 'Unknown')
        desc = coll.get('description', 'No description')
        chunks = coll.get('chunk_count', 0)
        available = coll.get('available', False)

        status = "✓" if available else "⚠"
        lines.append(f"{status} {name}")
        lines.append(f"  Description: {desc}")
        lines.append(f"  Chunks: {chunks:,}")

        if not available:
            reason = coll.get('unavailable_reason', 'Unknown reason')
            lines.append(f"  Status: Unavailable ({reason})")

        lines.append("")

    return "\n".join(lines)


def _format_search_result(result: Dict) -> str:
    results = result.get('results', [])
    count = result.get('count', 0)
    query = result.get('query', '')
    collection = result.get('collection_name', '')

    if count == 0:
        return f"No results found for query '{query}' in '{collection}'."

    lines = [f"Found {count} result(s) from '{collection}' for query: '{query}'\n"]

    for i, res in enumerate(results, 1):
        title = res.get('noteTitle', 'Unknown')
        score = res.get('similarityScore', 0.0)
        mod_date = res.get('modificationDate', '')
        content = res.get('content', '')

        content_preview = content[:200] + "..." if len(content) > 200 else content

        lines.append(f"{i}. {title} (similarity: {score:.2%})")
        if mod_date:
            lines.append(f"   Modified: {mod_date}")
        lines.append(f"   Preview: {content_preview}")
        lines.append("")

    return "\n".join(lines)
