# PRD: Multi-Collection MCP Server for Markdown Notes Search

## Introduction/Overview

This feature enables an MCP (Model Context Protocol) server to query multiple ChromaDB collections containing different knowledge bases (Bear notes, Zim wikis, documentation sites, etc.) through a unified interface. The server exposes tools that AI agents (like Claude Desktop) can use to discover available collections and perform semantic searches across specific knowledge bases.

**Problem Statement:**
Currently, the ChromaDB RAG system is designed for a single collection (`bear_notes_chunks`). Users need the ability to maintain multiple knowledge bases from different sources (personal notes, wikis, project documentation) and allow AI assistants to intelligently query the appropriate source based on user intent.

**Goal:**
Enable AI agents to discover and search across multiple knowledge bases without requiring code changes or manifest updates when new collections are added.

## Goals

1. **Self-Discovery:** AI agents can automatically discover all available knowledge bases in the ChromaDB instance
2. **Explicit Selection:** AI agents correctly identify and query the appropriate collection based on user queries
3. **Extensibility:** Users can add new collections without modifying MCP server code
4. **Rich Metadata:** Collections provide descriptive information to help AI agents understand their purpose
5. **Developer Experience:** Junior developers can understand and extend the system

## User Stories

### As an AI Agent (Claude Desktop)

1. **Story 1:** As an AI agent, I want to list all available knowledge bases so that I can understand what information sources are available to answer user questions.

2. **Story 2:** As an AI agent, when a user asks "What did I write about Python?", I want to search the `bear_notes` collection specifically so that I return relevant personal notes.

3. **Story 3:** As an AI agent, when a user asks "What were the major events in the American Civil War?", I want to search the `wikipedia_history_chunks` collection (described as "Wikipedia articles on world history...") so that I return relevant historical information.

4. **Story 4:** As an AI agent, when I attempt to search a non-existent collection, I want to receive clear error guidance so that I can inform the user or retry with valid collections.

### As a User (Knowledge Base Owner)

5. **Story 5:** As a user, I want to create a new collection for my project documentation by running the pipeline with a custom collection name, so that I can keep different knowledge sources organized.

6. **Story 6:** As a user, I want to ask my AI assistant questions like "search my wiki for X" and have it automatically query the correct collection.

### As a Developer

7. **Story 7:** As a developer, I want to understand how collection metadata is stored and accessed so that I can add new metadata fields if needed.

## Prerequisites

This MCP server depends on the multi-collection pipeline enhancements documented in:
**`markdown-notes-cag-data-creator/tasks/prd-multi-collection-pipeline.md`**

The pipeline PRD defines how collections are created with metadata (collection name and description). This MCP server PRD assumes those enhancements are implemented and available.

**Key metadata schema (from pipeline PRD):**
```python
{
    "hnsw:space": "cosine",
    "version": "1.0",
    "description": str,  # AI-optimized description (primary field for AI selection)
    "created_at": str    # ISO 8601 timestamp
}
```

**Note:** Collection identity depends solely on `collectionName` and `description`. The pipeline creates collections with validated descriptions to ensure AI agents can make correct selection decisions.

## Functional Requirements

### MCP Server Implementation (`markdown-notes-mcp-server/`)

**FR1:** The MCP server must expose a tool named `list_knowledge_bases` that:
- Returns all collections in the ChromaDB instance
- For each collection, returns: name, description, chunk count, created_at
- Handles ChromaDB connection errors gracefully

**FR2:** The MCP server must expose a tool named `search_knowledge_base` that:
- Accepts parameters:
  - `query` (string, required): User's search query
  - `collectionName` (string, required): Target collection
  - `contextMode` (string, optional): How much context to return - `enhanced` (default), `chunk_only`, or `full_note`
- Generates embeddings for the query using Ollama (`mxbai-embed-large:latest`)
- Performs semantic search in the specified collection
- Returns results with content based on `contextMode` (see FR4)

