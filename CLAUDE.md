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

### Testing and Development
```bash
# Test ChromaDB connection
python test-files/test-connect.py

# Test chunking and embedding pipeline
cd bear-notes-cag-data-creator
python ../test-files/test-chunking.py

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
- **`bear-notes-cag-data-creator/`**: RAG data pipeline and embedding generation
- **`chromadb_data/`**: Persistent vector database storage (ChromaDB)
- **`test-files/`**: Example implementations and integration tests
- **`.venv/`**: Shared Python virtual environment (Python 3.13)

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

#### Multi-Stage Processing Pipeline

**Stage 1: Note Extraction (`bear-notes-parser/`)**
- Processes Bear backup files (.bear2bk format - ZIP archives with TextBundle folders)
- Filters out trashed notes automatically
- Normalizes timestamps to UTC ISO format
- Outputs structured JSON with note metadata

**Stage 2: Content Chunking (`test-files/test-chunking.py`)**
- Semantic chunking that preserves markdown structure
- Smart boundary detection (respects code blocks, headings, paragraphs)
- Configurable chunk size (300 tokens default) with overlap (50 tokens)
- Maintains heading context for better retrieval accuracy

**Stage 3: Embedding Generation**
- Local AI embeddings using `mxbai-embed-large:latest` via Ollama
- L2 normalization for cosine similarity compatibility
- Batch processing with progress feedback
- No external API dependencies

**Stage 4: Vector Storage (ChromaDB)**
- HNSW index with cosine similarity metric
- Stable chunk IDs for incremental updates
- Rich metadata schema for provenance and filtering
- Persistent file-based storage

### Key Technical Decisions

#### Chunking Strategy
- **Token-based**: Uses tiktoken for accurate token counting (300-token target chunks)
- **Structure-preserving**: Maintains code blocks as atomic units
- **Heading-aware**: Respects markdown heading hierarchy for semantic boundaries
- **Overlap strategy**: 50-token overlap (10-20% ratio) for context continuity

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
collection = client.get_or_create_collection("notes", metadata={"hnsw:space": "cosine"})
```

#### Ollama AI Integration
```python
# Local embedding generation
from ollama import embeddings as ollama_embeddings
embeddings = ollama_embeddings(model="mxbai-embed-large:latest", prompt=text)
```

### Development Workflow

#### New Note Processing
1. Extract notes using `bear-notes-parser/cli.py`
2. Run chunking pipeline in `bear-notes-cag-data-creator/`
3. Verify results with `test-files/test-chunking.py`

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