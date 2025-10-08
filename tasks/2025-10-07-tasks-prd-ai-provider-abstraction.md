# Task List: AI Provider Abstraction Layer

**Generated from PRD:** [tasks/2025-10-07-prd-ai-provider-abstraction.md](2025-10-07-prd-ai-provider-abstraction.md)
**Date:** 2025-10-07
**Status:** In Progress - Parent Tasks Generated

---

## Relevant Files

**New Files to Create:**
- `markdown-notes-cag-data-creator/ai_provider.py` - Core abstraction layer for multi-provider AI support
- `markdown-notes-cag-data-creator/tests/test_ai_provider.py` - Unit tests for AI provider abstraction
- `configs/example-ollama.json` - Example configuration file for Ollama provider
- `configs/example-openai.json` - Example configuration file for OpenAI provider
- `configs/example-gemini.json` - Example configuration file for Google Gemini provider

**Files Created (Tasks 1.1-1.12):**

- `requirements.txt` - Project-level dependency file listing all core dependencies including litellm
- `markdown-notes-cag-data-creator/ai_provider.py` - Core abstraction layer for multi-provider AI support with LiteLLM integration
- `markdown-notes-cag-data-creator/tests/test_ai_provider.py` - Comprehensive unit tests for AI provider abstraction layer

**Files Modified (Tasks 2.1-2.8):**

- `markdown-notes-cag-data-creator/config_loader.py` - Extended to support `ai_provider` configuration section with JSON schema validation, backward compatibility defaults, and comprehensive error messages
- `markdown-notes-cag-data-creator/tests/test_config_loader.py` - Added 14 unit tests for AI provider config validation, backward compatibility, and error cases

**Files to Modify:**

- `markdown-notes-cag-data-creator/embedding.py` - Refactor to use AI provider abstraction instead of direct Ollama calls
- `markdown-notes-cag-data-creator/tests/test_embedding.py` - Update tests for new provider-based architecture
- `markdown-notes-cag-data-creator/storage.py` - Add support for storing AI provider metadata in ChromaDB collections
- `markdown-notes-cag-data-creator/tests/test_storage.py` - Add tests for metadata storage functionality
- `markdown-notes-cag-data-creator/full_pipeline.py` - Update to use config-driven AI provider initialization
- `markdown-notes-cag-data-creator/tests/test_full_pipeline.py` - Update tests for config-driven pipeline
- `markdown-notes-mcp-server/server.py` - Implement dynamic collection discovery with provider loading
- `markdown-notes-mcp-server/collection_discovery.py` - Update to read and instantiate providers from metadata
- `markdown-notes-mcp-server/tests/test_collection_discovery.py` - Add tests for provider-aware discovery
- `markdown-notes-mcp-server/search_tools.py` - Update to use collection-specific providers for query embeddings
- `markdown-notes-mcp-server/tests/test_search_tools.py` - Add tests for provider-aware search
- `markdown-notes-mcp-server/config.py` - Simplify to only require `chromadb_path` (remove provider config)
- `markdown-notes-mcp-server/tests/test_integration.py` - Add integration tests for multi-provider scenarios
- `requirements.txt` or `pyproject.toml` - Add `litellm` dependency

### Notes

- Unit tests should be placed alongside the code files they are testing in the `tests/` directory
- Use `pytest` to run tests. Running without a path executes all tests: `pytest`
- Run specific test files with: `pytest markdown-notes-cag-data-creator/tests/test_ai_provider.py`
- The existing test infrastructure uses `conftest.py` for shared fixtures

---

## Tasks

