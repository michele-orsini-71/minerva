# Minervium

**A unified RAG system for personal knowledge management**

Minervium is a powerful tool that transforms your markdown notes, articles, and documents into an intelligent, searchable knowledge base. It extracts content from various sources, indexes them with AI-powered embeddings, and makes them accessible through semantic search via the Model Context Protocol (MCP).

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](https://github.com/yourusername/minervium)

---

## 🎯 What is Minervium?

Minervium solves the problem of **information overload** in personal knowledge management. If you have:

- 📝 Hundreds of notes scattered across different apps (Bear, Notion, Obsidian)
- 📚 Markdown books and documentation you want to reference
- 🔬 Research articles and Wikipedia dumps you need to search
- 🤖 A need to give AI assistants access to your personal knowledge

...then Minervium is for you.

### Key Features

✨ **Multi-Source Support**: Extract notes from Bear, Zim articles, markdown books, or any source via custom extractors
🔍 **Semantic Search**: Find relevant information by meaning, not just keywords
🤖 **MCP Integration**: Works seamlessly with Claude Desktop and other MCP-compatible AI tools
🌐 **Multi-Provider AI**: Choose between local (Ollama) or cloud (OpenAI, Gemini) AI providers
📊 **Transparent Storage**: All data stored locally in ChromaDB with full control
🔧 **Extensible**: Write custom extractors for any data source in any language

---

## 🏗️ Architecture

Minervium follows a three-stage pipeline architecture:

```
┌─────────────────┐
│   DATA SOURCES  │
│   (Bear, Zim,   │
│  Books, etc.)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   EXTRACTORS    │──────▶ Standardized JSON │
│ (Independent    │      │  (Note Schema)    │
│   packages)     │      └─────────┬──────────┘
└─────────────────┘                │
                                   ▼
                         ┌──────────────────┐
                         │    MINERVIUM     │
                         │   (Core System)  │
                         └─────────┬────────┘
                                   │
        ┌──────────────────────────┼───────────────────────┐
        │                          │                       │
        ▼                          ▼                       ▼
  ┌──────────┐            ┌──────────────┐         ┌───────────┐
  │  INDEX   │            │   VALIDATE   │         │   PEEK    │
  │ Command  │            │   Command    │         │  Command  │
  └────┬─────┘            └──────────────┘         └───────────┘
       │
       ▼
  ┌──────────────────────────────────┐
  │       Vector Database            │
  │       (ChromaDB)                 │
  │  ┌──────────┐  ┌──────────┐    │
  │  │Collection│  │Collection│    │
  │  │  #1      │  │  #2      │    │
  │  └──────────┘  └──────────┘    │
  └────────────────┬─────────────────┘
                   │
                   ▼
            ┌──────────────┐
            │    SERVE     │
            │   Command    │
            │ (MCP Server) │
            └──────┬───────┘
                   │
                   ▼
            ┌──────────────┐
            │ AI Assistant │
            │ (Claude, etc)│
            └──────────────┘
```

### How It Works

1. **Extract** 📤: Extractors convert your notes into a standardized JSON format
2. **Validate** ✅: Minervium validates the JSON against a strict schema
3. **Index** 🗂️: Notes are chunked, embedded, and stored in ChromaDB with metadata
4. **Serve** 🚀: MCP server exposes semantic search to AI assistants
5. **Search** 🔎: AI assistants query your knowledge base through natural language

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- For local AI: [Ollama](https://ollama.ai) with `mxbai-embed-large` model
- For cloud AI: API keys for OpenAI or Google Gemini

### Installation

Minervium can be installed in two ways. Both methods make the `minervium` command globally available in your terminal without needing to activate any virtual environment.

#### Method 1: pipx (Recommended)

**pipx** automatically creates an isolated environment and makes the command globally available. This is the cleanest installation method.

```bash
# Install pipx if you don't have it
python -m pip install --user pipx
python -m pipx ensurepath

# Install Minervium
pipx install .

# That's it! The minervium command is now globally available
minervium --version
minervium --help
```

**Why pipx?**
- ✅ Clean: Each tool gets its own isolated environment
- ✅ Simple: One command to install, one command to uninstall
- ✅ Automatic: No PATH configuration needed
- ✅ Safe: No conflicts between different Python projects

#### Method 2: pip + alias

If you prefer traditional pip installation, you can install in a virtual environment and create a shell alias for convenience.

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Minervium
pip install -e .

# Test that it works (while venv is active)
minervium --version

# Add alias to your shell profile (~/.bashrc, ~/.zshrc, or ~/.bash_profile)
echo 'alias minervium="/path/to/your/project/.venv/bin/minervium"' >> ~/.zshrc

# Reload your shell configuration
source ~/.zshrc

# Now you can deactivate the venv
deactivate

# The minervium command still works!
minervium --help
```

**Important:** Replace `/path/to/your/project` with the actual absolute path to this project directory.

**For macOS/Linux users**, get the full path with:
```bash
echo "alias minervium=\"$(pwd)/.venv/bin/minervium\"" >> ~/.zshrc
```

**For Windows users**, add to your PowerShell profile:
```powershell
function minervium { & "C:\path\to\project\.venv\Scripts\minervium.exe" $args }
```

#### ⚠️ You Don't Need to Activate the Virtual Environment!

**Important concept:** Once Minervium is installed using either method above, you do **NOT** need to activate any virtual environment to use it. The `minervium` command will be available in any terminal session.

- **With pipx**: The command is automatically on your PATH
- **With pip + alias**: The alias points directly to the executable in the venv

You only need to activate the venv during development if you're modifying Minervium's code.

#### Verify Installation

After installation, verify everything works:

```bash
# Check version
minervium --version
# Expected output: minervium 1.0.0

# Check help
minervium --help
# Expected output: Full help text with all commands

# Test a simple command
minervium validate --help
# Expected output: Help text for the validate command
```

If you see command output without errors, installation was successful! 🎉

### Basic Workflow

```bash
# 1. Extract notes from a source (example: Bear Notes)
cd extractors/bear-notes-extractor
pip install -e .
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o bear-notes.json

# 2. Validate the extracted JSON
minervium validate bear-notes.json

# 3. Create an index configuration file
cat > config.json << 'EOF'
{
  "collection_name": "my_notes",
  "description": "My personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "json_file": "bear-notes.json"
}
EOF

# 4. Index the notes into ChromaDB
minervium index --config config.json --verbose

# 5. Peek at the indexed data
minervium peek my_notes --chromadb ./chromadb_data

# 6. Start the MCP server (for Claude Desktop integration)
minervium serve --config server-config.json
```

---

## 📖 Core Concepts

### The Note Schema

All data sources must be converted to a standardized JSON schema:

```json
{
  "notes": [
    {
      "id": "unique-note-id",
      "title": "Note Title",
      "content": "The full markdown content...",
      "metadata": {
        "source": "bear",
        "created": "2025-10-20T10:00:00Z",
        "modified": "2025-10-20T12:00:00Z",
        "tags": ["tag1", "tag2"]
      }
    }
  ]
}
```

See [docs/NOTE_SCHEMA.md](docs/NOTE_SCHEMA.md) for complete specification.

### Extractors

Extractors are independent packages that convert specific data sources into the standardized JSON schema. Minervium includes three official extractors:

- **bear-notes-extractor**: Extracts notes from Bear app backups (.bear2bk files)
- **zim-extractor**: Extracts articles from Zim Wikipedia dumps
- **markdown-books-extractor**: Converts markdown books into searchable notes

You can write custom extractors in any language. See [docs/EXTRACTOR_GUIDE.md](docs/EXTRACTOR_GUIDE.md).

### Collections

ChromaDB organizes data into **collections**. Each collection:

- Has a unique name (e.g., `bear_notes`, `research_papers`)
- Contains embeddings from a specific AI provider and model
- Stores metadata about its source and configuration
- Can be queried independently through the MCP server

---

## 🛠️ Commands

### `minervium index`

Index markdown notes into ChromaDB with AI embeddings.

```bash
minervium index --config index-config.json [--verbose] [--dry-run]
```

**Options:**
- `--config FILE`: Configuration JSON file (required)
- `--verbose`: Show detailed progress information
- `--dry-run`: Validate without actually indexing

**Example config:**
```json
{
  "collection_name": "my_notes",
  "description": "Personal notes collection",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json",
  "forceRecreate": false
}
```

### `minervium validate`

Validate notes JSON against the schema without indexing.

```bash
minervium validate notes.json [--verbose]
```

Use this before indexing to catch schema errors early.

### `minervium peek`

Inspect ChromaDB collections to see what's indexed.

```bash
minervium peek COLLECTION_NAME --chromadb PATH [--format table|json]
```

**Example:**
```bash
minervium peek bear_notes --chromadb ./chromadb_data --format table
```

### `minervium serve`

Start the MCP server to expose collections to AI assistants.

```bash
minervium serve --config server-config.json
```

**Example config:**
```json
{
  "chromadb_path": "./chromadb_data",
  "log_level": "INFO"
}
```

---

## 🎨 Usage Examples

### Example 1: Index Bear Notes with Local AI (Ollama)

```bash
# Extract Bear notes
bear-extractor "Bear Backup.bear2bk" -o bear-notes.json

# Create config for local AI
cat > bear-ollama.json << 'EOF'
{
  "collection_name": "bear_notes_local",
  "description": "Personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "json_file": "bear-notes.json"
}
EOF

# Index with verbose output
minervium index --config bear-ollama.json --verbose
```

### Example 2: Index Multiple Sources

```bash
# Extract from different sources
bear-extractor "Bear.bear2bk" -o bear.json
zim-extractor "wikipedia.zim" -o wiki.json
markdown-books-extractor books/ -o books.json

# Create separate collections for each
minervium index --config bear-config.json
minervium index --config wiki-config.json
minervium index --config books-config.json

# All collections available through single MCP server
minervium serve --config server-config.json
```

### Example 3: Test Before Indexing

```bash
# First, validate the extracted data
minervium validate notes.json --verbose

# Then do a dry run to check configuration
minervium index --config config.json --dry-run

# Finally, index for real
minervium index --config config.json --verbose
```

### Example 4: Complete Workflow with All Commands

This example shows all four Minervium commands in a realistic workflow:

```bash
# Step 1: Extract notes from Bear backup
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o my-notes.json -v

# Step 2: Validate the extracted JSON before indexing
minervium validate my-notes.json --verbose
# Output: ✓ JSON is valid
# Output: Found 1,234 notes

# Step 3: Create index configuration
cat > index-config.json << 'EOF'
{
  "collection_name": "personal_knowledge",
  "description": "My personal knowledge base from Bear notes covering software development, research, and project documentation",
  "chromadb_path": "./chromadb_data",
  "json_file": "my-notes.json",
  "forceRecreate": false
}
EOF

# Step 4: Index the notes (this may take a few minutes)
minervium index --config index-config.json --verbose
# Output: Processing 1,234 notes...
# Output: Created 5,678 chunks...
# Output: Generating embeddings...
# Output: ✓ Indexing complete!

# Step 5: Peek at the collection to verify what was indexed
minervium peek personal_knowledge --chromadb ./chromadb_data --format table
# Output shows: collection name, document count, sample entries, metadata

# Step 6: Peek with JSON format for detailed inspection
minervium peek personal_knowledge --chromadb ./chromadb_data --format json > collection-info.json

# Step 7: Create MCP server configuration
cat > server-config.json << 'EOF'
{
  "chromadb_path": "./chromadb_data",
  "log_level": "INFO"
}
EOF

# Step 8: Start the MCP server (makes your notes available to Claude Desktop)
minervium serve --config server-config.json
# Output: MCP server listening...
# Output: Collection 'personal_knowledge' available (5,678 chunks)
```

**What each command does:**
- **`validate`**: Checks JSON structure before spending time on indexing
- **`index`**: Processes notes, creates embeddings, stores in vector database
- **`peek`**: Lets you inspect what's in the database (metadata, counts, samples)
- **`serve`**: Exposes your indexed knowledge to AI assistants via MCP

### Example 5: Using Peek to Explore Multiple Collections

```bash
# List all collections (peek will show available collections if you don't specify one)
minervium peek --chromadb ./chromadb_data

# Inspect your Bear notes collection
minervium peek bear_notes --chromadb ./chromadb_data --format table

# Inspect Wikipedia articles collection
minervium peek wikipedia_history --chromadb ./chromadb_data --format table

# Get detailed JSON output for programmatic analysis
minervium peek bear_notes --chromadb ./chromadb_data --format json | jq '.metadata'

# Compare collection sizes
echo "Bear notes:"
minervium peek bear_notes --chromadb ./chromadb_data --format json | jq '.count'
echo "Wikipedia:"
minervium peek wikipedia_history --chromadb ./chromadb_data --format json | jq '.count'
```

---

## 🧩 Extending Minervium

### Writing Custom Extractors

Create extractors for any data source by outputting JSON that conforms to the note schema:

```python
# my_extractor.py
import json
from datetime import datetime

def extract_my_source(input_path):
    notes = []
    # ... extract your data ...
    notes.append({
        "id": "unique-id",
        "title": "Note Title",
        "content": "Markdown content here",
        "metadata": {
            "source": "my_source",
            "created": datetime.utcnow().isoformat() + "Z",
            "modified": datetime.utcnow().isoformat() + "Z"
        }
    })
    return {"notes": notes}

# Output to stdout or file
notes_data = extract_my_source("input.txt")
print(json.dumps(notes_data, indent=2))
```

Then validate and index:

```bash
python my_extractor.py input.txt > notes.json
minervium validate notes.json
minervium index --config config.json
```

See the [Extractor Guide](docs/EXTRACTOR_GUIDE.md) for detailed tutorials.

---

## 📚 Documentation

- **[Note Schema](docs/NOTE_SCHEMA.md)** - Complete JSON schema specification
- **[Extractor Guide](docs/EXTRACTOR_GUIDE.md)** - How to write custom extractors
- **[Configuration Guide](CONFIGURATION_GUIDE.md)** - All configuration options
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for working with this codebase

---

## 🤝 Contributing

Contributions are welcome! Here are some ways you can help:

- 🐛 Report bugs and request features via [GitHub Issues](https://github.com/yourusername/minervium/issues)
- 📝 Write extractors for new data sources
- 📚 Improve documentation
- 🧪 Add tests and improve code coverage
- 💡 Share your use cases and workflows

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Minervium builds upon these excellent open-source projects:

- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - Document chunking
- [Ollama](https://ollama.ai/) - Local AI models
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework

---

## 📮 Support

- 📖 Check the [documentation](docs/)
- 🐛 Report issues on [GitHub](https://github.com/yourusername/minervium/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/yourusername/minervium/discussions)

---

**Happy knowledge managing! 🧠✨**