**FR3:** The `search_knowledge_base` tool must return an error message with guidance when:
- The specified collection does not exist
- The error message must suggest calling `list_knowledge_bases` first

**FR4:** Search results must include the following fields per result, with `content` field varying by `context_mode`:

**Common fields (all modes):**

- `noteTitle` (string): Title of the source note
- `noteId` (string): Unique identifier of the source note
- `chunkIndex` (integer): Position of matching chunk within note
- `totalChunks` (integer): Total number of chunks in the note
- `modificationDate` (string): When the note was last modified (ISO 8601 format)
- `collectionName` (string): Which collection this result came from
- `similarityScore` (float): Relevance score (0.0 to 1.0)

**Content field by mode:**

1. **`chunk_only`:**
   - `content` (string): Only the matching chunk text
   - Pros: Minimal token usage, fast
   - Cons: May lack narrative context
   - Use case: Quick lookups, when chunk boundaries align with semantic units

2. **`enhanced` (DEFAULT):**
   - `content` (string): Matching chunk plus ±2 surrounding chunks (up to 5 total)
   - Must indicate which chunk matched (e.g., with marker `[MATCH START]...[MATCH END]`)
   - If at note boundaries, include available chunks (e.g., first chunk has no predecessors)
   - Pros: Preserves narrative flow, bounded size
   - Cons: ~5x token usage vs. chunk_only

3. **`full_note`:**
   - `content` (string): Complete note markdown
   - Indicate matching chunk location (e.g., `[MATCH AT CHUNK 3]` marker)
   - Pros: Full context available
   - Cons: May be 10,000+ chars, token-expensive, could fill context with 2-3 results
   - **Warning:** Should only be used when user explicitly needs complete note

**FR5:** The MCP server must initialize ChromaDB connection on startup and validate that:
- The ChromaDB path exists and is accessible
- At least one collection is available
- Ollama embedding service is running and accessible

**FR6:** If startup validation fails (FR5), the MCP server must:

- Exit with non-zero status code
- Log clear error message indicating which validation failed
- Provide actionable remediation steps:
  - If ChromaDB path invalid: Show expected path and suggest verifying config
  - If no collections exist: Suggest running pipeline to create collections
  - If Ollama unavailable: Suggest running `ollama serve`
- **Rationale:** Fail-fast prevents confusing runtime errors when server is in invalid state

**FR7:** The MCP server must expose a manifest file (JSON) that Claude Desktop can consume, defining the two tools with their parameters and descriptions.

### Error Handling

**FR8:** When ChromaDB connection fails, the MCP server must:
- Log the error with the database path
- Return a clear error message to the AI agent
- Suggest checking the ChromaDB path and data integrity

**FR8:** When Ollama embedding service is unavailable, the search tool must:
- Return an error message indicating the service is down
- Suggest running `ollama serve`

## Non-Goals (Out of Scope)

**NG1:** Automatic merging of results from multiple collections (user must specify target collection)

**NG2:** Authentication or access control for MCP server (assumes trusted local environment)

**NG3:** Web-based UI for collection management (CLI and MCP tools only)

**NG4:** Real-time note synchronization (collections updated via pipeline runs)

**NG5:** ~~Predefined or enforced list of source types (flexible string field)~~ **REMOVED:** source_type field eliminated from design

**NG6:** Cross-collection duplicate detection or deduplication

**NG7:** Collection versioning or rollback functionality

## Technical Considerations

### MCP Server Configuration

The MCP server requires a configuration file specifying the ChromaDB path and operational parameters.

**Configuration File Location:** `markdown-notes-mcp-server/config.json`

**JSON Schema:**

```json
{
  "chromadb_path": "string (required)",
  "default_max_results": "integer (optional, default: 5)",
  "embedding_model": "string (optional, default: mxbai-embed-large:latest)"
}
```

**Example Configuration:**

