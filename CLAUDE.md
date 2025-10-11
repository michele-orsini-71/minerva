# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Environment Setup

```bash
# Activate the virtual environment (Python 3.13)
source .venv/bin/activate

# Check Python version
python --version

# Verify required dependencies are installed
pip list | grep -E "(chromadb|ollama|numpy|nltk|tiktoken)"
```

### Running Ollama Services (Required for AI Operations)

```bash
# Start Ollama service (required for embeddings and AI queries)
ollama serve

# Pull required models
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b
```

### Bear Notes Parser Operations

```bash
# Process Bear backup files
cd bear-notes-parser
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"

# Programmatic usage example
python -c "from bear_parser import parse_bear_backup; notes = parse_bear_backup('Bear Notes 2025-09-20 at 08.49.bear2bk'); print(f'Extracted {len(notes)} notes')"
```

### Complete RAG Pipeline Operations

#### New Config-Driven Pipeline (Recommended)

The pipeline now supports **multi-provider AI abstraction** with JSON configuration files:

```bash
# Run pipeline with Ollama (local, no API keys needed)
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-ollama.json

# Run pipeline with OpenAI (requires OPENAI_API_KEY environment variable)
export OPENAI_API_KEY="sk-your-key-here"
python full_pipeline.py --config ../configs/example-openai.json

# Run pipeline with Google Gemini (requires GEMINI_API_KEY environment variable)
export GEMINI_API_KEY="your-key-here"
python full_pipeline.py --config ../configs/example-gemini.json

# Verbose mode shows detailed provider initialization and progress
python full_pipeline.py --config ../configs/example-ollama.json --verbose

# Dry run mode validates configuration without processing
python full_pipeline.py --config ../configs/example-ollama.json --dry-run
```

#### Legacy Command-Line Arguments (Deprecated)

```bash
# Old style: direct command-line arguments (still supported for backward compatibility)
python full_pipeline.py --verbose "../test-data/Bear Notes 2025-09-20 at 08.49.json"

# Custom chunk size and ChromaDB path
python full_pipeline.py --chunk-size 1200 --chromadb-path ../chromadb_data --verbose "../test-data/Bear Notes 2025-09-20 at 08.49.json"
```

### Testing and Development

```bash
# Test ChromaDB connection
python test-files/test-connect.py

# Test complete RAG pipeline
cd bear-notes-cag-data-creator
python full_pipeline.py --verbose ../test-data/sample.json

# Test individual components
python json_loader.py ../test-data/sample.json
python chunk_creator.py
python embedding.py  # Test Ollama connection
python storage.py    # Test ChromaDB operations

# Run Bear parser tests
cd bear-notes-parser
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"
```

## Architecture

This repository implements a **Bear Notes RAG (Retrieval-Augmented Generation) system** for personal knowledge management. The system extracts notes from Bear backups, processes them into semantic chunks, generates embeddings using local AI models, and stores them in a vector database for intelligent search and retrieval.

### High-Level Data Flow

```
Bear Backup (.bear2bk) → Parse Notes → Chunk Content → Generate Embeddings → Store in ChromaDB → Query/Search
```

### Project Structure

The repository is organized into several specialized components:

#### Core Components

- **`bear-notes-parser/`**: Bear backup file parser and CLI utility
- **`bear-notes-cag-data-creator/`**: Complete RAG pipeline (chunking + embeddings + storage)
- **`chromadb_data/`**: Persistent vector database storage (ChromaDB)
- **`test-files/`**: Example implementations and integration tests
- **`.venv/`**: Shared Python virtual environment (Python 3.13)
- **`chroma-peek/`**: Visual exploration tool for ChromaDB databases

#### Auxiliary Components

- **`bear-notes-mcp-server/`**: MCP server placeholder (future development)
- **`bear-notes-cag-mcp/`**: MCP integration placeholder
- **`prompts/`**: AI prompt templates for content generation

### Core Architecture Patterns

#### Offline-First AI Stack

- **No internet dependency**: All AI processing runs locally using Ollama
- **Local models**: `mxbai-embed-large:latest` for embeddings, `llama3.1:8b` for queries
- **Persistent storage**: ChromaDB maintains vector database between sessions
- **Self-contained**: Complete knowledge management system runs on local machine

