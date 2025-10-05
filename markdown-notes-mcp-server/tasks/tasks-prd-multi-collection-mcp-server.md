# Task List: Multi-Collection MCP Server

Generated from: `prd-multi-collection-mcp-server.md`

## Relevant Files

### Core Implementation Files
- `markdown-notes-mcp-server/server.py` - Main FastMCP server entry point with tool definitions for `list_knowledge_bases` and `search_knowledge_base`
- `markdown-notes-mcp-server/config.py` - Configuration loader and validator for server settings (ChromaDB path, max results, embedding model)
- `markdown-notes-mcp-server/collection_discovery.py` - Module for discovering and listing ChromaDB collections with metadata
- `markdown-notes-mcp-server/search_tools.py` - Semantic search implementation with context retrieval (chunk_only, enhanced, full_note modes)
- `markdown-notes-mcp-server/context_retrieval.py` - Logic for fetching surrounding chunks and full notes based on context mode
- `markdown-notes-mcp-server/startup_validation.py` - Server initialization checks (ChromaDB connection, Ollama service, collection availability)

### Configuration Files
- `markdown-notes-mcp-server/config.json` - Server configuration file (ChromaDB path, defaults, embedding model)
- `markdown-notes-mcp-server/config.schema.json` - JSON schema for validating configuration file

### Test Files
- `markdown-notes-mcp-server/tests/test_config.py` - Unit tests for configuration loading and validation
- `markdown-notes-mcp-server/tests/test_collection_discovery.py` - Unit tests for collection listing and metadata extraction
- `markdown-notes-mcp-server/tests/test_search_tools.py` - Unit tests for semantic search functionality
- `markdown-notes-mcp-server/tests/test_context_retrieval.py` - Unit tests for context mode implementations (chunk_only, enhanced, full_note)
- `markdown-notes-mcp-server/tests/test_startup_validation.py` - Unit tests for server initialization validation
- `markdown-notes-mcp-server/tests/test_integration.py` - End-to-end integration tests for MCP server tools

### Documentation Files
- `markdown-notes-mcp-server/README.md` - Already exists, may need updates for usage examples and configuration details
- `markdown-notes-mcp-server/TESTING.md` - Testing guide for developers (how to run tests, test data setup, manual testing with Claude Desktop)

### Reused Files (from existing codebase)
- `markdown-notes-cag-data-creator/embedding.py` - Reused for generating query embeddings via Ollama
- `markdown-notes-cag-data-creator/storage.py` - Reused for ChromaDB client initialization and collection operations
- `markdown-notes-cag-data-creator/models.py` - Reused for Chunk and ChunkWithEmbedding data structures

### Notes

- **Test execution:** Use `pytest markdown-notes-mcp-server/tests/` to run all tests, or specify individual test files
- **Dependencies:** FastMCP (mcp package) is already installed in the virtual environment (v2.11.2)
- **Code reuse:** The server imports modules from `markdown-notes-cag-data-creator/` for embedding generation and ChromaDB operations to maintain consistency with the pipeline
- **Configuration approach:** Server uses JSON config file instead of environment variables for persistence and clarity (as resolved in OQ2)

## Tasks

- [ ] **1.0 Implement Configuration Management**
  - [ ] 1.1 Create `config.schema.json` with JSON schema defining required/optional fields (`chromadb_path`, `default_max_results`, `embedding_model`)
  - [ ] 1.2 Create `config.json.example` with sample configuration showing absolute paths and default values
  - [ ] 1.3 Implement `config.py` module with `load_config()` function to read and parse JSON configuration file
  - [ ] 1.4 Add validation logic in `config.py` to ensure `chromadb_path` is absolute path (not relative)
  - [ ] 1.5 Add validation for `default_max_results` (integer between 1 and 100)
  - [ ] 1.6 Add validation for `embedding_model` format (string matching Ollama model naming convention)
  - [ ] 1.7 Implement clear error messages for missing or invalid configuration fields with actionable remediation steps
  - [ ] 1.8 Write unit tests in `tests/test_config.py` covering valid configs, missing fields, invalid paths, and out-of-range values

