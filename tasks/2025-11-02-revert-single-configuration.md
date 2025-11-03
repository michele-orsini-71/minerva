# PRD: Revert to Command-Specific Configuration System

**Created:** 2025-11-02
**Status:** Draft
**Priority:** High
**Target Release:** v3.0

---

## Introduction/Overview

Minerva currently uses a "unified configuration" system where a single JSON file contains configuration for all commands (index, chat, serve). This design has a critical flaw: the index command can only process ONE collection per run, despite the unified config supporting multiple collections. This defeats the purpose of having a unified configuration and creates unnecessary complexity.

**Problem:** Users must either:

- Create separate unified config files for each collection (defeating "unified" purpose)
- Edit the same unified config file repeatedly to index different collections
- Define all settings (AI providers, chat, server) even when only indexing

**Solution:** Revert to simple, command-specific configuration files where each config serves exactly one purpose.

---

## Goals

1. **Simplify Configuration:** Each config file has a single, clear purpose
2. **Enable Efficient Indexing:** Index multiple collections without editing configs
3. **Reduce Cognitive Load:** Users only configure what they need for each command
4. **Improve Maintainability:** Smaller, focused config files are easier to manage
5. **Better Modularity:** Mix and match configs freely (e.g., same server config, different chat configs)

---

## User Stories

### Story 1: Indexing Multiple Collections

**As a** knowledge worker with multiple note sources
**I want to** index each source with a dedicated config file
**So that** I can run `minerva index --config bear.json` and `minerva index --config wiki.json` without editing files

### Story 2: Sharing Configurations

**As a** team member
**I want to** share my index config for our team knowledge base
**So that** others can index the same data without seeing my personal chat/server settings

### Story 3: Simple Server Deployment

**As a** system administrator
**I want to** configure just the MCP server
**So that** I don't need to define indexing or chat settings I'm not using

### Story 4: Personal Chat Setup

**As a** developer using Minerva
**I want to** configure my preferred AI model for chat
**So that** I can switch between local LM Studio and Ollama without touching server configs

---

## Functional Requirements

### FR1: Index Command Configuration

1.1. Index command MUST accept a simple JSON config file via `--config` flag
1.2. Config MUST include: `collection_name`, `description`, `json_file`, `chromadb_path`
1.3. Config MUST include inline provider definition: `provider.type`, `provider.embedding_model`, `provider.llm_model`
1.4. Config MAY include: `chunk_size` (default: 1200), `force_recreate` (default: false), `skip_ai_validation` (default: false)
1.5. Provider settings MUST be embedded directly in config (no external references)
1.6. Index command MUST validate config on load and fail fast with clear error messages

### FR2: Chat Command Configuration

2.1. Chat command MUST accept a simple JSON config file via `--config` flag
2.2. Config MUST include: inline provider definition, `mcp_server_url`, `conversation_dir`
2.3. Config MAY include: `enable_streaming`, `max_tool_iterations`, `system_prompt_file`
2.4. Provider MUST be embedded inline (type, model, base_url, api_key)
2.5. Chat command MUST validate config on load

### FR3: Serve Command Configuration

3.1. Serve command MUST accept a simple JSON config file via `--config` flag
3.2. Config MUST include: `chromadb_path`, `default_max_results`
3.3. Config MAY include: `host`, `port` (for serve-http)
3.4. Serve command MUST validate config on load

### FR4: Remove Unified Config System

4.1. Delete `minerva/common/config_loader.py` (634 lines)
4.2. Remove all `UnifiedConfig`, `ProviderDefinition`, and related classes
4.3. Remove `minerva config validate` command entirely
4.4. Remove all imports and references to unified config across codebase

### FR5: Sample Configurations

5.1. Provide sample index configs: `configs/index/bear-notes-ollama.json`, `configs/index/wikipedia-lmstudio.json`
5.2. Provide sample chat configs: `configs/chat/ollama.json`, `configs/chat/lmstudio.json`, `configs/chat/openai.json`
5.3. Provide sample server configs: `configs/server/local.json`, `configs/server/network.json`
5.4. Each sample MUST include inline comments explaining settings
5.5. Delete existing unified configs: `configs/desktop-lmstudio.json`, `configs/hybrid-ollama-lmstudio.json`, `configs/server-ollama.json`

### FR6: Test Suite Updates

6.1. Rewrite `tests/test_index_command.py` to use simple index configs
6.2. Rewrite `tests/test_chat_config.py` to use simple chat configs
6.3. Delete `tests/test_unified_config_loader.py` entirely
6.4. Update all test fixtures to use command-specific configs
6.5. All existing tests MUST pass with new config system

### FR7: Documentation Updates

