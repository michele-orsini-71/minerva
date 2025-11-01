# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Minerva** is a unified RAG (Retrieval-Augmented Generation) system for personal knowledge management. It provides tools for extracting notes from various sources, indexing them with AI-powered embeddings, and serving them through an MCP server for semantic search via Claude Desktop.

## Quick Reference

### Installation

```bash
# Install Minerva from project root
pip install -e .

# Verify installation
minerva --version
minerva --help

# Install extractors (optional, as needed)
cd extractors/bear-notes-extractor && pip install -e .
cd extractors/zim-extractor && pip install -e .
cd extractors/markdown-books-extractor && pip install -e .
```

### Core Commands

```bash
# Validate extracted notes
minerva validate notes.json [--verbose]

# Index notes into ChromaDB
minerva index --config config.json [--verbose] [--dry-run]

# Peek at indexed collection
minerva peek COLLECTION_NAME --chromadb PATH [--format table|json]

# Start MCP server
minerva serve --config server-config.json
```

### Extractor Commands

```bash
# Extract Bear notes
bear-extractor "Bear Notes.bear2bk" -o notes.json [-v]

# Extract from ZIM archive
zim-extractor wikipedia.zim -o wiki.json [-l LIMIT] [-v]

# Extract markdown book
markdown-books-extractor book.md -o book.json [-v]
```

## Architecture

### System Overview

Minerva follows a three-stage pipeline architecture:

```
┌─────────────┐     ┌────────────┐     ┌──────────────┐     ┌──────────┐
│   Sources   │ ──▶ │ Extractors │ ──▶ │  Minerva   │ ──▶ │   MCP    │
│ (Bear, Zim, │     │  (JSON)    │     │   (Index)    │     │  Server  │
│   Books)    │     └────────────┘     └──────────────┘     └──────────┘
└─────────────┘                               │                    │
                                               ▼                    ▼
                                        ┌──────────────┐     ┌──────────┐
                                        │   ChromaDB   │     │  Claude  │
                                        │   (Vector)   │     │ Desktop  │
                                        └──────────────┘     └──────────┘
```

### Directory Structure

```
minerva/                     # Core package
├── __init__.py
├── __main__.py
├── cli.py                     # Main CLI entry point
├── commands/                  # CLI command implementations
│   ├── index.py              # Index command
│   ├── serve.py              # MCP server command
│   ├── peek.py               # Collection inspection
│   └── validate.py           # Schema validation
├── common/                    # Shared utilities
│   ├── schemas.py            # JSON schema definitions
│   ├── logger.py             # Logging system
│   ├── config.py             # Configuration handling
│   └── ai_provider.py        # Multi-provider AI abstraction
├── indexing/                  # Indexing pipeline
│   ├── chunking.py           # Document chunking
│   ├── embeddings.py         # Embedding generation
│   ├── storage.py            # ChromaDB operations
│   └── json_loader.py        # JSON loading
└── server/                    # MCP server
    ├── mcp_server.py         # FastMCP server
    ├── search_tools.py       # Search implementations
    ├── collection_discovery.py
    └── startup_validation.py

extractors/                    # Independent extractor packages
├── bear-notes-extractor/
│   ├── bear_extractor/
│   │   ├── cli.py
│   │   └── parser.py
│   └── setup.py
├── zim-extractor/
│   ├── zim_extractor/
│   │   ├── cli.py
│   │   └── parser.py
│   └── setup.py
└── markdown-books-extractor/
    ├── markdown_books_extractor/
    │   ├── cli.py
    │   └── parser.py
    └── setup.py

docs/                          # Documentation
├── NOTE_SCHEMA.md            # Schema specification
└── EXTRACTOR_GUIDE.md        # Extractor development

chromadb_data/                 # ChromaDB storage (persistent)
test-data/                     # Test files and sample data
```

## Development Workflows

### Complete Workflow: Extract → Index → Serve

```bash
# 1. Extract notes from Bear
bear-extractor "Bear Notes 2025-10-20.bear2bk" -v -o bear-notes.json

# 2. Validate
minerva validate bear-notes.json --verbose

# 3. Create index configuration
cat > bear-config.json << 'EOF'
{
  "collection_name": "bear_notes",
  "description": "Personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "json_file": "bear-notes.json"
}
EOF

# 4. Index
minerva index --config bear-config.json --verbose

# 5. Peek at results
minerva peek bear_notes --chromadb ./chromadb_data --format table

# 6. Start MCP server
cat > server-config.json << 'EOF'
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
EOF

minerva serve --config server-config.json
```

### Working with Multiple Sources