```json
{
  "chromadb_path": "/Users/username/my-code/search-markdown-notes/chromadb_data",
  "default_max_results": 5,
  "embedding_model": "mxbai-embed-large:latest"
}
```

**Validation Requirements:**

- `chromadb_path` must be absolute path (not relative)
- `chromadb_path` directory must exist and be readable
- `default_max_results` must be integer between 1 and 100
- `embedding_model` must match available Ollama model

**Configuration Loading:**

- Server reads config on startup (fails if missing or invalid)
- No environment variable fallback (explicit config required)
- Clear error messages for validation failures

### Dependencies

- **Existing:** ChromaDB, Ollama, Python 3.13, existing pipeline modules
- **New:** MCP SDK/framework (research needed for Python MCP implementation)

### Integration Points
1. **MCP Server → ChromaDB:** Read collections and metadata via ChromaDB Python client
2. **MCP Server → Ollama:** Reuse existing `embedding.py:generate_embedding()` function from pipeline
3. **MCP Server → AI Agent:** JSON-based tool interface via MCP protocol
4. **Pipeline → MCP Server:** Collections created by `markdown-notes-cag-data-creator` (see pipeline PRD)

### Architecture Notes
- **Reuse `chromadb_query_client.py`:** The existing test client (`test-files/chromadb_query_client.py`) contains the core query logic that the MCP server will wrap
- **Single MCP Instance:** One server process handles all collections
- **Stateless Tools:** Each tool call is independent, no session state maintained

### Collection Naming (Pipeline Responsibility)

Collection names are defined by users in pipeline configuration files (see pipeline PRD). The MCP server simply reads existing collections created by the pipeline.

**Example collection names:**
- `bear_notes_chunks` - Personal notes from Bear app
- `personal_wiki_chunks` - Personal Zim wiki
- `dnd_campaign_wiki_chunks` - D&D campaign Zim wiki
- `wikipedia_history_chunks` - Wikipedia history articles

**Note:** Collection identity depends on unique names and AI-optimized descriptions, not on any source_type field.

### ChromaDB Path Configuration

- **Source of truth:** MCP server configuration file (`config.json`)
- **No defaults:** Server fails to start if path not specified in config
- **Path requirements:** Absolute path, must point to the same ChromaDB directory used by the pipeline
- **Typical value:** `/Users/username/my-code/search-markdown-notes/chromadb_data`
- **Multiple collections:** All collections live in the same ChromaDB instance (not separate paths)

### Context Retrieval Implementation

**Challenge:** ChromaDB stores individual chunks, but `enhanced` and `full_note` modes require retrieving related chunks from the same note.

**Solution Approach:**

1. **For `enhanced` mode:**
   - After getting search results, extract `noteId` and `chunkIndex` from matched chunks
   - Query collection for chunks with same `noteId` where `chunkIndex` is in range `[matchIndex-2, matchIndex+2]`
   - Use ChromaDB's metadata filtering: `where={"noteId": noteId, "chunkIndex": {"$gte": minIdx, "$lte": maxIdx}}`
   - Concatenate chunks in order, marking the matched chunk

2. **For `full_note` mode:**
   - Query collection for all chunks with matching `noteId`
   - Sort by `chunkIndex`
   - Concatenate all chunks to reconstruct original note
   - Add marker indicating which chunk matched

3. **Chunk metadata requirements:**
   - Must store `noteId` in chunk metadata (implemented in pipeline ✅)
   - Must store `chunkIndex` in chunk metadata (implemented in pipeline ✅)
   - Should verify chunks are queryable by these fields

**Performance Impact:**
- `chunk_only`: 1 ChromaDB query (baseline)
- `enhanced`: 1 initial query + N follow-up queries (where N = number of results)
- `full_note`: 1 initial query + N follow-up queries, but larger data transfer

**Default Behavior:** The tool defaults to `enhanced` mode to provide narrative context and better user experience. AI agents can opt for `chunk_only` for quick lookups or `full_note` when complete context is explicitly needed.

