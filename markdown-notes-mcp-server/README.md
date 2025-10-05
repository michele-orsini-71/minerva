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

## Configuration

### Configuration File

The server uses a JSON configuration file (`config.json`) located in the `markdown-notes-mcp-server/` directory.

**Create your configuration:**

```bash
cd markdown-notes-mcp-server
cp config.json.example config.json
# Edit config.json with your paths
```

**Configuration format:**

```json
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "default_max_results": 3,
  "embedding_model": "mxbai-embed-large:latest"
}
```

### Configuration Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `chromadb_path` | string | ✅ Yes | Absolute path to ChromaDB database directory | Must be absolute path (no `~` or `../`), directory must exist |
| `default_max_results` | integer | ✅ Yes | Default number of search results to return | Must be between 1 and 100 |
| `embedding_model` | string | ✅ Yes | Ollama model name for embeddings | Must match pattern `model-name:tag` (e.g., `mxbai-embed-large:latest`) |

### Configuration Validation

The server validates configuration on startup:

- **Invalid path**: `ChromaDB path must be an absolute path (e.g., /Users/name/chromadb), not a relative path`
- **Missing field**: `Missing required configuration field: 'chromadb_path'. Please check config.json`
- **Out of range**: `default_max_results must be between 1 and 100, got: 500`
- **Invalid model**: `embedding_model must follow Ollama naming format (e.g., 'mxbai-embed-large:latest'), got: 'invalid'`

## Usage

### Running the Server

#### Stdio Mode (for Claude Desktop):

```bash
# Server reads config.json from its own directory
python server.py
```

The server will:
1. Load `config.json` from the current directory
2. Validate configuration fields
3. Check ChromaDB connection and collections
4. Verify Ollama service and model availability
5. Start MCP server in stdio mode

### Claude Desktop Integration

Add this to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "markdown-notes": {
      "command": "python",
      "args": [
        "/absolute/path/to/search-markdown-notes/markdown-notes-mcp-server/server.py"
      ]
    }
  }
}
```

**Important Notes:**
- Use **absolute paths**, not relative paths like `~/` or `../`
- The server reads its configuration from `config.json` in the same directory as `server.py`
- No need to pass `CHROMADB_PATH` as environment variable (use `config.json` instead)
- Restart Claude Desktop after adding or modifying the configuration

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

The following examples demonstrate how AI agents (like Claude) interact with the MCP server in real-world scenarios.

### Discovery Flow

**User:** "What knowledge bases do you have access to?"

**AI Agent:** *Calls `list_knowledge_bases()`*

**Tool Response:**
```json
[
  {
    "name": "bear_notes",
    "description": "Personal notes from Bear app covering software development and productivity",
    "chunk_count": 1543,
    "created_at": "2025-09-20T08:49:00Z"
  },
  {
    "name": "wikipedia_history",
    "description": "Wikipedia articles on world history and major events",
    "chunk_count": 3201,
    "created_at": "2025-09-25T14:30:00Z"
  }
]
```

**AI Response:** "I have access to two knowledge bases:
1. **bear_notes** - Your personal notes on software development and productivity (1,543 chunks)
2. **wikipedia_history** - Historical articles and events (3,201 chunks)"

### Basic Search Flow

**User:** "What did I write about Python async programming?"

**AI Agent:**
1. *Calls `list_knowledge_bases()` to discover collections*
2. *Identifies `bear_notes` as most relevant based on "personal notes" description*
3. *Calls `search_knowledge_base(query="Python async programming", collection_name="bear_notes", context_mode="enhanced", max_results=3)`*

**Tool Response:**
```json
[
  {
    "note_title": "Python Concurrency Patterns",
    "note_id": "abc123",
    "chunk_index": 2,
    "total_chunks": 5,
    "modification_date": "2025-09-15T10:30:00Z",
    "collection_name": "bear_notes",
    "similarity_score": 0.847,
    "content": "Threading vs multiprocessing trade-offs.\n\n[MATCH START]\nPython async/await provides a clean way to write concurrent code. The asyncio library is built into Python 3.7+ and offers event loop management, coroutines, and async context managers.\n[MATCH END]\n\nBest practices for async error handling."
  }
]
```

**AI Response:** "I found a note titled 'Python Concurrency Patterns' from September 15th. Here's the relevant section about async/await:

[Shows formatted content with context]

This note appears to be chunk 2 of 5, so there's more information in the complete note if you'd like me to retrieve it."

### Context Mode Selection Flow

**User:** "Search my notes for 'Docker containers' and show me just the relevant chunk"

**AI Agent:** *Calls `search_knowledge_base(query="Docker containers", collection_name="bear_notes", context_mode="chunk_only", max_results=1)`*

**Explanation:** AI chose `chunk_only` because user explicitly requested "just the relevant chunk"

---

**User:** "Find everything I wrote about machine learning"

**AI Agent:** *Calls `search_knowledge_base(query="machine learning", collection_name="bear_notes", context_mode="full_note", max_results=3)`*

**Explanation:** AI chose `full_note` because user said "everything" indicating desire for complete context

---

**User:** "What are the key points in my notes about REST APIs?"

**AI Agent:** *Calls `search_knowledge_base(query="REST APIs", collection_name="bear_notes", context_mode="enhanced", max_results=3)`*

**Explanation:** AI uses default `enhanced` mode for balanced context (preserves narrative flow without overwhelming with full notes)

### Multi-Collection Search Flow

**User:** "When did the Battle of Waterloo happen?"

**AI Agent:**
1. *Calls `list_knowledge_bases()` to discover collections*
2. *Identifies `wikipedia_history` as most relevant based on "historical" description*
3. *Calls `search_knowledge_base(query="Battle of Waterloo", collection_name="wikipedia_history", context_mode="chunk_only", max_results=1)`*

**Tool Response:**
```json
[
  {
    "note_title": "Napoleonic Wars",
    "note_id": "xyz789",
    "chunk_index": 0,
    "total_chunks": 1,
    "similarity_score": 0.912,
    "content": "The Battle of Waterloo took place on June 18, 1815, marking the final defeat of Napoleon Bonaparte."
  }
]
```

**AI Response:** "According to the Wikipedia history collection, the Battle of Waterloo took place on June 18, 1815. It marked the final defeat of Napoleon Bonaparte."

### Error Handling Flow

**User:** "Search for Python in my project documentation"

**AI Agent:** *Calls `search_knowledge_base(query="Python", collection_name="project_documentation", ...)`*

**Tool Error:**
```
Collection 'project_documentation' does not exist.
Available collections: bear_notes, wikipedia_history
Please call list_knowledge_bases first to see all available collections.
```

**AI Response:** "I don't have access to a collection called 'project_documentation'. Let me check what collections are available... [calls list_knowledge_bases] I found two collections: your Bear notes and Wikipedia history. Would you like me to search your Bear notes instead?"

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

## Troubleshooting

### MCP Server Not Appearing in Claude Desktop

**Symptoms:**
- Server doesn't show up in Claude Desktop's available tools
- No error messages in Claude Desktop

**Diagnostic Steps:**

1. **Check Claude Desktop configuration file syntax:**
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool

   # Linux
   cat ~/.config/Claude/claude_desktop_config.json | python -m json.tool
   ```

   Should output formatted JSON. If you see errors, fix JSON syntax.

