# minerva-kb

Orchestrator tool for managing Minerva repository-based knowledge base collections.

## Overview

`minerva-kb` is a unified CLI for the complete lifecycle of repository-based knowledge base collections.

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

**Example output:**

```
$ minerva-kb add ~/code/my-project

Collection name: my-project

✓ Found README.md
✓ Generated description: A Python library for data processing and analysis

Select AI provider:
1. OpenAI (cloud, requires API key)
2. Google Gemini (cloud, requires API key)
3. Ollama (local, free)
4. LM Studio (local, free)

Enter choice [1-4]: 1

✓ API key found in keychain (OPENAI_API_KEY)
✓ API key validated

Use default models?
  Embedding: text-embedding-3-small
  LLM: gpt-4o-mini
[Y/n]: y

✓ Extracting repository documentation...
  Processed 42 files

✓ Indexing collection...
  Created 127 chunks

✓ Collection 'my-project' created successfully!

Next steps:
  - Start watcher: minerva-kb watch my-project
  - Check status: minerva-kb status my-project
```

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

**Example output (table format):**

```
$ minerva-kb list

Collections (3):

my-project
  Repository: /Users/michele/code/my-project
  Provider: openai (gpt-4o-mini + text-embedding-3-small)
  Chunks: 1,247
  Watcher: ✓ Running (PID 12345)
  Last indexed: 2025-12-08 14:32:15

docs-collection
  Repository: /Users/michele/documents/notes
  Provider: ollama (llama3.1:8b + mxbai-embed-large:latest)
  Chunks: 523
  Watcher: ⚠ Not running
  Last indexed: 2025-12-07 09:15:42

legacy-kb
  Repository: /Users/michele/old-project
  Provider: gemini (gemini-1.5-flash + text-embedding-004)
  Chunks: 2,891
  Watcher: ✓ Running (PID 12378)
  Last indexed: 2025-12-08 11:20:33
```

**Example output (JSON format):**

```
$ minerva-kb list --format json

[
  {
    "name": "my-project",
    "repository_path": "/Users/michele/code/my-project",
    "provider": {
      "type": "openai",
      "embedding_model": "text-embedding-3-small",
      "llm_model": "gpt-4o-mini"
    },
    "chunks": 1247,
    "watcher": {
      "running": true,
      "pid": 12345
    },
    "last_indexed": "2025-12-08T14:32:15Z"
  },
  {
    "name": "docs-collection",
    "repository_path": "/Users/michele/documents/notes",
    "provider": {
      "type": "ollama",
      "embedding_model": "mxbai-embed-large:latest",
      "llm_model": "llama3.1:8b"
    },
    "chunks": 523,
    "watcher": {
      "running": false,
      "pid": null
    },
    "last_indexed": "2025-12-07T09:15:42Z"
  }
]
```

### `minerva-kb status <collection-name>`

Display detailed status for a specific collection.

**Shows:**
- Collection name and repository path
- AI provider configuration
- ChromaDB collection status
- Configuration file paths
- Watcher status and configuration
- Last modification timestamp

**Example output:**

```
$ minerva-kb status my-project

Collection: my-project
Repository: /Users/michele/code/my-project

AI Provider:
  Type: openai
  Embedding model: text-embedding-3-small
  LLM model: gpt-4o-mini
  API key: ✓ Stored in keychain (OPENAI_API_KEY)

ChromaDB:
  Status: ✓ Collection exists
  Chunks: 1,247
  Last modified: 2025-12-08 14:32:15

Configuration Files:
  Index config: ~/.minerva/apps/minerva-kb/my-project-index.json
  Watcher config: ~/.minerva/apps/minerva-kb/my-project-watcher.json
  Extracted data: ~/.minerva/apps/minerva-kb/my-project-extracted.json (2.3 MB)

Watcher:
  Status: ✓ Running (PID 12345)
  Watch patterns: .md, .mdx, .markdown, .rst, .txt
  Ignore patterns: .git, node_modules, .venv, __pycache__
  Debounce: 60 seconds
```

### `minerva-kb sync <collection-name>`

Manually trigger re-indexing for a collection.

**Use case:** After bulk changes to repository outside of watcher's scope.

**Example output:**

