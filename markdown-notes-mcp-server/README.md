# Multi-Collection MCP Server for Markdown Notes

An MCP (Model Context Protocol) server that enables AI agents like Claude Desktop to perform semantic search across multiple knowledge bases stored in ChromaDB.

## Features

- **Dynamic Collection Discovery**: AI agents can list all available knowledge bases without hardcoded configuration
- **Intelligent Search**: Semantic search powered by local Ollama embeddings
- **Flexible Context Modes**: Choose between minimal (`chunk_only`), balanced (`enhanced`), or maximum (`full_note`) context
- **Multi-Source Support**: Search across Bear notes, Zim wikis, documentation sites, and any markdown-based knowledge base
- **Zero Configuration**: New collections automatically available without server restarts or manifest updates

## Architecture

```
AI Agent (Claude Desktop)
    ↓
MCP Protocol (JSON-RPC)
    ↓
FastMCP Server (server.py)
    ↓
ChromaDB Collections ← Ollama Embeddings
```

### Why FastMCP?

FastMCP simplifies the MCP server implementation by providing:

1. **Declarative Tool Registration**: Use `@mcp.tool()` decorator instead of manual JSON-RPC handling
2. **Automatic Validation**: Type hints automatically validate parameters and generate schema
3. **Zero Boilerplate**: No need to write protocol handlers, error formatters, or manifest generators
4. **Clean Architecture**: Focus on business logic instead of protocol details

## Installation

### Prerequisites

- Python 3.13+
- Ollama running locally with `mxbai-embed-large:latest` model
- ChromaDB database populated by `markdown-notes-cag-data-creator` pipeline

### Setup

1. **Install dependencies:**
   ```bash
   # Activate the shared virtual environment
   source ../.venv/bin/activate

   # Install MCP SDK
   pip install mcp
   ```

2. **Ensure Ollama is running:**
   ```bash
   ollama serve

   # Verify the embedding model is available
   ollama list | grep mxbai-embed-large
   ```

3. **Verify ChromaDB has collections:**
   ```bash
   # Use the existing query client to test
   cd ../test-files
   python chromadb_query_client.py
   ```

## Usage

### Running the Server

#### Stdio Mode (for Claude Desktop):

```bash
# Default ChromaDB path
python server.py

# Custom ChromaDB path
CHROMADB_PATH=/path/to/chromadb python server.py
```

### Claude Desktop Integration

Add this to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "markdown-notes": {
      "command": "python",
      "args": [
        "/absolute/path/to/search-markdown-notes/markdown-notes-mcp-server/server.py"
      ],
      "env": {
        "CHROMADB_PATH": "/absolute/path/to/search-markdown-notes/chromadb_data/bear_notes_embeddings"
      }
    }
  }
}
```

**Important:** Use absolute paths, not relative paths like `~/` or `../`.

### Available Tools

#### 1. `list_knowledge_bases()`

Discover all available collections:

```python
# AI Agent Call (conceptual)
list_knowledge_bases()

# Returns:
[
    {
        "name": "bear_notes_chunks",
        "description": "Personal notes from Bear app covering software development, productivity, and learning",
        "chunk_count": 1543,
        "created_at": "2025-09-20T08:49:00Z"
    },
    {
        "name": "wikipedia_history_chunks",
        "description": "Wikipedia articles on world history, major events, and historical figures",
        "chunk_count": 3201,
        "created_at": "2025-09-25T14:30:00Z"
    }
]
```

#### 2. `search_knowledge_base(query, collection_name, context_mode, max_results)`

Perform semantic search:

```python
# AI Agent Call (conceptual)
search_knowledge_base(
    query="Python async patterns",
    collection_name="bear_notes_chunks",
    context_mode="enhanced",  # Optional: "chunk_only", "enhanced" (default), "full_note"
    max_results=3  # Optional: default is 3
)