```bash
# Extract from different sources
bear-extractor "Bear.bear2bk" -o bear.json
zim-extractor "wikipedia_history.zim" -l 1000 -o wiki.json
markdown-books-extractor "alice.md" -o alice.json

# Validate all
minerva validate bear.json
minerva validate wiki.json
minerva validate alice.json

# Index as separate collections
minerva index --config bear-config.json
minerva index --config wiki-config.json
minerva index --config alice-config.json

# All available through single MCP server
minerva serve --config server-config.json
```

### Testing Individual Components

```bash
# Test schema validation
python -c "
from minerva.common.schemas import validate_notes_file
import json

with open('test-data/sample.json') as f:
    data = json.load(f)

validate_notes_file(data, 'test-data/sample.json')
"

# Test chunking
python -c "
from minerva.indexing.chunking import create_chunks_for_notes

notes = [{'title': 'Test', 'markdown': 'Content...', 'size': 100, 'modificationDate': '2025-01-01T00:00:00Z'}]
chunked = create_chunks_for_notes(notes, target_chars=500)
print(f'Created {sum(len(n[\"chunks\"]) for n in chunked)} chunks')
"

# Test ChromaDB connection
python -c "
from minerva.indexing.storage import initialize_chromadb_client
client = initialize_chromadb_client('./chromadb_data')
print(f'Collections: {[c.name for c in client.list_collections()]}')
"
```

## Key Implementation Details

### Note Schema

All extractors must output JSON conforming to this schema:

```python
{
    "title": str,              # Required, non-empty
    "markdown": str,           # Required, can be empty
    "size": int,               # Required, >= 0, UTF-8 byte length
    "modificationDate": str,   # Required, ISO 8601 format
    "creationDate": str,       # Optional, ISO 8601 format
    # ... custom fields allowed
}
```

See `docs/NOTE_SCHEMA.md` for complete specification.

### Chunking Strategy

- **Character-based**: Default 1200 characters per chunk
- **LangChain-powered**: Uses `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter`
- **Structure-preserving**: Respects code blocks, tables, headings
- **Smart overlap**: Auto-calculated (typically ~200 chars) for context continuity
- **Stable IDs**: SHA256-based chunk identifiers

Configuration:

```python
from minerva.indexing.chunking import create_chunks_for_notes

chunked_notes = create_chunks_for_notes(
    notes,
    target_chars=1200,  # Configurable chunk size
    overlap_chars=None  # Auto-calculated if None
)
```

### AI Provider Abstraction

Minerva supports multiple AI providers through `ai_provider.py`:

```python
from minerva.common.ai_provider import AIProvider, AIProviderConfig

# Local Ollama
config = AIProviderConfig(
    provider_type='ollama',
    embedding_model='mxbai-embed-large:latest',
    llm_model='llama3.1:8b',
    base_url='http://localhost:11434'
)

# OpenAI
config = AIProviderConfig(
    provider_type='openai',
    embedding_model='text-embedding-3-small',
    llm_model='gpt-4o-mini',
    api_key='${OPENAI_API_KEY}'  # Resolved from env
)

provider = AIProvider(config)
embeddings = provider.generate_embeddings(['text1', 'text2'])
```

### Logging System

Context-aware logging routes output appropriately:

```python
from minerva.common.logger import get_logger

# CLI mode: stdout for user messages, stderr for errors
logger = get_logger(__name__, mode="cli", simple=True)

# MCP server mode: stderr for all logs
logger = get_logger(__name__, mode="mcp", simple=False)

logger.info("Processing...")
logger.success("✓ Complete")
logger.warning("Warning message")
logger.error("Error occurred")
```

## Running Ollama (Local AI)

Required for local embeddings and queries:

```bash
# Start Ollama service
ollama serve

# Pull required models (in separate terminal)
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b

# Verify models are available
ollama list
```

## Configuration Files

### Index Configuration

```json
{
  "collection_name": "my_notes",
  "description": "Descriptive text about this collection",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json",
  "forceRecreate": false,
  "skipAiValidation": false
}
```

### Server Configuration

```json
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
```

**Configuration fields:**
- `chromadb_path` (required): Absolute path to ChromaDB storage directory
- `default_max_results` (required): Default number of search results (recommended: 3-5, max: 15)

### Chat Configuration

```json
{
  "chromadb_path": "./chromadb_data",
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest",
      "base_url": "http://localhost:11434"
    },
    "llm": {
      "model": "llama3.1:8b",
      "base_url": "http://localhost:11434"
    }
  },
  "conversation_dir": "~/.minerva/conversations",
  "default_max_results": 3,
  "enable_streaming": true,
  "temperature": 0.0
}
```