- [ ] **2.0 Implement Collection Discovery Tool**
  - [ ] 2.1 Create `collection_discovery.py` module with `list_collections()` function
  - [ ] 2.2 Implement ChromaDB client initialization using `storage.py:initialize_chromadb_client()`
  - [ ] 2.3 Query all collections from ChromaDB using `client.list_collections()`
  - [ ] 2.4 Extract metadata from each collection: name, description, created_at (from collection.metadata)
  - [ ] 2.5 Retrieve chunk count for each collection using `collection.count()`
  - [ ] 2.6 Format response as list of dictionaries with fields: `name`, `description`, `chunk_count`, `created_at`
  - [ ] 2.7 Implement error handling for ChromaDB connection failures with clear error messages
  - [ ] 2.8 Write unit tests in `tests/test_collection_discovery.py` with mocked ChromaDB client and metadata
  - [ ] 2.9 Add integration test for real ChromaDB connection in `tests/test_integration.py`

- [ ] **3.0 Implement Semantic Search with Context Retrieval**
  - [ ] 3.1 Create `search_tools.py` module with `search_knowledge_base()` function accepting parameters: `query`, `collection_name`, `context_mode`, `max_results`
  - [ ] 3.2 Validate that `collection_name` exists using ChromaDB client, return error with `list_knowledge_bases` suggestion if not found
  - [ ] 3.3 Generate query embedding using `embedding.py:generate_embedding()` from existing pipeline module
  - [ ] 3.4 Handle Ollama service unavailability errors with "run 'ollama serve'" guidance (FR8)
  - [ ] 3.5 Perform semantic search in specified collection using `collection.query(query_embeddings=[embedding], n_results=max_results)`
  - [ ] 3.6 Extract initial search results with metadata: `noteId`, `title`, `chunkIndex`, `modificationDate`, `collectionName`, similarity score
  - [ ] 3.7 Create `context_retrieval.py` module with functions for different context modes
  - [ ] 3.8 Implement `get_chunk_only_content()` returning just the matched chunk content
  - [ ] 3.9 Implement `get_enhanced_content()` that queries for surrounding chunks (±2 from matched chunk) using metadata filtering
  - [ ] 3.10 In `get_enhanced_content()`, add `[MATCH START]` and `[MATCH END]` markers around the matched chunk
  - [ ] 3.11 Implement `get_full_note_content()` that queries all chunks with matching `noteId`, sorts by `chunkIndex`, and concatenates
  - [ ] 3.12 In `get_full_note_content()`, add marker indicating which chunk matched (e.g., `[MATCH AT CHUNK 3]`)
  - [ ] 3.13 Integrate context retrieval into `search_knowledge_base()` based on `context_mode` parameter (default: "enhanced")
  - [ ] 3.14 Format final results with all required fields per FR4: `noteTitle`, `noteId`, `chunkIndex`, `totalChunks`, `modificationDate`, `collectionName`, `similarityScore`, `content`
  - [ ] 3.15 Write unit tests in `tests/test_search_tools.py` for query validation, embedding generation, and result formatting
  - [ ] 3.16 Write unit tests in `tests/test_context_retrieval.py` for all three context modes (chunk_only, enhanced, full_note)
  - [ ] 3.17 Test edge cases: first chunk (no predecessors), last chunk (no successors), single-chunk notes

- [ ] **4.0 Implement Server Initialization and Validation**
  - [ ] 4.1 Create `startup_validation.py` module with `validate_server_prerequisites()` function
  - [ ] 4.2 Implement ChromaDB path validation: check that path exists and is accessible
  - [ ] 4.3 Implement collection availability check: verify at least one collection exists in ChromaDB
  - [ ] 4.4 Implement Ollama service check using `embedding.py:check_ollama_service()`
  - [ ] 4.5 Implement embedding model availability check using `embedding.py:check_model_availability()`
  - [ ] 4.6 Create detailed error messages for each validation failure with remediation steps (FR6):
    - ChromaDB path invalid: Show expected path, suggest verifying config
    - No collections: Suggest running pipeline to create collections
    - Ollama unavailable: Suggest `ollama serve`
    - Model unavailable: Suggest `ollama pull mxbai-embed-large:latest`
  - [ ] 4.7 Make validation function return tuple: `(success: bool, error_message: str | None)`
  - [ ] 4.8 Write unit tests in `tests/test_startup_validation.py` for all validation scenarios (success and each failure case)

