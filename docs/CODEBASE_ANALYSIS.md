# Minerva Configuration Architecture (Post-Unified Removal)

This reference outlines the per-command configuration flow after removing the legacy unified configuration system.

## 1. Shared Building Blocks

### 1.1 AI Provider Configuration (`minerva/common/ai_config.py`)
- `AIProviderConfig` encapsulates provider settings, rate limits, and API key resolution.
- `build_ai_provider_config()` constructs configs from JSON payloads with consistent validation.
- `resolve_env_variable()` handles `${VAR_NAME}` placeholders and raises helpful errors when missing.

### 1.2 Index Configuration (`minerva/common/index_config.py`)
- `IndexConfig` combines `chromadb_path`, a single `CollectionConfig`, and an `AIProviderConfig`.
- `load_index_config(path)` performs JSON parsing, schema validation, absolute path conversion, and semantic checks (chunk size bounds, description trimming, etc.).

### 1.3 Server Configuration (`minerva/common/server_config.py`)
- `ServerConfig` holds MCP server deployment options: Chroma path, default max results, optional host/port overrides.
- `load_server_config(path)` shares the same schema-first then semantic-validation approach.

## 2. Command Flows

### 2.1 Index (`minerva/commands/index.py`)
```
config = load_index_config(args.config)
notes = load_json_notes(config.collection.json_file)
provider = initialize_provider(config.provider)
```
- Each config indexes exactly one collection; reruns require separate config files or overrides.
- Provider configuration is inline, eliminating ID indirection.

### 2.2 Serve (`minerva/commands/serve.py` / `serve_http.py`)
```
server_config = load_server_config(args.config)
validate_server_prerequisites(server_config.chromadb_path)
provider_map, collections = discover_collections_with_providers(server_config.chromadb_path)
```
- Server configs focus on deployment; providers come from stored collection metadata.
- `minerva/server/startup_validation.py` loads `ServerConfig` to perform the same preflight checks.

## 3. Testing Support

- `tests/helpers/config_builders.py` provides `make_index_config` and `make_server_config` for writing temporary JSON configs and loading them through real loaders.
- `tests/test_index_command.py` and `tests/test_error_handling.py` exercise the loaders with success and failure scenarios.

## 4. Provider Initialization Patterns

- `initialize_provider(config: AIProviderConfig)` in `minerva/indexing/embeddings.py` remains the single entry point for constructing providers.
- All commands pass inline provider configs from their respective dataclasses; no global registry or ID lookup remains.
- API keys are resolved lazily via `AIProviderConfig.resolve_api_key()` to honour environment variables at runtime.

## 5. Error Handling Principles

- Loaders raise `ConfigError` with actionable multi-line messages.
- JSON schema validation surfaces field locations; semantic validation adds guidance (expected ranges, remediation steps).
- CLI commands catch these exceptions, log user-friendly banners, and exit with command-specific status codes.

## 6. Removal Summary

- Deleted modules: `minerva/common/config_loader.py`, `minerva/commands/config.py`, and `tests/test_unified_config_loader.py`.
- Removed unified sample configs: `configs/desktop-lmstudio.json`, `configs/hybrid-ollama-lmstudio.json`, `configs/server-ollama.json`.
- CLI no longer exposes the `config` subcommand; validation now occurs within individual command loaders.

This document serves as the canonical overview for the per-command configuration architecture introduced in v3.0.0.
