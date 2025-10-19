# Product Requirements Document: AI Provider Abstraction Layer

**Version:** 1.0
**Date:** 2025-10-07
**Status:** Ready for Implementation
**Author:** Product Team
**Related Documents:** [tasks/2025-10-07-ai-provider-abstraction-analysis-v3.md](2025-10-07-ai-provider-abstraction-analysis-v3.md)

---

## 1. Introduction/Overview

The current Markdown Notes RAG system is tightly coupled to Ollama for AI embeddings. This limits flexibility for users who may want to use cloud-based AI providers (OpenAI, Google Gemini, Azure) for better performance, or switch between providers based on cost, speed, or availability requirements.

This feature introduces an **AI Provider Abstraction Layer** that allows users to configure and use multiple AI providers across different note collections within the same system. Each collection can use a different embedding model, and the MCP server will automatically detect and use the correct provider for each collection at query time.

**Problem Solved:** Users cannot choose their AI provider or use different providers for different collections, limiting flexibility and preventing optimization for cost, performance, or offline requirements.

**Goal:** Enable flexible, multi-provider AI support while maintaining security, simplicity, and backward compatibility.

---

## 2. Goals

1. **Provider Flexibility:** Support multiple AI providers (Ollama, OpenAI, Google Gemini, Azure OpenAI, Anthropic) through a unified abstraction layer
2. **Per-Collection Configuration:** Allow each ChromaDB collection to use a different embedding model and provider
3. **Dynamic Discovery:** MCP server automatically discovers available collections and their AI providers from ChromaDB metadata at startup
4. **Security-First Design:** Never store API keys in files or databases; use environment variables exclusively
5. **Graceful Degradation:** System continues operating with available collections even if some providers are unavailable
6. **Embedding Compatibility:** Prevent cross-provider embedding mismatches through automatic validation
7. **Developer Experience:** Provide clear configuration schema, error messages, and documentation
8. **Automated Testing:** Core abstraction layer has unit tests to ensure reliability

---

## 3. User Stories

### Primary User: Developer/System Administrator

**US-1: Choose AI Provider**
- **As a** developer setting up a notes collection,
- **I want to** specify which AI provider to use (Ollama, OpenAI, etc.),
- **So that** I can optimize for cost, speed, or offline operation based on my needs.

**US-2: Multiple Providers**
- **As a** system administrator,
- **I want to** run multiple collections with different AI providers in the same ChromaDB instance,
- **So that** I can use local Ollama for personal notes and cloud providers for work notes.

**US-3: Automatic Provider Detection**
- **As a** developer running the MCP server,
- **I want to** see which collections are available and which failed to load,
- **So that** I can troubleshoot missing API keys or configuration issues.

**US-4: Secure API Key Management**
- **As a** security-conscious developer,
- **I want to** store API keys only in environment variables,
- **So that** I don't accidentally commit secrets to version control.

**US-5: Configuration Validation**
- **As a** developer creating a new collection,
- **I want to** know immediately if my AI provider configuration is invalid,
- **So that** I don't waste time processing notes with a broken configuration.

**US-6: Embedding Compatibility Protection**
- **As a** user querying a collection,
- **I want to** be prevented from querying with the wrong embedding model,
- **So that** I get accurate search results and clear error messages.

**US-7: Collection Description Quality**
- **As a** developer creating a collection,
- **I want to** validate my collection description for AI-friendliness,
- **So that** AI agents can better understand when to query this collection.

---

## 4. Functional Requirements

### 4.1 AI Provider Abstraction Module

**FR-1:** The system MUST provide a new module `ai_provider.py` that abstracts AI operations across multiple providers.

**FR-2:** The abstraction layer MUST support the following providers via LiteLLM:
- Ollama (local)
- OpenAI
- Google Gemini
- Azure OpenAI
- Anthropic Claude

**FR-3:** The `AIProvider` class MUST expose these methods:
- `generate_embedding(text: str) -> List[float]` - Generate single embedding
- `generate_embeddings_batch(texts: List[str]) -> List[List[float]]` - Generate batch embeddings
- `validate_description(description: str) -> Dict[str, Any]` - Validate collection description quality using LLM
- `get_embedding_metadata() -> Dict[str, Any]` - Return metadata for ChromaDB storage
- `check_availability() -> Dict[str, Any]` - Test provider availability

