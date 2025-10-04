# Bear Notes RAG Pipeline

A complete end-to-end pipeline for building a RAG (Retrieval-Augmented Generation) system from Bear notes. This tool processes Bear notes JSON data through the entire pipeline: semantic chunking → embedding generation → vector storage in ChromaDB.

## Overview

This is a **complete RAG pipeline** that takes Bear notes JSON (from the bear-notes-parser) and produces a fully populated ChromaDB vector database ready for AI-powered search and retrieval. The pipeline uses local AI models via Ollama, ensuring privacy and eliminating external API dependencies.

## Features

- **Complete RAG Pipeline**: Full end-to-end processing from JSON to searchable vector database
- **Local AI Processing**: Uses Ollama for embeddings (mxbai-embed-large) - no external API calls
- **Semantic Chunking**: LangChain text splitters with intelligent markdown structure preservation
- **ChromaDB Integration**: Persistent vector storage with metadata and cosine similarity search
- **High Performance**: Processes 1500+ notes efficiently with real-time progress reporting
- **Robust Error Handling**: Graceful handling of failures at every pipeline stage
- **Flexible Configuration**: Configurable chunk sizes, ChromaDB paths, and verbosity levels
- **Production Ready**: Modular architecture with comprehensive error handling and progress tracking

## Installation

### Prerequisites

- Python 3.6 or higher
- Virtual environment activated (recommended)
- **Ollama installed and running** (`ollama serve`)
- Required AI model: `ollama pull mxbai-embed-large:latest`

### Dependencies

```bash
# All dependencies should already be installed in the shared .venv
pip install langchain-text-splitters chromadb ollama numpy nltk tiktoken
```

## Usage

### Basic Usage

```bash
# Complete pipeline: JSON → Chunks → Embeddings → ChromaDB
python full_pipeline.py path/to/bear_notes.json
```

### Advanced Usage

```bash
# Custom chunk size (in characters)
python full_pipeline.py --chunk-size 800 notes.json

# Verbose output with detailed progress and statistics
python full_pipeline.py --verbose notes.json

# Custom ChromaDB storage location
python full_pipeline.py --chromadb-path ./my_vector_db notes.json

# Full example with all options
python full_pipeline.py --verbose --chunk-size 1200 --chromadb-path ../chromadb_data "../test-data/Bear Notes 2025-09-20 at 08.49.json"
```

### Command Line Options

- `json_file` - Path to Bear notes JSON file (required)
- `--chunk-size` - Target chunk size in characters (default: 1200)
- `--chromadb-path` - ChromaDB storage path (default: ../chromadb_data)
- `--verbose, -v` - Enable verbose output with detailed progress and statistics

## Architecture

### Components

1. **`json_loader.py`** - JSON file loading and validation

   - Handles file validation and error reporting
   - Validates Bear notes structure requirements
   - UTF-8 encoding support

2. **`chunk_creator.py`** - Markdown chunking using LangChain text splitters

   - Dual-stage approach: MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter
   - Optimized configuration for Bear notes with overlap support
   - Stable ID generation for chunks and notes
   - Progress reporting and error handling

3. **`embedding.py`** - Local embedding generation via Ollama

   - Uses mxbai-embed-large model for high-quality embeddings
   - Batch processing with error handling
   - L2 normalization for cosine similarity compatibility
   - Connection management and retry logic

4. **`storage.py`** - ChromaDB vector database operations

   - Persistent client initialization and collection management
   - Batch insertion with progress callbacks
   - Metadata schema design and cosine similarity configuration
   - Error handling and statistics reporting

5. **`full_pipeline.py`** - Complete pipeline orchestrator and CLI entry point
   - Command-line argument parsing and validation
   - End-to-end pipeline coordination
   - Real-time progress tracking and performance statistics
   - Comprehensive error handling for all pipeline stages

### Data Flow

```
Bear JSON → json_loader → chunk_creator → embedding → storage → ChromaDB
    ↓            ↓             ↓           ↓          ↓         ↓
  Load &      Parse &    LangChain     Ollama     ChromaDB   Ready for
 Validate     Chunk      Splitters   Embeddings   Storage   RAG Queries
```

**Complete Pipeline Stages:**

