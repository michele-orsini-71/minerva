# Minerva

**A unified RAG system for personal knowledge management**

Minerva is a powerful tool that transforms your markdown notes, articles, and documents into an intelligent, searchable knowledge base. It extracts content from various sources, indexes them with AI-powered embeddings, and makes them accessible through semantic search via the Model Context Protocol (MCP).

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](https://github.com/yourusername/minerva)

---

## 🎯 What is Minerva?

Minerva solves the problem of **information overload** in personal knowledge management. If you have:

- 📝 Hundreds of notes scattered across different apps (Bear, Notion, Obsidian)
- 📚 Markdown books and documentation you want to reference
- 🔬 Research articles and Wikipedia dumps you need to search
- 🤖 A need to give AI assistants access to your personal knowledge

...then Minerva is for you.

### Key Features

✨ **Multi-Source Support**: Extract notes from Bear, Zim articles, markdown books, or any source via custom extractors
🔍 **Semantic Search**: Find relevant information by meaning, not just keywords
🤖 **MCP Integration**: Works seamlessly with Claude Desktop and other MCP-compatible AI tools via Model Context Protocol
📝 **Automatic Citations**: AI assistants automatically cite source notes when presenting information
🌐 **Multi-Provider AI**: Choose between local (Ollama, LM Studio) or cloud (OpenAI, Anthropic, Gemini) AI providers
📊 **Transparent Storage**: All data stored locally in ChromaDB with full control
🔧 **Extensible**: Write custom extractors for any data source in any language
⚙️ **Command-Specific Configs**: Dedicated JSON files for index and server workflows

---

## 🏗️ Architecture

Minerva follows a three-stage pipeline architecture:

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
                         │    MINERVA     │
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
2. **Validate** ✅: Minerva validates the JSON against a strict schema
3. **Index** 🗂️: Notes are chunked, embedded, and stored in ChromaDB with metadata
4. **Serve** 🚀: MCP server exposes semantic search to AI assistants
5. **Search** 🔎: AI assistants query your knowledge base through natural language

---

> ⚠️ The legacy `minerva chat` CLI has been retired. Run `minerva serve` and connect a client such as LM Studio or Claude Desktop for conversational access.


## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- For local AI: [Ollama](https://ollama.ai) with `mxbai-embed-large` model, or [LM Studio](https://lmstudio.ai)
- For cloud AI: API keys for OpenAI, Anthropic Claude, or Google Gemini

### Installation

Minerva can be installed in two ways. Both methods make the `minerva` command globally available in your terminal without needing to activate any virtual environment.

#### Method 1: pipx (Recommended)

**pipx** automatically creates an isolated environment and makes the command globally available. This is the cleanest installation method.

```bash
# Install pipx if you don't have it
python -m pip install --user pipx
python -m pipx ensurepath

# Install Minerva
pipx install .

# That's it! The minerva command is now globally available
minerva --version
minerva --help
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

# Install Minerva
pip install -e .

# Test that it works (while venv is active)
minerva --version

# Add alias to your shell profile (~/.bashrc, ~/.zshrc, or ~/.bash_profile)
echo 'alias minerva="/path/to/your/project/.venv/bin/minerva"' >> ~/.zshrc

# Reload your shell configuration
source ~/.zshrc

# Now you can deactivate the venv
deactivate

# The minerva command still works!
minerva --help
```

**Important:** Replace `/path/to/your/project` with the actual absolute path to this project directory.

**For macOS/Linux users**, get the full path with:

```bash
echo "alias minerva=\"$(pwd)/.venv/bin/minerva\"" >> ~/.zshrc
```

**For Windows users**, add to your PowerShell profile:

```powershell
function minerva { & "C:\path\to\project\.venv\Scripts\minerva.exe" $args }
```

#### ⚠️ You Don't Need to Activate the Virtual Environment!

**Important concept:** Once Minerva is installed using either method above, you do **NOT** need to activate any virtual environment to use it. The `minerva` command will be available in any terminal session.

- **With pipx**: The command is automatically on your PATH
- **With pip + alias**: The alias points directly to the executable in the venv

You only need to activate the venv during development if you're modifying Minerva's code.

#### Verify Installation

After installation, verify everything works:

```bash
# Check version
minerva --version
# Expected output: minerva 1.0.0

# Check help
minerva --help
# Expected output: Full help text with all commands

# Test a simple command
minerva validate --help
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
minerva validate bear-notes.json

# 3. Create command-specific config files
mkdir -p configs/index configs/server
cat > configs/index/bear-notes-ollama.json << 'EOF'
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "name": "bear-notes",
    "description": "My personal notes from Bear app",
    "json_file": "../../bear-notes.json",
    "chunk_size": 1200
  },
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
EOF

cat > configs/server/local.json << 'EOF'
{
  "chromadb_path": "../../chromadb_data",
  "default_max_results": 5,
  "host": "127.0.0.1",
  "port": 8337
}
EOF

# 4. Index the notes into ChromaDB
minerva index --config configs/index/bear-notes-ollama.json --verbose

# 5. Peek at the indexed data
minerva peek my_notes --chromadb ./chromadb_data

# 6. Start the MCP server (for Claude Desktop integration)
minerva serve --config configs/server/local.json
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

Extractors are independent packages that convert specific data sources into the standardized JSON schema. Minerva includes three official extractors:

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

### `minerva index`

Index markdown notes into ChromaDB with AI embeddings.

```bash
minerva index --config configs/index/bear-notes-ollama.json [--verbose] [--dry-run]
```

**Options:**

- `--config FILE`: Index configuration JSON file (required)
- `--verbose`: Show detailed progress information
- `--dry-run`: Validate without actually indexing

**Example config (command-specific):**

```json
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "name": "my-notes",
    "description": "Personal notes collection",
    "json_file": "../../data/notes.json",
    "chunk_size": 1200,
    "force_recreate": false,
    "skip_ai_validation": false
  },
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
```

### `minerva validate`

Validate notes JSON against the schema without indexing.

```bash
minerva validate notes.json [--verbose]
```

Use this before indexing to catch schema errors early.

### `minerva peek`

Inspect ChromaDB collections to see what's indexed.

```bash
minerva peek COLLECTION_NAME --chromadb PATH [--format table|json]
```

**Example:**

```bash
minerva peek bear_notes --chromadb ./chromadb_data --format table
```

### `minerva serve`

Start the MCP server to expose collections to AI assistants.

```bash
minerva serve --config configs/server/local.json
```

**Example config:**

```json
{
  "chromadb_path": "../../chromadb_data",
  "default_max_results": 5,
  "host": "127.0.0.1",
  "port": 8337
}
```

## 🎨 Usage Examples

### Example 1: Index Bear Notes with Local AI (Ollama)

```bash
# Extract Bear notes
bear-extractor "Bear Backup.bear2bk" -o bear-notes.json