- [ ] **5.0 Create MCP Server Entry Point**
  - [ ] 5.1 Create `server.py` with FastMCP initialization using `from mcp.server.fastmcp import FastMCP`
  - [ ] 5.2 Load configuration on startup using `config.py:load_config()`
  - [ ] 5.3 Run startup validation using `startup_validation.py:validate_server_prerequisites()`
  - [ ] 5.4 Exit with non-zero status code and clear error message if validation fails (FR6)
  - [ ] 5.5 Define `list_knowledge_bases` tool using `@mcp.tool()` decorator
  - [ ] 5.6 Add comprehensive docstring to `list_knowledge_bases` tool describing its purpose and return format
  - [ ] 5.7 Implement `list_knowledge_bases` tool by calling `collection_discovery.py:list_collections()`
  - [ ] 5.8 Define `search_knowledge_base` tool using `@mcp.tool()` decorator with parameters: `query: str`, `collection_name: str`, `context_mode: str = "enhanced"`, `max_results: int | None = None`
  - [ ] 5.9 Add comprehensive docstring to `search_knowledge_base` tool describing parameters, context modes, and use cases (FR4 context mode descriptions)
  - [ ] 5.10 Use default `max_results` from config if not provided in tool call
  - [ ] 5.11 Implement `search_knowledge_base` tool by calling `search_tools.py:search_knowledge_base()`
  - [ ] 5.12 Add error handling for both tools to return user-friendly error messages (FR8)
  - [ ] 5.13 Run FastMCP server using `mcp.run()` in stdio mode for Claude Desktop integration
  - [ ] 5.14 Add logging statements for key operations (startup, tool invocations, errors)

- [ ] **6.0 Add Testing and Documentation**
  - [ ] 6.1 Create `tests/` directory structure with `__init__.py`
  - [ ] 6.2 Create test fixtures for mocked ChromaDB collections with sample metadata and chunks
  - [ ] 6.3 Create test fixtures for sample embeddings matching expected dimensions (1024 for mxbai-embed-large)
  - [ ] 6.4 Write integration tests in `tests/test_integration.py` that test complete flow: list collections → search → retrieve context
  - [ ] 6.5 Test error scenarios: collection not found, Ollama unavailable, ChromaDB connection failure
  - [ ] 6.6 Create `TESTING.md` documentation with instructions for running tests, setting up test data, and manual testing with Claude Desktop
  - [ ] 6.7 Update `README.md` with complete usage examples showing all three context modes
  - [ ] 6.8 Add example conversation flows in `README.md` demonstrating AI agent interaction patterns
  - [ ] 6.9 Document configuration file format and validation rules in `README.md`
  - [ ] 6.10 Add troubleshooting section in `README.md` for common errors (ChromaDB path issues, Ollama service down, etc.)
  - [ ] 6.11 Create example `config.json` file in repository root with placeholder paths and comments
  - [ ] 6.12 Add `.gitignore` entry for `config.json` to prevent committing local paths

## Implementation Order Recommendations

1. **Start with configuration (Task 1.0)** - Foundation for all other components
2. **Implement collection discovery (Task 2.0)** - Simpler than search, validates ChromaDB integration
3. **Build context retrieval (Task 3.7-3.12)** - Core complexity, test independently before integrating
4. **Implement search tools (Task 3.1-3.6, 3.13-3.17)** - Integrate context retrieval
5. **Add startup validation (Task 4.0)** - Ensures fail-fast behavior
6. **Wire up FastMCP server (Task 5.0)** - Bring all components together
7. **Comprehensive testing (Task 6.0)** - Validate end-to-end functionality

## Key Design Decisions (from PRD)

- **FastMCP framework** (OQ1): Reduces boilerplate from ~1000 to ~300 lines, automatic schema generation
- **Config file approach** (OQ2): JSON config provides persistence and clarity over environment variables
- **Default to enhanced mode** (OQ11): Better UX with narrative context preservation, AI can override
- **Single flexible tool** (OQ12): One `search_knowledge_base` tool with explicit context_mode parameter
- **Reuse pipeline modules**: Import `embedding.py` and `storage.py` from `markdown-notes-cag-data-creator/` for consistency

## Success Criteria (from PRD)

- **SM1**: AI agent correctly selects appropriate collection in 95% of test cases (depends on quality descriptions from pipeline)
- **SM2**: Users can add new collection in under 5 minutes (run pipeline with new collection name)
- **SM3**: Zero code changes required when adding new collection types
- **SM4**: MCP tool invocation latency under 2 seconds for typical queries (excluding LLM processing time)

## Dependencies

- **Prerequisite**: Multi-collection pipeline enhancements from `markdown-notes-cag-data-creator/tasks/prd-multi-collection-pipeline.md` must be implemented
- **Required collections**: At least one ChromaDB collection with proper metadata (`description`, `created_at`, `version`)
- **Ollama service**: Must be running with `mxbai-embed-large:latest` model available
- **Python packages**: `mcp` (FastMCP), `chromadb`, `ollama`, `numpy` (already installed in `.venv`)
