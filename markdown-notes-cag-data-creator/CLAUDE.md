# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Environment Setup
```bash
# Activate the shared virtual environment
source ../.venv/bin/activate

# Check Python version (should be 3.13.1)
python --version
```

### Dependencies
```bash
# Required packages are already installed in the virtual environment:
# chromadb, ollama, numpy, nltk, tiktoken

# Verify dependencies
pip list | grep -E "(chromadb|ollama|numpy|nltk|tiktoken)"
```

### Running Ollama Services
```bash
# Start Ollama service (required for embeddings)
ollama serve

# Pull required models (if not already available)
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b  # or alternative models as specified
```

### Testing the Implementation
```bash
# Run the example chunking script
python ../test-files/test-chunking.py

# Test with Bear notes data
python ../test-files/test-chunking.py  # Modify script to use actual data
```

### Working with Bear Notes Parser
```bash
# Process Bear backup file (from parent directory)
cd ../bear-notes-parser
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"

# Return to project directory
cd ../bear-notes-cag-data-creator
```

## Architecture

This project implements a **Bear Notes RAG (Retrieval-Augmented Generation) system** for creating vector embeddings and enabling AI-powered search across personal notes. The architecture follows a multi-stage pipeline approach.

### Project Structure

The project is organized across multiple directories in the parent workspace:
- **`bear-notes-cag-data-creator/`**: Main project directory (this directory)
- **`bear-notes-parser/`**: Bear backup file parser utility
- **`chromadb_data/`**: Persistent vector database storage
- **`test-files/`**: Example implementations and test scripts
- **`.venv/`**: Shared Python virtual environment

### Core Components

#### 1. Data Pipeline Architecture
```
Bear Backup (.bear2bk) → Parse Notes → Chunk Content → Generate Embeddings → Store in ChromaDB
```

#### 2. Bear Notes Parser (`../bear-notes-parser/`)
- **Input**: Bear backup files (.bear2bk format - ZIP archives with TextBundle folders)
- **Processing**: Extracts note metadata, filters out trashed notes, normalizes timestamps
- **Output**: JSON array with structured note data (title, markdown, size, modificationDate)
- **Key module**: `bear_parser.py` with `parse_bear_backup()` function

#### 3. Chunking Strategy (`../test-files/test-chunking.py`)
- **Semantic chunking**: Preserves markdown structure, headings, and code blocks
- **Chunk size**: 300 tokens (configurable) with 50-token overlap (10-20% overlap ratio)
- **Smart boundaries**: Maintains code block integrity, respects paragraph breaks
- **Heading context**: Carries heading path metadata for context reconstruction

#### 4. Vector Embedding System
- **Local AI model**: `mxbai-embed-large:latest` via Ollama
- **Embedding approach**: L2 normalization for cosine similarity in ChromaDB
- **Batch processing**: Processes texts individually through Ollama API
- **Vector storage**: ChromaDB with HNSW index and cosine distance metric

#### 5. ChromaDB Storage (`../chromadb_data/`)
- **Database type**: Persistent ChromaDB client (folder-based storage)
- **Index configuration**: HNSW with cosine similarity space
- **Chunk identification**: SHA256-based stable IDs (`note_id|modificationDate|chunk_index`)
- **Metadata schema**:
  - `note_id`: Stable SHA1 hash of note title
  - `title`: Original note title from Bear
  - `modificationDate`: UTC ISO format timestamp
  - `size`: UTF-8 byte size of original note
  - `chunk_index`: Sequential index within note
  - `heading_path`: Array of heading context (future enhancement)

### Key Design Patterns

#### Offline-First Architecture
- **No internet dependency**: All processing runs locally (Ollama + ChromaDB)
- **Local AI models**: Embeddings and query models run on local machine
- **Persistent storage**: ChromaDB maintains data between sessions

#### Incremental Processing Strategy
- **Stable chunk IDs**: Enable incremental updates without full rebuild
- **Modification tracking**: Uses Bear's modification dates for change detection
- **Future-ready**: Architecture supports differential updates (currently full rebuild)

#### Error Resilience
- **Note-level tolerance**: Continues processing if individual notes fail
- **Graceful degradation**: Skips corrupted chunks and continues
- **Progress tracking**: Callback system for long-running operations

#### Batch Processing Optimization
- **Recommended batch size**: 32-128 chunks per ChromaDB operation
- **Memory management**: Uses temporary directories with automatic cleanup
- **Progress feedback**: Real-time progress reporting during processing

### Data Flow Details

#### 1. Note Extraction
```python
# From bear-notes-parser
notes = parse_bear_backup("backup.bear2bk", progress_callback=show_progress)
# Returns: [{"title", "markdown", "size", "modificationDate"}, ...]
```

#### 2. Chunking Process
```python
# Smart markdown chunking with context preservation
chunks = chunk_markdown(note["markdown"], target_tokens=300, overlap_tokens=50)
# Preserves: code blocks, heading structure, paragraph boundaries
```

#### 3. Embedding Generation
```python
# Local embeddings via Ollama
embeddings = embed_texts(chunks)  # Uses mxbai-embed-large:latest
# Returns: L2-normalized vectors for cosine similarity
```

#### 4. ChromaDB Storage
```python
# Batch upsert with metadata
collection.add(ids=chunk_ids, documents=chunks, metadatas=metadata, embeddings=vectors)
# Enables: semantic search, note provenance, context reconstruction
```

### Configuration Parameters

#### Chunking Configuration
- **Target tokens**: 300 (configurable, ~800-1600 characters)
- **Overlap tokens**: 50 (10-20% overlap ratio)
- **Code block handling**: Atomic preservation (no splitting)
- **Heading preservation**: Maintains semantic boundaries

#### ChromaDB Configuration
- **Distance metric**: Cosine similarity (with L2-normalized embeddings)
- **Index type**: HNSW for efficient approximate nearest neighbor search
- **Batch size**: 32-128 chunks per operation (optimal performance)
- **Persistence**: File-based storage in `../chromadb_data/`

### Integration Points

#### With Bear Notes Parser
- Uses the existing `parse_bear_backup()` function for data extraction
- Depends on the JSON output format with required fields
- Leverages the parser's error handling and progress reporting

#### With Local AI Stack
- **Ollama service**: Must be running (`ollama serve`) before processing
- **Model availability**: `mxbai-embed-large:latest` must be pulled locally
- **Query models**: Supports llama3.1:8b, gpt-oss:20b, gemma3:12b-it-qat

#### Future RAG Query System
- ChromaDB collection ready for similarity search queries
- Metadata structure supports provenance and context reconstruction
- Embedding format compatible with query-time retrieval