## Relevant Files

- `minerva/common/ai_provider.py` - Core provider abstraction that needs LM Studio support and rate limiting.
- `minerva/common/ai_config.py` - Provider config dataclass to be updated for new schema fields and validation.
- `minerva/common/config_loader.py` - New or existing module to centralize unified config parsing and validation.
- `requirements.txt` - Project dependencies including HTTP client support.
- `setup.py` - Package metadata and install requirements to align with runtime needs.
- `minerva/chat/chat_engine.py` - Chat workflow to refactor around MCP interactions, streaming fallback, and history updates.
- `minerva/chat/config.py` - Chat runtime config builder sourced from unified configuration.
- `minerva/commands/config.py` - CLI entrypoint for unified config validation utilities.
- `minerva/chat/history.py` - Conversation persistence/compression updates triggered by new requirements.
- `minerva/chat/mcp_client.py` - New module encapsulating FastMCP client usage, tool execution, and fallbacks.
- `minerva/chat/commands.py` - CLI entrypoint to enforce `--config` usage and integrate new loader.
- `minerva/commands/index.py` - CLI index command to resolve provider IDs from unified config.
- `minerva/commands/serve.py` - MCP server command to load shared config and provider definitions.
- `minerva/indexing/embeddings.py` - Indexing entrypoint that boots providers for embedding generation.
- `minerva/server/collection_discovery.py` - Server-side helper to restore providers from stored metadata.
- `tasks/prd-lmstudio-integration-and-mcp-chat.md` - Source PRD for cross-reference during implementation.
- `docs/LMSTUDIO_SETUP.md` - Needs expansion to cover new guidance and rate limits.
- `docs/configuration.md` - New doc describing unified config schema and examples.
- `CLAUDE.md` - Documentation updates reflecting architecture changes.
- `README.md` - High-level setup instructions for LM Studio and unified config.
- `tests/test_ai_provider.py` - Unit tests for provider behavior, including LM Studio and rate limiting.
- `tests/test_chat_engine.py` - Tests for chat loop, streaming fallback, and history compression.
- `configs/desktop-lmstudio.json` - Sample unified config for all-LM Studio desktop workflow.
- `configs/hybrid-ollama-lmstudio.json` - Sample unified config mixing Ollama indexing and LM Studio chat.
- `configs/server-ollama.json` - Sample server-focused unified config for Ollama deployments.
- `tests/test_unified_config_loader.py` - Tests covering unified config parsing/validation.
- `tests/test_chat_config.py` - Tests for chat runtime config built from unified config.
- `tests/test_mcp_chat_integration.py` - Integration tests for MCP chat workflow.

### Notes

- Unit tests should typically be placed alongside the code files they are testing when feasible.
- Use `pytest [optional/test/path]` to run relevant suites; running without a path executes all configured tests.

## Tasks

- [x] 1.0 Implement LM Studio provider support and rate-limited AI provider abstraction enhancements
  - [x] 1.1 Extend `AIProviderConfig` and related schema to allow LM Studio-specific fields and rate-limit metadata.
  - [x] 1.2 Implement `LMStudioProvider` (or extend existing provider logic) to call LM Studio’s OpenAI-compatible endpoints.
  - [x] 1.3 Add optional rate limiting (requests/minute and concurrency) enforced in `AIProvider` before network calls.
  - [x] 1.4 Update provider factory/registration to recognize LM Studio configurations by `provider_type`.
  - [x] 1.5 Write unit tests covering LM Studio embeddings/chat plus rate-limit edge cases.

- [x] 2.0 Build the unified configuration system and shared loader across CLI commands
  - [x] 2.1 Design JSON Schema representing `ai_providers`, `indexing`, `chat`, and `server` sections.
  - [x] 2.2 Implement a config loader that reads a user-supplied file (`--config`), validates it, and resolves provider IDs.
  - [x] 2.3 Update CLI commands (`index`, `serve`, `chat`, etc.) to require `--config` and consume the shared loader outputs.
  - [x] 2.4 Add `minerva config validate` command to run schema validation and produce actionable error messages.
  - [x] 2.5 Provide sample configs (desktop, hybrid, server) aligned with the unified schema.
  - [x] 2.6 Create automated tests for config validation, including invalid and edge-case scenarios.

- [ ] 3.0 Refactor the chat command onto MCP, including streaming fallback, tool handling, and history compression updates
  - [ ] 3.1 Introduce an MCP client wrapper to manage FastMCP connections, tool definitions, and result ingestion.
  - [ ] 3.2 Update `ChatEngine` to fetch tool definitions from MCP, combine multi-content responses, and log progress.
  - [ ] 3.3 Implement streaming fallback logic: detect incompatibilities and downgrade to non-streaming with user warning.
  - [ ] 3.4 Enhance conversation history compression to summarize large tool responses per PRD guidance.
  - [ ] 3.5 Ensure chat respects max tool iterations and surfaces clear errors when MCP/LM Studio are unreachable.
  - [ ] 3.6 Update chat CLI UX for connection banners, slash commands (`/help`, `/clear`, `/exit`), and resume support.
  - [ ] 3.7 Add integration tests simulating tool calls via a mock MCP server.

- [ ] 4.0 Update documentation and examples for LM Studio setup, unified config, and deployment patterns
  - [ ] 4.1 Expand `docs/LMSTUDIO_SETUP.md` with installation, model selection, rate limiting, and server startup instructions.
  - [ ] 4.2 Author `docs/configuration.md` describing the unified schema, API key handling, and sample configs.
  - [ ] 4.3 Refresh `README.md` and `CLAUDE.md` to highlight LM Studio workflows, MCP architecture, and new CLI usage.
  - [ ] 4.4 Document deployment patterns (all LM Studio, hybrid, server/client) with concrete config examples.
  - [ ] 4.5 Remove or rewrite legacy per-command config references in docs and scripts.

- [ ] 5.0 Expand automated testing and validation for providers, MCP chat flow, and configuration schema
  - [ ] 5.1 Add provider unit tests (LM Studio + rate limiting) and ensure they run in CI.
  - [ ] 5.2 Create integration tests for chat/MCP interactions, including streaming fallback scenarios.
  - [ ] 5.3 Configure CI to run `minerva config validate` against bundled sample configs.
  - [ ] 5.4 Remove manual test scripts (`test-qwen-mcp-chat.py`, `test-qwen-tools.pt`) and QWEN*.md docs
  - [ ] 5.5 Ensure documentation references automated test commands for quick verification.
