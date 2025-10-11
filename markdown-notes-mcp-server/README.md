# Multi-Collection MCP Server for Markdown Notes

An MCP (Model Context Protocol) server that enables AI agents like Claude Desktop to perform semantic search across multiple knowledge bases stored in ChromaDB.

## Features

- **Dynamic Collection Discovery**: AI agents can list all available knowledge bases without hardcoded configuration
- **Multi-Provider AI Support**: Each collection can use different embedding providers (Ollama, OpenAI, Gemini)
- **Intelligent Search**: Semantic search with provider-specific embeddings (local or cloud)
- **Flexible Context Modes**: Choose between minimal (`chunk_only`), balanced (`enhanced`), or maximum (`full_note`) context
- **Multi-Source Support**: Search across Bear notes, Zim wikis, documentation sites, and any markdown-based knowledge base
- **Zero Configuration**: New collections automatically available without server restarts or manifest updates
- **Provider Metadata Travel**: AI provider config stored with collections, no server reconfiguration needed

## Architecture

```
AI Agent (Claude Desktop)
    ↓
MCP Protocol (JSON-RPC)
    ↓
FastMCP Server (server.py)
    ├─ Reads provider metadata from ChromaDB
    └─ Reconstructs AI providers (Ollama/OpenAI/Gemini)
    ↓
ChromaDB Collections
    ├─ Collection A (Ollama provider) → mxbai-embed-large
    ├─ Collection B (OpenAI provider) → text-embedding-3-small
    └─ Collection C (Gemini provider) → text-embedding-004
```

### Multi-Provider Architecture

The MCP server supports **heterogeneous AI providers** across collections:

1. **Pipeline Stage**: When you create a collection using `full_pipeline.py`, the AI provider configuration (type, models, API keys) is stored in the collection's metadata
2. **Discovery Stage**: When the MCP server starts, it reads all collections and reconstructs their AI providers from metadata
3. **Validation Stage**: The server checks each provider's availability (Ollama running, API keys set, models accessible)
4. **Query Stage**: When searching, the server uses the collection-specific provider to generate embeddings

**This architecture allows:**
- Different collections with different embedding models in the same database
- Mixing local (Ollama) and cloud (OpenAI, Gemini) providers
- No server reconfiguration when adding collections - metadata travels with the data

### Why FastMCP?

FastMCP simplifies the MCP server implementation by providing:

1. **Declarative Tool Registration**: Use `@mcp.tool()` decorator instead of manual JSON-RPC handling
2. **Automatic Validation**: Type hints automatically validate parameters and generate schema
3. **Zero Boilerplate**: No need to write protocol handlers, error formatters, or manifest generators
4. **Clean Architecture**: Focus on business logic instead of protocol details

## Installation

### Prerequisites

- Python 3.13+
- ChromaDB database populated by `markdown-notes-cag-data-creator` pipeline
- **AI Provider** (depending on what your collections use):
  - For Ollama collections: Ollama service running locally (`ollama serve`)
  - For OpenAI collections: `OPENAI_API_KEY` environment variable set
  - For Gemini collections: `GEMINI_API_KEY` environment variable set

### Setup

1. **Install dependencies:**
   ```bash
   # Activate the shared virtual environment
   source ../.venv/bin/activate

   # Install MCP SDK
   pip install mcp
   ```

2. **Set up AI providers (based on your collections):**

   **For Ollama collections:**
   ```bash
   # Start Ollama service in a separate terminal
   ollama serve

   # Pull required models (if not already present)
   ollama pull mxbai-embed-large:latest
   ollama pull llama3.1:8b
   ```

   **For OpenAI collections:**
   ```bash
   # Set your OpenAI API key
   export OPENAI_API_KEY="sk-your-key-here"
   ```

   **For Gemini collections:**
   ```bash
   # Set your Google Gemini API key
   export GEMINI_API_KEY="your-key-here"
   ```

3. **Verify ChromaDB has collections:**
   ```bash
   # List collections and their providers
   cd markdown-notes-mcp-server
   python collection_discovery.py /absolute/path/to/chromadb_data
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
  "default_max_results": 3
}
```

### Configuration Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `chromadb_path` | string | ✅ Yes | Absolute path to ChromaDB database directory | Must be absolute path (no `~` or `../`), directory must exist |
| `default_max_results` | integer | ✅ Yes | Default number of search results to return | Must be between 1 and 100 |

### How AI Provider Configuration Works

**The MCP server does NOT need AI provider configuration** - it reads provider metadata directly from ChromaDB collections!

When you create a collection using the pipeline (e.g., `python full_pipeline.py --config ../configs/example-ollama.json`), the pipeline stores AI provider metadata in the collection:
- Provider type (ollama/openai/gemini)
- Embedding model name and dimension
- LLM model name
- Base URL and API key reference