1. **Load** - Validate and parse Bear notes JSON
2. **Chunk** - Create semantic chunks with LangChain text splitters
3. **Embed** - Generate embeddings using local Ollama model (mxbai-embed-large)
4. **Store** - Insert into ChromaDB with metadata for retrieval

### Output

**Primary Output**: Fully populated ChromaDB vector database at the specified path (default: `../chromadb_data`)

**ChromaDB Schema**:

- **Collection**: "bear_notes" with cosine similarity space
- **Chunk IDs**: SHA256-based stable identifiers
- **Documents**: Chunk text content
- **Embeddings**: 1024-dimensional vectors from mxbai-embed-large
- **Metadata**: Rich metadata for each chunk

```json
{
  "note_id": "sha1_hash_of_note_title",
  "title": "Original Note Title",
  "modificationDate": "2025-01-01T10:00:00Z",
  "creationDate": "2025-01-01T09:00:00Z",
  "size": 1234,
  "chunk_index": 0
}
```

**Console Output**: Real-time progress, statistics, and performance metrics

```
🚀 Bear Notes Complete RAG Pipeline
📖 Loading Bear notes JSON...
✂️  Creating semantic chunks...
🧠 Generating embeddings with Ollama...
🗄️  Storing in ChromaDB...
🎉 Pipeline completed successfully!
💡 Database ready for RAG queries at: ../chromadb_data
```

## Configuration

### Pipeline Configuration

**Chunking Strategy (LangChain)**:

- **Target size**: 1200 characters (configurable via `--chunk-size`)
- **Overlap**: Auto-calculated (typically 200 characters)
- **Header processing**: MarkdownHeaderTextSplitter preserves heading structure
- **Recursive splitting**: RecursiveCharacterTextSplitter for large sections
- **Structure preservation**: Code blocks, tables, and paragraph boundaries maintained

**Embedding Configuration (Ollama)**:

- **Model**: mxbai-embed-large:latest (1024 dimensions)
- **Processing**: Individual text chunks with batch coordination
- **Normalization**: L2 normalization for cosine similarity
- **Connection**: Local Ollama service (http://localhost:11434)

**Storage Configuration (ChromaDB)**:

- **Distance metric**: Cosine similarity
- **Index**: HNSW for efficient similarity search
- **Persistence**: File-based storage (not in-memory)
- **Batch size**: Optimized for chunk insertion performance

### Performance

- **Overall pipeline**: ~50-100 chunks/second (depends on embedding generation)
- **Chunking alone**: ~1000+ notes/second
- **Embedding generation**: Rate-limited by Ollama model inference
- **ChromaDB storage**: ~500+ chunks/second insertion
- **Memory usage**: Efficient batch processing with progress tracking
- **Error tolerance**: Continues processing despite individual failures at any stage

## Examples

### Complete Bear backup to RAG database

```bash
# Step 1: Extract notes using bear-notes-parser
cd ../bear-notes-parser
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"

# Step 2: Ensure Ollama is running with required model
ollama serve  # In separate terminal
ollama pull mxbai-embed-large:latest

# Step 3: Run complete RAG pipeline
cd ../bear-notes-cag-data-creator
source ../.venv/bin/activate
python full_pipeline.py --verbose "../bear-notes-parser/Bear Notes 2025-09-20 at 08.49.json"
```

### Sample Output

```
🚀 Bear Notes Complete RAG Pipeline
============================================================
📁 Input file: ../test-data/Bear Notes 2025-09-20 at 08.49.json
📏 Target chunk size: 1200 characters
🗄️  ChromaDB path: ../chromadb_data

📖 Loading Bear notes JSON...
   ✅ Loaded 1552 notes
   📊 Total content: 2,847,392 characters
   📊 Average note size: 1,835 characters

✂️  Creating semantic chunks...
   ✅ Created 4247 chunks from 1552 notes

🧠 Generating embeddings with Ollama...
   ✅ Generated 4247 embeddings

🗄️  Storing in ChromaDB...
   📥 Storing: 4247/4247 chunks (100.0%)
   ✅ Stored 4247 chunks in ChromaDB

🎉 Pipeline completed successfully!
============================================================
📊 Notes processed: 1552
📦 Chunks created: 4247
🧠 Embeddings generated: 4247
🗄️  Chunks stored in ChromaDB: 4247
⏱️  Total processing time: 127.3 seconds
🚀 Performance: 33.4 chunks/second

💡 Database ready for RAG queries at: ../chromadb_data
```

## Error Handling

The pipeline provides comprehensive error handling at every stage:

**File and Data Validation**:

- **File not found**: Clear error message with file path
- **Invalid JSON**: Detailed JSON parsing error with line information
- **Missing fields**: Validation of required Bear notes fields
- **Encoding issues**: UTF-8 encoding error handling

**AI and Storage Errors**:

- **Ollama connection**: Checks for running service with helpful error messages
- **Model availability**: Validates required model (mxbai-embed-large) is pulled
- **Embedding failures**: Individual chunk failures don't stop pipeline
- **ChromaDB issues**: Database initialization and storage error handling

**Pipeline Resilience**:

- **Graceful degradation**: Continues processing despite individual failures
- **Progress preservation**: Partial results are preserved on interruption
- **Clear diagnostics**: Detailed error reporting with suggested fixes
- **Keyboard interrupt**: Clean shutdown with partial results summary

## Integration

**Upstream Dependencies**:

- **Bear Notes Parser** - provides the JSON input (`bear-notes-parser/cli.py`)
- **Ollama Service** - local AI model server for embeddings
- **Required Models** - mxbai-embed-large:latest for embedding generation

**Output Integration**:

- **ChromaDB Database** - ready for similarity search and retrieval
- **RAG Query Systems** - compatible with chromadb client queries
- **AI Chat Applications** - can use the vector database for context retrieval
- **Search Interfaces** - enables semantic search across Bear notes content

**Related Tools**:

- **chroma-peek** - visual exploration of the generated ChromaDB database
- **Future query tools** - planned RAG query interfaces for the vector database

## Development

### Testing

```bash
# Test complete pipeline with sample data
python full_pipeline.py --verbose ../test-data/sample.json

# Test individual components
python json_loader.py ../test-data/sample.json
python chunk_creator.py  # Runs built-in test
python embedding.py  # Test Ollama connection
python storage.py  # Test ChromaDB operations
```

### Module Usage

```python
# Complete pipeline programmatically
from json_loader import load_json_notes
from chunk_creator import create_chunks_for_notes
from embedding import generate_embeddings_batch
from storage import initialize_chromadb_client, get_or_create_collection, insert_chunks_batch

# Load and process notes
notes = load_json_notes("notes.json")
enriched_notes = create_chunks_for_notes(notes, target_chars=1200)

# Generate embeddings and store
all_chunks = [chunk for note in enriched_notes for chunk in note['chunks']]
embeddings = generate_embeddings_batch([chunk['content'] for chunk in all_chunks])

# Store in ChromaDB
client = initialize_chromadb_client("./my_db")
collection = get_or_create_collection(client)
insert_chunks_batch(collection, chunks_with_embeddings)
```

## Troubleshooting

### Common Issues

**"Connection to Ollama failed"**

- Ensure Ollama is running: `ollama serve`
- Check model is available: `ollama list | grep mxbai-embed-large`
- Pull model if missing: `ollama pull mxbai-embed-large:latest`

**"Model mxbai-embed-large:latest not found"**

- Pull the required model: `ollama pull mxbai-embed-large:latest`
- Verify installation: `ollama list`

**"ChromaDB database issues"**

- Check write permissions for ChromaDB path
- Ensure sufficient disk space for vector storage
- Default path: `../chromadb_data` (relative to script location)

**"JSON file must contain an array of notes"**

- Ensure input file is valid Bear notes JSON from bear-notes-parser
- Check file exists and is properly formatted

**Slow embedding generation**

- Normal for large note collections (embedding generation is rate-limited by model inference)
- Use `--verbose` flag to monitor progress
- Consider running on faster hardware for large datasets

**Memory issues with large datasets**

- Pipeline processes in batches to manage memory
- For very large datasets (10k+ notes), monitor system resources

### Performance Tips

- Use SSD storage for faster file I/O
- Ensure sufficient RAM for large note collections
- Consider processing in batches for very large datasets (10k+ notes)

## License

Part of the Bear Notes RAG system. See parent repository for license information.