#### Complete RAG Pipeline (`bear-notes-cag-data-creator/full_pipeline.py`)

**Stage 1: Note Extraction (`bear-notes-parser/`)**

- Processes Bear backup files (.bear2bk format - ZIP archives with TextBundle folders)
- Filters out trashed notes automatically
- Normalizes timestamps to UTC ISO format
- Outputs structured JSON with note metadata

**Stage 2: Content Chunking (`chunk_creator.py`)**

- LangChain-based semantic chunking that preserves markdown structure
- Smart boundary detection (respects code blocks, headings, paragraphs)
- Configurable chunk size (1200 characters default) with auto-calculated overlap
- Maintains heading context for better retrieval accuracy
- Stable SHA256-based chunk IDs for incremental updates

**Stage 3: Embedding Generation (`embedding.py`)**

- Local AI embeddings using `mxbai-embed-large:latest` via Ollama
- L2 normalization for cosine similarity compatibility
- Batch processing with progress feedback and error handling
- No external API dependencies - completely offline

**Stage 4: Vector Storage (`storage.py`)**

- ChromaDB with HNSW index and cosine similarity metric
- Rich metadata schema for provenance and filtering
- Batch insertion with progress callbacks
- Persistent file-based storage with efficient querying

**Complete Pipeline Integration**

- End-to-end processing in single command: `python full_pipeline.py notes.json`
- Real-time progress tracking across all stages
- Comprehensive error handling with graceful degradation
- Performance metrics and statistics reporting

### Key Technical Decisions

#### Chunking Strategy

- **Character-based**: 1200 characters target chunks (configurable via `--chunk-size`)
- **LangChain-powered**: Uses MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter
- **Structure-preserving**: Maintains code blocks, tables, and markdown elements as atomic units
- **Heading-aware**: Respects markdown heading hierarchy for semantic boundaries
- **Smart overlap**: Auto-calculated overlap (typically 200 characters) for context continuity
- **Stable IDs**: SHA256-based chunk identifiers enable incremental updates

#### Vector Database Design

- **Stable IDs**: SHA256-based chunk IDs enable incremental updates
- **Metadata schema**: `note_id`, `title`, `modificationDate`, `size`, `chunk_index`
- **Distance metric**: Cosine similarity (with L2-normalized embeddings)
- **Batch operations**: Optimized for 32-128 chunks per operation

#### Error Resilience

- **Note-level tolerance**: Continues processing if individual notes fail
- **Graceful degradation**: Skips corrupted chunks and continues
- **Progress tracking**: Real-time feedback for long-running operations
- **Automatic cleanup**: Temporary directories cleaned up automatically

### Integration Points

#### Complete Pipeline Integration

```python
# Full pipeline programmatic usage
from json_loader import load_json_notes
from chunk_creator import create_chunks_for_notes
from embedding import generate_embeddings_batch
from storage import initialize_chromadb_client, get_or_create_collection, insert_chunks_batch

# Load and process
notes = load_json_notes("notes.json")
enriched_notes = create_chunks_for_notes(notes, target_chars=1200)

# Generate embeddings and store
all_chunks = [chunk for note in enriched_notes for chunk in note['chunks']]
embeddings = generate_embeddings_batch([chunk['content'] for chunk in all_chunks])
client = initialize_chromadb_client("./chromadb_data")
collection = get_or_create_collection(client)
insert_chunks_batch(collection, chunks_with_embeddings)
```

#### Bear Notes Parser Integration

```python
# Core function usage
from bear_parser import parse_bear_backup
notes = parse_bear_backup("backup.bear2bk", progress_callback=show_progress)
# Returns: [{"title", "markdown", "size", "modificationDate", "creationDate"}, ...]
```

#### ChromaDB Integration

```python
# Vector database operations
import chromadb
client = chromadb.PersistentClient(path="chromadb_data")
collection = client.get_or_create_collection("bear_notes", metadata={"hnsw:space": "cosine"})
```

#### Ollama AI Integration

```python
# Local embedding generation
from ollama import embeddings as ollama_embeddings
embeddings = ollama_embeddings(model="mxbai-embed-large:latest", prompt=text)
```