**Configuration fields:**
- `chromadb_path` (required): Absolute path to ChromaDB storage directory
- `ai_provider` (required): AI provider configuration (see Index Configuration for details)
- `conversation_dir` (optional): Directory for conversation history (default: ~/.minerva/conversations)
- `default_max_results` (optional): Default number of search results (default: 3, max: 15)
- `enable_streaming` (optional): Enable streaming responses (default: true)
- `temperature` (optional): LLM temperature for responses (default: 0.0)

**Why Temperature 0.0?**

Minerva chat differs from general-purpose chatbots - it's designed for **precise information retrieval** from your personal knowledge base, not creative conversation. Temperature 0.0 provides:

- **Deterministic responses**: Same query → same answer (reliable for knowledge retrieval)
- **Consistent tool calling**: More reliable function calling for searching collections
- **Better offline compatibility**: Works with more local models at temp 0.0
- **Accurate synthesis**: Focuses on facts from your notes, not creative elaboration

Standard chat applications (ChatGPT, Claude) use temperature 0.7-1.0 for natural, varied responses. For Minerva's RAG use case, determinism is a feature, not a limitation.

**When to increase temperature:**
- If you want more varied phrasings of the same information
- If you're using Minerva for brainstorming rather than retrieval
- If you have a high-quality model (GPT-4, Claude) that handles tools well at higher temps

## Writing Extractors

Extractors are independent programs that output standard JSON. They can be written in any language.

### Python Example

```python
#!/usr/bin/env python3
import json
from datetime import datetime, timezone

def extract_my_source(input_path):
    notes = []

    # Your extraction logic
    for item in source_data:
        note = {
            "title": item.title,
            "markdown": item.content,
            "size": len(item.content.encode('utf-8')),
            "modificationDate": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        notes.append(note)

    return notes

if __name__ == "__main__":
    import sys
    notes = extract_my_source(sys.argv[1])
    print(json.dumps(notes, indent=2))
```

Test with:

```bash
python my_extractor.py input.source > notes.json
minerva validate notes.json
```

See `docs/EXTRACTOR_GUIDE.md` for complete tutorial.

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=minerva --cov-report=html

# Run specific test file
pytest tests/test_schemas.py

# Verbose mode
pytest -v
```

### Manual Testing

```bash
# Test complete workflow with sample data
bear-extractor test-data/sample.bear2bk -o /tmp/test.json
minerva validate /tmp/test.json
minerva index --config test-configs/sample-config.json --dry-run
```

## Common Tasks

### Adding a New Command

1. Create `minerva/commands/newcmd.py`:

```python
def run_newcmd(args):
    # Implementation
    pass
```

2. Update `minerva/cli.py`:

```python
from minerva.commands.newcmd import run_newcmd

# Add subparser
newcmd_parser = subparsers.add_parser('newcmd', help='...')
# Add arguments
```

3. Test:

```bash
minerva newcmd --help
```

### Modifying the Schema

1. Edit `minerva/common/schemas.py`
2. Update `NOTE_SCHEMA` dictionary
3. Update validation functions if needed
4. Update `docs/NOTE_SCHEMA.md` documentation
5. Run tests: `pytest tests/test_schemas.py`

### Adding a New Extractor

1. Create directory: `extractors/my-extractor/`
2. Create package structure:

```
extractors/my-extractor/
├── my_extractor/
│   ├── __init__.py
│   ├── cli.py
│   └── parser.py
├── setup.py
└── README.md
```

3. Implement extraction logic in `parser.py`
4. Create CLI in `cli.py`
5. Add console_scripts entry point in `setup.py`
6. Test: `pip install -e . && my-extractor input -o output.json`
7. Validate: `minerva validate output.json`

See `docs/EXTRACTOR_GUIDE.md` for detailed guide.

## Troubleshooting

### Import Errors

```bash
# Ensure Minerva is installed
pip install -e .

# Check installation
pip list | grep minerva

# Verify imports work
python -c "from minerva.cli import main; print('OK')"
```

### ChromaDB Issues

```bash
# Check ChromaDB directory exists
ls -la chromadb_data/

# List collections
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
print([c.name for c in client.list_collections()])
"

# Delete corrupted collection
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
client.delete_collection('collection_name')
"
```

### Ollama Connection Errors

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# Check models are available
ollama list
```

### Validation Failures

```bash
# Run with verbose mode to see all errors
minerva validate notes.json --verbose

# Check first note manually
jq '.[0]' notes.json

# Common issues:
# - Missing required fields (title, markdown, size, modificationDate)
# - Invalid date format (must be ISO 8601)
# - Wrong root type (must be array [...], not object {...})
# - Empty title
# - Negative size
```