### Performance Considerations
- Collection listing is a lightweight operation (metadata only)
- Search performance depends on collection size (HNSW index scales well)
- Consider caching collection list if access becomes frequent
- `enhanced` and `full_note` modes require additional ChromaDB queries (see Context Retrieval Implementation)

### Collection Description Quality

**Critical Dependency:** The MCP server's ability to help AI agents select the correct collection depends entirely on collection description quality. This is enforced by the pipeline (see `prd-multi-collection-pipeline.md` for description guidelines and validation).

**MCP Server Responsibility:** Simply return the `description` field from collection metadata in the `list_knowledge_bases` tool response. The AI agent uses these descriptions to make selection decisions.

## Success Metrics

**Primary Metric:**
**SM1:** AI agent correctly selects the appropriate collection based on user query intent in 95% of test cases **when collections have well-crafted descriptions** (see Collection Description Guidelines).

Test cases (assuming quality descriptions):
- "What did I write about Python?" → Queries `bear_notes_chunks` (described as "Personal notes... software development")
- "What were the key events of the American Civil War?" → Queries `wikipedia_history_chunks` (described as "Wikipedia articles on world history...")
- "How do I use the b4 patch command?" → Queries `b4_docs_chunks` (described as "GitHub b4 repository documentation...")
- "What's the current population of Tokyo?" → Queries `wikipedia_general_chunks` (described as "50,000 best Wikipedia articles for general knowledge...")

**Note:** This metric is contingent on authors providing AI-optimized descriptions. Poor descriptions will result in poor selection accuracy, which is **by design** - the system cannot compensate for inadequate metadata.

**Secondary Metrics:**
**SM2:** Users can add a new collection in under 5 minutes (run pipeline with new collection name)

**SM3:** Zero code changes required when adding new collection types

**SM4:** MCP tool invocation latency under 2 seconds for typical queries (excluding LLM processing time)

## Open Questions

**OQ1:** ~~Which MCP framework/SDK should we use for Python implementation?~~ **RESOLVED:** Use FastMCP.

- **Decision**: Use `mcp.server.fastmcp.FastMCP` from the official `mcp` Python package
- **Rationale**:
  - Recommended by Anthropic as the official SDK for MCP servers
  - Reduces boilerplate significantly (~300 lines vs 1000+ for custom JSON-RPC implementation)
  - Provides automatic parameter validation and schema generation from Python type hints
  - Enables clean decorator-based tool registration (`@mcp.tool()`)
  - Supports the self-discovery pattern (dynamic collection listing without hardcoded manifests)
- **Reference**: See `tasks/fastmcp-research.md` for detailed comparison and benefits analysis

**OQ2:** ~~How should the MCP server discover the ChromaDB path?~~ **RESOLVED:** Use config file.

- **Decision**: Use a configuration file in `markdown-notes-mcp-server/`
- **Format**: JSON config file specifying absolute path to ChromaDB database
- **Rationale**: Config file provides persistence and clarity over environment variables, easier to manage than CLI arguments
- **See:** Technical Considerations > MCP Server Configuration section for complete schema

**OQ3:** ~~Should `list_knowledge_bases` return additional statistics?~~ **RESOLVED:** No.

- **Decision**: Keep `list_knowledge_bases` response minimal (name, description, chunk_count, created_at only)
- **Rationale**: Additional statistics not needed for AI agent decision-making; keep response focused and token-efficient

**OQ4:** ~~Should we implement a `--max-results` parameter for `search_knowledge_base`?~~ **RESOLVED:** Yes, in config file.

- **Decision**: Configure `max_results` in the server config file (not as a per-query parameter)
- **Default**: 3 results (consistent with `chromadb_query_client.py`)
- **Rationale**: System-level setting rather than per-query control; keeps tool interface simple

