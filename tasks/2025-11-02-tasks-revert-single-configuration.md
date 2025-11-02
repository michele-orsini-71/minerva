## Relevant Files

### New Files to Create

- [x] `minerva/common/index_config.py` - Index command configuration schema, loader, and validation
- [x] `minerva/common/server_config.py` - Server command configuration schema, loader, and validation
- [x] `configs/index/bear-notes-ollama.json` - Sample index config with Ollama provider
- [x] `configs/index/wikipedia-lmstudio.json` - Sample index config with LM Studio provider
- [x] `configs/chat/ollama.json` - Sample chat config with Ollama provider
- [x] `configs/chat/lmstudio.json` - Sample chat config with LM Studio provider
- [x] `configs/chat/openai.json` - Sample chat config with OpenAI provider
- [x] `configs/server/local.json` - Sample server config for local development
- [x] `configs/server/network.json` - Sample server config for network deployment
- [x] `tests/helpers/config_builders.py` - Test helpers for building simple configs

### Files to Modify

- [x] `minerva/common/ai_config.py` - Extracted provider loading logic for reuse across loaders
- [x] `minerva/chat/config.py` - Added simple config loader while keeping legacy helper for unified configs
- [x] `minerva/commands/index.py` - Replace unified config with `load_index_config()`
- [x] `minerva/commands/chat.py` - Replace unified config with simple chat config loader
- [x] `minerva/commands/serve.py` - Replace unified config with `load_server_config()`
- [x] `minerva/commands/serve_http.py` - Replace unified config with `load_server_config()`
- [x] `minerva/server/mcp_server.py` - Update `initialize_server()` to use simple server config
- [x] `minerva/cli.py` - Update help text and command examples
- `tests/test_index_command.py` - Rewrite to use simple index configs instead of unified
- `tests/test_chat_config.py` - Rewrite to use simple chat configs instead of unified
- `tests/test_error_handling.py` - Update config fixtures to use simple configs
- `tests/test_import_paths.py` - Update any config references
- `tests/test_mcp_chat_integration.py` - Update ChatConfig fixtures
- [x] `CLAUDE.md` - Remove unified config section, add command-specific examples
- [x] `README.md` - Update features list and all config examples
- [x] `docs/configuration.md` - Rewrite as comprehensive guide for command-specific configs
- [x] `COMMAND_PARAMS_ANALYSIS.md` - Document final command-specific schemas
- `.github/workflows/ci.yml` - Update config validation for new structure

### Files to Delete

- `minerva/common/config_loader.py` - Unified config system (634 lines)
- `minerva/commands/config.py` - Config validation command (47 lines)
- `tests/test_unified_config_loader.py` - Unified config tests (113 lines)
- `configs/desktop-lmstudio.json` - Unified config sample
- `configs/hybrid-ollama-lmstudio.json` - Unified config sample
- `configs/server-ollama.json` - Unified config sample

### Notes

- Unit tests should typically be placed alongside the code files they are testing when feasible.
- Use `pytest [optional/test/path]` to run relevant suites; running without a path executes all configured tests.
- All config loaders should reuse existing `AIProviderConfig` and `RateLimitConfig` classes
- Follow frozen dataclass pattern for immutability
- Use existing path resolution and env variable substitution patterns

## Tasks

- [x] 1.0 Create new command-specific configuration loaders (index, chat, server)
  - [x] 1.1 Create `minerva/common/index_config.py` with IndexConfig dataclass, JSON schema, and `load_index_config()` function
  - [x] 1.2 Create `minerva/common/server_config.py` with ServerConfig dataclass, JSON schema, and `load_server_config()` function
  - [x] 1.3 Update `minerva/chat/config.py` to add `load_chat_config_from_file()` function that loads simple chat JSON config
  - [x] 1.4 Extract and reuse provider building logic from old config_loader.py into new loaders (handle nested vs flat provider schemas)
  - [x] 1.5 Add comprehensive error handling with helpful messages for missing/invalid fields in all loaders
  - [x] 1.6 Ensure all config loaders support environment variable substitution for API keys using existing `resolve_env_variable()` pattern

- [x] 2.0 Create sample configuration files for all commands
  - [x] 2.1 Create `configs/index/` directory and add `bear-notes-ollama.json` sample with inline provider
  - [x] 2.2 Add `configs/index/wikipedia-lmstudio.json` sample demonstrating LM Studio provider with rate limiting
  - [x] 2.3 Create `configs/chat/` directory and add `ollama.json`, `lmstudio.json`, and `openai.json` samples
  - [x] 2.4 Create `configs/server/` directory and add `local.json` and `network.json` samples
  - [x] 2.5 Add inline JSON comments to all sample configs explaining each field (use descriptive field values as documentation)
  - [x] 2.6 Ensure all sample configs use realistic paths and values that work for local development