**FR-4:** The `AIProviderConfig` class MUST support configuration parameters:
- `provider_type`: Type of provider (ollama, openai, gemini, azure, anthropic)
- `embedding_model`: Model name for embeddings
- `llm_model`: Model name for LLM operations (description validation)
- `base_url`: Optional base URL for custom endpoints (Ollama, Azure)
- `api_key`: API key (supports environment variable references like `${OPENAI_API_KEY}`)

**FR-5:** API keys specified as `${ENV_VAR_NAME}` MUST be automatically resolved from environment variables at runtime.

**FR-6:** If an environment variable is not set, the system MUST raise a clear error message indicating which variable is missing.

### 4.2 Pipeline Configuration

**FR-7:** The pipeline MUST accept a `--config` parameter pointing to a JSON configuration file.

**FR-8:** Each pipeline configuration file MUST contain:
- `collection_name`: Name of the ChromaDB collection
- `description`: Human-readable description for AI agents
- `chromadb_path`: Path to ChromaDB storage
- `json_file`: Path to input notes JSON file
- `forceRecreate`: Boolean to force collection recreation
- `skipAiValidation`: Boolean to skip LLM description validation
- `chunk_size`: Optional chunk size (default 1200)
- `ai_provider`: Object containing embedding and LLM configuration

**FR-9:** The `ai_provider` configuration MUST contain:
- `type`: Provider type (ollama, openai, gemini, etc.)
- `embedding`: Object with `model`, optional `base_url`, optional `api_key`
- `llm`: Object with `model`, optional `base_url`, optional `api_key`

**FR-10:** Configuration files with environment variable references (e.g., `"${OPENAI_API_KEY}"`) MUST be safe to commit to version control.

**FR-11:** Example configuration files MUST be provided for:
- Ollama (local, no API key)
- OpenAI (cloud, API key required)
- Google Gemini (cloud, API key required)

### 4.3 ChromaDB Metadata Storage

**FR-12:** When creating a collection, the pipeline MUST store AI provider metadata in ChromaDB collection metadata:
- `embedding_model`: Model name used for embeddings
- `embedding_provider`: Provider type (ollama, openai, etc.)
- `embedding_dimension`: Detected embedding dimension
- `embedding_base_url`: Base URL if applicable
- `embedding_api_key_ref`: Environment variable reference (e.g., `"${OPENAI_API_KEY}"`)
- `llm_model`: LLM model name used for validation
- `description`: Collection description
- `created_at`: ISO timestamp

**FR-13:** The stored `embedding_api_key_ref` MUST be the template reference (e.g., `"${OPENAI_API_KEY}"`) NOT the actual secret key.

**FR-14:** Embedding dimension MUST be auto-detected by generating a test embedding during pipeline initialization.

**FR-15:** Embedding metadata is REQUIRED when creating new collections. Collections without AI provider metadata cannot be queried and are considered invalid. Backward compatibility with legacy collections is NOT supported - all collections must be recreated with provider metadata.

### 4.4 MCP Server Dynamic Discovery

**FR-16:** The MCP server MUST have a minimal configuration file containing ONLY:
- `chromadb_path`: Path to ChromaDB storage

**FR-17:** At startup, the MCP server MUST:
1. Connect to ChromaDB
2. List all collections
3. For each collection, read metadata to extract AI provider configuration
4. Attempt to instantiate the AI provider from metadata
5. Test provider availability by generating a test embedding
6. Mark collection as available or unavailable based on test result

**FR-17:** The MCP server MUST log detailed status for each collection:
- Collection name
- Provider type and model
- Availability status (✅ AVAILABLE or ❌ UNAVAILABLE)
- Failure reason if unavailable (e.g., "Environment variable OPENAI_API_KEY not set")
- Embedding dimension if available

**FR-18:** The MCP server MUST print a summary at startup:
- Total collections found
- Number available
- Number unavailable

**FR-19:** If ZERO collections are available, the MCP server MUST exit with an error and provide troubleshooting guidance.