When the MCP server starts, it:
1. Discovers all collections in ChromaDB
2. Reads AI provider metadata from each collection
3. Reconstructs the appropriate AI provider for each collection
4. Checks provider availability (Ollama running, API keys set, etc.)
5. Marks collections as available/unavailable based on provider status

**This means:**
- Different collections can use different AI providers (Ollama, OpenAI, Gemini)
- The same MCP server can serve collections with different embedding models
- No need to restart the server when switching providers - just create collections with different configs
- Each collection remembers which provider it was created with

### Configuration Validation

The server validates configuration on startup:

- **Invalid path**: `ChromaDB path must be an absolute path (e.g., /Users/name/chromadb), not a relative path`
- **Missing field**: `Missing required configuration field: 'chromadb_path'. Please check config.json`
- **Out of range**: `default_max_results must be between 1 and 100, got: 500`

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
3. Check ChromaDB connection and discover all collections
4. Read AI provider metadata from each collection
5. Reconstruct and validate AI providers (checks Ollama service, API keys, etc.)
6. Display collection availability status
7. Start MCP server in stdio mode (only serving available collections)

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

No code changes needed! Just run the pipeline with a configuration file:

```bash
cd markdown-notes-cag-data-creator

# Create a new config file (or copy from configs/ directory)
# Edit: collection_name, description, json_file, and ai_provider settings
python full_pipeline.py --config ../configs/my-collection.json
```

**Example config file** (`configs/my-collection.json`):
```json
{
  "collection_name": "project_docs",
  "description": "Technical documentation for my software projects",
  "chromadb_path": "./chromadb_data",
  "json_file": "./data/project_notes.json",
  "chunk_size": 1200,
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest",
      "base_url": "http://localhost:11434"
    },
    "llm": {
      "model": "llama3.1:8b"
    }
  }
}
```

The new collection will automatically:
1. Store the AI provider metadata in ChromaDB
2. Appear in `list_knowledge_bases()` results when the MCP server starts
3. Be available for search if the provider is available (Ollama running, API keys set, etc.)

## Error Handling

The server provides clear error messages for common issues:

### ChromaDB Connection Errors

```
Failed to connect to ChromaDB at /path/to/chromadb.
Please check that the path exists and contains valid ChromaDB data.
```

**Solution:** Verify `chromadb_path` in `config.json` or run the pipeline to create collections.

### AI Provider Unavailable Errors

When the server starts, it checks each collection's AI provider availability. Collections may be marked as unavailable for these reasons:

**Ollama collections:**
```
✗ UNAVAILABLE: bear_notes
  Reason: Failed to connect to Ollama service at http://localhost:11434
```
**Solution:** Start Ollama with `ollama serve` in a separate terminal

**OpenAI collections:**
```
✗ UNAVAILABLE: research_notes
  Reason: Missing API key - OPENAI_API_KEY not found in environment
```
**Solution:** Set environment variable: `export OPENAI_API_KEY="sk-your-key-here"`

**Gemini collections:**
```
✗ UNAVAILABLE: wikipedia_archive
  Reason: Missing API key - GEMINI_API_KEY not found in environment
```
**Solution:** Set environment variable: `export GEMINI_API_KEY="your-key-here"`

**Old pipeline collections:**
```
✗ UNAVAILABLE: legacy_notes
  Reason: Missing AI provider metadata (created with old pipeline)
```
**Solution:** Recreate the collection using the updated pipeline with a config file

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

### "Collection unavailable" - Provider Issues

**Symptoms:**
The server starts but reports some collections as unavailable.

**For Ollama collections:**

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

3. **Verify required models are available:**
   ```bash
   ollama list
   # Check for the models your collection uses (check server startup logs)

   # If missing, pull them:
   ollama pull mxbai-embed-large:latest
   ollama pull llama3.1:8b
   ```

4. **Restart MCP server** (if using Claude Desktop, restart Claude Desktop)

**For OpenAI collections:**

1. **Set API key:**
   ```bash
   export OPENAI_API_KEY="sk-your-key-here"
   ```

2. **Verify API key is valid:**
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **Restart MCP server**

**For Gemini collections:**

1. **Set API key:**
   ```bash
   export GEMINI_API_KEY="your-key-here"
   ```

2. **Restart MCP server**

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

3. **Check if collection's AI provider is available:**
   - The MCP server only serves collections whose AI providers are available
   - Check server startup logs for collection availability status
   - Ensure required API keys are set or Ollama is running

### Slow Search Performance

**Symptoms:**
- Search takes >5 seconds
- MCP tool calls timeout

**Solutions:**

1. **Reduce chunk count (if collection is very large):**
   - Use more specific queries
   - Reduce `max_results` parameter

2. **Check AI provider performance:**
   - For Ollama: Embedding generation happens locally, may be CPU-bound
   - For cloud providers (OpenAI, Gemini): Network latency and rate limits apply
   - Check server logs for timing information

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

See implementation instructions in [`tasks/instructions.md`](tasks/old/2025-10-06-instructions.md).