### Development Workflow

#### Complete RAG Pipeline Processing

1. Extract notes using `bear-notes-parser/cli.py`
2. Ensure Ollama is running with required models
3. Run complete pipeline: `cd bear-notes-cag-data-creator && python full_pipeline.py --verbose notes.json`
4. Verify ChromaDB results with `chroma-peek` tool

#### Individual Component Testing

1. Test chunking: `python chunk_creator.py`
2. Test embeddings: `python embedding.py`
3. Test storage: `python storage.py`
4. Test complete integration: `python full_pipeline.py --verbose test_data.json`

#### Model Management

- Ensure Ollama service is running (`ollama serve`)
- Verify required models are available (`ollama list`)
- Pull new models as needed (`ollama pull <model>`)

#### Database Maintenance

- ChromaDB data persists in `chromadb_data/` directory
- Collection management through ChromaDB client API
- Backup database directory for data preservation

### Configuration and Dependencies

#### Python Environment

- **Python version**: 3.13 (configured in `.venv/`)
- **Key dependencies**: chromadb, ollama, litellm, numpy, nltk, tiktoken
- **Multi-provider support**: LiteLLM enables unified interface to Ollama, OpenAI, Gemini, Azure, Anthropic

#### AI Models

**Local (Ollama)**:
- **Embedding model**: `mxbai-embed-large:latest` (1024 dimensions)
- **LLM models**: `llama3.1:8b`, `gpt-oss:20b`, `gemma3:12b-it-qat`
- **Model storage**: Managed by Ollama (~/.ollama/)

**Cloud Providers**:
- **OpenAI**: `text-embedding-3-small` (1536 dim), `gpt-4o-mini`
- **Google Gemini**: `text-embedding-004` (768 dim), `gemini-1.5-flash`
- **Azure OpenAI**: Custom deployments
- **Anthropic**: Via LiteLLM proxy

#### Storage Configuration

- **Vector database**: `chromadb_data/` (persistent ChromaDB)
- **Provider metadata**: Stored in collection metadata for MCP server reconstruction
- **Temporary processing**: System temp directories (auto-cleanup)
- **Note outputs**: JSON files alongside input backups

## Multi-Provider AI Setup

### Configuration Files

The system uses JSON configuration files located in `configs/` directory. Each file specifies:
- **Collection metadata**: name, description, database paths
- **AI provider**: type (ollama/openai/gemini), models, API keys
- **Processing options**: chunk size, force recreate, skip validation

Example configurations are provided:
- `configs/example-ollama.json` - Local Ollama (no API keys)
- `configs/example-openai.json` - OpenAI cloud service
- `configs/example-gemini.json` - Google Gemini cloud service

### Setting Up API Keys

Cloud providers require API keys stored as **environment variables**:

```bash
# OpenAI
export OPENAI_API_KEY="sk-your-openai-api-key-here"

# Google Gemini
export GEMINI_API_KEY="your-gemini-api-key-here"

# Azure OpenAI (if using Azure)
export AZURE_API_KEY="your-azure-key-here"
export AZURE_API_BASE="https://your-resource.openai.azure.com"
```

**Security Note**: API keys are stored in config files as environment variable templates (e.g., `${OPENAI_API_KEY}`), not as actual secrets. The pipeline resolves these at runtime.

### Provider Metadata Flow

The multi-provider system follows this metadata flow:

```
1. Config File (configs/*.json)
   ↓
   Contains: provider type, models, API key templates

2. Pipeline Execution (full_pipeline.py)
   ↓
   - Initializes AI provider from config
   - Generates embeddings with provider
   - Extracts provider metadata

3. ChromaDB Storage (chromadb_data/)
   ↓
   Collection metadata includes:
   - embedding_provider: "ollama" / "openai" / "gemini"
   - embedding_model: "mxbai-embed-large:latest"
   - embedding_dimension: 1024
   - embedding_base_url: "http://localhost:11434"
   - embedding_api_key_ref: "${OPENAI_API_KEY}" or null
   - llm_model: "llama3.1:8b"

4. MCP Server Startup (markdown-notes-mcp-server/)
   ↓
   - Reads collection metadata from ChromaDB
   - Reconstructs AI provider for each collection
   - Resolves environment variables at runtime
   - Checks provider availability
   - Marks collections as available/unavailable

5. MCP Search Queries
   ↓
   - Uses collection-specific provider
   - Validates embedding dimensions match
   - Generates query embeddings with correct provider
```

