# Configuration Guide - Multi-Provider AI RAG System

This guide explains how to configure the Bear Notes RAG (Retrieval-Augmented Generation) system with support for multiple AI providers (Ollama, OpenAI, Google Gemini, Azure OpenAI).

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Pipeline Configuration (Creating Collections)](#pipeline-configuration)
3. [MCP Server Configuration (Querying Collections)](#mcp-server-configuration)
4. [Multi-Provider Setup](#multi-provider-setup)
5. [Example Workflows](#example-workflows)

---

## Architecture Overview

The system has two main components with **separate configuration files**:

### 1. Pipeline (`markdown-notes-cag-data-creator`)
**Purpose**: Creates ChromaDB collections with embeddings
**Config Location**: `configs/*.json` or `markdown-notes-cag-data-creator/collections/*.json`
**Key Decision**: **Which AI provider to use for embeddings and LLM**

### 2. MCP Server (`markdown-notes-mcp-server`)
**Purpose**: Queries existing collections via Claude Desktop
**Config Location**: `markdown-notes-mcp-server/config.json`
**Key Decision**: **Where ChromaDB data is stored**

### Important Distinction

- **Pipeline config** specifies AI models → creates collections → stores provider metadata IN the collection
- **MCP server config** does NOT specify AI models → reads provider metadata FROM each collection → uses the correct provider automatically

This design allows multiple collections to use different providers (e.g., one collection with Ollama, another with OpenAI).

---

## Pipeline Configuration

### Basic Structure

Pipeline configurations are JSON files that specify how to create a ChromaDB collection:

```json
{
  "collection_name": "my_notes",
  "description": "Personal notes about software development and project management",
  "chromadb_path": "./chromadb_data",
  "json_file": "./test-data/my-notes.json",
  "chunk_size": 1200,
  "forceRecreate": false,
  "skipAiValidation": false,
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

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `collection_name` | string | ✅ | Unique identifier (alphanumeric, `-`, `_`) |
| `description` | string | ✅ | When to use this collection (for AI agents) |
| `chromadb_path` | string | ✅ | Path to ChromaDB storage directory |
| `json_file` | string | ✅ | Path to Bear notes JSON file |
| `chunk_size` | integer | ❌ | Characters per chunk (default: 1200) |
| `forceRecreate` | boolean | ❌ | Delete existing collection (default: false) |
| `skipAiValidation` | boolean | ❌ | Skip description quality check (default: false) |
| `ai_provider` | object | ✅ | AI provider configuration (see below) |

### AI Provider Configuration

The `ai_provider` section specifies which AI service to use:

#### Ollama (Local, No API Key)

```json
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
```

**Prerequisites**:
```bash
# Start Ollama service
ollama serve

# Pull required models
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b
```

#### OpenAI (Cloud, Requires API Key)

```json
"ai_provider": {
  "type": "openai",
  "embedding": {
    "model": "text-embedding-3-small",
    "base_url": "https://api.openai.com/v1",
    "api_key": "${OPENAI_API_KEY}"
  },
  "llm": {
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1",
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

**Prerequisites**:
```bash
# Set environment variable (before running pipeline)
export OPENAI_API_KEY="sk-your-api-key-here"
```

**Note**: The `${OPENAI_API_KEY}` syntax is a template - the pipeline resolves it from environment variables at runtime.

#### Google Gemini (Cloud, Requires API Key)

```json
"ai_provider": {
  "type": "gemini",
  "embedding": {
    "model": "text-embedding-004",
    "base_url": null,
    "api_key": "${GEMINI_API_KEY}"
  },
  "llm": {
    "model": "gemini-1.5-flash",
    "base_url": null,
    "api_key": "${GEMINI_API_KEY}"
  }
}
```

**Prerequisites**:
```bash
# Set environment variable
export GEMINI_API_KEY="your-gemini-api-key-here"
```

---

## MCP Server Configuration

### File Location

`markdown-notes-mcp-server/config.json`

### Simple Structure

```json
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "default_max_results": 3
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chromadb_path` | string | ✅ | **Absolute path** to ChromaDB directory |
| `default_max_results` | integer | ✅ | Number of search results (1-100) |

### Why No AI Provider Configuration?

The MCP server **reads AI provider information from collection metadata**. When you create a collection with the pipeline, it stores:

- `embedding_provider`: "ollama" / "openai" / "gemini"
- `embedding_model`: "mxbai-embed-large:latest"
- `embedding_dimension`: 1024
- `embedding_base_url`: "http://localhost:11434"
- `embedding_api_key_ref`: "${OPENAI_API_KEY}" or null
- `llm_model`: "llama3.1:8b"

The MCP server automatically uses the correct provider for each collection when searching.

---

## Multi-Provider Setup

### Example: Multiple Collections with Different Providers

You can have collections using different AI providers in the same ChromaDB database:

```bash
# Collection 1: Personal notes with Ollama (local, free)
python full_pipeline.py --config configs/bear-notes-ollama.json

# Collection 2: Work docs with OpenAI (cloud, requires API key)
export OPENAI_API_KEY="sk-..."
python full_pipeline.py --config configs/work-docs-openai.json

# Collection 3: Research with Gemini (cloud, requires API key)
export GEMINI_API_KEY="..."
python full_pipeline.py --config configs/research-gemini.json
```

All three collections coexist in the same ChromaDB database. The MCP server handles them transparently.

### MCP Server Behavior

When the MCP server starts, it discovers all collections and checks provider availability:

```
[INFO] Discovering collections in ChromaDB...
[INFO] Found 3 collections

[INFO] Collection: bear_notes_ollama
[INFO]   Provider: ollama (mxbai-embed-large:latest)
[INFO]   Status: ✓ Available (dimension: 1024)

[INFO] Collection: work_docs_openai
[INFO]   Provider: openai (text-embedding-3-small)
[INFO]   Status: ✗ Unavailable
[INFO]   Reason: Missing API key - OPENAI_API_KEY not found

[INFO] Collection: research_gemini
[INFO]   Provider: gemini (text-embedding-004)
[INFO]   Status: ✓ Available (dimension: 768)

[INFO] Summary: 2 available, 1 unavailable
[INFO] MCP server ready (some collections unavailable)
```

Collections with unavailable providers are marked and skipped during searches.

---

## Example Workflows

### Workflow 1: Local-Only Setup (Ollama)

**Best for**: Privacy, no internet dependency, no costs

```bash
# 1. Start Ollama
ollama serve

# 2. Pull models
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b

# 3. Create collection
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-ollama.json

# 4. Configure MCP server
# Edit markdown-notes-mcp-server/config.json:
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "default_max_results": 3
}

# 5. Run MCP server in Claude Desktop
# (see README for Claude Desktop integration)
```

### Workflow 2: Cloud Setup (OpenAI)

**Best for**: Better embedding quality, faster processing

```bash
# 1. Set API key
export OPENAI_API_KEY="sk-your-key-here"

# 2. Create collection
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-openai.json

# 3. MCP server config (same as above)
# No changes needed - server reads provider from collection metadata

# 4. When starting Claude Desktop, ensure API key is set:
# Add to ~/.zshrc or ~/.bashrc:
export OPENAI_API_KEY="sk-your-key-here"
```

### Workflow 3: Hybrid Setup (Multiple Providers)

**Best for**: Flexibility - use local for personal notes, cloud for work

```bash
# Personal notes - Ollama (free, local)
ollama serve
python full_pipeline.py --config configs/personal-ollama.json

# Work notes - OpenAI (cloud, better quality)
export OPENAI_API_KEY="sk-..."
python full_pipeline.py --config configs/work-openai.json

# Configure MCP server (points to shared ChromaDB)
{
  "chromadb_path": "/absolute/path/to/shared/chromadb_data",
  "default_max_results": 3
}

# When querying, MCP server automatically uses the right provider per collection
```

---

## Troubleshooting

### "Missing API key" Error During Pipeline

**Problem**: Pipeline fails with `APIKeyMissingError`

**Solution**:
```bash
# Check which provider you're using in config file
cat configs/your-config.json | grep '"type"'

# Set the corresponding environment variable
export OPENAI_API_KEY="sk-..."  # For OpenAI
export GEMINI_API_KEY="..."      # For Gemini

# Verify it's set
echo $OPENAI_API_KEY

# Rerun pipeline
python full_pipeline.py --config configs/your-config.json
```

### "Collection unavailable" in MCP Server

**Problem**: MCP server marks collection as unavailable

**Diagnosis**:
```bash
# Check collection metadata
python -c "
import chromadb
client = chromadb.PersistentClient(path='chromadb_data')
collection = client.get_collection('your_collection')
print(collection.metadata)
"

# Look for:
# - embedding_provider: which provider is needed
# - embedding_api_key_ref: which env var is needed
```

**Solution**:
```bash
# For Ollama collections
ollama serve

# For OpenAI/Gemini collections
export OPENAI_API_KEY="sk-..."  # or GEMINI_API_KEY
# Restart Claude Desktop to pick up environment variable
```

### "Embedding dimension mismatch" Error

**Problem**: Trying to query with different embedding model than collection was created with

**Solution**: You must recreate the collection with `forceRecreate: true`:

```json
{
  "collection_name": "my_notes",
  "forceRecreate": true,
  "ai_provider": {
    "type": "openai",  // Changed from ollama
    ...
  }
}
```

⚠️ **Warning**: This deletes all existing data in the collection.

---

## Configuration File Locations Reference

```
search-markdown-notes/
├── configs/                              # Pipeline configs (recommended location)
│   ├── example-ollama.json              # Ollama template
│   ├── example-openai.json              # OpenAI template
│   └── example-gemini.json              # Gemini template
│
├── markdown-notes-cag-data-creator/
│   └── collections/                      # Alternative pipeline config location
│       ├── bear_notes_config.json       # Legacy format (no ai_provider section)
│       └── wikipedia_history_config.json
│
├── markdown-notes-mcp-server/
│   ├── config.json                       # MCP server config (simple)
│   └── config.schema.json                # JSON schema for validation
│
└── chromadb_data/                        # ChromaDB storage (created by pipeline)
```

---

## See Also

- **Pipeline README**: `markdown-notes-cag-data-creator/README.md`
- **MCP Server README**: `markdown-notes-mcp-server/README.md`
- **Main CLAUDE.md**: Project-wide documentation