### MCP Server Not Starting

```bash
# Check ChromaDB path exists
ls -la ./chromadb_data

# Check collections exist
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
print(f'Collections: {len(client.list_collections())}')
"

# Check server config
cat server-config.json

# Run with verbose logging
# (MCP servers log to stderr)
minerva serve --config server-config.json 2>&1 | tee server.log
```

### Performance Issues

**Slow indexing:**

- Check Ollama is running locally (not cloud API with rate limits)
- Verify chunk size isn't too small (default 1200 is good)
- Monitor system resources (CPU, RAM)

**Slow extraction:**

- For ZIM files: use `--limit` to test with smaller sample first
- For Bear: ensure backup file isn't corrupted
- Check disk I/O (SSD vs HDD makes big difference)

### MCP Token Limit Errors

**Error message:** `"MCP tool response exceeds maximum allowed tokens"`

**What's happening:**
- Each search result includes surrounding context (~1,500 tokens per result in enhanced mode)
- Different MCP clients have different token limits (Claude Desktop: 25,000 tokens)
- Requesting too many results exceeds the MCP client's response size limit

**Expected behavior (AI self-regulation):**
1. AI requests search with `max_results=10`
2. Minerva returns results (~29,000 tokens)
3. **MCP client rejects** the response with clear error message
4. AI understands the error and **automatically retries** with `max_results=5`
5. Second attempt succeeds

This is the **designed behavior** - the AI learns the limit through experience rather than being artificially constrained.

**Configuration:**
```json
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5  // Recommended: 3-5 (max allowed: 15)
}
```

**Best practices:**
- Start with `max_results=3-5` (default: 5)
- Maximum allowed: 15 results (prevents extreme values)
- Use `context_mode="chunk_only"` if you need more results with less context
- Monitor server logs to see estimated token counts

**Debugging:**
The server logs include token estimation:
```
ℹ Estimated response size: ~15,234 tokens
⚠ Response may exceed common MCP token limit (25,000 tokens)
```

**Why not hard-code a token limit?**
- Different MCP clients may have different limits
- Different AI contexts may have different budgets
- AI models can handle different token counts
- The self-regulation pattern is more flexible and future-proof

## Environment Variables

```bash
# For cloud AI providers
export OPENAI_API_KEY="sk-your-key"
export GEMINI_API_KEY="your-key"

# For custom Ollama endpoint
export OLLAMA_HOST="http://custom-host:11434"

# For debugging
export MINERVA_DEBUG=1  # Enable debug logging
```

## Code Style and Conventions

### Python Version

- Target: Python 3.10+
- Developed with: Python 3.13
- Use modern type hints: `list[dict]` instead of `List[Dict]`

### Import Organization

```python
# Standard library
import json
import sys
from datetime import datetime
from pathlib import Path

# Third-party
import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Local
from minerva.common.logger import get_logger
from minerva.common.schemas import validate_notes_file
```

### Naming Conventions

- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Modules**: `snake_case.py`
- **Packages**: `snake_case/`

### Error Handling

```python
# Specific exceptions
try:
    result = risky_operation()
except FileNotFoundError:
    logger.error(f"File not found: {path}")
    return 1
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    return 1

# Log and re-raise for unexpected errors
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

## Resources

### Documentation

- **README.md**: Project overview and quick start
- **docs/NOTE_SCHEMA.md**: Complete schema specification
- **docs/EXTRACTOR_GUIDE.md**: How to write extractors
- **extractors/README.md**: Overview of official extractors
- **docs/CONFIGURATION_GUIDE.md**: Configuration options
- **docs/RELEASE_NOTES_v2.0.md**: Version 2.0 release notes
- **docs/UPGRADE_v2.0.md**: Version 2.0 upgrade guide

### External Links

- **ChromaDB**: https://docs.trychroma.com/
- **LangChain**: https://python.langchain.com/docs/
- **Ollama**: https://ollama.ai/
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Kiwix/ZIM**: https://www.kiwix.org/

## Development Setup

```bash
# Clone repository
git clone <repo-url>
cd minerva

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Install extractors (optional)
cd extractors/bear-notes-extractor && pip install -e . && cd ../..
cd extractors/zim-extractor && pip install -e . && cd ../..
cd extractors/markdown-books-extractor && pip install -e . && cd ../..

# Run tests
pytest

# Check code style
black --check minerva/
flake8 minerva/
```

## Git Workflow

```bash
# Make changes
git add .
git commit -m "feat: add new feature"

# Push changes
git push origin main
```

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test updates
- `chore:` - Maintenance tasks