- [x] 1.0 Create AI Provider Abstraction Layer Module
  - [x] 1.1 Install LiteLLM dependency (`pip install litellm`) and update requirements.txt
  - [x] 1.2 Create `ai_provider.py` with `AIProviderConfig` dataclass (provider_type, embedding_model, llm_model, base_url, api_key fields)
  - [x] 1.3 Implement environment variable resolution function to replace `${ENV_VAR}` templates with actual values from `os.environ`
  - [x] 1.4 Implement `AIProvider` class constructor that initializes LiteLLM with resolved config
  - [x] 1.5 Implement `AIProvider.generate_embedding(text: str) -> List[float]` method using LiteLLM
  - [x] 1.6 Implement `AIProvider.generate_embeddings_batch(texts: List[str]) -> List[List[float]]` method with batch processing
  - [x] 1.7 Implement `AIProvider.get_embedding_metadata() -> Dict[str, Any]` to return provider type, model, dimension, base_url, api_key_ref
  - [x] 1.8 Implement `AIProvider.check_availability() -> Dict[str, Any]` to test provider connection with a test embedding
  - [x] 1.9 Implement `AIProvider.validate_description(description: str) -> Dict[str, Any]` using LLM to score collection descriptions (0-10 scale)
  - [x] 1.10 Add comprehensive error handling for missing API keys with `ValueError` containing actionable guidance
  - [x] 1.11 Add custom exception classes: `AIProviderError`, `APIKeyMissingError`, `ProviderUnavailableError`
  - [x] 1.12 Create unit tests in `tests/test_ai_provider.py` covering all methods, environment variable resolution, and error conditions

- [x] 2.0 Update Pipeline Configuration System
  - [x] 2.1 Update `COLLECTION_CONFIG_SCHEMA` in `config_loader.py` to add optional `ai_provider` object with type, embedding, and llm fields
  - [x] 2.2 Update `CollectionConfig` dataclass to include optional `ai_provider: Optional[Dict[str, Any]]` field
  - [x] 2.3 Add validation logic to ensure `ai_provider.type` is one of: ollama, openai, gemini, azure, anthropic
  - [x] 2.4 Add validation for `embedding` and `llm` sub-objects (required: model; optional: base_url, api_key)
  - [x] 2.5 Add validation to check that api_key values are either null or environment variable templates (`${VAR_NAME}`)
  - [x] 2.6 Add backward compatibility support: if `ai_provider` is missing, default to Ollama with `mxbai-embed-large:latest`
  - [x] 2.7 Update `config_loader.py` error messages to guide users on correct ai_provider format
  - [x] 2.8 Create unit tests in `tests/test_config_loader.py` for ai_provider validation, backward compatibility, and error cases

- [x] 3.0 Refactor Embedding Module to Use Provider Abstraction
  - [x] 3.1 Add module-level variable `_provider: Optional[AIProvider] = None` to store initialized provider instance
  - [x] 3.2 Create `initialize_provider(config: CollectionConfig) -> AIProvider` function that creates AIProvider from config
  - [x] 3.3 Update `generate_embedding()` to check `_provider` is initialized (raise assertion error if not) then delegate to `_provider.generate_embedding()`
  - [x] 3.4 Update `generate_embeddings()` to check `_provider` is initialized then delegate to `_provider.generate_embeddings_batch()`
  - [x] 3.5 Create `get_embedding_metadata() -> Dict[str, Any]` function that returns `_provider.get_embedding_metadata()`
  - [x] 3.6 Create `validate_description(description: str) -> Dict[str, Any]` function that delegates to `_provider.validate_description()`
  - [x] 3.7 Remove direct Ollama imports and replace with provider abstraction calls
  - [x] 3.8 Update error handling to catch `AIProviderError` and wrap in `EmbeddingError` with context
  - [x] 3.9 Keep backward-compatible function signatures (same parameters and return types)
  - [x] 3.10 Update unit tests in `tests/test_embedding.py` to mock `AIProvider` instead of direct Ollama calls
  - [x] 3.11 Add tests for uninitialized provider error handling
  - [x] 3.12 Add tests for provider initialization with different provider types