**OQ5:** ~~How should the AI agent be instructed to use these tools?~~ **RESOLVED:** Tool descriptions are sufficient.

- **Decision**: Rely on FastMCP tool descriptions and collection descriptions; Claude Desktop's system prompt is sufficient
- **Rationale**: Significant effort invested in multi-collection pipeline PRD to ensure collection descriptions are accurate and AI-optimized; no additional instruction mechanism needed

**OQ6:** ~~Should collection descriptions support markdown formatting?~~ **RESOLVED:** No.
- Collection descriptions should remain plain text strings
- AI agents parse semantic meaning, not visual formatting
- Markdown doesn't improve AI selection accuracy
- Plain text is simpler for JSON storage and validation
- Structured writing patterns (see pipeline PRD) achieve the same goals without formatting complexity

**OQ7:** ~~Do we need a tool to check ChromaDB/Ollama service health?~~ **RESOLVED:** Implicit checks only.

- **Decision**: No separate health check tool; perform implicit checks during search operations
- **Rationale**: Error handling during initialization (FR5) and search (FR7, FR8) provides sufficient feedback; dedicated health check tool adds complexity without significant benefit

**OQ8:** ~~Should we support filtering by source_type in `list_knowledge_bases`?~~ **RESOLVED:** source_type field removed from design. Collections distinguished by name and description only.

**OQ9:** ~~Will AI agents reliably interpret collection descriptions, or do we need fallback mechanisms?~~ **RESOLVED:** No fallback needed.

- **Decision**: Rely on collection description quality; no additional fallback mechanisms
- **Rationale**: Same as OQ5 - significant effort in pipeline PRD ensures description quality through validation and guidelines; fallback mechanisms would undermine the self-discovery pattern
- **Monitoring**: Real-world usage can inform future iterations if needed, but not implementing fallbacks upfront

**OQ11:** ~~Should the default `context_mode` be `chunk_only` or `enhanced`?~~ **RESOLVED:** Default is `enhanced`.
- Decision: Start with `enhanced` for better UX and narrative preservation
- AI agents can still opt for `chunk_only` when appropriate
- Monitor token usage in production; optimize if costs become problematic

**OQ12:** ~~How should AI agents know when to escalate from `chunk_only` to `enhanced` or `full_note`?~~ **RESOLVED:** Option A with caveat.

- **Decision**: Use Option A - Single `search_knowledge_base` tool with explicit guidance in tool description
- **Tool description guidance**: "Use enhanced mode for questions requiring context, chunk_only for quick lookups, full_note when user explicitly needs complete note"
- **Caveat**: Optimal performance depends on the nature of indexed documents; this approach provides flexibility without locking into a single strategy
- **Future optimization**: Monitor real-world usage patterns and adjust default/guidance if needed

---

## PRD Status: All Open Questions Resolved ✅

All open questions have been resolved. Key decisions:

| OQ | Decision | Summary |
|----|----------|---------|
| **OQ1** | FastMCP | Use `mcp.server.fastmcp.FastMCP` - Anthropic-recommended, reduces boilerplate, enables self-discovery |
| **OQ2** | Config file | ChromaDB path in config file with absolute path |
| **OQ3** | No | No additional statistics in `list_knowledge_bases` |
| **OQ4** | Config file | `max_results` configured in server config (default: 3) |
| **OQ5** | Tool descriptions | Rely on FastMCP tool descriptions and collection descriptions |
| **OQ7** | Implicit checks | No separate health check tool; checks during initialization and search |
| **OQ9** | No fallback | Trust collection description quality from pipeline validation |
| **OQ12** | Option A | Single flexible tool with explicit guidance; monitor and adjust based on usage |

**Configuration File Requirements:**

- `chromadb_path`: Absolute path to ChromaDB database
- `max_results`: Maximum search results (default: 3)

**Next Step:** Implementation ready to proceed following functional requirements (FR1-FR8) and resolved design decisions.
