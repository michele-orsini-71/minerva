# PRD: LM Studio Integration & MCP-Based Chat Architecture

## Introduction/Overview

Currently, Minerva supports Ollama as the primary AI provider for embeddings (indexing) and chat. However, Ollama's tool calling implementation is unreliable—it produces malformed JSON, enters infinite loops, and cannot properly orchestrate multi-step search operations. This makes the `minerva chat` command unusable in practice.

Through testing, we've discovered that **LM Studio** with Qwen 2.5 models provides reliable tool calling and can serve as both an embedding provider and chat orchestrator. Additionally, LM Studio exposes an OpenAI-compatible API, supports headless operation, and can run on both desktop and server environments.

This feature will:

1. Add **LM Studio as a first-class provider** alongside Ollama for all operations (embeddings, chat)
2. **Refactor the chat architecture** to use the MCP (Model Context Protocol) for all search operations
3. Provide a **unified configuration** that drives indexing, serving, and chat
4. Maintain **clear separation of concerns**: Chat orchestration (LM Studio) ↔ MCP Server (provider-agnostic) ↔ Search backend (Ollama or LM Studio)

**Problem Solved:** Users will be able to have functional, reliable chat with their knowledge bases using local AI models, while maintaining flexibility in provider choice for different components.

---

## Goals

1. **Add LM Studio provider support** for embeddings generation and chat operations
2. **Refactor chat to always use MCP** for search operations (clean separation)
3. **Eliminate tool calling issues** by using LM Studio for chat orchestration
4. **Maintain provider abstraction** so users can mix-and-match (e.g., Ollama indexes + LM Studio chat)
5. **Consolidate configuration** into a single schema-driven file that serves all commands
6. **Improve conversation history management** to handle large JSON responses from MCP
7. **Document deployment patterns** for single-user (desktop) and multi-user (server) scenarios

---

## User Stories

### Single User (Desktop)

**As a** desktop user who wants everything local and private,
**I want** to install only LM Studio and use it for both indexing and chat,
**So that** I have a simpler setup with one system instead of two.

### Power User (Hybrid Setup)

**As a** user who already has Ollama indexes,
**I want** to keep using my existing indexes via MCP server while using LM Studio for chat,
**So that** I don't need to re-index everything but can still have working chat.

### System Administrator (Multi-user Server)

**As a** sysadmin deploying for multiple users,
**I want** to run Ollama on the server for embeddings/MCP and let clients use LM Studio for chat,
**So that** I have a secure, stable server backend with flexible client options.

### Developer

**As a** developer extending Minerva,
**I want** a clean provider abstraction with consistent interfaces,
**So that** I can add new providers (e.g., vLLM, llama.cpp) easily in the future.

---

## Functional Requirements

### 1. Provider Abstraction Enhancement

**FR-1.1:** The `AIProvider` class must support a new provider type: `"lmstudio"`

**FR-1.2:** LM Studio provider must implement:

- `generate_embeddings(texts)` using `/v1/embeddings` endpoint
- `chat_completion(messages, tools, temperature, stream)` using `/v1/chat/completions`
- `chat_completion_streaming(...)` for streaming responses
- `check_availability()` to verify LM Studio server is running

**FR-1.3:** LM Studio providers must be defined in `ai_providers[]` with an `id`, `provider_type`, `base_url`, optional `embedding_model`, `llm_model`, and optional `rate_limit` block.

**FR-1.4:** All existing commands (`minerva index`, `minerva serve`) must work with LM Studio provider with no code changes except provider implementation

**FR-1.5:** Providers must honor optional `rate_limit` settings (requests_per_minute, concurrency) before dispatching network calls

### 2. MCP-Based Chat Architecture

**FR-2.1:** The chat command must ALWAYS connect to an MCP server for search operations (no direct ChromaDB access)

**FR-2.2:** Chat must use FastMCP Client library to communicate with MCP server over HTTP

**FR-2.3:** Chat must handle FastMCP's content structure correctly:

- When MCP returns multiple content items (array elements), parse ALL items, not just the first
- Combine multiple content items into a single list/array before passing to LLM
- Example: `list_knowledge_bases` returns 6 content items → combine into array of 6 collections

**FR-2.4:** Chat configuration (within the unified file) must reference the provider via `chat_provider_id` and include `mcp_server_url`, `conversation_dir`, `enable_streaming`, and `max_tool_iterations`.

**FR-2.5:** Tool definitions must match MCP server's tools exactly:

- `list_knowledge_bases()` → no parameters
- `search_knowledge_base(query, collection_name, max_results, context_mode)` → required: query, collection_name

**FR-2.6:** Chat must handle MCP connection failures gracefully:

- Check MCP server availability on startup
- Provide clear error message if MCP server not running
- Suggest command to start MCP server

**FR-2.7:** Streaming is disabled by default; when enabled, the client must detect incompatibilities and automatically downgrade to non-streaming with a user-facing warning

### 3. Conversation History Management

**FR-3.1:** Chat must maintain conversation history for context continuity

**FR-3.2:** Tool result compression:

- When tool returns large JSON responses (>2000 chars), compress the tool result in history
- Keep first N results in full, summarize rest as count
- Example: "5 search results returned, showing top 3 in detail, 2 more available"

**FR-3.3:** History must include:

- System prompt (not part of saved history)
- User messages
- Assistant messages (including tool_calls field when tools used)
- Tool results (compressed as per FR-3.2)

**FR-3.4:** Conversation history must be saved to disk automatically in JSON format

**FR-3.5:** Users must be able to resume previous conversations with `--resume CONVERSATION_ID`

### 4. Chat User Interface

**FR-4.1:** Chat must display tool execution progress:

```
🔍 Calling search_knowledge_base(query="Python", collection="notes")
✓ Found 5 results
```

**FR-4.2:** Chat must support these commands during conversation:

- `/help` - Show help
- `/clear` - Start new conversation (saves current)
- `/exit` or `exit` or `quit` - Exit (saves conversation)

**FR-4.3:** Chat must show connection status on startup:

```
🔌 Connecting to LM Studio...
✓ Connected (model: qwen2.5-14b-instruct-mlx)

🔌 Connecting to Minerva MCP server...
✓ Connected (6 collections available)
```

**FR-4.4:** Chat must prevent infinite tool calling loops:

- Maximum 5 iterations per user query
- If max reached, return partial response with warning

### 5. Documentation & Setup

**FR-5.1:** Add comprehensive LM Studio setup guide:

- Installation instructions (macOS, Linux, Windows)
- How to download models via GUI or CLI
- How to start server (GUI and `lms server start`)
- Recommended models for different hardware specs

**FR-5.2:** Document three deployment patterns:

- **Pattern A**: All LM Studio (single user, desktop)
- **Pattern B**: Ollama indexes + LM Studio chat (hybrid)
- **Pattern C**: Ollama server + LM Studio clients (multi-user)

**FR-5.3:** Update `CLAUDE.md` with:

- LM Studio provider configuration examples
- MCP-based chat architecture diagram
- Troubleshooting guide for common issues

**FR-5.4:** Update documentation to remove references to legacy per-command configs and show how to author the unified file manually

**FR-5.5:** Ship JSON Schema + `minerva config validate` command, with docs describing schema fields and API key handling practices

### 6. Testing

**FR-6.1:** Unit tests for LM Studio provider:

- Embeddings generation
- Chat completion (with/without tools)
- Availability checking
- Error handling

**FR-6.2:** Integration test for MCP chat workflow:

- Start mock MCP server
- Simulate chat with tool calling
- Verify tool results properly parsed
- Verify conversation history maintained

**FR-6.3:** Manual test script (like `test-qwen-mcp-chat.py`) must be preserved as example

---

## Non-Goals (Out of Scope)