- [x] 4.0 Update Storage Module for Provider Metadata
  - [x] 4.1 Update `build_collection_metadata()` function signature to accept optional `embedding_metadata: Optional[Dict[str, Any]]` parameter
  - [x] 4.2 Merge embedding_metadata fields into collection metadata dictionary: `embedding_model`, `embedding_provider`, `embedding_dimension`, `embedding_base_url`, `embedding_api_key_ref`, `llm_model`
  - [x] 4.3 Ensure API key references are stored as templates (e.g., `${OPENAI_API_KEY}`), NOT actual secret values
  - [x] 4.4 Update `create_collection()` and `recreate_collection()` to accept optional `embedding_metadata` parameter and pass to `build_collection_metadata()`
  - [x] 4.5 Update `get_or_create_collection()` (backward compatibility function) to accept `embedding_metadata` parameter
  - [x] 4.6 Add validation to prevent storing actual API keys (check for patterns like `sk-`, `AIza`, etc. and raise error)
  - [x] 4.7 Update unit tests in `tests/test_storage.py` to verify metadata storage, verify templates are stored (not secrets)
  - [x] 4.8 Add test case to ensure actual API keys are rejected with clear error message

- [ ] 5.0 Update Pipeline to Use Config-Driven Provider Initialization
  - [ ] 5.1 Import `initialize_provider`, `get_embedding_metadata`, `validate_description` from updated `embedding.py`
  - [ ] 5.2 In `main()`, after loading config, call `initialize_provider(config)` to set up the AI provider
  - [ ] 5.3 Add try-except block around provider initialization to catch `AIProviderError` and print actionable error messages
  - [ ] 5.4 Call `provider.check_availability()` before processing to fail fast if provider is unavailable
  - [ ] 5.5 Print provider status: type, embedding model, LLM model, embedding dimension, availability
  - [ ] 5.6 If `skipAiValidation` is false, call `validate_description(config.description)` and log the score/feedback
  - [ ] 5.7 If description validation score < 7, log warning but continue (non-blocking)
  - [ ] 5.8 After provider initialization, call `get_embedding_metadata()` to retrieve metadata for storage
  - [ ] 5.9 Pass embedding_metadata to `create_collection()` or `recreate_collection()` calls
  - [ ] 5.10 Update error handling in `handle_embedding_error()` to provide provider-specific troubleshooting (not just Ollama)
  - [ ] 5.11 Update verbose output to show provider configuration details
  - [ ] 5.12 Update unit tests in `tests/test_full_pipeline.py` to test config-driven provider initialization
  - [ ] 5.13 Add integration test for complete pipeline flow with Ollama (no API keys required)

- [ ] 6.0 Implement MCP Server Dynamic Collection Discovery
  - [ ] 6.1 Update `collection_discovery.py` to read collection metadata and extract AI provider fields
  - [ ] 6.2 Create `reconstruct_provider_from_metadata(metadata: Dict) -> Optional[AIProvider]` function
  - [ ] 6.3 Extract provider config from metadata: type, embedding_model, base_url, api_key_ref, llm_model
  - [ ] 6.4 Resolve environment variables in api_key_ref templates at runtime using `os.environ.get()`
  - [ ] 6.5 Instantiate `AIProvider` with reconstructed config
  - [ ] 6.6 Call `provider.check_availability()` to test provider connectivity (generate test embedding)
  - [ ] 6.7 Return provider instance if available, or None if unavailable (with reason)
  - [ ] 6.8 Update `list_collections()` to return availability status for each collection
  - [ ] 6.9 Mark collections without AI metadata as unavailable with reason "Missing AI provider metadata (created with old pipeline)"
  - [ ] 6.10 Update MCP server startup in `server.py` to call enhanced collection discovery
  - [ ] 6.11 Store map of available collections to their provider instances in server state
  - [ ] 6.12 Print detailed startup log showing each collection's provider, model, availability status, and failure reasons
  - [ ] 6.13 Print summary: total collections, available count, unavailable count
  - [ ] 6.14 If zero collections are available, exit with error and troubleshooting guidance
  - [ ] 6.15 Update `list_knowledge_bases` tool to return only available collections
  - [ ] 6.16 Update unit tests in `tests/test_collection_discovery.py` for provider reconstruction and availability checking
  - [ ] 6.17 Add test cases for missing API keys, invalid metadata, and mixed availability scenarios

