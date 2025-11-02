# Unified Configuration Guide

Minerva uses a unified configuration system that consolidates all settings into a single JSON file. This guide explains the configuration schema, API key handling, environment variable substitution, and provides complete examples.

## Table of Contents

- [Overview](#overview)
- [Configuration Schema](#configuration-schema)
- [AI Providers](#ai-providers)
- [Indexing Configuration](#indexing-configuration)
- [Chat Configuration](#chat-configuration)
- [Server Configuration](#server-configuration)
- [Environment Variables](#environment-variables)
- [Complete Examples](#complete-examples)
- [Migration from Legacy Configs](#migration-from-legacy-configs)
- [Validation](#validation)

## Overview

### Unified Configuration Benefits

The unified configuration approach provides:

- **Single source of truth**: All settings in one file
- **Provider reuse**: Define AI providers once, reference by ID
- **Consistency**: Same provider for indexing and querying
- **Flexibility**: Mix different providers for different purposes
- **Validation**: Built-in schema validation with helpful error messages

### Configuration Structure

A unified config file has four main sections:

```json
{
  "ai_providers": [...],
  "indexing": {...},
  "chat": {...},
  "server": {...}
}
```

Each section is optional depending on which Minerva commands you use.

### Commands and Required Sections

| Command | Required Sections |
|---------|-------------------|
| `minerva index` | `ai_providers`, `indexing` |
| `minerva serve` | `server` |
| `minerva chat` | `ai_providers`, `chat`, `server` (if using MCP) |
| `minerva config validate` | Any/all sections |

## Configuration Schema

### Complete Schema Template

```json
{
  "ai_providers": [
    {
      "id": "provider-unique-id",
      "provider_type": "ollama|lmstudio|openai|anthropic|gemini",
      // Provider-specific fields...
    }
  ],
  "indexing": {
    "chromadb_path": "/absolute/path/to/chromadb",
    "collections": [
      {
        "collection_name": "collection-name",
        "description": "What this collection contains",
        "json_file": "./path/to/notes.json",
        "chunk_size": 1200,
        "force_recreate": false,
        "skip_ai_validation": false,
        "ai_provider_id": "provider-unique-id"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "provider-unique-id",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "/absolute/path/to/chromadb",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

## AI Providers

AI providers define the models and services used for embeddings and language model inference.

### Provider Types

Minerva supports five provider types:

1. **ollama** - Local Ollama server
2. **lmstudio** - LM Studio desktop application
3. **openai** - OpenAI API
4. **anthropic** - Anthropic Claude API
5. **gemini** - Google Gemini API

### Ollama Provider

```json
{
  "id": "ollama-local",
  "provider_type": "ollama",
  "base_url": "http://localhost:11434",
  "embedding": {
    "model": "mxbai-embed-large:latest"
  },
  "llm": {
    "model": "llama3.1:8b"
  }
}
```

**Fields:**
- `id` (required): Unique identifier for referencing this provider
- `provider_type` (required): Must be `"ollama"`
- `base_url` (optional): Ollama server URL (default: `http://localhost:11434`)
- `embedding.model` (required): Model for generating embeddings
- `llm.model` (required): Model for chat/completions

**Requirements:**
- Ollama server running: `ollama serve`
- Models downloaded: `ollama pull mxbai-embed-large:latest`

### LM Studio Provider

```json
{
  "id": "lmstudio-local",
  "provider_type": "lmstudio",
  "base_url": "http://localhost:1234/v1",
  "embedding_model": "qwen2.5-7b-instruct",
  "llm_model": "qwen2.5-14b-instruct",
  "rate_limit": {
    "requests_per_minute": 60,
    "concurrency": 1
  }
}
```

**Fields:**
- `id` (required): Unique identifier
- `provider_type` (required): Must be `"lmstudio"`
- `base_url` (required): LM Studio API endpoint
- `embedding_model` (required): Model name for embeddings
- `llm_model` (required): Model name for chat
- `rate_limit` (optional): Rate limiting configuration

**Rate Limit Fields:**
- `requests_per_minute` (optional): Max requests per minute (null = unlimited)
- `concurrency` (optional): Max concurrent requests (null = unlimited)

**Requirements:**
- LM Studio running with server started
- Models loaded in LM Studio
- See [LM Studio Setup Guide](LMSTUDIO_SETUP.md)

### OpenAI Provider

```json
{
  "id": "openai-cloud",
  "provider_type": "openai",
  "api_key": "${OPENAI_API_KEY}",
  "embedding": {
    "model": "text-embedding-3-small"
  },
  "llm": {
    "model": "gpt-4o-mini"
  }
}
```

**Fields:**
- `id` (required): Unique identifier
- `provider_type` (required): Must be `"openai"`
- `api_key` (required): OpenAI API key (use environment variable)
- `embedding.model` (required): Embedding model name
- `llm.model` (required): Chat model name

**Common Models:**
- Embeddings: `text-embedding-3-small`, `text-embedding-3-large`
- Chat: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`

**Requirements:**
- OpenAI API key: `export OPENAI_API_KEY="sk-..."`
- Active OpenAI account with credits

### Anthropic Provider

```json
{
  "id": "claude-cloud",
  "provider_type": "anthropic",
  "api_key": "${ANTHROPIC_API_KEY}",
  "embedding": {
    "model": "voyage-2"
  },
  "llm": {
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

**Fields:**
- `id` (required): Unique identifier
- `provider_type` (required): Must be `"anthropic"`
- `api_key` (required): Anthropic API key
- `embedding.model` (required): Embedding model (via Voyage AI)
- `llm.model` (required): Claude model name

**Common Models:**
- Embeddings: `voyage-2`, `voyage-large-2`
- Chat: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`

**Requirements:**
- Anthropic API key: `export ANTHROPIC_API_KEY="sk-ant-..."`

### Gemini Provider

```json
{
  "id": "gemini-cloud",
  "provider_type": "gemini",
  "api_key": "${GEMINI_API_KEY}",
  "embedding": {
    "model": "text-embedding-004"
  },
  "llm": {
    "model": "gemini-1.5-pro"
  }
}
```

**Fields:**
- `id` (required): Unique identifier
- `provider_type` (required): Must be `"gemini"`
- `api_key` (required): Google API key
- `embedding.model` (required): Embedding model
- `llm.model` (required): Gemini model name

**Common Models:**
- Embeddings: `text-embedding-004`, `embedding-001`
- Chat: `gemini-1.5-pro`, `gemini-1.5-flash`

**Requirements:**
- Google API key: `export GEMINI_API_KEY="AIza..."`

### Multiple Providers

You can define multiple providers and use them for different purposes:

```json
{
  "ai_providers": [
    {
      "id": "ollama-indexing",
      "provider_type": "ollama",
      "embedding": {
        "model": "mxbai-embed-large:latest"
      },
      "llm": {
        "model": "llama3.1:8b"
      }
    },
    {
      "id": "openai-chat",
      "provider_type": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "embedding": {
        "model": "text-embedding-3-small"
      },
      "llm": {
        "model": "gpt-4o-mini"
      }
    }
  ]
}
```

Use cases:
- **Ollama for indexing** (free, fast) + **OpenAI for chat** (higher quality)
- **LM Studio for desktop** + **Ollama for server**
- **Different models for different collections**

## Indexing Configuration

The indexing section defines how notes are processed and stored.

### Basic Structure

```json
{
  "indexing": {
    "chromadb_path": "/absolute/path/to/chromadb_data",
    "collections": [...]
  }
}
```

### Collection Configuration

```json
{
  "collection_name": "my-notes",
  "description": "Personal notes about software development and research",
  "json_file": "./notes.json",
  "chunk_size": 1200,
  "force_recreate": false,
  "skip_ai_validation": false,
  "ai_provider_id": "ollama-local"
}
```

**Fields:**

- `collection_name` (required): Unique collection identifier
  - Alphanumeric, hyphens, underscores only
  - Example: `personal-notes`, `wiki_history`

- `description` (required): What this collection contains
  - Used by AI to decide when to search this collection
  - Be specific and descriptive
  - Example: "Personal notes from Bear app covering software development, project management, and technical documentation from 2020-2025"

- `json_file` (required): Path to notes JSON file
  - Relative to config file or absolute path
  - Must conform to [Note Schema](NOTE_SCHEMA.md)

- `chunk_size` (optional): Target characters per chunk
  - Default: 1200
  - Range: 500-3000
  - Larger = more context, fewer chunks
  - Smaller = more precise, more chunks

- `force_recreate` (optional): Delete existing collection
  - Default: false
  - Set to true to replace existing collection

- `skip_ai_validation` (optional): Skip description quality check
  - Default: false
  - Set to true to bypass AI validation of description

- `ai_provider_id` (required): ID of AI provider to use
  - Must match an ID from `ai_providers` section
  - This provider will be used for embeddings

### Multiple Collections

```json
{
  "indexing": {
    "chromadb_path": "/shared/chromadb",
    "collections": [
      {
        "collection_name": "bear-notes",
        "description": "Personal notes from Bear",
        "json_file": "./bear.json",
        "ai_provider_id": "ollama-local"
      },
      {
        "collection_name": "wikipedia",
        "description": "Wikipedia articles about history",
        "json_file": "./wiki.json",
        "ai_provider_id": "openai-cloud"
      }
    ]
  }
}
```

All collections share the same `chromadb_path` but can use different AI providers.

## Chat Configuration

The chat section configures the interactive chat command.

### Basic Structure

```json
{
  "chat": {
    "chat_provider_id": "ollama-local",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  }
}
```

### Fields

- `chat_provider_id` (required): ID of AI provider for chat
  - Must match an ID from `ai_providers` section
  - Used for LLM inference and tool responses

- `mcp_server_url` (required): MCP server endpoint
  - Default: `http://localhost:8000/mcp`
  - Must match running MCP server

- `conversation_dir` (optional): Where to save conversations
  - Default: `~/.minerva/conversations`
  - Supports `~` expansion
  - Created automatically if missing

- `enable_streaming` (optional): Enable streaming responses
  - Default: false
  - LM Studio may not support streaming with all models
  - Set to true for real-time response rendering

- `max_tool_iterations` (optional): Max tool calls per turn
  - Default: 5
  - Prevents infinite tool call loops
  - Range: 1-10

### Streaming Considerations

**When to enable streaming:**
- Using OpenAI, Anthropic, or Gemini
- Want real-time response rendering
- Model supports streaming

**When to disable streaming:**
- Using LM Studio (may not support streaming)
- Prefer complete responses
- Debugging tool calls

The chat system automatically falls back to non-streaming if the provider doesn't support it.

## Server Configuration

The server section configures the MCP server.

### Basic Structure

```json
{
  "server": {
    "chromadb_path": "/absolute/path/to/chromadb_data",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

### Fields

- `chromadb_path` (required): Absolute path to ChromaDB directory
  - Must be absolute path
  - Should match `indexing.chromadb_path`

- `default_max_results` (required): Default search result count
  - Recommended: 3-5
  - Maximum: 15 (hard limit to prevent token overflow)
  - Users can override per-query

- `host` (optional): Server bind address
  - Default: `127.0.0.1` (localhost only)
  - `0.0.0.0` to allow remote connections
  - Security: Only use `0.0.0.0` on trusted networks

- `port` (optional): Server port
  - Default: 8000
  - Range: 1024-65535
  - Must not conflict with other services

### Deployment Patterns

**Local Desktop:**
```json
{
  "host": "127.0.0.1",
  "port": 8000
}
```

**Server (Remote Access):**
```json
{
  "host": "0.0.0.0",
  "port": 8000
}
```

**Custom Port:**
```json
{
  "host": "127.0.0.1",
  "port": 8080
}
```

## Environment Variables

Configuration files support environment variable substitution using `${VAR_NAME}` syntax.

### Syntax

```json
{
  "api_key": "${OPENAI_API_KEY}",
  "chromadb_path": "${HOME}/chromadb_data",
  "base_url": "${OLLAMA_HOST:-http://localhost:11434}"
}
```

### Features

**Basic substitution:**
```json
"${OPENAI_API_KEY}"
```
Replaced with value of `OPENAI_API_KEY` environment variable.

**With default value:**
```json
"${OLLAMA_HOST:-http://localhost:11434}"
```
Uses `OLLAMA_HOST` if set, otherwise uses default value.

**Path expansion:**
```json
"~/.minerva/conversations"
```
`~` is expanded to user's home directory.

### Common Variables

```bash
# AI Provider Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="AIza..."

# Service URLs
export OLLAMA_HOST="http://localhost:11434"
export LMSTUDIO_URL="http://localhost:1234/v1"

# Paths
export MINERVA_CHROMADB="${HOME}/chromadb_data"
export MINERVA_CONVERSATIONS="${HOME}/.minerva/conversations"
```

### Security Best Practices

**DO:**
- Store API keys in environment variables
- Use `.env` files (don't commit to git)
- Use `${VAR_NAME}` in config files
- Set variables in shell profile

**DON'T:**
- Hardcode API keys in config files
- Commit API keys to version control
- Share config files with hardcoded keys

## Complete Examples

### Example 1: All LM Studio (Desktop)

```json
{
  "ai_providers": [
    {
      "id": "lmstudio-local",
      "provider_type": "lmstudio",
      "base_url": "http://localhost:1234/v1",
      "embedding_model": "qwen2.5-7b-instruct",
      "llm_model": "qwen2.5-14b-instruct",
      "rate_limit": {
        "requests_per_minute": 60,
        "concurrency": 1
      }
    }
  ],
  "indexing": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "collections": [
      {
        "collection_name": "personal-notes",
        "description": "Personal notes from Bear app covering software development, research, and project documentation",
        "json_file": "./notes.json",
        "chunk_size": 1200,
        "ai_provider_id": "lmstudio-local"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "lmstudio-local",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

**Use case:** Desktop user, all local, no API costs

### Example 2: Hybrid (Ollama + LM Studio)

```json
{
  "ai_providers": [
    {
      "id": "ollama-indexing",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434",
      "embedding": {
        "model": "mxbai-embed-large:latest"
      },
      "llm": {
        "model": "llama3.1:8b"
      }
    },
    {
      "id": "lmstudio-chat",
      "provider_type": "lmstudio",
      "base_url": "http://localhost:1234/v1",
      "embedding_model": "qwen2.5-7b-instruct",
      "llm_model": "qwen2.5-14b-instruct",
      "rate_limit": {
        "requests_per_minute": 45,
        "concurrency": 1
      }
    }
  ],
  "indexing": {
    "chromadb_path": "/Users/me/chromadb",
    "collections": [
      {
        "collection_name": "notes",
        "description": "Personal knowledge base",
        "json_file": "./notes.json",
        "ai_provider_id": "ollama-indexing"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "lmstudio-chat",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false
  },
  "server": {
    "chromadb_path": "/Users/me/chromadb",
    "default_max_results": 5
  }
}
```

**Use case:** Fast indexing with Ollama, better chat with LM Studio

### Example 3: Cloud (OpenAI)

```json
{
  "ai_providers": [
    {
      "id": "openai-cloud",
      "provider_type": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "embedding": {
        "model": "text-embedding-3-small"
      },
      "llm": {
        "model": "gpt-4o-mini"
      }
    }
  ],
  "indexing": {
    "chromadb_path": "${HOME}/chromadb_data",
    "collections": [
      {
        "collection_name": "research-papers",
        "description": "Academic research papers and technical documentation",
        "json_file": "./papers.json",
        "ai_provider_id": "openai-cloud"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "openai-cloud",
    "mcp_server_url": "http://localhost:8000/mcp",
    "enable_streaming": true
  },
  "server": {
    "chromadb_path": "${HOME}/chromadb_data",
    "default_max_results": 5
  }
}
```

**Use case:** High quality, willing to pay for API

### Example 4: Server Deployment

```json
{
  "ai_providers": [
    {
      "id": "ollama-server",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434",
      "embedding": {
        "model": "mxbai-embed-large:latest"
      },
      "llm": {
        "model": "llama3.1:8b"
      }
    }
  ],
  "indexing": {
    "chromadb_path": "/srv/minerva/chromadb_data",
    "collections": [
      {
        "collection_name": "team-knowledge",
        "description": "Shared team knowledge base and documentation",
        "json_file": "/srv/minerva/data/team-notes.json",
        "chunk_size": 1400,
        "ai_provider_id": "ollama-server"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "ollama-server",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "/var/minerva/conversations",
    "enable_streaming": false
  },
  "server": {
    "chromadb_path": "/srv/minerva/chromadb_data",
    "default_max_results": 5,
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**Use case:** Shared server for team access

## Migration from Legacy Configs

If you're upgrading from separate per-command configs, here's how to migrate.

### Legacy Index Config

**Old (index-config.json):**
```json
{
  "collection_name": "my_notes",
  "description": "Personal notes",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json"
}
```

**New (unified config):**
```json
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_data",
    "collections": [
      {
        "collection_name": "my_notes",
        "description": "Personal notes",
        "json_file": "./notes.json",
        "ai_provider_id": "ollama-local"
      }
    ]
  }
}
```

### Legacy Server Config

**Old (server-config.json):**
```json
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
```

**New (add to unified config):**
```json
{
  "server": {
    "chromadb_path": "./chromadb_data",
    "default_max_results": 5
  }
}
```

### Legacy Chat Config

**Old (chat-config.json):**
```json
{
  "chromadb_path": "./chromadb_data",
  "ai_provider": {
    "type": "ollama",
    "embedding": {"model": "mxbai-embed-large:latest"},
    "llm": {"model": "llama3.1:8b"}
  },
  "enable_streaming": true
}
```

**New (unified config):**
```json
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "chat": {
    "chat_provider_id": "ollama-local",
    "mcp_server_url": "http://localhost:8000/mcp",
    "enable_streaming": true
  },
  "server": {
    "chromadb_path": "./chromadb_data",
    "default_max_results": 5
  }
}
```

## Validation

### Built-in Validation

Validate your config before using it:

```bash
minerva config validate --config myconfig.json
```

**Success output:**
```
✓ Configuration is valid
✓ Found 2 AI provider(s)
✓ Found 1 collection(s) in indexing section
✓ Chat configuration is valid
✓ Server configuration is valid
```

**Error output:**
```
✗ Configuration validation failed

Errors:
- ai_providers[0].provider_type: Invalid value 'unknown'. Must be one of: ollama, lmstudio, openai, anthropic, gemini
- indexing.collections[0].ai_provider_id: References unknown provider 'missing-id'
- chat.chat_provider_id: Required field missing
```

### Common Validation Errors

**Missing required field:**
```
Error: indexing.collections[0].collection_name is required
```
Fix: Add the missing field.

**Invalid provider reference:**
```
Error: ai_provider_id 'my-provider' not found in ai_providers
```
Fix: Ensure the ID matches exactly (case-sensitive).

**Invalid path:**
```
Error: chromadb_path must be absolute path, got './chromadb'
```
Fix: Use absolute path like `/Users/me/chromadb` or `${HOME}/chromadb`.

**Invalid provider type:**
```
Error: provider_type must be one of: ollama, lmstudio, openai, anthropic, gemini
```
Fix: Use correct provider type name.

### Manual Validation

Check your config structure:

```bash
# Validate JSON syntax
cat config.json | python -m json.tool

# Check environment variables resolve
cat config.json | envsubst
```

## Best Practices

### Organization

**Single config for everything:**
```
project/
├── config.json              # One config file
├── chromadb_data/           # Shared ChromaDB
├── data/
│   ├── notes.json
│   └── books.json
└── .env                     # Environment variables
```

**Separate configs by environment:**
```
project/
├── configs/
│   ├── desktop.json         # Local desktop
│   ├── server.json          # Production server
│   └── dev.json             # Development
└── chromadb_data/
```

### Security

1. **Never commit API keys:**
   ```bash
   # .gitignore
   .env
   *-secrets.json
   ```

2. **Use environment variables:**
   ```json
   {"api_key": "${OPENAI_API_KEY}"}
   ```

3. **Use .env files:**
   ```bash
   # .env (don't commit!)
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

4. **Load .env before running:**
   ```bash
   source .env
   minerva index --config config.json
   ```

### Version Control

**Track configs:**
```bash
git add configs/*.json
git commit -m "feat: update AI provider config"
```

**Ignore secrets:**
```bash
# .gitignore
.env
*-local.json
chromadb_data/
```

### Testing

**Dry run before indexing:**
```bash
minerva config validate --config config.json
```

**Test with small dataset:**
```json
{
  "collections": [
    {
      "json_file": "./test-data/sample-10-notes.json"
    }
  ]
}
```

## See Also

- [LM Studio Setup Guide](LMSTUDIO_SETUP.md) - LM Studio installation and configuration
- [Chat Guide](CHAT_GUIDE.md) - Using the chat command
- [Note Schema](NOTE_SCHEMA.md) - JSON schema for notes
- [Main README](../README.md) - General documentation
