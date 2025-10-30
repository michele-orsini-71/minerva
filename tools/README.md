# Tools Directory

Utility scripts for managing and inspecting the markdown notes RAG system.

## Available Tools

### inspect_chromadb.py

A comprehensive ChromaDB inspection tool that provides quick insights into your vector database collections.

**Purpose**: Get a fast overview of all collections, their metadata, AI configurations, and content without querying the full pipeline.

**Features**:
- 📊 Database summary with collection counts and statistics
- 🔍 Detailed collection metadata inspection
- 🤖 AI provider configuration display
- 📝 Sample document preview (verbose mode)
- 💾 JSON output for scripting and automation
- 🎨 Colorized terminal output

**Usage**:

```bash
# Basic inspection - show all collections
python tools/inspect_chromadb.py chromadb_data

# Inspect specific collection
python tools/inspect_chromadb.py chromadb_data --collection alice-in-wonderland

# Verbose mode - includes sample documents
python tools/inspect_chromadb.py chromadb_data --verbose

# JSON output - for scripting/automation
python tools/inspect_chromadb.py chromadb_data --json

# Combine options
python tools/inspect_chromadb.py chromadb_data --collection bear_notes --verbose --json
```

**Output Examples**:

*Standard Output:*
```
================================================================================
ChromaDB Database Summary
================================================================================

  Location:          /path/to/chromadb_data
  Total Collections: 3
  Total Chunks:      310,060

  Providers:
    ollama: 1 collection(s)
    Unknown: 2 collection(s)

================================================================================
Collection: alice-in-wonderland
================================================================================

Basic Information:
  Chunk Count:  152
  Created At:   2025-10-12 14:50:00 UTC
  Version:      1.0

Description:
  This collection contains the full text of the book Alice's Adventures...

AI Provider Configuration:
  Provider:     ollama
  Embedding:    mxbai-embed-large:latest
  Dimension:    1024
  LLM Model:    llama3.1:8b
  Base URL:     http://localhost:11434

Index Configuration:
  Distance:     cosine
```

*Verbose Output (adds sample documents):*
```
Sample Documents:

  Sample 1:
    Title:    Alice's Adventures in Wonderland - Chapter 1
    Chunk:    0
    Content:  # Alice's Adventures in Wonderland - Chapter 1...

  Sample 2:
    Title:    Alice's Adventures in Wonderland - Chapter 1
    Chunk:    1
    Content:  There was nothing so very remarkable in that...
```

*JSON Output (for scripting):*
```json
{
  "database_path": "/path/to/chromadb_data",
  "total_collections": 1,
  "collections": [
    {
      "name": "alice-in-wonderland",
      "chunk_count": 152,
      "metadata": {...},
      "ai_provider": {...}
    }
  ]
}
```

**Options**:

| Flag | Description |
|------|-------------|
| `-h, --help` | Show help message and exit |
| `-c NAME, --collection NAME` | Inspect specific collection only |
| `-v, --verbose` | Show sample documents and detailed information |
| `-j, --json` | Output results as JSON (for scripting) |

**Use Cases**:

1. **Quick Health Check**: See all collections and their sizes
   ```bash
   python tools/inspect_chromadb.py chromadb_data
   ```

2. **Verify Pipeline Output**: Check if collection was created correctly
   ```bash
   python tools/inspect_chromadb.py chromadb_data -c alice-in-wonderland -v
   ```

3. **Automation/Scripting**: Extract metadata programmatically
   ```bash
   python tools/inspect_chromadb.py chromadb_data --json | jq '.collections[].chunk_count'
   ```

4. **Debug AI Configuration**: Verify provider settings
   ```bash
   python tools/inspect_chromadb.py chromadb_data -c my-collection
   ```

5. **Content Preview**: See sample documents from a collection
   ```bash
   python tools/inspect_chromadb.py chromadb_data --verbose
   ```

**Requirements**:
- Python 3.8+
- chromadb library (`pip install chromadb`)

**Related Tools**:
- `minerva index` - Create and populate collections
- `minerva serve` - Query collections via MCP server
- `../chroma-peek/` - Visual ChromaDB exploration tool

---

## Contributing New Tools

When adding new tools to this directory:

1. **Follow naming convention**: Use descriptive names with underscores (e.g., `backup_collection.py`)
2. **Add to this README**: Document usage, options, and examples
3. **Include help text**: Implement `--help` with argparse
4. **Handle errors gracefully**: Provide clear error messages
5. **Support scripting**: Consider adding `--json` output mode
6. **Make executable**: `chmod +x your_tool.py`
7. **Add shebang**: `#!/usr/bin/env python3`

## Tool Ideas (TODO)

Future utility scripts that would be useful:

- [ ] `backup_collection.py` - Export collection to portable format
- [ ] `merge_collections.py` - Combine multiple collections
- [ ] `delete_collection.py` - Safe collection deletion with confirmation
- [ ] `migrate_collection.py` - Convert between embedding providers
- [ ] `stats_reporter.py` - Generate detailed statistics reports
- [ ] `validate_embeddings.py` - Check embedding quality and consistency
- [ ] `search_tester.py` - Test search quality with sample queries