- [ ] 7.0 Update MCP Search Tools for Provider-Aware Queries
  - [ ] 7.1 Update `search_knowledge_base()` in `search_tools.py` to accept `provider: AIProvider` parameter
  - [ ] 7.2 Replace direct `generate_embedding()` call with `provider.generate_embedding(query)`
  - [ ] 7.3 Retrieve expected embedding dimension from collection metadata
  - [ ] 7.4 Validate generated embedding dimension matches collection's expected dimension
  - [ ] 7.5 Raise hard error if dimensions mismatch: "Embedding dimension mismatch! Query: {actual}, Collection: {expected}"
  - [ ] 7.6 Update MCP server's `search_knowledge_base` tool to look up provider for target collection
  - [ ] 7.7 Pass collection-specific provider to `search_knowledge_base()` function
  - [ ] 7.8 Add error handling for queries to unavailable collections: "Collection not available. Use list_knowledge_bases() to see available collections"
  - [ ] 7.9 Update unit tests in `tests/test_search_tools.py` to mock provider-based embedding generation
  - [ ] 7.10 Add test for embedding dimension validation (both matching and mismatching scenarios)
  - [ ] 7.11 Add test for unavailable collection query attempts

- [ ] 8.0 Create Example Configuration Files
  - [ ] 8.1 Create `configs/` directory at project root if it doesn't exist
  - [ ] 8.2 Create `configs/example-ollama.json` with local Ollama configuration (no API keys, base_url: http://localhost:11434)
  - [ ] 8.3 Use `mxbai-embed-large:latest` for embeddings and `llama3.1:8b` for LLM in Ollama config
  - [ ] 8.4 Create `configs/example-openai.json` with OpenAI configuration using `${OPENAI_API_KEY}` template
  - [ ] 8.5 Use `text-embedding-3-small` for embeddings and `gpt-4o-mini` for LLM in OpenAI config
  - [ ] 8.6 Create `configs/example-gemini.json` with Google Gemini configuration using `${GEMINI_API_KEY}` template
  - [ ] 8.7 Use `text-embedding-004` for embeddings and `gemini-1.5-flash` for LLM in Gemini config
  - [ ] 8.8 Add comments in JSON files (if possible) or create accompanying README explaining each field
  - [ ] 8.9 Ensure all config files use relative paths for `chromadb_path` and `json_file`
  - [ ] 8.10 Set `forceRecreate: false` and `skipAiValidation: false` as defaults in examples
  - [ ] 8.11 Verify all example configs pass JSON schema validation

- [ ] 9.0 Integration Testing and Documentation
  - [ ] 9.1 Create integration test in `tests/test_integration.py` for Ollama end-to-end pipeline (create collection with metadata)
  - [ ] 9.2 Add integration test for MCP server discovery with single Ollama collection
  - [ ] 9.3 Add integration test for MCP search using collection-specific provider
  - [ ] 9.4 Add integration test for dimension validation (create collection with one model, try to query with different model)
  - [ ] 9.5 Add integration test for mixed availability: some collections available, some unavailable due to missing API keys
  - [ ] 9.6 Create test fixture with multiple collections using different providers in ChromaDB
  - [ ] 9.7 Test backward compatibility: verify old collections (no metadata) are marked unavailable
  - [ ] 9.8 Update `CLAUDE.md` with new pipeline usage: `python full_pipeline.py --config configs/example-ollama.json`
  - [ ] 9.9 Add section to `CLAUDE.md` documenting multi-provider setup (setting API keys, running with different providers)
  - [ ] 9.10 Add troubleshooting section for common errors: missing API keys, dimension mismatches, unavailable providers
  - [ ] 9.11 Document the provider metadata flow: config → ChromaDB → MCP reconstruction
  - [ ] 9.12 Add examples of MCP server startup output for different scenarios (all available, some unavailable, none available)
  - [ ] 9.13 Run full test suite with `pytest` and ensure all tests pass
  - [ ] 9.14 Manually test complete workflow: create Ollama collection, start MCP server, perform searches
  - [ ] 9.15 If OpenAI/Gemini API keys available, manually test multi-provider scenario

---

**Status:** Complete - All parent tasks and sub-tasks generated. Ready for implementation.
