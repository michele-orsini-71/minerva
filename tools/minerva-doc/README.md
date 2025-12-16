# minerva-doc

Orchestrator for managing document-based knowledge base collections in Minerva.

## Overview

**minerva-doc** is a CLI tool that simplifies managing collections derived from structured documents (notes, books, articles). It provides an opinionated workflow for adding, updating, and serving document-based knowledge bases without manual configuration.

## What does minerva-doc handle?

- **Collection creation**: Add JSON-formatted documents to ChromaDB
- **AI provider selection**: Interactive setup for OpenAI, Gemini, Ollama, or LM Studio
- **Auto-description**: AI-generated collection descriptions
- **Collection updates**: Re-index with new data or different providers
- **Multi-collection serving**: Unified MCP server for all collections
- **Collision prevention**: Prevents name conflicts across minerva tools

## Use Cases

Use minerva-doc when you have structured documents in JSON format:
- **Bear notes** (exported via `bear-extractor`)
- **Zim archives** (extracted via `zim-extractor`)
- **Markdown books** (processed via `markdown-books-extractor`)
- **Custom document collections** (following Minerva's note schema)

## When to use minerva-doc vs minerva-kb

| Feature | minerva-doc | minerva-kb |
|---------|-------------|------------|
| **Input** | Pre-extracted JSON documents | Git repositories |
| **Auto-extraction** | No (uses extractors) | Yes (via repository-doc-extractor) |
| **Auto-watching** | No (manual updates) | Yes (file watcher for repos) |
| **Use case** | Static document collections | Live codebases |
| **Examples** | Bear notes, Zim dumps, books | Source code, documentation repos |

## Installation

### Prerequisites

```bash
# Install Minerva core
cd /path/to/minerva
pip install -e .

# Install minerva-common (shared library)
pipx install tools/minerva-common
```

### Install minerva-doc

```bash
# From Minerva project root
cd tools/minerva-doc

# Install with pipx (recommended)
pipx install .

# Inject minerva-common dependency
pipx inject minerva-doc ../minerva-common

# Verify installation
minerva-doc --version
minerva-doc --help
```

## Quick Start

### Add a collection (<2 minutes)

```bash
# Extract notes (using Bear as example)
bear-extractor "Bear Notes.bear2bk" -o notes.json

# Add to minerva-doc
minerva-doc add notes.json --name my-notes

# Follow interactive prompts:
# 1. Select AI provider (OpenAI, Gemini, Ollama, LM Studio)
# 2. Choose models (or use defaults)
# 3. Provide or auto-generate description
# Collection is created and indexed automatically!

# Start MCP server
minerva-doc serve
```

That's it! Your collection is now searchable via Claude Desktop.

## Commands

### `add` - Add a collection

```bash
minerva-doc add <json-file> --name <collection-name>
```

Creates and indexes a new collection from pre-extracted JSON documents.

**Example:**
```bash
minerva-doc add bear-notes.json --name notes
minerva-doc add wiki.json --name wikipedia
```

### `list` - List all collections

```bash
minerva-doc list [--format table|json]
```

Shows all collections in ChromaDB, indicating which are managed by minerva-doc.

**Example:**
```bash
minerva-doc list
minerva-doc list --format json
```

### `status` - Check collection details

```bash
minerva-doc status <collection-name>
```

Displays detailed information about a specific collection.

**Example:**
```bash
minerva-doc status notes
```

### `update` - Re-index a collection

```bash
minerva-doc update <collection-name> <json-file>
```

Updates an existing collection with new data or different AI provider.

**Example:**
```bash
minerva-doc update notes updated-notes.json
```

### `remove` - Delete a collection

```bash
minerva-doc remove <collection-name>
```

Removes collection from ChromaDB and minerva-doc registry.

**Example:**
```bash
minerva-doc remove notes
```

### `serve` - Start MCP server

```bash
minerva-doc serve
```

Starts the Minerva MCP server, exposing all collections to Claude Desktop.

## Shared Infrastructure

minerva-doc uses shared infrastructure under `~/.minerva/`:

```
~/.minerva/
├── chromadb/              # Shared ChromaDB storage
├── server.json            # Shared MCP server config
└── apps/
    ├── minerva-doc/       # minerva-doc app data
    │   └── collections.json   # Collection registry
    └── minerva-kb/        # minerva-kb app data (if installed)
        └── collections.json   # Repo collection registry
```

## Multi-Tool Compatibility

minerva-doc works alongside minerva-kb:
- **Shared ChromaDB**: Both tools use the same vector database
- **Shared server**: Single MCP server exposes all collections
- **Collision prevention**: Tools prevent duplicate collection names
- **Cross-tool visibility**: `list` and `serve` show collections from both tools

## Examples

### Bear Notes Workflow

```bash
# 1. Extract Bear notes
bear-extractor "Bear Notes.bear2bk" -o bear-notes.json

# 2. Add to minerva-doc
minerva-doc add bear-notes.json --name bear-notes

# 3. Query via Claude Desktop
minerva-doc serve
```

### Zim Archive Workflow

```bash
# 1. Extract from Zim
zim-extractor wikipedia.zim -l 10000 -o wiki.json

# 2. Add to minerva-doc
minerva-doc add wiki.json --name wikipedia

# 3. Start server
minerva-doc serve
```

### Markdown Book Workflow

```bash
# 1. Extract markdown book
markdown-books-extractor alice-in-wonderland.md -o alice.json

# 2. Add to minerva-doc
minerva-doc add alice.json --name alice

# 3. Check status
minerva-doc status alice
```

## Troubleshooting

### "Collection already exists" error

This means a collection with that name already exists in ChromaDB. Check which tool manages it:

```bash
minerva-doc list
minerva-kb list  # if minerva-kb is installed
```

### "Not managed by minerva-doc" error

You're trying to update/remove a collection not created by minerva-doc. Use the tool that created it:
- For repos: `minerva-kb remove <name>`
- For unmanaged collections: Use `minerva` CLI directly

### Permission errors

Check `~/.minerva/` directory permissions:

```bash
ls -la ~/.minerva
chmod 700 ~/.minerva
chmod 600 ~/.minerva/server.json
```

## Development

### Run tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=minerva_doc --cov-report=html
```

### Install in development mode

```bash
pip install -e .
```

## License

MIT License - see LICENSE file for details.

## Links

- **Minerva documentation**: See main repository README
- **minerva-kb guide**: docs/MINERVA_KB_GUIDE.md
- **minerva-common API**: docs/MINERVA_COMMON.md
- **Extractor guide**: docs/EXTRACTOR_GUIDE.md