7.1. Update `CLAUDE.md`: Remove unified config section, add command-specific config examples
7.2. Update `README.md`: Remove unified config from features, update all examples
7.3. Rewrite `docs/configuration.md` as comprehensive guide to command-specific configs
7.4. Update CLI help text in `minerva/cli.py` with new config examples
7.5. All documentation MUST accurately reflect new system

### FR8: CI/CD Updates

8.1. Update `.github/workflows/ci.yml` to validate new sample configs
8.2. Remove unified config validation from CI pipeline
8.3. All CI tests MUST pass with new system

---

## Non-Goals (Out of Scope)

**NG1:** Backward compatibility with unified configs (no users exist)
**NG2:** Migration tools or scripts (not needed)
**NG3:** External provider definition files (inline only for simplicity)
**NG4:** Config validation command (simple schemas validate on load)
**NG5:** Support for referencing providers by ID across configs
**NG6:** Preserving the unified config system in any form

---

## Design Considerations

### Index Config Schema Example

```json
{
  "collection_name": "bear_notes",
  "description": "Personal notes from Bear app with tags and timestamps",
  "json_file": "./data/bear-notes.json",
  "chromadb_path": "./chromadb_data",
  "chunk_size": 1200,
  "force_recreate": false,
  "skip_ai_validation": false,
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
```

### Chat Config Schema Example

```json
{
  "provider": {
    "provider_type": "lmstudio",
    "base_url": "http://localhost:1234/v1",
    "model": "qwen2.5-14b-instruct",
    "rate_limit": {
      "requests_per_minute": 60,
      "concurrency": 1
    }
  },
  "mcp_server_url": "http://localhost:8000/mcp",
  "conversation_dir": "~/.minerva/conversations",
  "enable_streaming": false,
  "max_tool_iterations": 5
}
```

### Server Config Schema Example

```json
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5,
  "host": "127.0.0.1",
  "port": 8000
}
```

---

## Technical Considerations

### Implementation Files to Create

- `minerva/common/index_config.py` - Index config loader and schema
- `minerva/common/chat_config_loader.py` - Chat config loader and schema
- `minerva/common/server_config.py` - Server config loader and schema

### Files to Modify

- `minerva/commands/index.py` - Use new index config loader
- `minerva/commands/chat.py` - Use new chat config loader
- `minerva/commands/serve.py` - Use new server config loader
- `minerva/commands/serve_http.py` - Use new server config loader
- `minerva/chat/config.py` - Build ChatConfig from simple config
- `minerva/server/mcp_server.py` - Load simple server config
- `minerva/cli.py` - Update help text and examples

### Files to Delete

- `minerva/common/config_loader.py` (634 lines)
- `minerva/commands/config.py` (47 lines)
- `tests/test_unified_config_loader.py` (113 lines)
- `configs/desktop-lmstudio.json`
- `configs/hybrid-ollama-lmstudio.json`
- `configs/server-ollama.json`

### Dependencies

- No new external dependencies required
- All existing validation libraries (jsonschema) remain useful
- Existing AIProvider system unchanged, just initialized differently

---

## Success Metrics

**SM1:** All commands use simple, focused config files
**SM2:** Zero references to "unified config" in codebase or documentation
**SM3:** All 518+ existing tests pass with new config system
**SM4:** Sample configs provided for all common use cases
**SM5:** Documentation accurately reflects new system with working examples
**SM6:** CI/CD pipeline validates all sample configs successfully
**SM7:** Net code reduction of ~400 lines (remove ~800, add ~400)

---

## Open Questions

**Q1:** Should we keep `COMMAND_PARAMS_ANALYSIS.md` as implementation reference?
**Answer:** Yes, update with "Implemented" status and final schema examples

**Q2:** Should provider configs support environment variable substitution?
**Answer:** Yes, maintain existing `${ENV_VAR}` pattern for API keys

**Q3:** Should we version this as v3.0.0 (breaking change)?
**Answer:** Yes, this is a breaking change warranting major version bump

**Q4:** Should chat config support multiple MCP servers?
**Answer:** Out of scope - keep simple, one server per config

---

## Implementation Checklist

- [ ] Phase 1: Create new config loaders (index, chat, server)
- [ ] Phase 2: Create sample configs for all commands
- [ ] Phase 3: Update command implementations
- [ ] Phase 4: Rewrite test suite
- [ ] Phase 5: Update all documentation
- [ ] Phase 6: Delete unified config system
- [ ] Phase 7: Update CI/CD pipeline
- [ ] Phase 8: Run full verification and cleanup

---

**Estimated Effort:** 6-8 hours focused implementation
**Target Completion:** Next 1-2 weeks for v3.0 release
