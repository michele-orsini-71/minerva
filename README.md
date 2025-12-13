# Minerva

A unified RAG system for personal knowledge management

---

## What is Minerva?

Minerva is a tool that transforms your markdown notes, articles, and documents into a searchable knowledge base. It extracts content from various sources, indexes them with AI-powered embeddings, and makes them accessible through semantic search via the Model Context Protocol (MCP).

Minerva solves the problem of **information overload** in personal knowledge management. If you have:

- Hundreds of notes scattered across different apps (Bear, Notion, Obsidian)
- Markdown books and documentation you want to reference
- Research articles and Wikipedia dumps you need to search
- A need to give AI assistants access to your personal knowledge

...then Minerva is for you.

### Key Features

- **Multi-Source Support**: Extract notes from Bear, Zim articles, markdown books, or any source via custom extractors
- **Semantic Search**: Find relevant information by meaning, not just keywords
- **MCP Integration**: Works seamlessly with Claude Desktop and other MCP-compatible AI tools via Model Context Protocol
- **Automatic Citations**: AI assistants automatically cite source notes when presenting information
- **Multi-Provider AI**: Choose between local (Ollama, LM Studio) or cloud (OpenAI, Gemini) AI providers
- **Transparent Storage**: All data stored locally in ChromaDB with full control
- **Extensible**: Write custom extractors for any data source in any language
-️ **Command-Specific Configs**: Dedicated JSON files for index and server workflows

---

## Architecture

Minerva follows a three-stage pipeline architecture:

```txt
┌─────────────────┐
│   DATA SOURCES  │
│   (Bear, Zim,   │
│  Books, etc.)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────-─┐
│   EXTRACTORS    │──────▶ Standardized JSON │
│ (Independent    │      │  (Note Schema)    │
│   packages)     │      └─────────┬─────────┘
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
  │  ┌──────────┐  ┌──────────┐      │
  │  │Collection│  │Collection│      │
  │  │  #1      │  │  #2      │      │
  │  └──────────┘  └──────────┘      │
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

1. Extract: Extractors convert your notes into a standardized JSON format
2. Validate: Minerva validates the JSON against a strict schema
3. Index️: Notes are chunked, embedded, and stored in ChromaDB with metadata
4. Serve: MCP server exposes semantic search to AI assistants
5. Search: AI assistants query your knowledge base through natural language

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- ChromaDB 1.3.6 or higher (installed automatically with Minerva)
- For local AI: [Ollama](https://ollama.ai) or [LM Studio](https://lmstudio.ai)
- For cloud AI: API keys for OpenAI or Google Gemini

> **Note:** ChromaDB 1.3.6+ is required to prevent database corruption issues. Earlier versions (including 1.1.0) have known bugs that can corrupt the database during concurrent operations.

### Choose Your Deployment

Minerva supports multiple deployment scenarios depending on your needs:

#### 🎯 Option A: Personal Local Knowledge Base (Easiest)

**Use case:** Index your code repositories for use with Claude Desktop
**Guide:** See [`tools/minerva-kb/README.md`](tools/minerva-kb/README.md)

This automated installer:

- Installs Minerva and minerva-kb via pipx
- Installs repository extractor and file watcher
- Guides you to create your first collection with `minerva-kb add`

```bash
./tools/minerva-kb/install.sh
```

After installation, manage collections with simple commands:

```bash
minerva-kb add /path/to/your/repository    # Create collection
minerva-kb list                            # View all collections
minerva-kb watch my-project                # Start auto-updates
```

#### 🔧 Option B: Custom Setup (Full Control)

**Use case:** Custom indexing pipelines, multiple collections, advanced configuration
**Guide:** Continue reading this README for manual installation and configuration

Install Minerva as a library and configure everything yourself:

- Choose your own directory structure
- Manage credentials your way (env vars, keychain, envchain, etc.)
- Create custom indexing workflows
- Deploy as HTTP server for team access

---

### Installation

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

- Clean: Each tool gets its own isolated environment
- Simple: One command to install, one command to uninstall
- Automatic: No PATH configuration needed
- Safe: No conflicts between different Python projects
- Secure: Built-in OS keychain support for API keys

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

#### You Don't Need to Activate the Virtual Environment!

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

### API Key Management

Minerva provides secure API key storage using your operating system's encrypted keychain. This is the recommended method for managing cloud provider credentials.

#### Store API Keys Securely

For cloud AI providers (OpenAI, Gemini), store your API key once in the OS keychain:

```bash
# Store OpenAI API key (prompts securely)
minerva keychain set OPENAI_API_KEY