**FR-20:** If at least ONE collection is available, the MCP server MUST start successfully and expose only available collections.

### 4.5 Collection Availability Management

**FR-21:** Collections without AI provider metadata (created with old pipeline) MUST be marked as unavailable.

**FR-22:** Unavailable collections MUST NOT be returned by the `list_knowledge_bases()` tool.

**FR-23:** Attempting to query an unavailable collection MUST return a clear error message: `"Collection '{name}' is not available. Use list_knowledge_bases() to see available collections."`

**FR-24:** The MCP server console logs MUST show all collections (available and unavailable) for administrative visibility.

### 4.6 Query-Time Embedding Validation

**FR-25:** When processing a query, the MCP server MUST:
1. Retrieve the AI provider for the target collection
2. Generate query embedding using the same provider as the collection
3. Validate embedding dimension matches collection metadata
4. Query ChromaDB with the embedding

**FR-26:** If embedding dimensions mismatch, the system MUST raise an error:
```
"Embedding dimension mismatch! Query embedding: {actual}, Collection expects: {expected}"
```

**FR-27:** The dimension mismatch error MUST be a hard blocking error, not a warning.

### 4.7 Description Validation (AI-Enhanced)

**FR-28:** If `skipAiValidation` is false in the pipeline config, the system MUST validate the collection description using the configured LLM.

**FR-29:** Description validation MUST score the description from 0-10 based on AI agent usability.

**FR-30:** The validation MUST check if the description clearly explains:
1. What content is in the collection
2. When an AI should query this collection
3. What types of questions it answers

**FR-31:** Validation results MUST be logged with score and reason.

**FR-32:** If validation fails (score < 7), the system MUST log a warning but continue processing (not a blocking error).

### 4.8 Refactored Existing Modules

**FR-33:** The `embedding.py` module MUST be refactored to use the AI provider abstraction:
- Remove direct Ollama dependency
- Add `initialize_provider(config_path)` function
- Add `get_embedding_metadata()` function
- Add `validate_description()` function
- Maintain backward-compatible function signatures for `generate_embedding()` and `generate_embeddings_batch()`

**FR-34:** The `storage.py` module MUST be updated to accept embedding metadata:
- Add `embedding_metadata` parameter to `get_or_create_collection()`
- Merge embedding metadata into collection metadata

**FR-35:** The `full_pipeline.py` MUST be updated to:
- Require `--config` parameter
- Initialize AI provider from config
- Test provider availability before processing
- Get embedding metadata and pass to storage
- Log provider status and configuration
- Support optional description validation

**FR-36:** The MCP server MUST be updated to:
- Load provider from collection metadata
- Dynamically discover collections at startup
- Store provider instances for available collections
- Use correct provider per collection for queries

### 4.9 Error Handling

**FR-37:** Uninitialized provider usage in `embedding.py` MUST raise an assertion error with message:
```
"AI Provider not initialized! This is a programming error. Call initialize_provider(config_path) before using embedding functions."
```

**FR-38:** Missing environment variables MUST raise a `ValueError` with message:
```
"Environment variable '{name}' not set. Please export {name}=<your-api-key>"
```

**FR-39:** Provider unavailability during pipeline initialization MUST raise an `AIProviderError` with details.

**FR-40:** All errors MUST be logged with sufficient context for debugging (provider type, model name, configuration file path).

### 4.10 Testing Requirements

**FR-41:** The `ai_provider.py` module MUST have unit tests covering:
- AIProviderConfig initialization
- Environment variable resolution
- API key template handling
- Provider instantiation
- Embedding generation (mocked)
- Error conditions (missing env vars, invalid config)

**FR-42:** Integration tests MUST verify:
- Metadata flow: config → ChromaDB → MCP reconstruction
- MCP collection discovery with mixed availability
- Embedding dimension validation (mismatch detection)
- Provider initialization failures (missing env vars)

**FR-43:** Tests MUST use Ollama as the primary test provider (no API keys required).

**FR-44:** Cloud provider tests (OpenAI, Gemini) MAY be skipped if API keys are not available in test environment.

---

## 5. Non-Goals (Out of Scope)

**NG-1:** Automatic migration of existing collections to add AI provider metadata (users must re-run pipeline)

