# Minerva Command Parameters Analysis

## Status

Command-specific configuration loaders (`IndexConfig`, `ServerConfig`) are implemented in Minerva v3.0.0. Each command now consumes an independent JSON file with inline AI provider definitions and consistent validation.

## Summary Table

| Command | Needs AI Provider? | Needs ChromaDB? | Config File | Complexity |
|---------|-------------------|-----------------|-------------|------------|
| `index` | ✅ Yes | ✅ Yes (write) | `configs/index/<name>.json` | Medium (per collection) |
| `serve` | ❌ No | ✅ Yes (read) | `configs/server/<profile>.json` | Low |
| `serve-http` | ❌ No | ✅ Yes (read) | `configs/server/<profile>.json` | Low + runtime flags |
| `peek` | ❌ No | ✅ Yes (read) | CLI args only | Minimal |
| `validate` | ❌ No | ❌ No | CLI args only | Minimal |

---

## `minerva index`

**Purpose**: Index one collection of notes into ChromaDB with embeddings.

**Config schema** (`minerva.common.index_config.IndexConfig`):

```json
{
  "chromadb_path": "<string>",
  "collection": {
    "name": "<string>",
    "description": "<string>",
    "json_file": "<string>",
    "chunk_size": 1200,
    "force_recreate": false,
    "skip_ai_validation": false
  },
  "provider": {
    "provider_type": "ollama|lmstudio|openai|anthropic|gemini",
    "embedding_model": "<string>",
    "llm_model": "<string>",
    "base_url": "<string>",
    "api_key": "${ENV}",
    "rate_limit": {
      "requests_per_minute": 60,
      "concurrency": 1
    }
  }
}
```

- One config per collection; run the command repeatedly for multiple collections.
- Paths are resolved relative to the config file then normalised to absolute paths.
- Provider payload supports both flat (`embedding_model`) and nested (`embedding.model`) shapes.
- Validation errors highlight the precise field path, eg. `collection → name`.

**Key Flags**:
- `--config FILE` – required index config.
- `--verbose` – detailed progress and chunking stats.
- `--dry-run` – schema validation and AI provider initialisation without writing to ChromaDB.

---

## `minerva serve`

**Purpose**: Launch the MCP server in stdio mode for Claude Desktop.

**Config schema** (`minerva.common.server_config.ServerConfig`):

```json
{
  "chromadb_path": "<string>",
  "default_max_results": 6,
  "host": "127.0.0.1",
  "port": 8337
}
```

- `host`/`port` are optional in stdio mode; keep them for parity with `serve-http`.
- `default_max_results` is enforced between 1 and 15.

---

## `minerva serve-http`

**Purpose**: Expose the MCP server over HTTP for remote clients.

- Uses the same server config as `serve`.
- Runtime overrides via `--host`/`--port` flags take priority over config values.
- Ideal for Docker or remote deployments.

## CLI-Only Commands

- `minerva peek` requires `chromadb_path` (positional) and optional `collection_name`/`--format`. No config files.
- `minerva validate` takes a JSON notes file path and optional `--verbose`.

---

## Cross-Cutting Notes

- AI provider definitions are inline for index configs. Shared logic lives in `minerva/common/ai_config.py`.
- Environment variables are supported via `${NAME}` placeholders; missing values raise clear `ConfigError` messages.
- Config loaders ensure all resolved file system paths are absolute before returning dataclasses.
- CI loads every sample config during the `validate-configs` step (see `.github/workflows/ci.yml`).

---

## Migration Summary

- Unified configs (`configs/*.json`) and `minerva config validate` are deprecated and scheduled for removal.
- Copy/rename sample configs under `configs/index/` and `configs/server/` as starting points.
- Automate indexing by iterating over the files in `configs/index/` and invoking `minerva index` for each.
- Update any documentation or scripts that reference the legacy unified configuration to point at the new dataclasses (`IndexConfig`, `ServerConfig`).