1. **Removing Ollama support** - Ollama remains a supported provider for indexing and MCP server
2. **GUI for LM Studio** - We integrate with LM Studio's existing GUI, not building our own
3. **Cloud provider migration** - OpenAI/Gemini providers remain separate concern
4. **Advanced history management** - Smart compression, summarization, token counting (deferred to future phase)
5. **Model fine-tuning** - Using pre-trained models as-is
6. **Multi-modal support** - Text-only for this phase
7. **Distributed MCP servers** - Single MCP server per setup
8. **Authentication/authorization** - Not adding auth to MCP or LM Studio connections

---

## Technical Considerations

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MINERVA CHAT COMMAND                     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         LM Studio (Chat Orchestration)                │ │
│  │  - Decides when to search vs. respond                 │ │
│  │  - Handles tool calling                               │ │
│  │  - Generates final responses                          │ │
│  └────────────────────┬──────────────────────────────────┘ │
│                       │                                     │
│                       │ Tool Calls                          │
│                       ↓                                     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           FastMCP Client (HTTP)                       │ │
│  │  - Connects to MCP server                             │ │
│  │  - Calls list_knowledge_bases, search_knowledge_base │ │
│  │  - Parses content items correctly                     │ │
│  └────────────────────┬──────────────────────────────────┘ │
└─────────────────────────┼──────────────────────────────────┘
                         │ HTTP
                         ↓
         ┌───────────────────────────────────┐
         │      MINERVA MCP SERVER           │
         │  (minerva serve-http)             │
         │                                   │
         │  - Provider-agnostic              │
         │  - Can use Ollama OR LM Studio    │
         │  - Exposes search tools           │
         └────────────┬──────────────────────┘
                      │
                      ↓
         ┌───────────────────────────────────┐
         │      ChromaDB + AI Provider       │
         │                                   │
         │  - Ollama (embeddings)            │
         │  OR                               │
         │  - LM Studio (embeddings)         │
         └───────────────────────────────────┘