### MCP Server Multi-Provider Behavior

When the MCP server starts, it discovers all collections and checks provider availability:

#### Example: All Collections Available

```
[INFO] Discovering collections in ChromaDB...
[INFO] Found 2 collections

[INFO] Collection: bear_notes_ollama
[INFO]   Provider: ollama (mxbai-embed-large:latest)
[INFO]   Status: ✓ Available (dimension: 1024)

[INFO] Collection: bear_notes_openai
[INFO]   Provider: openai (text-embedding-3-small)
[INFO]   Status: ✓ Available (dimension: 1536)

[INFO] Summary: 2 available, 0 unavailable
[INFO] MCP server ready
```

#### Example: Mixed Availability

```
[INFO] Discovering collections in ChromaDB...
[INFO] Found 3 collections

[INFO] Collection: bear_notes_ollama
[INFO]   Provider: ollama (mxbai-embed-large:latest)
[INFO]   Status: ✓ Available (dimension: 1024)

[INFO] Collection: bear_notes_openai
[INFO]   Provider: openai (text-embedding-3-small)
[INFO]   Status: ✗ Unavailable
[INFO]   Reason: Missing API key - OPENAI_API_KEY not found in environment

[INFO] Collection: bear_notes_gemini
[INFO]   Provider: gemini (text-embedding-004)
[INFO]   Status: ✗ Unavailable
[INFO]   Reason: Missing API key - GEMINI_API_KEY not found in environment

[INFO] Summary: 1 available, 2 unavailable
[INFO] MCP server ready (some collections unavailable)
```

#### Example: No Collections Available

```
[ERROR] No collections are available!

Troubleshooting:
1. Check that ChromaDB path is correct and contains collections
2. For Ollama collections: Ensure 'ollama serve' is running
3. For OpenAI collections: Set OPENAI_API_KEY environment variable
4. For Gemini collections: Set GEMINI_API_KEY environment variable
5. Run the pipeline to create new collections

[ERROR] Exiting - no collections available for queries
```

## Troubleshooting

### Common Errors and Solutions

#### Error: "Missing API key"

**Symptom**: Pipeline fails with `APIKeyMissingError` or provider marked as unavailable

**Cause**: Required environment variable for cloud provider is not set

**Solution**:
```bash
# Check which API key is needed (look at error message or config file)
# Set the environment variable:
export OPENAI_API_KEY="sk-your-key-here"
export GEMINI_API_KEY="your-key-here"

# Verify it's set
echo $OPENAI_API_KEY

# Then rerun the pipeline
python full_pipeline.py --config ../configs/example-openai.json
```

#### Error: "Embedding dimension mismatch"

**Symptom**: `EmbeddingError: Embedding dimension mismatch! Query: 1536, Collection: 1024`

**Cause**: Trying to query a collection with a different embedding model than it was created with

**Example**: Collection created with Ollama `mxbai-embed-large` (1024 dim), but MCP server trying to use OpenAI `text-embedding-3-small` (1536 dim)

**Solution**:
```bash
# Option 1: Use the same provider that created the collection
# Check collection metadata to see which provider was used:
python -c "
import chromadb
client = chromadb.PersistentClient(path='chromadb_data')
collection = client.get_collection('your_collection_name')
print(collection.metadata)
"

# The metadata will show:
# - embedding_provider: "ollama" / "openai" / "gemini"
# - embedding_model: the specific model used
# - embedding_dimension: expected dimension

# Option 2: Recreate the collection with the new provider
# Edit your config file to set forceRecreate: true
python full_pipeline.py --config ../configs/example-openai.json
```

**Prevention**: The MCP server automatically uses the correct provider for each collection by reading metadata. This error should only occur if metadata is corrupted or missing.

#### Error: "Ollama service unavailable"

**Symptom**: `ProviderUnavailableError: Failed to connect to Ollama service`

**Cause**: Ollama service is not running