**NG-2:** Interactive API key prompting or secrets management integration (AWS Secrets Manager, HashiCorp Vault)

**NG-3:** API key rotation mechanisms

**NG-4:** Cost tracking or usage analytics across providers

**NG-5:** Automatic provider failover or load balancing

**NG-6:** Support for providers not supported by LiteLLM

**NG-7:** Configuration validation CLI tool or wizard (defer to future iteration)

**NG-8:** Full note retrieval in query results (only chunk + metadata)

**NG-9:** Web UI for configuration management

**NG-10:** Performance benchmarking across providers (defer to post-implementation)

---

## 6. Design Considerations

### 6.1 Configuration File Examples

**Location:** `configs/` directory at project root

**Ollama Example (`configs/example-ollama.json`):**
```json
{
  "collection_name": "personal_notes",
  "description": "Personal knowledge base with programming tips and tutorials",
  "forceRecreate": false,
  "skipAiValidation": false,
  "chromadb_path": "../chromadb_data",
  "json_file": "../test-data/personal-notes.json",
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest",
      "base_url": "http://localhost:11434",
      "api_key": null
    },
    "llm": {
      "model": "llama3.1:8b",
      "base_url": "http://localhost:11434",
      "api_key": null
    }
  }
}
```

**OpenAI Example (`configs/example-openai.json`):**
```json
{
  "collection_name": "work_notes",
  "description": "Work-related technical notes covering Python, Docker, and cloud infrastructure",
  "forceRecreate": false,
  "skipAiValidation": false,
  "chromadb_path": "../chromadb_data",
  "json_file": "../test-data/work-notes.json",
  "ai_provider": {
    "type": "openai",
    "embedding": {
      "model": "text-embedding-3-small",
      "api_key": "${OPENAI_API_KEY}"
    },
    "llm": {
      "model": "gpt-4o-mini",
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

### 6.2 MCP Server Startup Output

Expected console output when starting MCP server:

```
📋 Loading MCP configuration from config.json...
💾 Connecting to ChromaDB at ../chromadb_data...
✅ ChromaDB connected

🔍 Discovering collections and testing AI provider availability...

📦 Collection: work_notes
   Provider: openai
   Model: text-embedding-3-small
   API Key: ${OPENAI_API_KEY}
   Testing provider availability... ✅ AVAILABLE
   Embedding dimension: 1536

📦 Collection: personal_notes
   Provider: ollama
   Model: mxbai-embed-large:latest
   Testing provider availability... ✅ AVAILABLE
   Embedding dimension: 1024

📦 Collection: old_collection
   ⚠️  UNAVAILABLE: Missing AI provider metadata (created with old pipeline)
   → Re-index this collection with new pipeline to enable

============================================================
📊 Collection Discovery Summary:
   ✅ Available: 2
   ❌ Unavailable: 1
   📦 Total: 3
============================================================