```

### Key Design Decisions

**1. Why MCP for all providers?**

- Clean separation: Chat doesn't know about ChromaDB
- Easier testing: Mock MCP server for tests
- Flexible: Can swap backend without changing chat
- Protocol-driven: MCP is standardized

**2. Why FastMCP specifically?**

- Official Python client for MCP
- Handles HTTP transport (streamable-http)
- Returns structured ToolResult objects
- Actively maintained

**3. Content item handling**

- MCP returns arrays as multiple content items (not one JSON array)
- Must loop through ALL content items and combine
- Critical for `list_knowledge_bases` returning multiple collections

**4. Provider choice flexibility**

- Indexing provider (config): User's choice
- MCP server provider (config): User's choice
- Chat orchestration (chat config): Separate choice
- Example: Ollama indexes → Ollama MCP → LM Studio chat

### Dependencies

- `fastmcp>=2.11.2` (already installed)
- `openai>=1.101.0` (already installed, for LM Studio client)
- LM Studio application (user installs separately)
- No new Python dependencies needed

### File Changes Overview

**New Files:**

- `minerva/providers/lmstudio_provider.py` - LM Studio provider implementation
- `tasks/prd-lmstudio-integration-and-mcp-chat.md` - This PRD
- `docs/LMSTUDIO_SETUP.md` - Setup guide
- `docs/DEPLOYMENT_PATTERNS.md` - Three deployment patterns

**Modified Files:**

- `minerva/common/ai_provider.py` - Add LM Studio provider type
- `minerva/chat/chat_engine.py` - Refactor to use MCP client
- `minerva/chat/config.py` - Add MCP server URL config
- `minerva/chat/tools.py` - Remove (replaced by MCP client)
- `CLAUDE.md` - Update with new architecture
- `README.md` - Add LM Studio as option

**Test Files:**

- Keep `test-qwen-mcp-chat.py` as example
- Add unit tests for LM Studio provider
- Add integration test for MCP chat

---

## Design Considerations

### Configuration

- Ship a single shared config file that every subcommand loads via `--config`.
- Top-level keys: `ai_providers`, `indexing`, `chat`, and `server`.
- Provide JSON Schema + `minerva config validate` to catch errors before commands run.

**Schema highlights:**

```json
{
  "ai_providers": [
    {
      "id": "lm-studio-qwen",
      "provider_type": "lmstudio",
      "base_url": "http://localhost:1234/v1",
      "embedding_model": "qwen2.5-7b-instruct-mlx",
      "llm_model": "qwen2.5-14b-instruct-mlx",
      "rate_limit": { "requests_per_minute": 60, "concurrency": 1 }
    },
    {
      "id": "ollama-default",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434",
      "embedding_model": { "model": "mxbai-embed-large:latest" },
      "llm_model": { "model": "llama3.1:8b" }
    }
  ],
  "indexing": {
    "collections": [
      {
        "collection_name": "my-personal-notes",
        "description": "Personal notes...",
        "json_file": "./test-data/Bear Notes.json",
        "force_recreate": true,
        "ai_provider_id": "ollama-default"
      }
    ]
  },
  "chat": {
    "mcp_server_url": "http://localhost:8000/mcp",
    "chat_provider_id": "lm-studio-qwen",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "/Users/michele/my-code/minerva/chromadb_data",
    "default_max_results": 5
  }
}
```

**Command behavior:**

- Users supply the unified config explicitly (e.g., `minerva index --config /path/to/config.json`).
- `minerva index` resolves `ai_provider_id` for each collection at runtime.
- `minerva serve` reads `server` + relevant provider definitions when exposing MCP tools.
- `minerva chat` loads `chat_provider_id`, rate-limiting policy, and streaming flag.

Documentation (new `docs/configuration.md`) explains the schema, shows end-to-end examples, and notes how API keys should be stored safely within the file.

### Error Messages

**LM Studio not running:**

```
❌ Cannot connect to LM Studio
   Ensure LM Studio is running with server started.

   Desktop: Open LM Studio → Developer tab → Start Server
   CLI: lms server start

   Expected URL: http://localhost:1234
```

**MCP server not running:**

```
❌ Cannot connect to Minerva MCP server at http://localhost:8000/mcp
   Start it with: minerva serve-http --config /path/to/config.json --port 8000
```

**Wrong model loaded:**

```
⚠️  Warning: Expected model 'qwen2.5-14b-instruct-mlx' but found 'qwen2.5-7b-instruct-mlx'
   The chat will continue but may have reduced quality.

   To load correct model: lms load qwen2.5-14b-instruct-mlx