```
$ minerva-kb sync my-project

Syncing collection 'my-project'...

✓ Extracting repository documentation...
  Processed 45 files (3 new, 2 modified, 1 deleted)

✓ Indexing collection...
  Updated 137 chunks (127 existing, 8 new, 2 removed)

✓ Collection 'my-project' synced successfully!
```

### `minerva-kb watch [<collection-name>]`

Start file watcher for a collection.

**Behavior:**
- If collection name provided: starts watcher for that collection
- If no name: interactive selection menu
- Runs in foreground (Ctrl+C to stop)

**Example output:**

```
$ minerva-kb watch my-project

▶️ Starting watcher for 'my-project'... Press Ctrl+C to stop.

Watching: /Users/michele/code/my-project
Patterns: .md, .mdx, .markdown, .rst, .txt
Debounce: 60 seconds

[2025-12-08 14:45:23] Watcher started (PID 12456)
[2025-12-08 14:47:15] Change detected: docs/api.md
[2025-12-08 14:48:15] Re-indexing collection...
[2025-12-08 14:48:32] ✓ Re-indexed (128 chunks)

^C
[2025-12-08 14:50:01] Watcher stopped
```

### `minerva-kb remove <collection-name>`

Delete collection and all associated data.

**Deletes:**
- ChromaDB collection and embeddings
- Configuration files (index, watcher)
- Extracted repository data

**Note:** Repository files are NOT affected.

**Example output:**

```
$ minerva-kb remove my-project

Collection: my-project
Repository: /Users/michele/code/my-project
Provider: openai (gpt-4o-mini + text-embedding-3-small)
Chunks: 1,247

⚠️ WARNING: This will delete:
  - ChromaDB collection and all embeddings
  - Configuration files (~/.minerva/apps/minerva-kb/)
  - Extracted data (~/.minerva/apps/minerva-kb/my-project-extracted.json)

Your repository files will NOT be affected.

Type YES to confirm deletion: YES

✓ Stopping watcher (PID 12345)...
✓ Deleting configuration files...
  - my-project-index.json
  - my-project-watcher.json
  - my-project-extracted.json
✓ Deleting ChromaDB collection...

✓ Collection 'my-project' removed successfully!

Note: API keys remain in keychain
To remove: minerva keychain delete OPENAI_API_KEY
```

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

## FAQ

### How do I change the AI provider for a collection?

Run `minerva-kb add <repo-path>` again. The tool will detect the existing collection and prompt you to change the provider. This will trigger a full re-indexing with the new provider's embeddings.

### How do I rename a collection?

Collection names are derived from repository folder names and cannot be renamed directly. To rename:

1. Remove the old collection: `minerva-kb remove <old-name>`
2. Rename your repository folder
3. Add it again: `minerva-kb add <repo-path>`

### Where are my configs and data stored?

All minerva-kb data is stored in `~/.minerva/`:

- Configuration files: `~/.minerva/apps/minerva-kb/`
- ChromaDB data: `~/.minerva/chromadb/`
- API keys: OS keychain (via `minerva keychain`)

### How do I backup my collections?

To backup:

```bash
# Backup ChromaDB
tar -czf chromadb-backup.tar.gz ~/.minerva/chromadb/

# Backup configs
tar -czf configs-backup.tar.gz ~/.minerva/apps/minerva-kb/
```

To restore, extract both archives back to their original locations.

### Can I use different providers for different collections?

Yes! Each collection has its own provider configuration. You can mix and match:

- Collection A: OpenAI (cloud)
- Collection B: Ollama (local)
- Collection C: Gemini (cloud)

### What happens if I delete my repository folder?

The collection will still exist in ChromaDB with all indexed data. However:

- The watcher will fail (repository path doesn't exist)
- You cannot sync the collection (no source files)
- You can still search the collection via MCP

To clean up, run: `minerva-kb remove <collection-name>`

### How do I stop all watchers?

```bash
# List all collections with watcher status
minerva-kb list

# Kill each running watcher by PID
kill <PID1> <PID2> <PID3>
```

### Can I index non-repository folders?

Yes! The tool works with any directory containing documentation files (.md, .mdx, .rst, .txt). It doesn't require Git.

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