🚀 MCP Server ready with 2 available collection(s)
```

### 6.3 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Execution                        │
│                                                               │
│  Config File → AIProvider → Embeddings → ChromaDB            │
│                     ↓                         ↓               │
│              Test Availability        Store Metadata         │
│                                        (provider config)      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  MCP Server Startup                          │
│                                                               │
│  ChromaDB → Read Metadata → Reconstruct AIProvider           │
│                                      ↓                        │
│                               Test Availability              │
│                                      ↓                        │
│                         Build Available Collections Map      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    MCP Query Flow                            │
│                                                               │
│  Query → Get Provider → Generate Embedding → ChromaDB        │
│                              ↓                                │
│                      Validate Dimension                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Technical Considerations

### 7.1 Dependencies

**New Dependency:**
- `litellm` - Unified interface for 100+ AI providers

**Installation:**
```bash
pip install litellm
```

### 7.2 Embedding Dimension Compatibility

Different models produce different embedding dimensions:

| Provider | Model | Dimensions |
|----------|-------|------------|
| Ollama | mxbai-embed-large | 1024 |
| OpenAI | text-embedding-3-small | 1536 |
| OpenAI | text-embedding-3-large | 3072 |
| Google | text-embedding-004 | 768 |

Each collection stores its embedding dimension in metadata. The MCP server validates dimensions match at query time.

### 7.3 Security Architecture

**API Key Flow:**

1. **Configuration (Template):** `"api_key": "${OPENAI_API_KEY}"`
2. **Metadata Storage (Template):** `"embedding_api_key_ref": "${OPENAI_API_KEY}"`
3. **Runtime (Resolution):** `os.environ.get("OPENAI_API_KEY")`

**What's Safe to Commit:**
- ✅ Config files (contain templates like `${OPENAI_API_KEY}`)
- ✅ Code and scripts
- ❌ Actual API keys
- ❌ `.env` files with secrets

### 7.4 Known Limitations

**Secret Coupling:**
- Pipeline and MCP server must use **same environment variable names**
- Example: If pipeline uses `${OPENAI_API_KEY}`, MCP must have that exact variable
- This is a **naming contract** between pipeline and MCP
- Trade-off accepted for simplicity

**Backward Compatibility:**
- Collections created with old pipeline (without AI metadata) are unavailable
- Users must re-run pipeline to add metadata
- No automatic migration tool

**Re-indexing Required:**
- Changing embedding model requires re-creating the collection
- ChromaDB doesn't support schema migrations for embedding dimensions

### 7.5 File Structure

```
project-root/
├── configs/                              # User-managed config files
│   ├── example-ollama.json
│   ├── example-openai.json
│   └── example-gemini.json
├── markdown-notes-cag-data-creator/
│   ├── ai_provider.py                   # NEW: Abstraction layer
│   ├── embedding.py                     # MODIFIED: Use abstraction
│   ├── storage.py                       # MODIFIED: Accept metadata
│   ├── full_pipeline.py                 # MODIFIED: Config-driven
│   └── ...
├── markdown-notes-mcp-server/
│   ├── config.json                      # MODIFIED: Minimal config
│   ├── mcp_server.py                    # MODIFIED: Dynamic discovery
│   └── ...
└── chromadb_data/                       # Persistent storage
```

---

## 8. Success Metrics

### 8.1 Primary Metric: Provider Diversity

**Target:** Successfully configure and use at least 3 different AI providers (Ollama + 2 cloud providers) across different collections in the same ChromaDB instance.

**Measurement:**
- Create test collections with Ollama, OpenAI, and Gemini
- Verify all collections are available in MCP server
- Execute queries against each collection
- Confirm correct provider is used per collection

**Success Criteria:** All 3 providers work correctly with proper metadata storage and query-time validation.

### 8.2 Secondary Metrics

**SM-1: Configuration Simplicity**
- Developer can create a valid config file in < 5 minutes
- Config validation catches errors before processing starts

**SM-2: Error Clarity**
- Missing API key error messages clearly state which variable to set
- Dimension mismatch errors explain the incompatibility

**SM-3: Reliability**
- Unit test coverage ≥ 80% for `ai_provider.py`
- Integration tests pass with Ollama (no failures)

**SM-4: Security**
- Zero API keys found in config files (only templates)
- Zero API keys found in ChromaDB metadata (only references)

---

## 9. Open Questions

**OQ-1:** Should we provide a config validation script (`validate_config.py`) to check configs before running the pipeline?
- **Context:** Would catch config errors early
- **Trade-off:** Adds development time but improves UX

**OQ-2:** Should the MCP server support hot-reloading when collections change?
- **Context:** Currently requires restart to discover new collections
- **Trade-off:** Complex implementation vs. rare use case

**OQ-3:** Should we log embedding generation costs for cloud providers?
- **Context:** Would help users track API usage
- **Trade-off:** Requires provider-specific cost calculation

**OQ-4:** Should dimension validation happen during pipeline execution (early warning)?
- **Context:** Currently only validated at query time
- **Trade-off:** More robust but adds complexity

**OQ-5:** Should we support multiple API keys for the same provider (e.g., different OpenAI accounts)?
- **Context:** Would allow per-collection billing separation
- **Trade-off:** More complex configuration schema

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1)
- Create `ai_provider.py` with `AIProvider` and `AIProviderConfig` classes
- Implement environment variable resolution
- Add LiteLLM dependency
- Write unit tests for `ai_provider.py`
- Create example configuration files

**Acceptance:** `ai_provider.py` works with Ollama, tests pass

### Phase 2: Pipeline Integration (Week 2)
- Refactor `embedding.py` to use abstraction
- Update `storage.py` to accept metadata
- Update `full_pipeline.py` for config-driven execution
- Test metadata flow: config → ChromaDB

**Acceptance:** Pipeline creates collections with AI metadata, Ollama works end-to-end

### Phase 3: MCP Server (Week 3)
- Implement dynamic collection discovery
- Add provider loading from metadata
- Update query flow to use collection-specific providers
- Test with multiple collections using different providers

**Acceptance:** MCP server discovers collections, queries work with correct providers

### Phase 4: Testing & Documentation (Week 4)
- Complete integration tests
- Test multi-provider scenarios (Ollama + OpenAI + Gemini)
- Write user guide for creating configs
- Write troubleshooting guide
- Update CLAUDE.md with new usage patterns

**Acceptance:** All tests pass, documentation complete, multi-provider demo works

---

## 11. Appendix: Example User Workflows

### Workflow 1: Create Collection with Ollama (Local)

```bash
# No API keys needed
cd markdown-notes-cag-data-creator