# Create collection-specific config
mkdir -p configs/index
cat > configs/index/bear-notes-ollama.json << 'EOF'
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "name": "bear-notes",
    "description": "Personal notes from Bear app",
    "json_file": "../../bear-notes.json",
    "chunk_size": 1200
  },
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
EOF

# Index with verbose output
minerva index --config configs/index/bear-notes-ollama.json --verbose
```

### Example 2: Use LM Studio for Desktop Workflows

```bash
# Start LM Studio and load a model (e.g., qwen2.5-7b-instruct)

# Update provider block to target LM Studio
cat > configs/index/wiki-history.json << 'EOF'
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "name": "wiki-history",
    "description": "Wikipedia history articles",
    "json_file": "../../wiki.json"
  },
  "provider": {
    "provider_type": "lmstudio",
    "base_url": "http://localhost:1234/v1",
    "embedding_model": "qwen2.5-7b-instruct",
    "llm_model": "qwen2.5-14b-instruct",
    "rate_limit": {
      "requests_per_minute": 60,
      "concurrency": 1
    }
  }
}
EOF

minerva index --config configs/index/wiki-history.json --verbose
```

See the [LM Studio Setup Guide](docs/LMSTUDIO_SETUP.md) for detailed installation instructions.

### Example 3: Manage Multiple Collections

```bash
# Create one config per collection
cp configs/index/bear-notes-ollama.json configs/index/books-notes.json
cp configs/index/bear-notes-ollama.json configs/index/research-papers.json

# Update description/json_file/provider as needed, then run:
minerva index --config configs/index/bear-notes-ollama.json
minerva index --config configs/index/books-notes.json
minerva index --config configs/index/research-papers.json

# Serve every collection from the same ChromaDB path
minerva serve --config configs/server/local.json
```

### Example 4: Validate Configurations Quickly

```bash
python -c "from minerva.common.index_config import load_index_config; load_index_config('configs/index/bear-notes-ollama.json')"
python -c "from minerva.common.server_config import load_server_config; load_server_config('configs/server/local.json')"
```

---

## 🧩 Extending Minerva

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
minerva validate notes.json
minerva index --config configs/index/bear-notes-ollama.json
```

See the [Extractor Guide](docs/EXTRACTOR_GUIDE.md) for detailed tutorials.

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=minerva --cov-report=html

# Run specific test suites
pytest tests/test_ai_provider.py -v              # Provider tests
pytest tests/test_index_command.py -v            # Index command and config loader tests
```

### Validate Configuration

```bash
# Validate sample configs
python -c "from minerva.common.index_config import load_index_config; load_index_config('configs/index/bear-notes-ollama.json')"
python -c "from minerva.common.server_config import load_server_config; load_server_config('configs/server/local.json')"
```

### Continuous Integration

The project includes GitHub Actions CI that automatically:
- Runs all tests with coverage
- Validates sample configurations
- Lints code with black, isort, and flake8
- Tests on Python 3.10, 3.11, 3.12, and 3.13

---

## 📚 Documentation

- **[Configuration Guide](docs/configuration.md)** - Command-specific configuration reference for index and server
- **[LM Studio Setup Guide](docs/LMSTUDIO_SETUP.md)** - Installing and configuring LM Studio
- **[Note Schema](docs/NOTE_SCHEMA.md)** - Complete JSON schema specification
- **[Extractor Guide](docs/EXTRACTOR_GUIDE.md)** - How to write custom extractors
- **[Legacy Config Guide](docs/CONFIGURATION_GUIDE.md)** - Archived reference for the pre-v3 unified system
- **[Release Notes v2.0](docs/RELEASE_NOTES_v2.0.md)** - What's new in version 2.0
- **[Upgrade Guide v2.0](docs/UPGRADE_v2.0.md)** - How to upgrade from v1.x
- **[CLAUDE.md](CLAUDE.md)** - Developer guide for working with this codebase

---

## 🤝 Contributing

Contributions are welcome! Here are some ways you can help:

- 🐛 Report bugs and request features via [GitHub Issues](https://github.com/yourusername/minerva/issues)
- 📝 Write extractors for new data sources
- 📚 Improve documentation
- 🧪 Add tests and improve code coverage
- 💡 Share your use cases and workflows

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Minerva builds upon these excellent open-source projects:

- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - Document chunking
- [Ollama](https://ollama.ai/) - Local AI models
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework

---

## 📮 Support

- 📖 Check the [documentation](docs/)
- 🐛 Report issues on [GitHub](https://github.com/yourusername/minerva/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/yourusername/minerva/discussions)

---

**Happy knowledge managing! 🧠✨**