- [x] 3.0 Update command implementations to use new config loaders
  - [x] 3.1 Update `minerva/commands/index.py` to use `load_index_config()` instead of `load_unified_config()`
  - [x] 3.2 Remove multi-collection error check (lines 68-72) since each config = one collection now
  - [x] 3.3 Update provider initialization in index command to use inline provider from IndexConfig
  - [x] 3.4 Update `minerva/commands/chat.py` to use `load_chat_config_from_file()` instead of unified config
  - [x] 3.5 Update `minerva/commands/serve.py` and `serve_http.py` to use `load_server_config()`
  - [x] 3.6 Update `minerva/server/mcp_server.py` `initialize_server()` function to accept ServerConfig instead of UnifiedConfig
  - [x] 3.7 Update all error messages to remove references to unified config structure

- [x] 4.0 Rewrite test suite for command-specific configurations
  - [x] 4.1 Create `tests/helpers/config_builders.py` with helper functions `make_index_config()`, `make_chat_config()`, `make_server_config()`
  - [x] 4.2 Rewrite `tests/test_index_command.py` to use `make_index_config()` helper instead of unified config
  - [x] 4.3 Rewrite `tests/test_chat_config.py` to test `load_chat_config_from_file()` with simple chat configs
  - [x] 4.4 Update `tests/test_mcp_chat_integration.py` ChatConfig fixtures to use simple chat config structure
  - [x] 4.5 Update `tests/test_error_handling.py` to build simple configs instead of unified configs
  - [x] 4.6 Update any other tests that reference `UnifiedConfig`, `build_unified_config()`, or `make_unified_config()`
  - [x] 4.7 Run full test suite and fix any remaining failures

- [x] 5.0 Update all documentation to reflect new configuration system
  - [x] 5.1 Update `CLAUDE.md` - remove "Unified Configuration" section, add "Command-Specific Configuration" section with examples
  - [x] 5.2 Update `CLAUDE.md` - replace all config examples with simple per-command configs
  - [x] 5.3 Update `README.md` - remove unified config from features list, update Quick Start section
  - [x] 5.4 Update `README.md` - update all command usage examples to show new config file paths
  - [x] 5.5 Rewrite `docs/configuration.md` as comprehensive guide for command-specific configs with full schema documentation
  - [x] 5.6 Update `minerva/cli.py` help text and epilog examples to show new config file organization
  - [x] 5.7 Update `COMMAND_PARAMS_ANALYSIS.md` to mark as "Implemented" with final schemas

- [x] 6.0 Remove unified configuration system and related code
  - [x] 6.1 Delete `minerva/common/config_loader.py` (634 lines of unified config code)
  - [x] 6.2 Delete `minerva/commands/config.py` (config validate command)
  - [x] 6.3 Delete `tests/test_unified_config_loader.py` (113 lines of unified config tests)
  - [x] 6.4 Delete old unified sample configs: `configs/desktop-lmstudio.json`, `configs/hybrid-ollama-lmstudio.json`, `configs/server-ollama.json`
  - [x] 6.5 Remove imports of `UnifiedConfig`, `ProviderDefinition`, `load_unified_config` from all remaining files
  - [x] 6.6 Remove `config` subcommand from `minerva/cli.py` argument parser
  - [x] 6.7 Search codebase for any remaining references to "unified" config and remove/update them

- [ ] 7.0 Update CI/CD pipeline for new configuration validation
  - [ ] 7.1 Update `.github/workflows/ci.yml` to remove `minerva config validate` step
  - [ ] 7.2 Add validation step that loads all sample configs using their respective loaders (index, chat, server)
  - [ ] 7.3 Update CI to test config loading doesn't crash: `python -c "from minerva.common.index_config import load_index_config; load_index_config('configs/index/bear-notes-ollama.json')"`
  - [ ] 7.4 Ensure CI runs full test suite with new config system

- [ ] 8.0 Run full verification and final cleanup
  - [ ] 8.1 Run complete test suite: `pytest -v` and ensure all 518+ tests pass
  - [ ] 8.2 Manually test each command with new configs: index, chat, serve, serve-http
  - [ ] 8.3 Verify all sample configs load successfully without errors
  - [ ] 8.4 Check for any TODO comments or temporary code left in implementation
  - [ ] 8.5 Run grep for "unified" and "UnifiedConfig" across codebase to catch any missed references
  - [ ] 8.6 Update version number to v3.0.0 in `minerva/cli.py` and `setup.py` (breaking change)
  - [ ] 8.7 Review git diff to ensure no unintended changes were made
