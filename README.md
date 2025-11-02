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
⚙️ **Unified Configuration**: Single config file for all components with provider reuse

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

# 3. Create a unified configuration file
cat > config.json << 'EOF'
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_data",
    "collections": [
      {
        "collection_name": "my_notes",
        "description": "My personal notes from Bear app",
        "json_file": "bear-notes.json",
        "ai_provider_id": "ollama-local"
      }
    ]
  },
  "server": {
    "chromadb_path": "./chromadb_data",
    "default_max_results": 5
  }
}
EOF

# 4. Index the notes into ChromaDB
minerva index --config config.json --verbose

# 5. Peek at the indexed data
minerva peek my_notes --chromadb ./chromadb_data

# 6. Start the MCP server (for Claude Desktop integration)
minerva serve --config config.json
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
minerva index --config index-config.json [--verbose] [--dry-run]
```

**Options:**

- `--config FILE`: Configuration JSON file (required)
- `--verbose`: Show detailed progress information
- `--dry-run`: Validate without actually indexing

**Example config (unified):**

```json
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_data",
    "collections": [
      {
        "collection_name": "my_notes",
        "description": "Personal notes collection",
        "json_file": "./notes.json",
        "ai_provider_id": "ollama-local"
      }
    ]
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
minerva serve --config server-config.json
```

**Example config (unified):**

```json
{
  "server": {
    "chromadb_path": "./chromadb_data",
    "default_max_results": 5
  }
}
```

### `minerva chat`

Interactive AI-powered chat interface that can search and query your knowledge bases.

```bash
minerva chat --config chat-config.json [OPTIONS]
```

**Options:**

- `--config FILE`: Chat configuration JSON file (required)
- `-q "QUESTION"`: Single-question mode (ask and exit)
- `--system "PROMPT"`: Custom system prompt
- `--list`: List all past conversations
- `--resume ID`: Resume a previous conversation

**Example config:**

```json
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest"
    },
    "llm": {
      "model": "llama3.1:8b"
    }
  },
  "conversation_dir": "~/.minerva/conversations",
  "default_max_results": 3,
  "enable_streaming": true
}
```

**Interactive mode:**

```bash
minerva chat --config chat-config.json

Welcome to Minerva Chat! 🤖
Connected to 3 knowledge base(s) via Ollama (llama3.1:8b)

Commands: /clear (new conversation) | /help | /exit

You: What knowledge bases are available?
AI: 🔍 Listing available knowledge bases...
    I have access to 3 knowledge bases:
    - personal-notes (1,234 chunks)
    - python-books (5,678 chunks)
    ...

You: Search python-books for decorators
AI: 🔍 Searching 'python-books' for: 'decorators'...
    [AI provides information based on search results]
```

**Single-question mode:**

```bash
minerva chat --config chat-config.json -q "Summarize my Python notes"
```

See the [Chat Guide](docs/CHAT_GUIDE.md) for detailed usage, configuration, and examples.

---

## 🎨 Usage Examples

### Example 1: Index Bear Notes with Local AI (Ollama)

```bash
# Extract Bear notes
bear-extractor "Bear Backup.bear2bk" -o bear-notes.json

# Create unified config for local AI
cat > bear-ollama.json << 'EOF'
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_data",
    "collections": [
      {
        "collection_name": "bear_notes_local",
        "description": "Personal notes from Bear app",
        "json_file": "bear-notes.json",
        "ai_provider_id": "ollama-local"
      }
    ]
  }
}
EOF

# Index with verbose output
minerva index --config bear-ollama.json --verbose
```

### Example 2: Using LM Studio for Desktop

```bash
# Start LM Studio and load a model (e.g., qwen2.5-7b-instruct)
# Start the server in LM Studio on port 1234

