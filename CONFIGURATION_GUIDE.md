# Minervium Configuration Guide

This guide explains how to configure Minervium for indexing notes and serving them through the MCP server, with support for multiple AI providers (Ollama, OpenAI, Google Gemini, Azure OpenAI).

## Table of Contents

1. [Overview](#overview)
2. [Index Configuration](#index-configuration)
3. [Server Configuration](#server-configuration)
4. [AI Provider Setup](#ai-provider-setup)
5. [Multi-Collection Setup](#multi-collection-setup)
6. [Complete Examples](#complete-examples)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Minervium uses JSON configuration files for two main operations:

### 1. Indexing (`minerva index`)

**Purpose**: Create ChromaDB collections with AI embeddings
**Command**: `minerva index --config index-config.json`
**Config specifies**: Source data, AI provider, collection settings

### 2. Serving (`minerva serve`)

**Purpose**: Expose collections via MCP server for Claude Desktop
**Command**: `minerva serve --config server-config.json`
**Config specifies**: ChromaDB location, logging settings

### Key Design Principle

**AI provider metadata is stored IN each collection** during indexing. The MCP server reads this metadata and uses the correct provider automatically. This allows:

- Multiple collections with different AI providers
- No provider configuration needed for the server
- Consistent embeddings for queries and indexed content

---

## Index Configuration

### Basic Structure

Create a JSON configuration file (e.g., `my-config.json`):

```json
{
  "collection_name": "my_notes",
  "description": "Personal notes about software development, project management, and research",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json",
  "forceRecreate": false,
  "skipAiValidation": false
}
```

Then index:

```bash
minerva index --config my-config.json --verbose
```

### Required Fields

| Field             | Type   | Description                                           | Example                          |
| ----------------- | ------ | ----------------------------------------------------- | -------------------------------- |
| `collection_name` | string | Unique collection identifier (alphanumeric, `-`, `_`) | `"bear_notes"`                   |
| `description`     | string | When to use this collection (guides AI on content)    | `"Personal notes from Bear app"` |
| `chromadb_path`   | string | Path to ChromaDB storage directory                    | `"./chromadb_data"`              |
| `json_file`       | string | Path to notes JSON file                               | `"./bear-notes.json"`            |

### Optional Fields

| Field              | Type    | Default | Description                                 |
| ------------------ | ------- | ------- | ------------------------------------------- |
| `forceRecreate`    | boolean | `false` | Delete and recreate collection if it exists |
| `skipAiValidation` | boolean | `false` | Skip description quality validation         |

### Collection Naming

**Valid names**:

- `bear_notes` ✅
- `wikipedia-history` ✅
- `my_collection_v2` ✅

**Invalid names**:

- `bear notes` ❌ (spaces)
- `my/collection` ❌ (slashes)
- `col.2025` ❌ (periods)

### Description Guidelines

The description guides the AI on when to search this collection. Be specific:

**Good descriptions**:

```json
"Personal notes from Bear app covering software development, project management, meeting notes, and technical documentation from 2020-2025"
```

```json
"Wikipedia articles about world history, major events, historical figures, and civilizations"
```

**Poor descriptions**:

```json
"My notes" // Too vague
```

```json
"Notes" // Doesn't indicate content
```

---

## Server Configuration

### Basic Structure

Create server configuration (e.g., `server-config.json`):

```json
{
  "chromadb_path": "./chromadb_data",
  "log_level": "INFO"
}
```

Then start server:

```bash
minerva serve --config server-config.json
```

### Fields

| Field           | Type   | Required | Default  | Description                                        |
| --------------- | ------ | -------- | -------- | -------------------------------------------------- |
| `chromadb_path` | string | ✅       | -        | Path to ChromaDB storage                           |
| `log_level`     | string | ❌       | `"INFO"` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### What the Server Does

When started, the server:

1. Scans `chromadb_path` for collections
2. Reads AI provider metadata from each collection
3. Checks provider availability (API keys, Ollama running, etc.)
4. Marks collections as available/unavailable
5. Exposes available collections via MCP

### Server Output Example

```
[INFO] Discovering collections in ChromaDB...
[INFO] Found 3 collections

[INFO] Collection: bear_notes
[INFO]   Provider: ollama (mxbai-embed-large:latest)
[INFO]   Status: ✓ Available (dimension: 1024)

[INFO] Collection: wikipedia_history
[INFO]   Provider: openai (text-embedding-3-small)
[INFO]   Status: ✗ Unavailable
[INFO]   Reason: Missing API key - OPENAI_API_KEY not found

[INFO] Summary: 1 available, 2 unavailable
[INFO] MCP server ready
```

---

## AI Provider Setup

Minervium supports multiple AI providers through environment variables. Collections remember which provider they used during indexing.

### Local: Ollama (No API Keys)

**Configuration**: Not needed in config file (default provider)

**Setup**:

```bash
# Start Ollama service
ollama serve

# Pull models (in separate terminal)
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b

# Verify
ollama list
```

**Index with Ollama**:

```bash
# Create config (no AI provider specified = uses Ollama)
cat > ollama-config.json << 'EOF'
{
  "collection_name": "my_notes_local",
  "description": "Personal notes indexed with local Ollama",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json"
}
EOF

# Index
minerva index --config ollama-config.json --verbose
```

**Models used** (default):

- Embeddings: `mxbai-embed-large:latest` (1024 dimensions)
- LLM: `llama3.1:8b`

### Cloud: OpenAI

**Configuration**: Set environment variable

**Setup**:

```bash
# Set API key
export OPENAI_API_KEY="sk-your-openai-api-key-here"

# Verify (optional)
echo $OPENAI_API_KEY
```

**Index with OpenAI**:

```bash
# Create config - provider auto-detected from env
cat > openai-config.json << 'EOF'
{
  "collection_name": "my_notes_openai",
  "description": "Personal notes indexed with OpenAI embeddings",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json"
}
EOF

# Index (OpenAI used if API key is set)
minerva index --config openai-config.json --verbose
```

**Models used** (when `OPENAI_API_KEY` is set):

- Embeddings: `text-embedding-3-small` (1536 dimensions)
- LLM: `gpt-4o-mini`

### Cloud: Google Gemini

**Configuration**: Set environment variable

**Setup**:

```bash
# Set API key
export GEMINI_API_KEY="your-gemini-api-key-here"

# Verify
echo $GEMINI_API_KEY
```

**Index with Gemini**:

```bash
# Create config
cat > gemini-config.json << 'EOF'
{
  "collection_name": "my_notes_gemini",
  "description": "Personal notes indexed with Gemini embeddings",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json"
}
EOF

# Index (Gemini used if API key is set)
minerva index --config gemini-config.json --verbose
```

**Models used** (when `GEMINI_API_KEY` is set):

- Embeddings: `text-embedding-004` (768 dimensions)
- LLM: `gemini-1.5-flash`

### Provider Selection Logic

Minervium selects the AI provider based on environment variables:

1. If `OPENAI_API_KEY` is set → Use OpenAI
2. Else if `GEMINI_API_KEY` is set → Use Gemini
3. Else → Use Ollama (default, requires `ollama serve`)

**Priority**: OpenAI > Gemini > Ollama

To force a specific provider, unset other API keys:

```bash
# Force Ollama
unset OPENAI_API_KEY
unset GEMINI_API_KEY
minerva index --config config.json

# Force Gemini (even if OpenAI key is set)
unset OPENAI_API_KEY
export GEMINI_API_KEY="your-key"
minerva index --config config.json
```

---

## Multi-Collection Setup

### Why Multiple Collections?

Use separate collections for:

- **Different sources**: Bear notes, Wikipedia, books
- **Different topics**: Work notes, personal notes, research
- **Different languages**: English Wikipedia, Spanish Wikipedia
- **Testing**: Production collection vs. test samples

### Creating Multiple Collections

```bash
# Extract from different sources
bear-extractor "Bear.bear2bk" -o bear.json
zim-extractor "wikipedia_history.zim" -l 5000 -o wiki.json
markdown-books-extractor "alice.md" -o alice.json

# Create configs for each
cat > bear-config.json << 'EOF'
{
  "collection_name": "bear_notes",
  "description": "Personal notes from Bear app about software development and projects",
  "chromadb_path": "./chromadb_data",
  "json_file": "bear.json"
}
EOF

cat > wiki-config.json << 'EOF'
{
  "collection_name": "wikipedia_history",
  "description": "Wikipedia articles about world history, historical events, and civilizations",
  "chromadb_path": "./chromadb_data",
  "json_file": "wiki.json"
}
EOF

cat > alice-config.json << 'EOF'
{
  "collection_name": "alice_in_wonderland",
  "description": "Lewis Carroll's Alice's Adventures in Wonderland - classic literature",
  "chromadb_path": "./chromadb_data",
  "json_file": "alice.json"
}
EOF

# Index all collections
minerva index --config bear-config.json --verbose
minerva index --config wiki-config.json --verbose
minerva index --config alice-config.json --verbose

# Single server serves all
minerva serve --config server-config.json
```

### Using Different Providers per Collection

```bash
# Collection 1: Ollama (local, free)
# Ensure no API keys are set
unset OPENAI_API_KEY
unset GEMINI_API_KEY

minerva index --config bear-config.json --verbose
# → Uses Ollama

# Collection 2: OpenAI (cloud, better quality)
export OPENAI_API_KEY="sk-your-key"

minerva index --config wiki-config.json --verbose
# → Uses OpenAI

# Both collections work together
minerva serve --config server-config.json
# → Server auto-detects provider for each collection
```

### Managing Multiple Collections

```bash
# List all collections
minerva peek --chromadb ./chromadb_data

# Peek at specific collection
minerva peek bear_notes --chromadb ./chromadb_data --format table

# Compare collection metadata
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
for coll in client.list_collections():
    meta = coll.metadata
    print(f'{coll.name}: {meta.get(\"embedding_provider\")}/{meta.get(\"embedding_model\")}')
"
```

### Shared ChromaDB Path

All collections share the same `chromadb_path`:

```
chromadb_data/
├── bear_notes/          # Collection 1
│   ├── data/
│   └── metadata
├── wikipedia_history/   # Collection 2
│   ├── data/
│   └── metadata
└── alice_in_wonderland/ # Collection 3
    ├── data/
    └── metadata
```

Benefits:

- One server serves all collections
- Simpler backup (backup one directory)
- Collections don't interfere with each other

---

## Complete Examples

### Example 1: Single Collection with Ollama

```bash
# 1. Start Ollama
ollama serve &

# 2. Extract notes
bear-extractor "Bear Notes.bear2bk" -o notes.json -v

# 3. Validate
minerva validate notes.json

# 4. Create config
cat > config.json << 'EOF'
{
  "collection_name": "my_notes",
  "description": "Personal notes covering software development, project management, and technical documentation",
  "chromadb_path": "./chromadb_data",
  "json_file": "notes.json"
}
EOF

# 5. Index
minerva index --config config.json --verbose

# 6. Peek
minerva peek my_notes --chromadb ./chromadb_data --format table

# 7. Create server config
cat > server-config.json << 'EOF'
{
  "chromadb_path": "./chromadb_data",
  "log_level": "INFO"
}
EOF

# 8. Start server
minerva serve --config server-config.json
```

### Example 2: Multiple Collections, Mixed Providers

```bash
# Setup: Ollama running, OpenAI API key set
ollama serve &
export OPENAI_API_KEY="sk-your-key"

# Extract from sources
bear-extractor "Bear.bear2bk" -o bear.json
zim-extractor "wikipedia.zim" -l 1000 -o wiki.json

# Config 1: Bear notes with Ollama (free)
unset OPENAI_API_KEY  # Force Ollama
cat > bear-config.json << 'EOF'
{
  "collection_name": "bear_notes",
  "description": "Personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "json_file": "bear.json"
}
EOF
minerva index --config bear-config.json --verbose

# Config 2: Wikipedia with OpenAI (better quality)
export OPENAI_API_KEY="sk-your-key"  # Use OpenAI
cat > wiki-config.json << 'EOF'
{
  "collection_name": "wikipedia",
  "description": "Wikipedia articles about various topics",
  "chromadb_path": "./chromadb_data",
  "json_file": "wiki.json"
}
EOF
minerva index --config wiki-config.json --verbose

# Server auto-detects providers
cat > server-config.json << 'EOF'
{
  "chromadb_path": "./chromadb_data",
  "log_level": "INFO"
}
EOF
minerva serve --config server-config.json
# Output:
# Collection: bear_notes (ollama) ✓ Available
# Collection: wikipedia (openai) ✓ Available
```

### Example 3: Test → Production Workflow

```bash
# 1. Test with sample (1000 notes)
zim-extractor "large-archive.zim" -l 1000 -o sample.json

cat > test-config.json << 'EOF'
{
  "collection_name": "test_sample",
  "description": "Test collection for validation",
  "chromadb_path": "./test_chromadb",
  "json_file": "sample.json"
}
EOF

minerva index --config test-config.json --dry-run  # Validate only
minerva index --config test-config.json --verbose  # Actually index

# 2. Verify quality
minerva peek test_sample --chromadb ./test_chromadb --format table

# 3. If good, index full dataset
zim-extractor "large-archive.zim" -o full.json

cat > prod-config.json << 'EOF'
{
  "collection_name": "production_collection",
  "description": "Full production collection",
  "chromadb_path": "./chromadb_data",
  "json_file": "full.json"
}
EOF

minerva index --config prod-config.json --verbose
```

### Example 4: Recreating a Collection

```bash
# Situation: Need to recreate collection with new data

# Option 1: Force recreate in config
cat > config.json << 'EOF'
{
  "collection_name": "my_notes",
  "description": "Updated notes",
  "chromadb_path": "./chromadb_data",
  "json_file": "new-notes.json",
  "forceRecreate": true  // ← Deletes existing collection
}
EOF

minerva index --config config.json --verbose

# Option 2: Delete manually
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
client.delete_collection('my_notes')
print('Deleted')
"

# Then index normally
minerva index --config config.json --verbose
```

---

## Troubleshooting

### Issue: "Collection already exists"

**Error**: `Collection 'my_notes' already exists`

**Cause**: Collection name is already in use.

**Solutions**:

```bash
# Option 1: Use different name
# Edit config.json: "collection_name": "my_notes_v2"

# Option 2: Force recreate
# Edit config.json: "forceRecreate": true

# Option 3: Delete manually
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
client.delete_collection('my_notes')
"
```

### Issue: "Missing API key"

**Error**: `Missing required environment variable: OPENAI_API_KEY`

**Cause**: Config expects OpenAI but API key not set.

**Solution**:

```bash
# Option 1: Set API key
export OPENAI_API_KEY="sk-your-key"

# Option 2: Use Ollama instead
unset OPENAI_API_KEY
minerva index --config config.json
```

### Issue: Server shows "Collection unavailable"

**Situation**: MCP server starts but collection marked unavailable.

**Possible causes**:

1. **Ollama not running** (collection uses Ollama):

```bash
ollama serve
```

2. **Missing API key** (collection uses OpenAI/Gemini):

```bash
export OPENAI_API_KEY="sk-your-key"
# Restart server
minerva serve --config server-config.json
```

3. **Wrong ChromaDB path**:

```bash
# Check config
cat server-config.json
# Verify path exists
ls -la ./chromadb_data
```

### Issue: "Embedding dimension mismatch"

**Error**: `Embedding dimension mismatch! Query: 1536, Collection: 1024`

**Cause**: Trying to query collection with different provider than used during indexing.

**Explanation**:

- Collection created with Ollama (1024 dims)
- Server trying to use OpenAI (1536 dims)

**Solution**: This shouldn't happen - server reads provider from collection metadata. If it does:

```bash
# Check collection metadata
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
coll = client.get_collection('collection_name')
print(coll.metadata)
"

# If metadata is missing/corrupted, recreate collection
```

### Issue: Slow indexing

**Symptoms**: Indexing takes very long

**Solutions**:

1. **Check AI provider**:

```bash
# Ollama (fast, local):
ps aux | grep ollama  # Should be running

# OpenAI/Gemini (slower, rate limited):
# Consider using Ollama for large collections
unset OPENAI_API_KEY
unset GEMINI_API_KEY
```

2. **Test with sample first**:

```bash
# Extract small sample
zim-extractor archive.zim -l 100 -o sample.json
minerva index --config sample-config.json
# If fast, proceed with full dataset
```

3. **Check system resources**:

```bash
# Monitor CPU/RAM
top

# Check disk I/O
iostat -x 1
```

### Issue: Description validation fails

**Warning**: `Description validation score < 7 - consider improving`

**Cause**: Description too generic or unclear.

**Solutions**:

```bash
# Option 1: Improve description
# Bad:  "My notes"
# Good: "Personal notes about software development, covering Python, JavaScript, system design, and best practices from 2020-2025"

# Option 2: Skip validation
# Edit config.json: "skipAiValidation": true
```

---

## Environment Variables Reference

| Variable         | Purpose                  | Example                      |
| ---------------- | ------------------------ | ---------------------------- |
| `OPENAI_API_KEY` | OpenAI API access        | `sk-proj-abc123...`          |
| `GEMINI_API_KEY` | Google Gemini API access | `AIza...`                    |
| `OLLAMA_HOST`    | Custom Ollama endpoint   | `http://192.168.1.100:11434` |
| `MINERVA_DEBUG`  | Enable debug logging     | `1`                          |

---

## Configuration File Locations

**Recommended structure**:

```
project/
├── configs/                # All config files
│   ├── bear-config.json
│   ├── wiki-config.json
│   └── server-config.json
├── chromadb_data/          # ChromaDB storage
│   ├── bear_notes/
│   └── wikipedia/
└── notes/                  # Extracted JSON
    ├── bear.json
    └── wiki.json
```

**Usage**:

```bash
# Index from configs directory
minerva index --config configs/bear-config.json

# Or use absolute paths
minerva index --config /path/to/config.json
```

---

## Best Practices

### 1. Descriptive Collection Names

Use meaningful names that indicate content:

- ✅ `bear_notes_work_2025`
- ✅ `wikipedia_history_en`
- ✅ `classic_literature`
- ❌ `collection1`
- ❌ `test`
- ❌ `notes`

### 2. Clear Descriptions

Help the AI understand when to use each collection:

```json
{
  "description": "Personal notes from Bear app covering software development (Python, JavaScript, Rust), system design patterns, database architecture, and API development. Includes meeting notes, project planning documents, and technical research from 2020-2025."
}
```

### 3. Consistent ChromaDB Path

Use the same `chromadb_path` for all collections:

```json
{
  "chromadb_path": "./chromadb_data" // Same for all configs
}
```

### 4. Backup Strategy

```bash
# Backup ChromaDB regularly
tar -czf chromadb-backup-$(date +%Y%m%d).tar.gz chromadb_data/

# Backup config files
tar -czf configs-backup-$(date +%Y%m%d).tar.gz configs/
```

### 5. Version Control

```bash
# Add to .gitignore:
chromadb_data/
*.json.bak
test_chromadb/

# Track config files:
git add configs/*.json
git commit -m "feat: add collection configs"
```

---

## Resources

- **Schema Documentation**: See `docs/NOTE_SCHEMA.md` for JSON format
- **Extractor Guide**: See `docs/EXTRACTOR_GUIDE.md` for creating extractors
- **Developer Guide**: See `CLAUDE.md` for development workflows

---

## Support

- Report issues: [GitHub Issues](https://github.com/yourusername/minerva/issues)
- Ask questions: [GitHub Discussions](https://github.com/yourusername/minerva/discussions)