# Run pipeline with Ollama config
python full_pipeline.py --config configs/personal-ollama.json --verbose

# Output:
# 🤖 Initializing AI provider...
# ✅ Provider ready: ollama
#    Embedding model: mxbai-embed-large:latest
#    Embedding dimension: 1024
# ... (processing continues)
```

### Workflow 2: Create Collection with OpenAI

```bash
# Set API key first
export OPENAI_API_KEY="sk-proj-..."

cd markdown-notes-cag-data-creator

# Run pipeline with OpenAI config
python full_pipeline.py --config configs/work-openai.json --verbose

# Output:
# 🤖 Initializing AI provider...
# ✅ Provider ready: openai
#    Embedding model: text-embedding-3-small
#    Embedding dimension: 1536
# ... (processing continues)
```

### Workflow 3: Start MCP Server with Multiple Providers

```bash
# Set required API keys
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."

# Start MCP server
cd markdown-notes-mcp-server
python mcp_server.py

# Output shows all collections:
# 📦 Collection: work_notes (openai) ✅ AVAILABLE
# 📦 Collection: research_notes (gemini) ✅ AVAILABLE
# 📦 Collection: personal_notes (ollama) ✅ AVAILABLE
# 🚀 MCP Server ready with 3 available collection(s)
```

### Workflow 4: Troubleshoot Missing API Key

```bash
# Don't set GEMINI_API_KEY

cd markdown-notes-mcp-server
python mcp_server.py

# Output:
# 📦 Collection: research_notes
#    Provider: gemini
#    Model: text-embedding-004
#    API Key: ${GEMINI_API_KEY}
#    Testing provider availability... ❌ UNAVAILABLE
#    Reason: Environment variable 'GEMINI_API_KEY' not set
#
# ⚠️  Warning: 1 collection unavailable (research_notes)
# 🚀 MCP Server ready with 2 available collection(s)
```

---

## 12. Acceptance Criteria Summary

**AC-1:** Developer can create pipeline config for Ollama, OpenAI, and Gemini using provided examples

**AC-2:** Pipeline successfully creates collections with AI provider metadata stored in ChromaDB

**AC-3:** MCP server discovers all collections and correctly identifies available vs. unavailable based on API key availability

**AC-4:** MCP server logs clear status for each collection (provider, model, availability, reason if unavailable)

**AC-5:** Queries against available collections use the correct AI provider per collection

**AC-6:** Embedding dimension mismatches are detected and blocked with clear error messages

**AC-7:** API keys are never stored in files or ChromaDB (only environment variable references)

**AC-8:** Unit tests for `ai_provider.py` achieve ≥80% coverage and pass

**AC-9:** Integration tests verify metadata flow and multi-provider scenarios

**AC-10:** User guide and troubleshooting guide are complete and accurate

**AC-11:** Collections created with old pipeline (no metadata) are marked unavailable with clear guidance

**AC-12:** Description validation works when enabled, provides score and feedback

---

**End of PRD**