2. **Verify absolute paths (no `~` or `../`):**
   ```json
   {
     "mcpServers": {
       "markdown-notes": {
         "command": "python",
         "args": [
           "/Users/yourname/search-markdown-notes/markdown-notes-mcp-server/server.py"
         ]
       }
     }
   }
   ```

3. **Test server runs successfully:**
   ```bash
   cd /path/to/search-markdown-notes/markdown-notes-mcp-server
   python server.py
   # Should show initialization messages, not error
   # Press Ctrl+C to stop
   ```

4. **Check Claude Desktop logs:**
   ```bash
   # macOS
   tail -f ~/Library/Logs/Claude/mcp-server-markdown-notes.log

   # Look for connection errors or startup failures
   ```

5. **Restart Claude Desktop completely:**
   - Quit (not just close window)
   - Reopen
   - Wait 10-15 seconds for MCP server initialization

### "Configuration file not found" Error

**Symptoms:**
```
Configuration file not found: config.json
Please create config.json in the same directory as server.py
```

**Solution:**

1. **Create configuration file:**
   ```bash
   cd markdown-notes-mcp-server
   cp config.json.example config.json
   ```

2. **Edit with your paths:**
   ```bash
   # macOS/Linux
   nano config.json

   # Or use your preferred editor
   ```

3. **Verify configuration:**
   ```bash
   python -c "from config import load_config; print(load_config('config.json'))"
   ```

### "ChromaDB path does not exist" Error

**Symptoms:**
```
ChromaDB path does not exist: /path/to/chromadb_data
Please verify the chromadb_path in config.json
```

**Solution:**

1. **Check if path exists:**
   ```bash
   ls /path/to/chromadb_data
   ```

2. **If path doesn't exist, create collections:**
   ```bash
   cd ../bear-notes-cag-data-creator
   python full_pipeline.py \
       --collection-name "bear_notes" \
       --collection-description "Personal notes from Bear app" \
       --chromadb-path /absolute/path/to/chromadb_data \
       ../test-data/your-notes.json
   ```

3. **Update config.json with correct absolute path:**
   ```json
   {
     "chromadb_path": "/Users/yourname/search-markdown-notes/chromadb_data",
     ...
   }
   ```

### "No collections found in ChromaDB" Error