**Solution**:
```bash
# Start Ollama service in a separate terminal
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags

# Pull required models if not present
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b
```

#### Error: "Model not available"

**Symptom**: Provider initialization fails with "model not found"

**Solution for Ollama**:
```bash
# List available models
ollama list

# Pull the required model
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b
```

**Solution for Cloud Providers**:
- Verify model name is correct in config file
- Check provider documentation for available models
- Ensure you have access to the requested model tier

#### Error: "Collection already exists"

**Symptom**: `StorageError: Collection 'bear_notes' already exists`

**Cause**: Trying to create a collection that already exists without `forceRecreate` flag

**Solution**:
```bash
# Option 1: Use force recreate flag in config
# Edit config file: "forceRecreate": true

# Option 2: Use different collection name
# Edit config file: "collection_name": "bear_notes_v2"

# Option 3: Delete existing collection manually
python -c "
import chromadb
client = chromadb.PersistentClient(path='chromadb_data')
client.delete_collection('bear_notes')
"
```

#### Error: "Collection not found" (MCP Server)

**Symptom**: MCP search fails with "Collection 'xyz' does not exist"

**Cause**: Collection was deleted or ChromaDB path is incorrect

**Solution**:
```bash
# Check what collections exist
python -c "
import chromadb
client = chromadb.PersistentClient(path='chromadb_data')
collections = client.list_collections()
print([c.name for c in collections])
"

# Verify ChromaDB path in MCP server config
cat markdown-notes-mcp-server/config.json

# Recreate missing collections by running pipeline
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-ollama.json
```

#### Warning: "Description validation score < 7"

**Symptom**: Pipeline shows warning about low description quality score

**Cause**: Collection description is too generic or unclear

**Impact**: Non-blocking warning - pipeline continues normally

**Solution**:
```bash
# Option 1: Improve description in config file
# Make it more specific and detailed about collection contents

# Option 2: Skip validation entirely
# Edit config file: "skipAiValidation": true

# Example of good vs bad descriptions:
# Bad:  "Personal notes"
# Good: "Personal notes exported from Bear app covering software development,
#        project management, meeting notes, research findings, and technical documentation"
```

### Performance Issues

#### Slow embedding generation

**Symptom**: Pipeline takes a long time to generate embeddings

**Causes and Solutions**:

1. **Using cloud API with rate limits**:
   ```bash
   # Cloud providers have rate limits
   # Consider using Ollama for local processing (faster, no rate limits)
   python full_pipeline.py --config ../configs/example-ollama.json
   ```

2. **Large batch of notes**:
   ```bash
   # Process incrementally or use smaller test set first
   # Test with small sample:
   python full_pipeline.py --config ../configs/test-small.json --verbose
   ```

3. **Ollama on slow hardware**:
   ```bash
   # Check Ollama resource usage
   # Consider using smaller/faster model or cloud provider
   ```

#### ChromaDB database corruption

**Symptom**: Errors when accessing ChromaDB, inconsistent results

**Solution**:
```bash
# Backup current database
cp -r chromadb_data chromadb_data_backup_$(date +%Y%m%d)

# Delete corrupted database
rm -rf chromadb_data

# Recreate collections from source JSON
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-ollama.json
```

### Debugging Tips

#### Enable verbose mode

```bash
# Get detailed logging
python full_pipeline.py --config ../configs/example-ollama.json --verbose
```

#### Test provider connection

```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Test OpenAI (requires API key)
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test programmatically
python -c "
from ai_provider import AIProvider, AIProviderConfig

config = AIProviderConfig(
    provider_type='ollama',
    embedding_model='mxbai-embed-large:latest',
    llm_model='llama3.1:8b',
    base_url='http://localhost:11434'
)

provider = AIProvider(config)
result = provider.check_availability()
print(f'Available: {result[\"available\"]}')
if not result['available']:
    print(f'Error: {result[\"error\"]}')
"
```

#### Inspect collection metadata

```bash
# View all collection metadata
python -c "
import chromadb
import json

client = chromadb.PersistentClient(path='chromadb_data')
collections = client.list_collections()

for coll in collections:
    print(f'\nCollection: {coll.name}')
    print(json.dumps(coll.metadata, indent=2))
"
```