# Store Gemini API key
minerva keychain set GEMINI_API_KEY
```

Your API keys are encrypted and stored in:

- **macOS**: Keychain Access (AES-256, Touch ID/Face ID support)
- **Linux**: GNOME Keyring / KWallet (Secret Service)
- **Windows**: Credential Manager (DPAPI, Windows Hello support)

#### Manage Stored Keys

```bash
# List stored providers
minerva keychain list

# View a key (masked for security)
minerva keychain get OPENAI_API_KEY
# Output: API key for 'OPENAI_API_KEY': sk-ab...xyz

# Update a key
minerva keychain set OPENAI_API_KEY

# Delete a key
minerva keychain delete OPENAI_API_KEY
```

#### Using Keys in Configuration

Reference stored keys in your config files:

```json
{
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini"
  }
}
```

Minerva resolves `${OPENAI_API_KEY}` by checking:

1. Environment variable `OPENAI_API_KEY` (highest priority)
2. OS keychain entry for `OPENAI_API_KEY` (fallback)
3. Error if not found (with helpful suggestions)

#### Alternative: Environment Variables

For CI/CD pipelines or temporary overrides, use environment variables:

```bash
# Set for current session
export OPENAI_API_KEY="sk-your-key-here"

# Or inline for single command
OPENAI_API_KEY="sk-..." minerva index --config config.json
```

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
  "default_max_results": 6
}
EOF

# 4. Index the notes into ChromaDB
minerva index --config configs/index/bear-notes-ollama.json --verbose

# 5. Peek at the indexed data
minerva peek bear_notes --chromadb ./chromadb_data


# 6. Start the MCP server (for Claude Desktop integration)
# Using minerva-kb (recommended - auto-managed config):
minerva-kb serve

# Or using minerva directly with manual config:
minerva serve --config configs/server/local.json

---

## Core Concepts

### The Note Schema

All data sources must be converted to a standardized JSON array:

```json
[
  {
    "title": "Note Title",
    "markdown": "The full markdown content...",
    "size": 1234,
    "modificationDate": "2025-10-20T12:00:00Z",
    "creationDate": "2025-10-20T10:00:00Z",
    "tags": ["optional", "custom", "fields"]
  }
]
```

**Required fields:**
- `title` (string, non-empty)
- `markdown` (string, can be empty)
- `size` (integer, UTF-8 byte length)
- `modificationDate` (string, ISO 8601 format)

**Optional fields:**
- `creationDate` (string, ISO 8601 format)
- Any custom fields for metadata

See [docs/NOTE_SCHEMA.md](docs/NOTE_SCHEMA.md) for complete specification.

### Extractors

Extractors are independent packages that convert specific data sources into the standardized JSON schema. Minerva includes four official extractors:

- **bear-notes-extractor**: Extracts notes from Bear app backups (.bear2bk files)
- **zim-extractor**: Extracts articles from Zim Wikipedia dumps
- **markdown-books-extractor**: Converts markdown books into searchable notes
- **repository-doc-extractor**: Extracts markdown documentation from code repositories

You can write custom extractors in any language. See [docs/EXTRACTOR_GUIDE.md](docs/EXTRACTOR_GUIDE.md).

### Collections

ChromaDB organizes data into **collections**. Each collection:

- Has a unique name (e.g., `bear_notes`, `research_papers`)
- Contains embeddings from a specific AI provider and model
- Stores metadata about its source and configuration
- Can be queried independently through the MCP server

---

## Commands

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

### `minerva remove`

Permanently delete a ChromaDB collection. The command prints the full collection summary, then requires two confirmations before deleting anything.

```bash
minerva remove ./chromadb_data bear_notes
```

Use this when cleaning up experimental collections or rebuilding test data. Because deletion is irreversible, the command cannot be automated or forced—be prepared to type both `YES` and the collection name to proceed.

### `minerva query`

Query ChromaDB collections directly with semantic search.

```bash
minerva query CHROMADB_PATH "search query" [--collection NAME] [--max-results N] [--format text|json] [--verbose]
```

**Options:**

- `CHROMADB_PATH`: Path to ChromaDB directory (required)
- `"search query"`: Text to search for (required)
- `--collection NAME`: Query specific collection (optional, searches all if omitted)
- `--max-results N`: Number of results to return (default: 5)
- `--format text|json`: Output format (default: text)
- `--verbose`: Show detailed search progress logs

**Examples:**

```bash
# Query specific collection
minerva query ~/.minerva/chromadb "How does authentication work?" --collection my_docs