# Create config for LM Studio
cat > lmstudio-config.json << 'EOF'
{
  "ai_providers": [
    {
      "id": "lmstudio-local",
      "provider_type": "lmstudio",
      "base_url": "http://localhost:1234/v1",
      "embedding_model": "qwen2.5-7b-instruct",
      "llm_model": "qwen2.5-14b-instruct",
      "rate_limit": {
        "requests_per_minute": 60,
        "concurrency": 1
      }
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_data",
    "collections": [
      {
        "collection_name": "my_notes",
        "description": "Personal knowledge base",
        "json_file": "notes.json",
        "ai_provider_id": "lmstudio-local"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "lmstudio-local",
    "mcp_server_url": "http://localhost:8000/mcp",
    "enable_streaming": false
  },
  "server": {
    "chromadb_path": "./chromadb_data",
    "default_max_results": 5
  }
}
EOF

# Index, serve, and chat - all using LM Studio
minerva index --config lmstudio-config.json --verbose
minerva serve --config lmstudio-config.json &
minerva chat --config lmstudio-config.json
```

See the [LM Studio Setup Guide](docs/LMSTUDIO_SETUP.md) for detailed installation and configuration instructions.

### Example 3: Index Multiple Sources

```bash
# Extract from different sources
bear-extractor "Bear.bear2bk" -o bear.json
zim-extractor "wikipedia.zim" -o wiki.json
markdown-books-extractor books/ -o books.json

# Create unified config with multiple collections
cat > multi-collection.json << 'EOF'
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_data",
    "collections": [
      {
        "collection_name": "bear_notes",
        "description": "Personal notes from Bear",
        "json_file": "bear.json",
        "ai_provider_id": "ollama-local"
      },
      {
        "collection_name": "wikipedia",
        "description": "Wikipedia articles",
        "json_file": "wiki.json",
        "ai_provider_id": "ollama-local"
      },
      {
        "collection_name": "books",
        "description": "Technical books",
        "json_file": "books.json",
        "ai_provider_id": "ollama-local"
      }
    ]
  },
  "server": {
    "chromadb_path": "./chromadb_data",
    "default_max_results": 5
  }
}
EOF

# Index all collections
minerva index --config multi-collection.json --verbose

# All collections available through single MCP server
minerva serve --config multi-collection.json
```

### Example 3: Test Before Indexing

```bash
# First, validate the extracted data
minerva validate notes.json --verbose

# Then do a dry run to check configuration
minerva index --config config.json --dry-run

# Finally, index for real
minerva index --config config.json --verbose
```

### Example 4: Complete Workflow with All Commands

This example shows all four Minerva commands in a realistic workflow:

```bash
# Step 1: Extract notes from Bear backup
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o my-notes.json -v

# Step 2: Validate the extracted JSON before indexing
minerva validate my-notes.json --verbose
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
minerva index --config index-config.json --verbose
# Output: Processing 1,234 notes...
# Output: Created 5,678 chunks...
# Output: Generating embeddings...
# Output: ✓ Indexing complete!

# Step 5: Peek at the collection to verify what was indexed
minerva peek personal_knowledge --chromadb ./chromadb_data --format table
# Output shows: collection name, document count, sample entries, metadata

# Step 6: Peek with JSON format for detailed inspection
minerva peek personal_knowledge --chromadb ./chromadb_data --format json > collection-info.json

# Step 7: Create MCP server configuration
cat > server-config.json << 'EOF'
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
EOF

# Step 8: Start the MCP server (makes your notes available to Claude Desktop)
minerva serve --config server-config.json
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
minerva peek --chromadb ./chromadb_data

# Inspect your Bear notes collection
minerva peek bear_notes --chromadb ./chromadb_data --format table

# Inspect Wikipedia articles collection
minerva peek wikipedia_history --chromadb ./chromadb_data --format table

# Get detailed JSON output for programmatic analysis
minerva peek bear_notes --chromadb ./chromadb_data --format json | jq '.metadata'

# Compare collection sizes
echo "Bear notes:"
minerva peek bear_notes --chromadb ./chromadb_data --format json | jq '.count'
echo "Wikipedia:"
minerva peek wikipedia_history --chromadb ./chromadb_data --format json | jq '.count'
```

### Example 6: Interactive Chat with Your Knowledge Base

```bash
# Create chat configuration with Ollama (local AI)
cat > chat-config.json << 'EOF'
{
  "chromadb_path": "/Users/you/chromadb_data",
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest"
    },
    "llm": {
      "model": "llama3.1:8b"
    }
  },
  "conversation_dir": "~/.minerva/conversations",
  "default_max_results": 3,
  "enable_streaming": true
}
EOF

# Start interactive chat session
minerva chat --config chat-config.json

# Example conversation:
# You: What knowledge bases do I have?
# AI: 🔍 Listing available knowledge bases...
#     Found 2 knowledge bases:
#     ✓ personal-notes (1,234 chunks)
#     ✓ python-books (5,678 chunks)
#
# You: Search python-books for information about decorators
# AI: 🔍 Searching 'python-books' for: 'decorators'...
#     [Provides detailed information from your indexed Python books]
#
# You: Can you give me examples?
# AI: [Continues conversation with examples based on previous context]

# Single-question mode (useful for scripts)
minerva chat --config chat-config.json \
  -q "Summarize my notes about Docker best practices"

# List previous conversations
minerva chat --config chat-config.json --list

# Resume a previous conversation
minerva chat --config chat-config.json --resume 20251030-143022-abc123

# Use custom system prompt
minerva chat --config chat-config.json \
  --system "You are a Python expert. Focus on code quality and best practices."
```

**Chat Features:**

- 🔍 **Semantic Search**: AI searches your knowledge bases using natural language
- 💬 **Context Aware**: Maintains conversation history for follow-up questions
- 📚 **Multi-Collection**: Access all your indexed collections in one chat
- 💾 **Auto-Save**: Conversations automatically saved and resumable
- ⚡ **Streaming**: Real-time response streaming for better UX
- 🎯 **Smart Context**: Automatic context window management with summarization

See the [Chat Guide](docs/CHAT_GUIDE.md) for advanced usage, troubleshooting, and more examples.

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
minerva index --config config.json
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
pytest tests/test_mcp_chat_integration.py -v     # MCP integration tests
pytest tests/test_unified_config_loader.py -v    # Config validation tests
```

### Validate Configuration

```bash
# Validate a configuration file
minerva config validate path/to/config.json

# Validate all sample configs
for config in configs/*.json; do
  minerva config validate "$config"
done
```

### Continuous Integration

The project includes GitHub Actions CI that automatically:
- Runs all tests with coverage
- Validates sample configurations
- Lints code with black, isort, and flake8
- Tests on Python 3.10, 3.11, 3.12, and 3.13

---

## 📚 Documentation

- **[Unified Configuration Guide](docs/configuration.md)** - Complete guide to unified configuration (recommended)
- **[LM Studio Setup Guide](docs/LMSTUDIO_SETUP.md)** - Installing and configuring LM Studio
- **[Chat Guide](docs/CHAT_GUIDE.md)** - Interactive chat command usage and examples
- **[Note Schema](docs/NOTE_SCHEMA.md)** - Complete JSON schema specification
- **[Extractor Guide](docs/EXTRACTOR_GUIDE.md)** - How to write custom extractors
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Legacy per-command configuration (deprecated)
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