```

---

## Success Metrics

1. **Tool calling reliability**: 90%+ success rate on test queries (up from ~0% with Ollama)
2. **User setup time**: Single-user setup completes in <30 minutes
3. **Collection listing accuracy**: 100% of collections shown (not just first one)
4. **Search result quality**: Relevant results returned with proper citations
5. **Zero infinite loops**: Max iterations prevents runaway tool calling
6. **Config validation coverage**: Sample configs (desktop, hybrid, server) pass `minerva config validate` in CI

---

## Decisions & Resolved Questions

### Provider Configuration Strategy

- Adopt a single shared config file that every command references explicitly; per-command config files are removed.
- Providers live in `ai_providers[]` and are referenced via `ai_provider_id`/`chat_provider_id`, enabling hybrid setups without duplicating credentials.
- Shared values (e.g., `chromadb_path`) reside once under `server` and are imported where needed.
- Users manage API keys directly in the unified config; no profile or layered override system is planned.
- Ship JSON Schema + `minerva config validate` to ensure changes in one section cannot silently break other commands.

### Streaming & Tool Results

- FastMCP streaming works with LM Studio; default `enable_streaming` to `false` and document how to toggle it.
- Detect streaming incompatibilities (e.g., Ollama) and automatically fall back to non-streaming mode with a warning so users do not need to edit config mid-session.

### Rate Limiting

- Add optional per-provider `rate_limit` config (requests_per_minute + concurrency) enforced by a lightweight token bucket to avoid overwhelming LM Studio.
- Provide conservative defaults for LM Studio; Ollama defaults remain unlimited unless specified.

### Model Quantization Guidance

- Do not prescribe quantization levels; instead link to LM Studio documentation for users who want to tune memory/performance trade-offs.

### Multi-model Conversations

- Chat sessions use a single model; switching requires starting a new conversation or loading a different config file.

### Telemetry

- No anonymous usage or telemetry collection is planned for this phase.

---

## Implementation Phases

### Phase 1: LM Studio Provider (Week 1)

- Implement `LMStudioProvider` class
- Add provider type to `AIProviderConfig`
- Unit tests for embeddings and chat
- Verify existing `minerva index` works with LM Studio

### Phase 2: MCP Chat Refactor (Week 2)

- Refactor `ChatEngine` to use FastMCP Client
- Fix content item parsing (combine multiple items)
- Implement conversation history compression
- Add connection checks and error handling

### Phase 3: Unified Configuration & UX (Week 3)

- Implement shared config loader that resolves provider IDs across commands
- Require explicit `--config` usage across CLI commands and update help text
- Ship JSON Schema + `minerva config validate`
- Add chat commands (/help, /clear, /exit) and improve tool execution progress display
- Expand error messages to reference unified config paths

### Phase 4: Testing & Documentation (Week 4)

- Write unit and integration tests (including config validation + rate limiting)
- Create LM Studio setup guide
- Document three deployment patterns
- Update CLAUDE.md and README.md
- Add CI job that lint-checks sample configs with `minerva config validate`

### Phase 5: Polish & Release (Week 5)

- Convert existing test fixtures to the unified config format and remove legacy samples
- Add troubleshooting section to docs (streaming fallbacks, rate limits)
- Manual testing with real knowledge bases
- Prepare release notes highlighting configuration changes

---

## Notes for Junior Developer

### Understanding the Architecture

Think of it like a restaurant:

- **LM Studio** = The chef (decides what to cook, orchestrates)
- **MCP Server** = The kitchen (has the ingredients, does the work)
- **ChromaDB** = The pantry (stores the actual data)

The chef doesn't go to the pantry directly—they ask the kitchen (MCP) for ingredients (search results), and the kitchen handles the details.

### Key Concepts

**MCP (Model Context Protocol):**

- Standardized way for AI to call tools
- Like REST API but specifically for AI assistants
- Returns structured `ToolResult` objects

**FastMCP:**

- Python library for MCP clients
- Handles HTTP transport and protocol details
- Returns `CallToolResult` with `content` list

**Tool Calling:**

- AI model decides when to use tools (like search)
- Model outputs JSON: `{"name": "search_knowledge_base", "arguments": {"query": "..."}}`
- We execute the tool via MCP
- Feed results back to model
- Model generates final response

**Provider Abstraction:**

- Different AI services (Ollama, LM Studio) have different APIs
- We wrap them in a common interface (`AIProvider`)
- Rest of code doesn't care which provider is used

### Common Pitfalls

1. **FastMCP content items**: When MCP returns an array, it's split into multiple content items. Always loop through ALL items!

2. **Async/await**: FastMCP is async. Use `async with` for client connection:

   ```python
   async with client:
       result = await client.call_tool(...)
   ```

3. **JSON serialization**: Tool results must be JSON-serializable for the LLM. Use `json.dumps()` before adding to messages.

4. **History management**: Large tool results can fill context. Compress them but keep enough info for LLM to understand.

### Where to Start

1. Read `test-qwen-mcp-chat.py` - it's a working prototype of the final architecture
2. Look at existing `AIProvider` class to understand the interface
3. Study `chat_engine.py` to see current implementation
4. Start with Phase 1 (LM Studio provider) - it's self-contained

---

**End of PRD**

_This document should be reviewed and approved before implementation begins. The "To Review/TBD" section must be resolved first._
