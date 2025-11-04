# Command-Specific Configuration Guide

Minerva v3 introduces dedicated configuration files for each command. Instead of managing a monolithic JSON document, you maintain small, focused files:

- `configs/index/` – one file per collection you want to index
- `configs/chat/` – personal chat settings per environment
- `configs/server/` – MCP server profiles (local stdio or HTTP deployments)

All loaders share validation helpers, environment-variable substitution, and detailed error messages. This guide documents the schemas, field constraints, and recommended workflows for each file type.

## Table of Contents

- [Directory Layout](#directory-layout)
- [Index Configuration](#index-configuration)
  - [Schema Overview](#schema-overview)
  - [Example: Ollama](#example-ollama)
  - [Example: LM Studio](#example-lm-studio)
- [Chat Configuration](#chat-configuration)
  - [Schema Overview](#chat-schema-overview)
  - [Example: Ollama](#chat-example-ollama)
  - [Example: OpenAI](#chat-example-openai)
- [Server Configuration](#server-configuration)
  - [Schema Overview](#server-schema-overview)
  - [Example Profiles](#example-profiles)
- [AI Provider Schema](#ai-provider-schema)
- [Environment Variables](#environment-variables)
- [Validation Workflow](#validation-workflow)
- [Migration Notes](#migration-notes)

## Directory Layout

Each config file is resolved relative to its own location. Paths can be absolute or relative; relative entries are resolved before validation and must produce absolute paths.

```
configs/
├── index/
│   ├── bear-notes-ollama.json
│   └── wikipedia-lmstudio.json
├── chat/
│   ├── ollama.json
│   └── openai.json
└── server/
    ├── local.json
    └── network.json
```

You may create additional files alongside these samples. Keep secrets (API keys, absolute paths) out of version control.

### Path Resolution Examples

All paths in config files (`chromadb_path`, `json_file`, `conversation_dir`) are resolved **relative to the config file's directory**.

**Example 1: Config in `configs/index/`**
```
project/
├── chromadb_data/          # Shared database
├── data/
│   └── notes.json          # Source data
└── configs/
    └── index/
        └── notes.json      # Config file here
```

In `configs/index/notes.json`:
```json
{
  "chromadb_path": "../../chromadb_data",    // Go up 2 levels
  "collection": {
    "json_file": "../../data/notes.json"     // Go up 2 levels, then into data/
  }
}
```

**Example 2: Config in same directory as data**
```
project/
├── chromadb_data/
└── my-notes/
    ├── config.json         # Config file here
    └── notes.json          # Data file here
```

In `my-notes/config.json`:
```json
{
  "chromadb_path": "../chromadb_data",       // Go up 1 level
  "collection": {
    "json_file": "./notes.json"              // Same directory
  }
}
```

**Example 3: Using absolute paths (no resolution)**
```json
{
  "chromadb_path": "/srv/minerva/chromadb_data",
  "collection": {
    "json_file": "/data/notes/extracted.json"
  }
}
```

**Tip:** Use `./` for same directory, `../` to go up one level, or absolute paths for clarity.

## Index Configuration

Index configs describe a single collection and its embedding provider. Loader: `minerva.common.index_config.load_index_config`.

### Schema Overview

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
    /* AI provider payload */
  }
}
```

| Field                           | Type    | Required | Notes                                                                                   |
| ------------------------------- | ------- | -------- | --------------------------------------------------------------------------------------- |
| `chromadb_path`                 | string  | ✅       | Resolved to absolute path; directory is created if missing by downstream storage layer. |
| `collection.name`               | string  | ✅       | Regex `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`, max 63 chars.                                      |
| `collection.description`        | string  | ✅       | 10–2000 characters after trimming. Used for AI validation messages.                     |
| `collection.json_file`          | string  | ✅       | Path to normalized notes JSON. Resolver accepts relative paths.                         |
| `collection.chunk_size`         | integer | ❌       | 300–20,000 (default 1200).                                                              |
| `collection.force_recreate`     | boolean | ❌       | When `true`, drops and rebuilds the collection.                                         |
| `collection.skip_ai_validation` | boolean | ❌       | Bypasses optional LLM-based note validation.                                            |
| `provider`                      | object  | ✅       | See [AI Provider Schema](#ai-provider-schema).                                          |

Validation failures identify the offending field with a helpful trace (for example `collection → name`).

### Example: Ollama

```json
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "name": "bear-notes",
    "description": "Notes exported from Bear with metadata preserved for personal knowledge management.",
    "json_file": "../../data/bear/normalized-notes.json",
    "chunk_size": 1200,
    "force_recreate": false,
    "skip_ai_validation": false
  },
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
```

### Example: LM Studio

```json
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "name": "wikipedia-history",
    "description": "Curated Wikipedia history dump (1k articles).",
    "json_file": "../../data/wiki/history.json",
    "chunk_size": 1400
  },
  "provider": {
    "provider_type": "lmstudio",
    "base_url": "http://localhost:1234/v1",
    "embedding_model": "qwen2.5-7b-instruct",
    "llm_model": "qwen2.5-14b-instruct",
    "rate_limit": {
      "requests_per_minute": 60,
      "concurrency": 1
    }
  }
}
```

## Chat Configuration

Chat configs control conversational features and provider selection. Loader: `minerva.chat.config.load_chat_config_from_file`.

### Chat Schema Overview

```json
{
  "chromadb_path": "<string>",
  "conversation_dir": "<string>",
  "mcp_server_url": "<string>",
  "enable_streaming": false,
  "max_tool_iterations": 5,
  "system_prompt_file": null,
  "provider": {
    /* AI provider payload */
  }
}
```

| Field                 | Type           | Required | Notes                                                                     |
| --------------------- | -------------- | -------- | ------------------------------------------------------------------------- |
| `chromadb_path`       | string         | ✅       | Must resolve to absolute path; reused for local caching and tool routing. |
| `conversation_dir`    | string         | ✅       | Directory is created if it does not exist. Supports `~` expansion.        |
| `mcp_server_url`      | string         | ✅       | Must include scheme + host (e.g., `http://127.0.0.1:8337`). The `/mcp` endpoint is added automatically. |
| `enable_streaming`    | boolean        | ❌       | Default `false`. Enables streaming responses in supported providers.      |
| `max_tool_iterations` | integer        | ❌       | 1–10, defaults to 5.                                                      |
| `system_prompt_file`  | string or null | ❌       | Optional path to custom system prompt; `null` clears it.                  |
| `provider`            | object         | ✅       | Embedding/LLM provider for chat completions.                              |

### Example: Ollama

```json
{
  "chromadb_path": "../../chromadb_data",
  "conversation_dir": "../../state/chat/conversations",
  "mcp_server_url": "http://127.0.0.1:8337",
  "enable_streaming": true,
  "max_tool_iterations": 4,
  "system_prompt_file": null,
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
```

### Example: OpenAI

```json
{
  "chromadb_path": "../../chromadb_data",
  "conversation_dir": "../../state/chat/conversations",
  "mcp_server_url": "https://minerva.example.com/mcp",
  "enable_streaming": true,
  "max_tool_iterations": 5,
  "system_prompt_file": "../../prompts/chat-system.md",
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "embedding_model": {
      "model": "text-embedding-3-small"
    },
    "llm_model": {
      "model": "gpt-4o-mini"
    }
  }
}
```

## Server Configuration

Server configs are lightweight and affect both `minerva serve` (stdio) and `minerva serve-http` (network mode). Loader: `minerva.common.server_config.load_server_config`.

### Server Schema Overview

```json
{
  "chromadb_path": "<string>",
  "default_max_results": 6,
  "host": "127.0.0.1",
  "port": 8337
}
```

| Field                 | Type            | Required | Notes                                                              |
| --------------------- | --------------- | -------- | ------------------------------------------------------------------ |
| `chromadb_path`       | string          | ✅       | Must resolve to absolute path.                                     |
| `default_max_results` | integer         | ✅       | Range 1–15. Controls result count when clients omit `max_results`. |
| `host`                | string or null  | ❌       | Optional override; ignored by stdio server.                        |
| `port`                | integer or null | ❌       | Required for HTTP deployments.                                     |

### Example Profiles

**Local development (`configs/server/local.json`):**

```json
{
  "chromadb_path": "../../chromadb_data",
  "default_max_results": 6,
  "host": "127.0.0.1",
  "port": 8337
}
```

**Network deployment (`configs/server/network.json`):**

```json
{
  "chromadb_path": "/srv/minerva/chromadb_data",
  "default_max_results": 5,
  "host": "0.0.0.0",
  "port": 9000
}
```

## AI Provider Schema

All configs share the same provider schema defined in `minerva/common/ai_config.py`. Supported `provider_type` values: `ollama`, `lmstudio`, `openai`, `anthropic`, `gemini`.

Core fields:

- `provider_type` (required)
- `base_url` (optional for local providers)
- `embedding_model` / `llm_model` (flat format)
- or nested blocks using `embedding` / `llm` with `model` and optional `temperature`
- `api_key` (for cloud providers; supports `${ENV_VAR}` placeholders)
- `rate_limit.requests_per_minute` and `rate_limit.concurrency` (optional)

Providers may include additional keys specific to each service. The loader normalises shapes (nested vs. flat) to the `AIProviderConfig` dataclass.

## Environment Variables

Use `${NAME}` placeholders anywhere a secret or host-specific value is required:

```json
{
  "provider_type": "openai",
  "api_key": "${OPENAI_API_KEY}",
  "llm_model": { "model": "gpt-4o-mini" },
  "embedding_model": { "model": "text-embedding-3-small" }
}
```

`load_*_config()` resolves the placeholder against the current environment. Missing variables raise `ConfigError` with guidance on how to export the value.

## Validation Workflow

1. Edit or copy a sample config under `configs/`.
2. Run the appropriate loader to validate:
   ```bash
   python -c "from minerva.common.index_config import load_index_config; load_index_config('configs/index/bear-notes-ollama.json')"
   python -c "from minerva.chat.config import load_chat_config_from_file; load_chat_config_from_file('configs/chat/ollama.json')"
   python -c "from minerva.common.server_config import load_server_config; load_server_config('configs/server/local.json')"
   ```
3. Execute the target command (`minerva index`, `minerva chat`, `minerva serve`).

Validation errors include the offending field path, original value, and suggested fixes.

## Migration Notes

- Unified configuration files (`minerva/common/config_loader.py`) have been removed in v3.0.0.
- Create one index config per collection. Re-run `minerva index` for each collection you want to refresh.
- Chat and server configs no longer read from a shared provider registry; embed the provider definition inline.
- Delete or archive any previous `configs/*.json` unified files—they are not consumed by the new loaders.
- Update automation and CI scripts to call the dedicated loaders (see `.github/workflows/ci.yml` for examples).
