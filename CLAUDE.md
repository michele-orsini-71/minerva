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
```bash
# Run complete pipeline: JSON → Chunks → Embeddings → ChromaDB
cd bear-notes-cag-data-creator
python full_pipeline.py --verbose "../test-data/Bear Notes 2025-09-20 at 08.49.json"

# Custom chunk size and ChromaDB path
python full_pipeline.py --chunk-size 1200 --chromadb-path ../chromadb_data --verbose "../test-data/Bear Notes 2025-09-20 at 08.49.json"

# Quick pipeline test
python full_pipeline.py "../test-data/sample.json"
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
from json_loader import load_bear_notes_json
from chunk_creator import create_chunks_for_notes
from embedding import generate_embeddings_batch
from storage import initialize_chromadb_client, get_or_create_collection, insert_chunks_batch

# Load and process
notes = load_bear_notes_json("notes.json")
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
- **Key dependencies**: chromadb, ollama, numpy, nltk, tiktoken
- **No external APIs**: All processing runs locally

#### AI Models
- **Embedding model**: `mxbai-embed-large:latest`
- **Query models**: `llama3.1:8b`, `gpt-oss:20b`, `gemma3:12b-it-qat`
- **Model storage**: Managed by Ollama (~/.ollama/)

#### Storage Configuration
- **Vector database**: `chromadb_data/` (persistent ChromaDB)
- **Temporary processing**: System temp directories (auto-cleanup)
- **Note outputs**: JSON files alongside input backups