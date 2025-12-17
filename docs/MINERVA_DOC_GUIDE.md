# minerva-doc Complete Guide

**Orchestrator tool for managing document-based knowledge base collections in Minerva**

## Table of Contents

- [What is minerva-doc?](#what-is-minerva-doc)
- [When to Use minerva-doc](#when-to-use-minerva-doc)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Workflow Examples](#workflow-examples)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

---

## What is minerva-doc?

**minerva-doc** is a CLI tool that simplifies managing document-based knowledge base collections in Minerva. It provides an opinionated workflow for adding, updating, and serving collections derived from structured documents like notes, books, and articles.

### Key Features

- **Simplified workflow**: No manual config files - everything is managed for you
- **AI provider selection**: Interactive setup for OpenAI, Gemini, Ollama, or LM Studio
- **Auto-description**: AI-generated collection descriptions from your documents
- **Collection updates**: Re-index with new data or switch providers
- **Multi-collection serving**: Unified MCP server for all your collections
- **Collision prevention**: Prevents naming conflicts across Minerva tools
- **Shared infrastructure**: Works seamlessly with minerva-kb

### What minerva-doc Manages

- ✅ Collection creation from pre-extracted JSON
- ✅ Registry tracking (metadata, provider, dates)
- ✅ Index configuration generation
- ✅ Embedding and indexing
- ✅ MCP server configuration

### What You Need to Provide

- Pre-extracted JSON files (using extractors)
- AI provider credentials (if using cloud providers)
- Collection names and optional descriptions

---

## When to Use minerva-doc

### Use minerva-doc for:

✅ **Static document collections**
- Bear notes exports
- Zim archive dumps
- Markdown books and articles
- Pre-extracted documentation
- One-time or infrequently updated content

✅ **When you have JSON data**
- Output from Minerva extractors
- Custom extraction pipelines
- Exported note databases

### Use minerva-kb instead for:

❌ **Live codebases**
- Git repositories
- Active documentation that changes frequently
- Projects where you want automatic file watching

### Comparison Table

| Feature | minerva-doc | minerva-kb |
|---------|-------------|------------|
| **Input** | Pre-extracted JSON files | Git repositories |
| **Auto-extraction** | No (use extractors separately) | Yes (via repository-doc-extractor) |
| **File watching** | No (manual updates) | Yes (auto-reindex on changes) |
| **Update frequency** | Manual / infrequent | Automatic / frequent |
| **Use cases** | Notes, books, archives | Source code, live docs |
| **Examples** | Bear exports, Zim dumps | GitHub repos, local projects |

---

## Installation

### Prerequisites

1. **Python 3.10+**
   ```bash
   python --version  # Should be 3.10 or higher
   ```

2. **Minerva core**
   ```bash
   cd /path/to/minerva
   pip install -e .
   ```

3. **minerva-common** (shared library)
   ```bash
   pip install -e tools/minerva-common
   ```

4. **AI Provider** (choose one):
   - **Ollama** (recommended for local/free):
     ```bash
     # Install from https://ollama.ai
     ollama serve
     ollama pull mxbai-embed-large:latest
     ollama pull llama3.1:8b
     ```
   - **OpenAI**: Set `OPENAI_API_KEY` environment variable
   - **Gemini**: Set `GEMINI_API_KEY` environment variable
   - **LM Studio**: Start server on `localhost:1234`

### Install minerva-doc

```bash
cd /path/to/minerva/tools/minerva-doc

# Install with pip (development mode)
pip install -e .

# Verify installation
minerva-doc --version
minerva-doc --help
```

---

## Quick Start

**Get your first collection running in under 2 minutes!**

### Step 1: Prepare Your Data

Extract documents to JSON using Minerva extractors:

```bash
# Example: Bear notes
bear-extractor "Bear Notes.bear2bk" -o notes.json

# Example: Zim archive
zim-extractor wikipedia.zim -l 1000 -o wiki.json

# Example: Markdown book
markdown-books-extractor book.md -o book.json
```

### Step 2: Add Collection

```bash
minerva-doc add notes.json --name my-notes
```

**Interactive prompts:**
1. **AI provider**: Select from OpenAI, Gemini, Ollama, or LM Studio
2. **Models**: Choose embedding and LLM models (or use defaults)
3. **Description**: Provide custom or auto-generate from content

**Example session:**
```
Validating JSON file: notes.json
✓ JSON file is valid

Select AI provider:
  1) OpenAI (cloud)
  2) Gemini (cloud)
  3) Ollama (local)
  4) LM Studio (local)
Choice [1-4]: 3

Selected AI Provider:
  Provider: ollama
  Embedding model: mxbai-embed-large:latest
  LLM model: llama3.1:8b

Collection description (press Enter to auto-generate):
  [Auto-generating description...]

Use this description? (Y/n): y

Indexing collection (this may take a few minutes)...
✓ Collection indexed successfully

============================================================
✓ Collection created successfully!
============================================================
  Collection name: my-notes

Next steps:
  1. Check status:   minerva-doc status my-notes
  2. List all:       minerva-doc list
  3. Start server:   minerva-doc serve
```

### Step 3: Query Your Collection

```bash
# Start MCP server
minerva-doc serve
```

Then configure Claude Desktop to use the server (see [MCP Server Setup](#mcp-server-setup)).

---

## Command Reference

### `add` - Create a Collection

**Create and index a new collection from JSON documents.**

```bash
minerva-doc add <json-file> --name <collection-name>
```

**Arguments:**
- `json-file`: Path to JSON file (from extractor output)
- `--name`: Unique collection name (required)

**Examples:**
```bash
# Add Bear notes
minerva-doc add bear-notes.json --name bear-notes

# Add Wikipedia dump
minerva-doc add wiki.json --name wikipedia-history

# Add markdown book
minerva-doc add alice.json --name alice-in-wonderland
```

**What it does:**
1. Validates JSON file format
2. Checks for name collisions
3. Prompts for AI provider selection
4. Generates or prompts for description
5. Creates embeddings and indexes
6. Registers collection in `~/.minerva/apps/minerva-doc/collections.json`

---

### `list` - Show All Collections

**Display all collections in ChromaDB.**

```bash
minerva-doc list [--format table|json]
```

**Options:**
- `--format`: Output format (default: `table`)
  - `table`: Human-readable table
  - `json`: Machine-readable JSON

**Examples:**
```bash
# Table format (default)
minerva-doc list

# JSON format
minerva-doc list --format json

# Filter managed collections with jq
minerva-doc list --format json | jq '.managed[].name'
```

**Sample output:**
```
================================================================================
Managed Collections (minerva-doc)
================================================================================

Collection: bear-notes
  Description:  Personal notes covering software development, AI research...
  Provider:     ollama
  Chunks:       1,234
  Indexed:      2025-01-15T10:30:00
  Source:       /Users/you/notes/bear-notes.json

================================================================================
Unmanaged Collections
================================================================================

⚠️  These collections exist in ChromaDB but are not managed by minerva-doc.
    They may be managed by minerva-kb or created directly via minerva CLI.

  - my-project-kb (456 chunks)

================================================================================
Total: 1 managed, 1 unmanaged
================================================================================
```

---

### `status` - Check Collection Details

**Display detailed information about a specific collection.**

```bash
minerva-doc status <collection-name>
```

**Examples:**
```bash
minerva-doc status bear-notes
```

**Sample output:**
```
============================================================
Collection Status: bear-notes
============================================================

General Information:
  Name:         bear-notes
  Description:  Personal notes covering software development...
  Source JSON:  /Users/you/notes/bear-notes.json

AI Provider:
  Type:             ollama
  Embedding model:  mxbai-embed-large:latest
  LLM model:        llama3.1:8b
  Base URL:         http://localhost:11434

ChromaDB Status:
  Chunks:       1,234
  Status:       ✓ Indexed

Dates:
  Created:      2025-01-15T10:30:00Z
  Last indexed: 2025-01-15T10:30:00Z

============================================================
```

---

### `update` - Re-index Collection

**Update an existing collection with new data or different AI provider.**

```bash
minerva-doc update <collection-name> <json-file>
```

**Arguments:**
- `collection-name`: Name of existing collection
- `json-file`: Path to new JSON file

**Examples:**
```bash
# Update with new data, keep same provider
minerva-doc update bear-notes updated-notes.json

# Update and change provider
minerva-doc update bear-notes updated-notes.json
# Answer 'y' to "Change AI provider?"
```

**What it does:**
1. Validates collection exists in registry
2. Validates new JSON file
3. Shows current provider
4. Prompts: "Change AI provider?"
   - **No**: Uses existing provider and description
   - **Yes**: Prompts for new provider, regenerates description, force recreates
5. Re-indexes collection
6. Updates registry timestamps

**Use cases:**
- New export from source (updated Bear notes)
- Switch from cloud to local AI provider
- Switch embedding models for better results

---

### `remove` - Delete Collection

**Remove collection and all associated data.**

```bash
minerva-doc remove <collection-name>
```

**Examples:**
```bash
minerva-doc remove old-notes
```

**What it deletes:**
- ✅ All embeddings from ChromaDB
- ✅ Collection metadata from registry

**What it keeps:**
- ✅ Source JSON file (your documents are safe)
- ✅ Shared server configuration
- ✅ Other collections

**Safety:**
- Requires typing "YES" exactly to confirm
- Cannot be undone (except from backups)

---

### `serve` - Start MCP Server

**Start the Minerva MCP server to expose collections to Claude Desktop.**

```bash
minerva-doc serve
```

**What it does:**
- Starts MCP server using shared config (`~/.minerva/server.json`)
- Exposes ALL collections in ChromaDB (minerva-doc + minerva-kb)
- Runs in foreground (Ctrl+C to stop)

**MCP Server Setup:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "minerva": {
      "command": "minerva-doc",
      "args": ["serve"]
    }
  }
}
```

Or use minerva-kb (both work):
```json
{
  "mcpServers": {
    "minerva": {
      "command": "minerva-kb",
      "args": ["serve"]
    }
  }
}
```

**Note:** Both minerva-doc and minerva-kb serve the same collections. Use whichever tool you prefer.

---

## Workflow Examples

### Example 1: Bear Notes Workflow

**Scenario:** You have notes exported from Bear app.

```bash
# 1. Extract notes to JSON
bear-extractor "Bear Notes.bear2bk" -v -o bear-notes.json

# 2. Validate (optional)
minerva validate bear-notes.json

# 3. Add to minerva-doc
minerva-doc add bear-notes.json --name bear-notes
# Select provider: Ollama
# Auto-generate description

# 4. Verify
minerva-doc status bear-notes

# 5. Start server
minerva-doc serve

# 6. Query via Claude Desktop
# Ask: "Search my Bear notes for information about Python testing"
```

**Update workflow:**
```bash
# When you have new notes
bear-extractor "Bear Notes New.bear2bk" -o updated-notes.json
minerva-doc update bear-notes updated-notes.json
# Answer 'n' to keep same provider
```

---

### Example 2: Zim Archive Workflow

**Scenario:** You have a Zim archive (offline Wikipedia, Stack Exchange, etc.).

```bash
# 1. Extract from Zim (limit to 10,000 articles for testing)
zim-extractor wikipedia_history.zim -l 10000 -o wiki-history.json

# 2. Add to minerva-doc
minerva-doc add wiki-history.json --name wikipedia-history
# Select provider: OpenAI (for better quality on large datasets)
# Auto-generate description

# 3. Query
minerva-doc serve
# Ask Claude: "Search Wikipedia for the history of the printing press"
```

**Full dataset:**
```bash
# Extract entire archive (may take hours)
zim-extractor wikipedia_history.zim -o wiki-full.json

# Update collection
minerva-doc update wikipedia-history wiki-full.json
```

---

### Example 3: Markdown Book Workflow

**Scenario:** You have a markdown book you want to query.

```bash
# 1. Extract markdown book
markdown-books-extractor "Alice in Wonderland.md" -o alice.json

# 2. Add to minerva-doc
minerva-doc add alice.json --name alice
# Select provider: LM Studio (local, fast)
# Custom description: "Lewis Carroll's Alice in Wonderland"

# 3. Verify
minerva-doc status alice

# 4. Query
minerva-doc serve
# Ask Claude: "Find all references to the Cheshire Cat in Alice in Wonderland"
```

---

### Example 4: Multi-Collection Management

**Scenario:** Manage multiple document collections.

```bash
# Add multiple collections
minerva-doc add bear-notes.json --name notes
minerva-doc add wiki.json --name wikipedia
minerva-doc add alice.json --name alice

# List all
minerva-doc list

# Check each
minerva-doc status notes
minerva-doc status wikipedia
minerva-doc status alice

# Serve all at once
minerva-doc serve

# Query any collection via Claude Desktop
# Claude has access to all three collections simultaneously
```

---

## Troubleshooting

### Common Errors

#### "Collection already exists"

**Error:**
```
Error: Collection 'my-notes' already exists
  Owner: minerva-doc (document-based collection)
  Action: Use a different name, update it, or remove it with:
    minerva-doc update my-notes <new-json-file>
    minerva-doc remove my-notes
```

**Solutions:**
1. **Different name**: `minerva-doc add data.json --name my-notes-v2`
2. **Update existing**: `minerva-doc update my-notes new-data.json`
3. **Remove and recreate**:
   ```bash
   minerva-doc remove my-notes
   minerva-doc add data.json --name my-notes
   ```

---

#### "Collection not found in registry"

**Error:**
```
Error: Collection 'test' not found
  This collection is not managed by minerva-doc
```

**Cause:** Collection doesn't exist or is managed by another tool.

**Solutions:**
1. **List all collections**: `minerva-doc list`
2. **Check minerva-kb**: `minerva-kb list` (if installed)
3. **Create it**: `minerva-doc add data.json --name test`

---

#### "JSON file validation failed"

**Error:**
```
✗ JSON file validation failed:
  Missing required field 'title' in note 5
  Invalid date format in note 12
```

**Causes:**
- Malformed JSON
- Missing required fields (title, markdown, size, modificationDate)
- Invalid date formats

**Solutions:**
1. **Check extractor output**: Ensure you used a Minerva extractor
2. **Validate schema**: See `docs/NOTE_SCHEMA.md` for required format
3. **Fix manually**: Edit JSON to fix errors
4. **Re-extract**: Run extractor again with correct options

---

#### "Permission denied" errors

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/Users/you/.minerva/...'
```

**Solutions:**
```bash
# Fix directory permissions
chmod 700 ~/.minerva
chmod 700 ~/.minerva/apps
chmod 700 ~/.minerva/apps/minerva-doc

# Fix file permissions
chmod 600 ~/.minerva/server.json
chmod 600 ~/.minerva/apps/minerva-doc/collections.json
```

---

#### "ChromaDB collection not found"

**Warning in status:**
```
⚠️  Warning: Collection not found in ChromaDB
    The collection may have been deleted manually.
```

**Causes:**
- Collection deleted directly via minerva CLI
- ChromaDB database corruption
- Wrong ChromaDB path

**Solutions:**
1. **Re-index**:
   ```bash
   minerva-doc update my-collection original-data.json
   # Answer 'n' to provider change
   ```

2. **Remove and recreate**:
   ```bash
   minerva-doc remove my-collection  # Cleans up registry
   minerva-doc add data.json --name my-collection
   ```

---

### FAQ

**Q: Can I use minerva-doc and minerva-kb together?**
A: Yes! They share the same ChromaDB and server. Collections from both tools are accessible via a single MCP server.

**Q: What happens if I delete my source JSON file?**
A: The collection remains in ChromaDB and is still queryable. However, you cannot update it without the source file. Keep backups!

**Q: Can I change the AI provider after creating a collection?**
A: Yes! Use `minerva-doc update <name> <json-file>` and answer 'y' to change provider.

**Q: How do I back up my collections?**
A: Back up three things:
1. Source JSON files
2. `~/.minerva/chromadb/` (vector database)
3. `~/.minerva/apps/minerva-doc/collections.json` (registry)

**Q: Can I rename a collection?**
A: Not directly. Create a new one with the new name, then remove the old:
```bash
minerva-doc add data.json --name new-name
minerva-doc remove old-name
```

**Q: Which AI provider should I use?**
A:
- **Ollama**: Free, local, good quality, unlimited usage
- **OpenAI**: Best quality, costs money, requires internet
- **Gemini**: Good quality, cheaper than OpenAI
- **LM Studio**: Local, customizable models

---

## Advanced Usage

### Provider Selection Tips

**For small collections (<1,000 notes):**
- Any provider works well
- Ollama recommended (free, local)

**For large collections (>10,000 notes):**
- OpenAI or Gemini (better quality on large datasets)
- Or use powerful Ollama models (llama3.1:70b)

**For privacy-sensitive data:**
- Ollama or LM Studio only (local processing)
- Never use cloud providers for confidential information

**For offline usage:**
- Ollama or LM Studio only

---

### Description Best Practices

**Auto-generated descriptions:**
- Pros: Fast, analyzes actual content, consistent
- Cons: Generic, may miss context

**Custom descriptions:**
- Pros: Specific, contextual, you control the message
- Cons: Takes time, may not reflect actual content

**Best approach:**
1. Auto-generate first
2. Review the generated description
3. Edit if needed (via update command)

**Good description examples:**
```
✅ "Personal software development notes from 2020-2025, covering Python, Go, databases, and AI research"
✅ "Wikipedia articles on European history from 1500-1900"
✅ "Technical documentation for the XYZ project API and deployment guides"

❌ "My notes" (too vague)
❌ "A collection of documents" (not specific)
```

---

### Multi-Collection Strategy

**By topic:**
```bash
minerva-doc add work-notes.json --name work
minerva-doc add personal-notes.json --name personal
minerva-doc add research-notes.json --name research
```

**By source:**
```bash
minerva-doc add bear-export.json --name bear
minerva-doc add notion-export.json --name notion
minerva-doc add obsidian-export.json --name obsidian
```

**By time period:**
```bash
minerva-doc add notes-2023.json --name notes-2023
minerva-doc add notes-2024.json --name notes-2024
minerva-doc add notes-2025.json --name notes-2025
```

**Querying multiple collections:**
Claude Desktop can search across all collections simultaneously. Just ask naturally:
- "Search all my notes for information about Python testing"
- "Find references to machine learning in any collection"

---

## Next Steps

- **Read extractors documentation**: `extractors/README.md`
- **Check schema specification**: `docs/NOTE_SCHEMA.md`
- **Review minerva-kb guide**: `docs/MINERVA_KB_GUIDE.md`
- **Explore minerva-common API**: `docs/MINERVA_COMMON.md` (coming soon)

---

## Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check `docs/` directory
- **Examples**: See `tools/minerva-doc/test-data/` for sample JSON

---

**Happy querying! 🚀**
