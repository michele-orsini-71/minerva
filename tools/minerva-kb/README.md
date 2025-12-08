# minerva-kb

Orchestrator tool for managing Minerva repository-based knowledge base collections.

## Overview

`minerva-kb` is a unified CLI for the complete lifecycle of repository-based knowledge base collections. It replaces the monolithic setup wizard and provides simple commands for adding, listing, updating, watching, and removing collections.

## Installation

```bash
# From minerva repository root
pipx install tools/minerva-kb
```

## Prerequisites

- Python 3.10 or higher
- `minerva` (core CLI): `pipx install .`
- `repository-doc-extractor`: `pipx install extractors/repository-doc-extractor`
- `local-repo-watcher`: `pipx install tools/local-repo-watcher`

## Quick Start

### Add Your First Collection

```bash
minerva-kb add /path/to/your/repository
```

This will:
1. Generate a description from your README
2. Prompt for AI provider selection (OpenAI, Gemini, Ollama, LM Studio)
3. Extract and index your repository
4. Create a searchable knowledge base

### List All Collections

```bash
minerva-kb list
```

### Check Collection Status

```bash
minerva-kb status <collection-name>
```

### Start File Watcher

```bash
minerva-kb watch <collection-name>
```

### Manual Re-indexing

```bash
minerva-kb sync <collection-name>
```

### Remove Collection

```bash
minerva-kb remove <collection-name>
```

## Command Reference

### `minerva-kb add <repo-path>`

Create a new collection or update an existing collection's AI provider.

**Options:**
- `<repo-path>`: Path to repository to index

**Behavior:**
- Collection name is derived from repository folder name
- Checks if collection already exists
- If new: prompts for provider, extracts, and indexes
- If exists: prompts to change provider (re-indexes if yes)

### `minerva-kb list [--format table|json]`

Display all managed collections with status information.

**Options:**
- `--format`: Output format (default: table)

**Display includes:**
- Collection name
- Repository path
- AI provider and models
- Chunk count
- Watcher status (running/stopped with PID)
- Last indexed timestamp

### `minerva-kb status <collection-name>`

Display detailed status for a specific collection.

**Shows:**
- Collection name and repository path
- AI provider configuration
- ChromaDB collection status
- Configuration file paths
- Watcher status and configuration
- Last modification timestamp

### `minerva-kb sync <collection-name>`

Manually trigger re-indexing for a collection.

**Use case:** After bulk changes to repository outside of watcher's scope.

### `minerva-kb watch [<collection-name>]`

Start file watcher for a collection.

**Behavior:**
- If collection name provided: starts watcher for that collection
- If no name: interactive selection menu
- Runs in foreground (Ctrl+C to stop)

### `minerva-kb remove <collection-name>`

Delete collection and all associated data.

**Deletes:**
- ChromaDB collection and embeddings
- Configuration files (index, watcher)
- Extracted repository data

**Note:** Repository files are NOT affected.

## Configuration

All configuration files are stored in `~/.minerva/apps/minerva-kb/`:

- `<collection>-index.json`: Index configuration
- `<collection>-watcher.json`: Watcher configuration
- `<collection>-extracted.json`: Extracted repository data
- `server.json`: Shared MCP server configuration

ChromaDB data is stored in `~/.minerva/chromadb/`.

## Collection Naming

Collection names are automatically derived from repository folder names:

- Converted to lowercase
- Spaces → hyphens
- Only alphanumeric characters and hyphens
- 3-512 characters (ChromaDB requirement)

**Examples:**
- `/code/minerva` → `minerva`
- `/code/My Cool Project` → `my-cool-project`
- `/code/React_Component-Library` → `react-component-library`

## AI Providers

Supported providers:

1. **OpenAI** (cloud, requires API key)
   - Default embedding: text-embedding-3-small
   - Default LLM: gpt-4o-mini

2. **Google Gemini** (cloud, requires API key)
   - Default embedding: text-embedding-004
   - Default LLM: gemini-1.5-flash

3. **Ollama** (local, free)
   - You specify which models you've pulled

4. **LM Studio** (local, free)
   - You specify which models you've loaded

API keys are stored securely in OS keychain via `minerva keychain`.

## Troubleshooting

### Collection Not Found

```bash
minerva-kb list  # See all available collections
```

### Watcher Already Running

```bash
kill <PID>  # Stop existing watcher
minerva-kb watch <collection>  # Start new watcher
```

### API Key Invalid

```bash
minerva keychain set OPENAI_API_KEY  # Update key
minerva-kb sync <collection>  # Re-index if needed
```

### Ollama/LM Studio Not Running

Start the service before running `minerva-kb add`:

```bash
# Ollama
ollama serve

# LM Studio
# Start LM Studio application
```

## Examples

### Add Second Collection

```bash
minerva-kb add ~/code/my-docs
# Follow prompts to select provider
# Collection created and indexed
```

### Change Provider for Existing Collection

```bash
minerva-kb add ~/code/my-project
# Detects existing collection
# Prompt: "Change AI provider? [y/N]"
# Enter 'y' to change provider
# Collection re-indexed with new provider
```

### Watch Multiple Collections

```bash
# Terminal 1
minerva-kb watch project-1

# Terminal 2
minerva-kb watch project-2
```

## Development

### Running Tests

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=minerva_kb
```

## See Also

- [Minerva Documentation](../../docs/)
- [MINERVA_KB_GUIDE.md](../../docs/MINERVA_KB_GUIDE.md) - Comprehensive guide
- [MINERVA_KB_EXAMPLES.md](../../docs/MINERVA_KB_EXAMPLES.md) - Example workflows
- [MIGRATE_TO_MINERVA_KB.md](../../docs/MIGRATE_TO_MINERVA_KB.md) - Migration guide

## License

MIT
