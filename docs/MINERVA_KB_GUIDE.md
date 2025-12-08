# Minerva KB Complete Guide

A comprehensive guide to managing repository-based knowledge base collections with `minerva-kb`.

## Table of Contents

- [Introduction](#introduction)
- [Core Concepts](#core-concepts)
- [Workflows](#workflows)
- [Configuration](#configuration)
- [AI Provider Setup](#ai-provider-setup)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)
- [Migration Guide](#migration-guide)

---

## Introduction

### The Problem

Setting up a knowledge base collection from a repository traditionally required:

1. Manual extraction of documentation files
2. Configuration file creation and editing
3. Understanding ChromaDB, embeddings, and AI providers
4. Setting up file watchers for automatic updates
5. Repeating all steps for each additional repository

This process took 15+ minutes per repository and required deep technical knowledge.

### The Solution

`minerva-kb` is a unified orchestrator that manages the complete lifecycle of repository-based knowledge base collections. It provides:

- **Simple Commands**: `add`, `list`, `status`, `sync`, `watch`, `remove`
- **Automatic Configuration**: Generates all config files automatically
- **Smart Defaults**: Sensible defaults with easy customization
- **Multi-Collection Support**: Manage multiple repositories effortlessly
- **Provider Flexibility**: Switch between OpenAI, Gemini, Ollama, and LM Studio

### Benefits

- **Time Savings**: Add a second collection in <2 minutes (vs 15+ minutes manually)
- **Lower Barrier**: No need to understand ChromaDB internals or config schemas
- **Consistency**: All collections follow the same structure and conventions
- **Safety**: Built-in validation, confirmations, and rollback support
- **Observability**: Clear status reporting and error messages

---

## Core Concepts

### Collections

A **collection** is a searchable knowledge base derived from a repository's documentation. Each collection:

- Has a unique name (derived from repository folder name)
- Stores embeddings in ChromaDB
- Has configuration files for indexing and watching
- Can use any supported AI provider
- Is independent of other collections

**Example**: Repository at `/code/my-project` becomes collection `my-project`.

### AI Providers

An **AI provider** supplies two key services:

1. **Embedding Model**: Converts text chunks into vector embeddings for semantic search
2. **LLM Model**: Generates descriptions and optimizes search queries

Supported providers:

- **OpenAI** (cloud): Requires API key, pay-per-use, high quality
- **Google Gemini** (cloud): Requires API key, pay-per-use, fast and affordable
- **Ollama** (local): Free, runs locally, requires model downloads
- **LM Studio** (local): Free, runs locally, GUI for model management

**Important**: Each collection uses one provider. Embeddings from different providers are incompatible, so changing providers requires full re-indexing.

### File Watchers

A **file watcher** monitors a repository for changes and automatically re-indexes when documentation files are modified.

Key characteristics:

- Runs in foreground (not a daemon)
- Uses debouncing (waits 60 seconds after last change)
- Watches specific file patterns (`.md`, `.mdx`, `.rst`, `.txt`)
- Ignores common directories (`.git`, `node_modules`, `.venv`)
- Each collection can have its own watcher

**Example workflow**: Edit `docs/api.md` → watcher detects change → waits 60 seconds → re-extracts and re-indexes automatically.

### Configuration Files

`minerva-kb` stores all data in `~/.minerva/`:

```
~/.minerva/
├── chromadb/                           # ChromaDB vector database
│   └── [collection data]
└── apps/
    └── minerva-kb/
        ├── my-project-index.json       # Index configuration
        ├── my-project-watcher.json     # Watcher configuration
        ├── my-project-extracted.json   # Extracted repository data
        └── server.json                 # Shared MCP server config
```

**Key points**:

- Each collection has three files: `*-index.json`, `*-watcher.json`, `*-extracted.json`
- `server.json` is shared across all collections
- API keys are stored in OS keychain (not in config files)
- ChromaDB data is shared (single database for all collections)

### Collection Naming

Collection names are automatically derived from repository folder names using these rules:

1. Convert to lowercase
2. Replace spaces and underscores with hyphens
3. Remove all non-alphanumeric characters except hyphens
4. Collapse multiple consecutive hyphens
5. Trim leading and trailing hyphens
6. Validate length (3-512 characters, ChromaDB requirement)

**Examples**:

| Repository Path | Collection Name |
|----------------|-----------------|
| `/code/minerva` | `minerva` |
| `/code/My Cool Project` | `my-cool-project` |
| `/code/React_Component-Library` | `react-component-library` |
| `/code/API-v2.0` | `api-v2-0` |
| `/code/docs__2024` | `docs-2024` |

---

## Workflows

### Adding Your First Collection

**Goal**: Index a repository and make it searchable via Claude Desktop.

**Steps**:

```bash
# 1. Navigate to your repository (or use absolute path)
cd ~/code/my-project

# 2. Add the collection
minerva-kb add .
```

**What happens**:

1. **Name derivation**: Collection name `my-project` is derived from folder name
2. **Description generation**:
   - If `README.md` exists: AI generates optimized description from content
   - If no README: Prompts you to enter description manually
3. **Provider selection**:
   - Shows menu with 4 provider options
   - For cloud providers (OpenAI/Gemini): checks for API key, prompts if missing, validates key
   - For local providers (Ollama/LM Studio): checks if service is running, shows instructions if not
   - Prompts for model selection (or use defaults)
4. **Extraction**: Calls `repository-doc-extractor` to extract documentation files
5. **Indexing**: Calls `minerva index` to create embeddings and store in ChromaDB
6. **Configuration**: Saves `*-index.json` and `*-watcher.json` files
7. **Server config**: Creates `server.json` if it doesn't exist

**Output example**:

```
Collection name: my-project

✓ Found README.md
✓ Generated description: A Python library for data processing and analysis

Select AI provider:
1. OpenAI (cloud, requires API key)
2. Google Gemini (cloud, requires API key)
3. Ollama (local, free)
4. LM Studio (local, free)

Enter choice [1-4]: 3

✓ Connected to Ollama at http://localhost:11434

Enter embedding model [mxbai-embed-large:latest]:
Enter LLM model [llama3.1:8b]:

✓ Extracting repository documentation...
  Processed 42 files

✓ Indexing collection...
  Created 127 chunks

✓ Collection 'my-project' created successfully!

Next steps:
  - Start watcher: minerva-kb watch my-project
  - Check status: minerva-kb status my-project
```

**Next steps**: Start the watcher (see [Starting a Watcher](#starting-a-watcher)).

### Adding a Second Collection

**Goal**: Add another repository without repeating the learning curve.

**Steps**:

```bash
minerva-kb add ~/code/documentation-site
```

**What's different**:

- You already have API keys set up (if using cloud providers)
- You already have `server.json` configured
- The process is much faster (typically <2 minutes)

**Key insight**: Each collection is independent. You can use different providers:

- Collection 1: OpenAI
- Collection 2: Ollama (local, free)
- Collection 3: Gemini

### Changing an Existing Collection's Provider

**Goal**: Switch from OpenAI to Ollama (or any provider change).

**Steps**:

```bash
# Run add command on existing repository
minerva-kb add ~/code/my-project
```

**What happens**:

1. Detects collection already exists (config files found)
2. Displays current provider configuration
3. Prompts: "Change AI provider? [y/N]"
4. If NO: exits with no changes
5. If YES:
   - Runs provider selection flow
   - Stops watcher if running
   - Re-extracts repository
   - Re-indexes with new provider (using `--force-recreate`)
   - Displays success with reminder to restart watcher

**Output example**:

```
Collection 'my-project' already exists.

Current provider:
  Type: openai
  Embedding: text-embedding-3-small
  LLM: gpt-4o-mini

Change AI provider? [y/N]: y

[Provider selection flow...]

✓ Stopping watcher (PID 12345)...
✓ Re-extracting repository...
✓ Re-indexing collection...
  Created 127 chunks

✓ Provider updated successfully!

⚠ Watcher was stopped during update.
  To restart: minerva-kb watch my-project
```

### Listing All Collections

**Goal**: See all managed collections and their status.

**Steps**:

```bash
# Table format (default)
minerva-kb list

# JSON format (for scripting)
minerva-kb list --format json
```

**What you see**:

- Collection name
- Repository path
- AI provider and models
- Chunk count (with thousands separator)
- Watcher status (✓ Running with PID or ⚠ Not running)
- Last indexed timestamp

**Use cases**:

- Check watcher status across all collections
- Find collection names for other commands
- Monitor chunk counts after updates
- Export collection metadata (JSON format)

### Checking Collection Status

**Goal**: Get detailed diagnostics for a specific collection.

**Steps**:

```bash
minerva-kb status my-project
```

**What you see**:

- **Collection info**: Name and repository path
- **AI provider**: Type, models, API key status
- **ChromaDB**: Collection exists, chunk count, last modified
- **Config files**: Paths to all three config files, extracted data file size
- **Watcher**: Status (running/stopped), patterns, debounce settings

**Use cases**:

- Troubleshoot issues (missing ChromaDB collection, config file mismatch)
- Verify provider configuration before changing
- Check watcher configuration (patterns, debounce)
- Find config file paths for manual editing (advanced)

### Starting a Watcher

**Goal**: Automatically re-index when documentation files change.

**Steps**:

```bash
# With collection name
minerva-kb watch my-project

# Interactive mode (prompts for selection)
minerva-kb watch
```

**What happens**:

1. Validates collection exists
2. Checks if watcher already running (exits if yes)
3. Starts `local-repo-watcher` with collection's watcher config
4. Runs in foreground (Ctrl+C to stop)

**Output example**:

```
▶️ Starting watcher for 'my-project'... Press Ctrl+C to stop.

Watching: /Users/michele/code/my-project
Patterns: .md, .mdx, .markdown, .rst, .txt
Debounce: 60 seconds

[2025-12-08 14:45:23] Watcher started (PID 12456)
[2025-12-08 14:47:15] Change detected: docs/api.md
[2025-12-08 14:48:15] Re-indexing collection...
[2025-12-08 14:48:32] ✓ Re-indexed (128 chunks)
```

**Best practices**:

- Run in a dedicated terminal window or tmux session
- Don't background with `&` (use tmux/screen instead for persistence)
- Monitor output for indexing errors
- Stop cleanly with Ctrl+C (not `kill -9`)

### Manual Re-indexing

**Goal**: Trigger re-indexing without waiting for watcher or after bulk changes.

**Steps**:

```bash
minerva-kb sync my-project
```

**Use cases**:

- Made bulk changes outside of watched patterns (e.g., added 50 files)
- Watcher was stopped during significant repository changes
- Want to verify indexing works after provider change
- Debugging indexing issues

**What happens**:

1. Validates collection exists
2. Calls `repository-doc-extractor` to re-extract
3. Calls `minerva index` to update ChromaDB
4. Reports chunk count changes

### Removing a Collection

**Goal**: Delete collection and all associated data.

**Steps**:

```bash
minerva-kb remove my-project
```

**What happens**:

1. Validates collection is managed (has config files)
2. Displays collection details and deletion warning
3. Prompts for confirmation: "Type YES to confirm deletion: "
4. If confirmed:
   - Stops watcher if running
   - Deletes config files (`*-index.json`, `*-watcher.json`, `*-extracted.json`)
   - Calls `minerva remove` to delete ChromaDB collection
5. Displays success with reminder about API keys

**Important notes**:

- Repository files are **NOT** affected
- API keys remain in keychain (shared across collections)
- Operation cannot be undone (except from backups)
- Must type `YES` exactly (case-sensitive)

---

## Configuration

### Index Configuration Schema

Located at `~/.minerva/apps/minerva-kb/<collection>-index.json`.

```json
{
  "chromadb_path": "/Users/michele/.minerva/chromadb",
  "collection": {
    "name": "my-project",
    "description": "A Python library for data processing and analysis",
    "json_file": "/Users/michele/.minerva/apps/minerva-kb/my-project-extracted.json",
    "chunk_size": 1200,
    "force_recreate": false,
    "skip_ai_validation": false
  },
  "provider": {
    "provider_type": "openai",
    "base_url": "https://api.openai.com/v1",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini",
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

**Key fields**:

- `chromadb_path`: Absolute path to ChromaDB database (shared across collections)
- `collection.name`: Sanitized collection name
- `collection.description`: Optimized description for RAG search
- `collection.json_file`: Path to extracted repository data
- `collection.chunk_size`: Target characters per chunk (default 1200)
- `provider.provider_type`: One of `openai`, `gemini`, `ollama`, `lmstudio`
- `provider.api_key`: Environment variable reference (resolved at runtime)

### Watcher Configuration Schema

Located at `~/.minerva/apps/minerva-kb/<collection>-watcher.json`.

```json
{
  "repository_path": "/Users/michele/code/my-project",
  "collection_name": "my-project",
  "extracted_json_path": "/Users/michele/.minerva/apps/minerva-kb/my-project-extracted.json",
  "index_config_path": "/Users/michele/.minerva/apps/minerva-kb/my-project-index.json",
  "debounce_seconds": 60.0,
  "include_extensions": [".md", ".mdx", ".markdown", ".rst", ".txt"],
  "ignore_patterns": [".git", "node_modules", ".venv", "__pycache__"]
}
```

**Key fields**:

- `repository_path`: Absolute path to source repository
- `collection_name`: Collection identifier (matches index config)
- `extracted_json_path`: Where extractor writes output
- `index_config_path`: Where indexer reads configuration
- `debounce_seconds`: Wait time after last change before re-indexing (default 60)
- `include_extensions`: File patterns to watch
- `ignore_patterns`: Directories to skip

### Server Configuration Schema

Located at `~/.minerva/apps/minerva-kb/server.json` (shared across all collections).

```json
{
  "chromadb_path": "/Users/michele/.minerva/chromadb",
  "default_max_results": 5,
  "host": "127.0.0.1",
  "port": 8337
}
```

**Key fields**:

- `chromadb_path`: Same ChromaDB path used by all collections
- `default_max_results`: Default number of search results (1-15)
- `host`: HTTP host (for `minerva serve --http`)
- `port`: HTTP port (for `minerva serve --http`)

**Auto-creation**: This file is created automatically on first `minerva-kb add` if missing.

### Environment Variables

API keys are stored in OS keychain and referenced via environment variables:

- `${OPENAI_API_KEY}`: OpenAI API key
- `${GEMINI_API_KEY}`: Google Gemini API key

**Management commands**:

```bash
# Set API key
minerva keychain set OPENAI_API_KEY

# Get API key (for debugging)
minerva keychain get OPENAI_API_KEY

# Delete API key
minerva keychain delete OPENAI_API_KEY
```

**Security**: Keys are stored in OS-native secure storage (Keychain on macOS, Secret Service on Linux).

---

## AI Provider Setup

### OpenAI

**Requirements**: OpenAI account and API key.

**Setup steps**:

1. Create account at https://platform.openai.com/
2. Navigate to API keys section
3. Create new secret key
4. Run `minerva keychain set OPENAI_API_KEY`
5. Paste key when prompted

**Default models**:

- Embedding: `text-embedding-3-small` (cost-effective, high quality)
- LLM: `gpt-4o-mini` (fast, affordable)

**Cost considerations**:

- Embeddings: ~$0.02 per 1M tokens
- LLM calls: ~$0.15 per 1M input tokens
- Typical repository (~100 docs): ~$0.10-0.50 to index

**Recommended for**: Production use, high-quality embeddings, consistent performance.

### Google Gemini

**Requirements**: Google Cloud account and Gemini API key.

**Setup steps**:

1. Create account at https://makersuite.google.com/app/apikey
2. Create API key
3. Run `minerva keychain set GEMINI_API_KEY`
4. Paste key when prompted

**Default models**:

- Embedding: `text-embedding-004` (latest model)
- LLM: `gemini-1.5-flash` (fast, affordable)

**Cost considerations**:

- Embeddings: Free up to generous limits
- LLM calls: Very affordable pricing
- Typical repository: Often free under quota

**Recommended for**: Cost-conscious users, fast iteration, experimentation.

### Ollama

**Requirements**: Ollama installed and running locally.

**Setup steps**:

1. Install Ollama:
   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Start Ollama service:
   ```bash
   ollama serve
   ```

3. Pull required models:
   ```bash
   # Embedding model (required)
   ollama pull mxbai-embed-large:latest

   # LLM model (required)
   ollama pull llama3.1:8b
   ```

4. Verify models available:
   ```bash
   ollama list
   ```

**Default models**:

- Embedding: `mxbai-embed-large:latest` (high quality, local)
- LLM: `llama3.1:8b` (good balance of quality and speed)

**Performance considerations**:

- Requires 8GB+ RAM for `llama3.1:8b`
- Embedding generation: slower than cloud (but free)
- Typical repository (~100 docs): 5-10 minutes to index

**Recommended for**: Privacy-conscious users, offline work, avoiding API costs.

### LM Studio

**Requirements**: LM Studio desktop application.

**Setup steps**:

1. Download from https://lmstudio.ai/
2. Install and launch application
3. Download models via LM Studio's UI:
   - Search for embedding models (e.g., `nomic-embed-text`)
   - Search for LLM models (e.g., `llama-3.1-8b`)
4. Start local server (button in LM Studio UI)
5. Verify server running:
   ```bash
   curl http://localhost:1234/v1/models
   ```

**Default models**:

- Embedding: User's choice (specify during `minerva-kb add`)
- LLM: User's choice (specify during `minerva-kb add`)

**Performance considerations**:

- Similar to Ollama (local, free, requires good hardware)
- GUI makes model management easier
- OpenAI-compatible API (easy integration)

**Recommended for**: Users who prefer GUI, want to experiment with different models, local-first setup.

---

## Troubleshooting

### Collection Not Found

**Error**:
```
❌ Collection 'my-project' not found
```

**Causes**:

1. Collection name typo
2. Collection was never created
3. Collection was removed

**Solutions**:

```bash
# List all collections to find correct name
minerva-kb list

# Check if config files exist
ls ~/.minerva/apps/minerva-kb/
```

### API Key Invalid or Missing

**Error**:
```
❌ Failed to connect to OpenAI: Invalid API key
```

**Causes**:

1. API key never set
2. API key expired or revoked
3. Insufficient API credits

**Solutions**:

```bash
# Set new API key
minerva keychain set OPENAI_API_KEY

# Verify key is set
minerva keychain get OPENAI_API_KEY

# Re-index collection if needed
minerva-kb sync my-project
```

### Ollama Not Running

**Error**:
```
❌ Cannot connect to Ollama at http://localhost:11434
```

**Causes**:

1. Ollama service not started
2. Ollama running on different port
3. Ollama not installed

**Solutions**:

```bash
# Start Ollama
ollama serve

# Check if running
curl http://localhost:11434/api/tags

# If different port, update config manually (advanced)
```

### LM Studio Not Running

**Error**:
```
❌ Cannot connect to LM Studio at http://localhost:1234
```

**Causes**:

1. LM Studio not started
2. Local server not enabled in LM Studio
3. Models not loaded

**Solutions**:

1. Open LM Studio application
2. Click "Start Server" button
3. Verify models are loaded
4. Retry `minerva-kb add`

### Watcher Already Running

**Error**:
```
⚠️ Watcher already running for 'my-project' (PID 12345)
```

**Causes**:

1. Watcher started in another terminal
2. Previous watcher didn't shut down cleanly

**Solutions**:

```bash
# Stop existing watcher
kill 12345

# Or force kill if unresponsive
kill -9 12345

# Start new watcher
minerva-kb watch my-project
```

### Collection Name Conflict

**Error**:
```
❌ Collection 'my-project' already exists in ChromaDB
⚠️ This collection was not created by minerva-kb
```

**Causes**:

1. Collection created manually outside minerva-kb
2. Previous minerva-kb run left orphaned collection
3. Name collision with different repository

**Solutions**:

```bash
# Option 1: Abort and choose different name
# (rename repository folder)

# Option 2: Wipe and recreate
# (prompted during add command)
minerva-kb add /path/to/repo
# Choose option 2 when prompted
```

### Extraction Failed

**Error**:
```
❌ Extraction failed: repository-doc-extractor exited with code 1
```

**Causes**:

1. Repository path doesn't exist
2. Permission denied (can't read files)
3. repository-doc-extractor not installed

**Solutions**:

```bash
# Verify repository path
ls /path/to/repository

# Check permissions
ls -la /path/to/repository

# Verify extractor installed
which repository-doc-extractor

# Reinstall if missing
pipx install extractors/repository-doc-extractor
```

### Indexing Failed

**Error**:
```
❌ Indexing failed: minerva index exited with code 3
```

**Causes**:

1. ChromaDB connection error
2. Provider API error (rate limit, invalid key)
3. Corrupted extracted JSON

**Solutions**:

```bash
# Check ChromaDB directory
ls ~/.minerva/chromadb/

# Check extracted JSON validity
python -c "import json; json.load(open('/path/to/extracted.json'))"

# Check provider (if cloud)
minerva keychain get OPENAI_API_KEY

# Retry with verbose output
minerva index --config /path/to/index-config.json --verbose
```

### Watcher Not Detecting Changes

**Symptoms**: Modify files but collection doesn't re-index.

**Causes**:

1. Watcher not running
2. File extension not in watch patterns
3. File in ignored directory
4. Debounce delay (wait 60 seconds)

**Solutions**:

```bash
# Check watcher status
minerva-kb list  # Look for "⚠ Not running"

# Check watcher config
minerva-kb status my-project

# Verify file should be watched
# Included: .md, .mdx, .markdown, .rst, .txt
# Excluded: .git, node_modules, .venv, __pycache__

# Manual sync as workaround
minerva-kb sync my-project
```

### ChromaDB Collection Missing

**Error** (from `minerva-kb status`):
```
ChromaDB:
  Status: ❌ Collection missing
```

**Causes**:

1. Indexing never completed successfully
2. ChromaDB database corrupted
3. Collection manually deleted

**Solutions**:

```bash
# Re-index collection
minerva-kb sync my-project

# If sync fails, remove and re-add
minerva-kb remove my-project
minerva-kb add /path/to/repository
```

### Permission Denied on Config Files

**Error**:
```
❌ Failed to write config: Permission denied
```

**Causes**:

1. `~/.minerva/apps/minerva-kb/` directory doesn't exist
2. Incorrect permissions on directory
3. Disk full

**Solutions**:

```bash
# Create directory if missing
mkdir -p ~/.minerva/apps/minerva-kb

# Fix permissions
chmod 700 ~/.minerva/apps/minerva-kb

# Check disk space
df -h ~
```

---

## Advanced Topics

### Managing Multiple Collections

**Use case**: Index multiple repositories for comprehensive knowledge base.

**Strategy**:

```bash
# Add all repositories
minerva-kb add ~/code/project-a
minerva-kb add ~/code/project-b
minerva-kb add ~/code/project-c

# Use different providers for cost optimization
# Project A: OpenAI (main project, high quality)
# Project B: Ollama (side project, local)
# Project C: Gemini (documentation, free tier)

# List all
minerva-kb list

# Watch important ones
# Terminal 1
minerva-kb watch project-a

# Terminal 2
minerva-kb watch project-b
```

**Best practices**:

- Use cloud providers for frequently-accessed collections
- Use local providers for rarely-queried collections
- Monitor costs with cloud provider dashboards
- Sync manually for infrequently-updated collections (skip watcher)

### Backup and Restore

**Backup strategy**:

```bash
# Create backup directory
mkdir -p ~/minerva-backups/$(date +%Y-%m-%d)

# Backup ChromaDB (all collections)
tar -czf ~/minerva-backups/$(date +%Y-%m-%d)/chromadb.tar.gz \
  ~/.minerva/chromadb/

# Backup configs (all collections)
tar -czf ~/minerva-backups/$(date +%Y-%m-%d)/configs.tar.gz \
  ~/.minerva/apps/minerva-kb/

# Backup script (recommended)
cat > ~/bin/backup-minerva.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y-%m-%d)
BACKUP_DIR=~/minerva-backups/$DATE
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/chromadb.tar.gz ~/.minerva/chromadb/
tar -czf $BACKUP_DIR/configs.tar.gz ~/.minerva/apps/minerva-kb/
echo "✓ Backup complete: $BACKUP_DIR"
EOF

chmod +x ~/bin/backup-minerva.sh
```

**Restore strategy**:

```bash
# Stop all watchers first
minerva-kb list  # Note all running PIDs
kill <PID1> <PID2> <PID3>

# Restore ChromaDB
tar -xzf ~/minerva-backups/2025-12-08/chromadb.tar.gz -C ~/

# Restore configs
tar -xzf ~/minerva-backups/2025-12-08/configs.tar.gz -C ~/

# Verify restoration
minerva-kb list
minerva-kb status <collection-name>
```

**Automated backups**:

```bash
# Add to crontab (daily at 2 AM)
crontab -e

# Add line:
0 2 * * * ~/bin/backup-minerva.sh
```

### Customizing Chunk Size

**Use case**: Optimize chunk size for specific content types.

**Default**: 1200 characters (works well for most documentation).

**Adjustment strategy**:

1. Create collection normally:
   ```bash
   minerva-kb add ~/code/my-project
   ```

2. Edit index config manually:
   ```bash
   nano ~/.minerva/apps/minerva-kb/my-project-index.json

   # Change:
   "chunk_size": 1200

   # To:
   "chunk_size": 800  # For short API docs
   # Or:
   "chunk_size": 2000  # For long-form guides
   ```

3. Re-index:
   ```bash
   minerva-kb sync my-project
   ```

**Guidelines**:

- **Short chunks (600-1000)**: API references, function docs, quick facts
- **Medium chunks (1000-1500)**: General documentation, tutorials
- **Long chunks (1500-2500)**: Long-form guides, conceptual docs

**Trade-offs**:

- Smaller chunks: More precise search, more chunks (higher cost)
- Larger chunks: More context per result, fewer chunks (lower cost)

### Monitoring Provider Costs

**OpenAI dashboard**:

1. Visit https://platform.openai.com/usage
2. View costs by model and date
3. Set up billing alerts

**Gemini dashboard**:

1. Visit https://console.cloud.google.com/apis/dashboard
2. View quota usage
3. Monitor free tier limits

**Cost estimation**:

```bash
# Estimate for new collection
# 1. Count documentation files
find ~/code/my-project -name "*.md" -o -name "*.txt" | wc -l

# 2. Estimate word count
find ~/code/my-project -name "*.md" -exec wc -w {} + | tail -1

# 3. Rough cost (OpenAI)
# - 100,000 words ≈ 133,000 tokens
# - Embedding: 133,000 tokens × $0.02 / 1M ≈ $0.003
# - Description generation: ~500 tokens × $0.15 / 1M ≈ $0.0001
# Total: ~$0.003 per indexing

# For local providers (Ollama/LM Studio): $0 (free)
```

### Migrating Between Providers

**Use case**: Start with OpenAI, migrate to Ollama to reduce costs.

**Steps**:

1. Set up target provider:
   ```bash
   # For Ollama
   ollama serve
   ollama pull mxbai-embed-large:latest
   ollama pull llama3.1:8b
   ```

2. Change provider:
   ```bash
   minerva-kb add ~/code/my-project
   # Choose "y" when prompted to change provider
   # Select Ollama
   ```

3. Verify migration:
   ```bash
   minerva-kb status my-project
   # Check provider shows "ollama"
   ```

**Important**: Full re-indexing is required. Embeddings from different providers are incompatible.

### Handling Large Repositories

**Challenge**: Repositories with 1,000+ documentation files take long to index.

**Strategies**:

1. **Use local provider** (Ollama/LM Studio) to avoid API rate limits
2. **Increase chunk size** to reduce total chunks
3. **Filter files during extraction** (not directly supported, but can manually edit extracted JSON)
4. **Split into multiple collections** (e.g., separate docs vs source code comments)

**Example**:

```bash
# Large repo (~2,000 docs)
minerva-kb add ~/code/large-project

# Choose Ollama (no rate limits)
# Use chunk_size: 2000 (reduces chunks by ~40%)
# Expect 30-60 minutes for initial indexing
```

### Collection Lifecycle Management

**Typical lifecycle**:

1. **Creation**: `minerva-kb add ~/code/my-project`
2. **Active development**: Watcher running, automatic updates
3. **Maintenance**: Occasional manual syncs, no watcher
4. **Archival**: Keep collection, disable watcher, infrequent access
5. **Retirement**: `minerva-kb remove my-project`

**Lifecycle commands**:

```bash
# Active development
minerva-kb watch my-project  # Keep running

# Maintenance
# Stop watcher (Ctrl+C), sync manually when needed
minerva-kb sync my-project

# Archival
# Remove from regular backups, check status occasionally
minerva-kb status my-project

# Retirement
minerva-kb remove my-project
```

---

## Migration Guide

### From Manual Setup (Pre-minerva-kb)

**If you previously set up collections manually** (without minerva-kb), here's how to adopt them:

**Not directly supported**: minerva-kb cannot automatically adopt unmanaged collections.

**Migration path** (requires re-creation):

1. **Document existing collections**:
   ```bash
   # List unmanaged collections
   python -c "
   import chromadb
   client = chromadb.PersistentClient(path='/Users/michele/.minerva/chromadb')
   for c in client.list_collections():
       print(c.name)
   "

   # Note which repositories they came from
   ```

2. **Remove unmanaged collections**:
   ```bash
   # For each unmanaged collection
   minerva remove ~/.minerva/chromadb <collection-name>
   ```

3. **Re-add with minerva-kb**:
   ```bash
   # For each repository
   minerva-kb add /path/to/repository
   ```

**Why re-creation is necessary**: minerva-kb requires specific config files (`*-index.json`, `*-watcher.json`) that don't exist for manually-created collections.

### From Old Setup Wizard

**If you used the old monolithic setup wizard** (1,277 lines in `apps/local-repo-kb/setup.py`):

**Key differences**:

| Old Setup Wizard | minerva-kb |
|-----------------|------------|
| Guided one-time setup | On-demand collection management |
| Single collection focus | Multi-collection native |
| 15+ minute setup | <2 minute second collection |
| Complex configuration editing | Simple commands |
| Manual watcher management | Built-in watcher lifecycle |

**Migration steps**:

1. **Identify existing collection**:
   - Check `~/.minerva/apps/minerva-kb/` for config files
   - If files exist: already migrated (configs are compatible)
   - If not: follow manual setup migration above

2. **No action needed if configs exist**: minerva-kb uses the same config format as the old wizard.

3. **Start using new commands**:
   ```bash
   # Old workflow
   # Run setup.py -> wait 15 minutes -> manually start watcher

   # New workflow
   minerva-kb add /path/to/repo  # <2 minutes
   minerva-kb watch repo-name     # Start watcher
   ```

### From Local Repo Watcher Manager

**If you used `local-repo-watcher-manager`** (deprecated tool):

**Key differences**:

| watcher-manager | minerva-kb watch |
|----------------|------------------|
| Separate tool for watcher only | Integrated watcher + full lifecycle |
| Manual watcher config creation | Auto-generated configs |
| No collection status visibility | Built-in status command |

**Migration path**:

1. **Stop existing watchers**:
   ```bash
   # Find and kill all watcher-manager processes
   ps aux | grep local-repo-watcher
   kill <PID1> <PID2>
   ```

2. **Remove watcher-manager**:
   ```bash
   pipx uninstall local-repo-watcher-manager
   ```

3. **Use minerva-kb watch**:
   ```bash
   minerva-kb watch my-project
   ```

**Note**: `local-repo-watcher` (the underlying watcher) is still required. Only the manager layer is replaced.

---

## Summary

**minerva-kb** provides a complete solution for managing repository-based knowledge bases:

- **Simple**: 6 commands cover entire lifecycle
- **Fast**: <2 minutes for second collection
- **Flexible**: Multiple providers, multiple collections
- **Safe**: Confirmations, validations, clear errors
- **Observable**: Status reporting, chunk counts, watcher monitoring

**Get started**:

```bash
pipx install tools/minerva-kb
minerva-kb add ~/code/my-project
```

**Get help**:

- Command help: `minerva-kb --help`, `minerva-kb <command> --help`
- Examples: See [MINERVA_KB_EXAMPLES.md](MINERVA_KB_EXAMPLES.md)
- Issues: Check troubleshooting section above

**Next steps after first collection**:

1. Start watcher: `minerva-kb watch my-project`
2. Add second collection: `minerva-kb add ~/code/another-repo`
3. Configure Claude Desktop to use collections (see main Minerva docs)