# Query all collections
minerva query ~/.minerva/chromadb "API design patterns" --max-results 10

# JSON output for scripting
minerva query ~/.minerva/chromadb "error handling" --format json

# Verbose mode for debugging
minerva query ~/.minerva/chromadb "database schema" --collection my_docs --verbose
```

### `minerva serve`

Start the MCP server in stdio mode to expose collections to AI assistants (for Claude Desktop).

```bash
minerva serve --config configs/server/local.json
```

**Example config:**

```json
{
  "chromadb_path": "../../chromadb_data",
  "default_max_results": 6
}
```

### `minerva serve-http`

Start the MCP server in HTTP mode for network access (for team deployments).

```bash
minerva serve-http --config configs/server/remote.json
```

**Example config:**

```json
{
  "chromadb_path": "/data/chromadb",
  "default_max_results": 6,
  "host": "0.0.0.0",
  "port": 8337
}
```

**Note:** For local Claude Desktop use, use `minerva serve` (stdio mode). The HTTP mode is for remote deployments or custom integrations.

## Usage Examples

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

---

## Extending Minerva

### Writing Custom Extractors

Create extractors for any data source by outputting JSON that conforms to the note schema:

```python
# my_extractor.py
import json
from datetime import datetime

def extract_my_source(input_path):
    notes = []
    # ... extract your data ...
    content = "Markdown content here"
    notes.append({
        "title": "Note Title",
        "markdown": content,
        "size": len(content.encode('utf-8')),
        "modificationDate": datetime.utcnow().isoformat().replace('+00:00', 'Z'),
        "creationDate": datetime.utcnow().isoformat().replace('+00:00', 'Z'),
        "source": "my_source"  # Custom field (optional)
    })
    return notes  # Return array, not dict with "notes" key

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

## Testing

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

## Documentation

- [Configuration Guide](docs/configuration.md) - Command-specific configuration reference for index and server
- [LM Studio Setup Guide](docs/LMSTUDIO_SETUP.md) - Installing and configuring LM Studio
- [Note Schema](docs/NOTE_SCHEMA.md) - Complete JSON schema specification
- [Extractor Guide](docs/EXTRACTOR_GUIDE.md) - How to write custom extractors
- [Legacy Config Guide](docs/CONFIGURATION_GUIDE.md) - Archived reference for the pre-v3 unified system
- [Release Notes v2.0](docs/RELEASE_NOTES_v2.0.md) - What's new in version 2.0
- [Upgrade Guide v2.0](docs/UPGRADE_v2.0.md) - How to upgrade from v1.x
- [CLAUDE.md](CLAUDE.md) - Developer guide for working with this codebase

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Minerva builds upon these excellent open-source projects:

- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - Document chunking
- [Ollama](https://ollama.ai/) - Local AI models
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework

---

## About the Name

Minerva is named after the Roman goddess of wisdom, knowledge, and strategic warfare—fitting for a system that helps manage and retrieve knowledge.
This project is dedicated to the memory of my mother, Nadia Minerva (Sept 30th, 1947 - Oct 17th, 2025).