# Returns:
[
    {
        "note_title": "Python Concurrency Patterns",
        "note_id": "ABC123",
        "chunk_index": 2,
        "total_chunks": 5,
        "modification_date": "2025-09-15T10:30:00Z",
        "collection_name": "bear_notes_chunks",
        "similarity_score": 0.847,
        "content": "Previous chunk context...\n\n[MATCH START]\nAsync/await in Python provides...\n[MATCH END]\n\nNext chunk context..."
    }
]
```

### Context Modes Explained

| Mode | Content Returned | Token Usage | Best For |
|------|------------------|-------------|----------|
| `chunk_only` | Just the matched chunk | ~300 tokens | Quick fact lookups |
| `enhanced` (default) | Match + 2 surrounding chunks | ~1,500 tokens | Most queries (preserves narrative flow) |
| `full_note` | Complete note | 5,000-20,000 tokens | When user explicitly needs full context |

## Example Conversations

### Discovery Flow

**User:** "What knowledge bases do you have access to?"

**AI Agent:** *Calls `list_knowledge_bases()`*

**Response:** "I have access to three knowledge bases:
1. **bear_notes_chunks** - Your personal notes on software development and productivity (1,543 chunks)
2. **wikipedia_history_chunks** - Historical articles and events (3,201 chunks)
3. **project_docs_chunks** - Documentation for your current projects (892 chunks)"

### Search Flow

**User:** "What did I write about Python async programming?"

**AI Agent:** *Calls `search_knowledge_base(query="Python async programming", collection_name="bear_notes_chunks", context_mode="enhanced")`*

**Response:** "I found a note titled 'Python Concurrency Patterns' from September 15th. Here's the relevant section: [shows enhanced context with surrounding chunks]"

## Development

### Project Structure

```
markdown-notes-mcp-server/
├── server.py              # Main MCP server implementation (FastMCP)
├── README.md              # This file
├── tasks/
│   ├── prd-multi-collection-mcp-server.md  # Product requirements
│   └── instructions.md    # Implementation notes
└── .claude/               # Claude Code configuration
```

### Testing

1. **Test ChromaDB Connection:**
   ```bash
   # Use the existing test client
   cd ../test-files
   python chromadb_query_client.py
   ```

2. **Test MCP Server Locally:**
   ```bash
   # Run the server
   python server.py

   # It should initialize and wait for JSON-RPC requests
   ```

3. **Test with Claude Desktop:**
   - Add the server to your Claude Desktop config
   - Restart Claude Desktop
   - Try: "List my knowledge bases" or "Search my notes for Python"

### Adding New Collections

No code changes needed! Just run the pipeline with a new collection name:

```bash
cd ../bear-notes-cag-data-creator
python full_pipeline.py \
    --collection-name "my_new_collection" \
    --collection-description "Description for AI to understand when to use this collection" \
    ../data/my_new_notes.json
```

The new collection will automatically appear in `list_knowledge_bases()` results.

## Error Handling

The server provides clear error messages for common issues:

### ChromaDB Connection Errors

```
Failed to connect to ChromaDB at /path/to/chromadb.
Please check that the path exists and contains valid ChromaDB data.
```

**Solution:** Verify `CHROMADB_PATH` environment variable or run the pipeline to create collections.

### Ollama Service Errors

```
Ollama embedding service is unavailable.
Please ensure Ollama is running (run 'ollama serve' in another terminal).
```

**Solution:** Start Ollama with `ollama serve`

### Collection Not Found

```
Collection 'invalid_name' does not exist.
Available collections: bear_notes_chunks, wikipedia_history_chunks
Please call list_knowledge_bases first to see all available collections.
```

**Solution:** AI agent should call `list_knowledge_bases()` to discover valid collection names.

## Implementation Notes

### Why FastMCP Over Custom Implementation?

**Pros:**
- ✅ 300 lines vs. 1000+ lines for custom JSON-RPC server
- ✅ Automatic schema generation from type hints
- ✅ Built-in validation and error handling
- ✅ Recommended by Anthropic for MCP implementations
- ✅ Active development and community support

**Cons:**
- ⚠️ Additional dependency (`mcp` package)
- ⚠️ Less control over low-level protocol details (rarely needed)

### Design Decisions

1. **Single Server Instance**: One MCP server handles all collections (vs. separate servers per collection)
   - **Rationale:** Easier to maintain, AI agent controls collection selection

2. **Dynamic Collection Discovery**: No hardcoded collection list in manifest
   - **Rationale:** Users can add collections without code changes

3. **Default to Enhanced Context**: `context_mode="enhanced"` as default
   - **Rationale:** Better UX, preserves narrative flow, AI can override when needed

4. **Reuse Existing Code**: Imports from `bear-notes-cag-data-creator/` modules
   - **Rationale:** DRY principle, consistent embedding logic with pipeline

## Related Projects

- **[bear-notes-parser](../bear-notes-parser/)** - Extract notes from Bear backups
- **[bear-notes-cag-data-creator](../bear-notes-cag-data-creator/)** - Create ChromaDB collections with embeddings
- **[test-files/chromadb_query_client.py](../test-files/chromadb_query_client.py)** - Interactive query testing tool

## License

Same as parent project.

## Contributing

See implementation instructions in [`tasks/instructions.md`](tasks/instructions.md).