**Symptoms:**
```
No collections found in ChromaDB at /path/to/chromadb_data
Please run the pipeline to create at least one collection
```

**Solution:**

1. **Verify ChromaDB directory is not empty:**
   ```bash
   ls -la /path/to/chromadb_data
   ```

2. **Create a collection:**
   ```bash
   cd bear-notes-cag-data-creator
   python full_pipeline.py \
       --collection-name "my_notes" \
       --collection-description "My personal notes" \
       ../test-data/sample.json
   ```

3. **Verify collection was created:**
   ```bash
   python -c "
   import chromadb
   client = chromadb.PersistentClient(path='/path/to/chromadb_data')
   print([c.name for c in client.list_collections()])
   "
   ```

### "Ollama embedding service is unavailable" Error

**Symptoms:**
```
Ollama embedding service is unavailable.
Please ensure Ollama is running (run 'ollama serve' in another terminal).
```

**Solution:**

1. **Check if Ollama is running:**
   ```bash
   curl http://localhost:11434/api/version
   ```

   Should return version info. If not, Ollama is not running.

2. **Start Ollama service:**
   ```bash
   # In a separate terminal, run:
   ollama serve

   # Keep this terminal open
   ```

3. **Verify Ollama is accessible:**
   ```bash
   ollama list
   ```

### "Embedding model not available" Error

**Symptoms:**
```
Embedding model 'mxbai-embed-large:latest' is not available in Ollama.
Please run: ollama pull mxbai-embed-large:latest
```

**Solution:**

1. **Pull the required model:**
   ```bash
   ollama pull mxbai-embed-large:latest
   ```

   This will download ~700MB.

2. **Verify model is available:**
   ```bash
   ollama list | grep mxbai-embed-large
   ```

   Should show: `mxbai-embed-large:latest`

3. **Test embedding generation:**
   ```bash
   python -c "
   from ollama import embeddings
   result = embeddings(model='mxbai-embed-large:latest', prompt='test')
   print(f'Embedding dimension: {len(result[\"embedding\"])}')
   "
   ```

### Search Returns No Results

**Symptoms:**
- `search_knowledge_base` returns empty array `[]`
- No errors, just no matches found

**Diagnostic Steps:**

1. **Verify collection has data:**
   ```bash
   python -c "
   import chromadb
   client = chromadb.PersistentClient(path='/path/to/chromadb_data')
   collection = client.get_collection('bear_notes')
   print(f'Chunk count: {collection.count()}')
   "
   ```

   Should show positive count.

2. **Test with broad query:**
   ```python
   # Try a very general query that should match something
   search_knowledge_base(
       query="the",  # Very common word
       collection_name="bear_notes",
       chromadb_path="/path/to/chromadb_data",
       context_mode="chunk_only",
       max_results=10
   )
   ```

3. **Check embedding model matches:**
   - Pipeline and server must use same embedding model
   - If you created embeddings with different model, rebuild:
     ```bash
     cd bear-notes-cag-data-creator
     python full_pipeline.py --embedding-model mxbai-embed-large:latest ...
     ```

### Slow Search Performance

**Symptoms:**
- Search takes >5 seconds
- MCP tool calls timeout

**Solutions:**

1. **Reduce chunk count (if collection is very large):**
   - Use more specific queries
   - Reduce `max_results` parameter

2. **Check Ollama performance:**
   ```bash
   time python -c "
   from ollama import embeddings
   embeddings(model='mxbai-embed-large:latest', prompt='test query')
   "
   ```

   Should take <1 second. If slower, Ollama may be CPU-bound.

3. **Verify ChromaDB HNSW index:**
   ```python
   collection = client.get_collection('bear_notes')
   print(collection.metadata)
   # Should show: {"hnsw:space": "cosine"}
   ```

### Python Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'chromadb'
```

**Solution:**

1. **Activate virtual environment:**
   ```bash
   source ../.venv/bin/activate
   ```

2. **Verify dependencies installed:**
   ```bash
   pip list | grep -E "(chromadb|ollama|mcp|numpy)"
   ```

3. **Install missing dependencies:**
   ```bash
   pip install chromadb ollama mcp numpy
   ```

### "Collection does not exist" During Search

**Symptoms:**
```
Collection 'bear_notes' does not exist.
Available collections: bear_notes_chunks, wikipedia_history
```

**Explanation:** Collection names must match exactly (case-sensitive).

**Solution:**

1. **List actual collection names:**
   ```bash
   python -c "
   import chromadb
   client = chromadb.PersistentClient(path='/path/to/chromadb_data')
   for c in client.list_collections():
       print(c.name)
   "
   ```

2. **Use exact name in search:**
   ```python
   search_knowledge_base(
       query="test",
       collection_name="bear_notes_chunks",  # Use exact name
       ...
   )
   ```

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
