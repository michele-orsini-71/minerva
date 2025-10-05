# Markdown Notes RAG Pipeline

A complete end-to-end pipeline for building a multi-collection RAG (Retrieval-Augmented Generation) system from markdown notes. This tool processes markdown notes JSON data through the entire pipeline: semantic chunking → embedding generation → vector storage in ChromaDB with intelligent collection management.

## Overview

This is a **complete multi-collection RAG pipeline** that takes markdown notes JSON and produces fully populated ChromaDB vector database collections ready for AI-powered search and retrieval. The pipeline uses local AI models via Ollama, ensuring privacy and eliminating external API dependencies. Collections are intelligently named and described for accurate routing in multi-collection RAG systems.

## Features

- **Multi-Collection Architecture**: Named collections with rich descriptions for intelligent routing
- **Config-Based Workflow**: JSON configuration files for reproducible, version-controlled pipelines
- **Complete RAG Pipeline**: Full end-to-end processing from JSON to searchable vector database
- **Local AI Processing**: Uses Ollama for embeddings (mxbai-embed-large) - no external API calls
- **AI-Powered Validation**: Optional AI validation of collection descriptions for quality assurance
- **Semantic Chunking**: LangChain text splitters with intelligent markdown structure preservation
- **ChromaDB Integration**: Persistent vector storage with metadata and cosine similarity search
- **Dry-Run Mode**: Fast validation mode to preview operations without modifying data
- **High Performance**: Processes 1500+ notes efficiently with real-time progress reporting
- **Robust Error Handling**: Graceful handling of failures at every pipeline stage
- **Production Ready**: Modular architecture with comprehensive error handling and progress tracking

## Installation

### Prerequisites

- Python 3.13 or higher
- Virtual environment activated (recommended)
- **Ollama installed and running** (`ollama serve`)
- Required AI models:
  - Embeddings: `ollama pull mxbai-embed-large:latest`
  - Validation (optional): `ollama pull llama3.1:8b`

### Dependencies

```bash
# All dependencies should already be installed in the shared .venv
pip install langchain-text-splitters chromadb ollama numpy nltk tiktoken jsonschema
```

## Usage

### Quick Start

1. **Create a collection configuration** (JSON file):

```json
{
  "collection_name": "my_notes",
  "description": "Personal notes about software development, architecture patterns, and technical research. Use this when searching for coding best practices and design decisions.",
  "chromadb_path": "/path/to/chromadb_data",
  "json_file": "/path/to/notes.json",
  "chunk_size": 1200,
  "forceRecreate": false,
  "skipAiValidation": false
}
```

2. **Run the pipeline**:

```bash
# Basic usage with config file
python full_pipeline.py --config collections/my_collection.json

# With verbose output
python full_pipeline.py --config collections/my_collection.json --verbose

# Dry-run mode (validation only, no data changes)
python full_pipeline.py --config collections/my_collection.json --dry-run
```

### Configuration File Format

The JSON configuration file supports the following fields:

**Required Fields:**

- `collection_name` (string): Unique collection identifier (1-63 chars, alphanumeric with `-` or `_`)
- `description` (string): Detailed description of when to use this collection (10-1000 chars)
- `chromadb_path` (string): Path to ChromaDB storage location
- `json_file` (string): Path to markdown notes JSON file

**Optional Fields:**

- `chunk_size` (number): Target chunk size in characters (default: 1200, range: 300-20000)
- `forceRecreate` (boolean): Delete and recreate collection if it exists (default: false)
- `skipAiValidation` (boolean): Skip AI validation of collection description (default: false)

### Command Line Options

- `--config` (required): Path to collection configuration JSON file
- `--verbose, -v`: Enable verbose output with detailed progress and statistics
- `--dry-run`: Validation-only mode - checks config and estimates without modifying data

## Architecture

### Components

1. **`config_loader.py`** - Configuration file loading and validation
   - JSON schema validation with helpful error messages
   - Support for both required and optional fields
   - Type checking and range validation
   - Immutable configuration objects

2. **`config_validator.py`** - Multi-stage configuration validation
   - Collection name format validation
   - AI-powered description quality validation (optional)
   - ChromaDB path and JSON file validation
   - Actionable error messages with fix suggestions

3. **`json_loader.py`** - JSON file loading and validation
   - Handles file validation and error reporting
   - Validates markdown notes structure requirements
   - UTF-8 encoding support

4. **`chunk_creator.py`** - Markdown chunking using LangChain text splitters
   - Dual-stage approach: MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter
   - Optimized configuration for markdown notes with overlap support
   - Stable ID generation for chunks and notes
   - Immutable API (returns new data)

5. **`embedding.py`** - Local embedding generation via Ollama
   - Uses mxbai-embed-large model for high-quality embeddings
   - Batch processing with error handling
   - L2 normalization for cosine similarity compatibility
   - Immutable API (returns enriched chunks)

6. **`storage.py`** - ChromaDB vector database operations
   - Multi-collection support with metadata
   - Explicit create/recreate operations
   - Batch insertion with progress callbacks
   - Metadata schema design and cosine similarity configuration
   - Immutable API with comprehensive error handling

7. **`validation.py`** - Collection metadata validation
   - Collection name pattern validation
   - AI-powered description quality scoring
   - Ollama-based semantic validation
   - Helpful error messages with improvement suggestions

8. **`full_pipeline.py`** - Complete pipeline orchestrator and CLI entry point
   - Config-based argument parsing
   - Dry-run mode for validation
   - End-to-end pipeline coordination
   - Real-time progress tracking and performance statistics
   - Comprehensive error handling for all pipeline stages

### Data Flow

```
Config JSON → config_loader → config_validator → Notes JSON → chunk_creator
    ↓              ↓                  ↓                ↓            ↓
 Collection    Validate         AI Quality       Load Notes    LangChain
   Config       Schema          Validation         & Parse     Chunking
                                                                    ↓
                                                              embedding
                                                                    ↓
                                                               Ollama AI
                                                                    ↓
                                                               storage
                                                                    ↓
                                                            ChromaDB Collection
```

**Complete Pipeline Stages:**

1. **Config Load** - Load and validate collection configuration JSON
2. **Config Validate** - Validate collection name and description (with optional AI quality check)
3. **Notes Load** - Load and validate markdown notes JSON
4. **Chunk** - Create semantic chunks with LangChain text splitters (immutable)
5. **Embed** - Generate embeddings using local Ollama model (mxbai-embed-large, immutable)
6. **Store** - Create/recreate collection and insert chunks with metadata (immutable)

### Output

**Primary Output**: Named ChromaDB collection in the specified database path

**ChromaDB Schema**:

- **Collection**: User-defined name with rich description for AI routing
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

```text
Markdown Notes Multi-Collection RAG Pipeline
============================================================
Loading collection configuration...
   Configuration loaded from: collections/my_notes.json
   Collection: my_notes
   Description: Personal notes about software development...

Loading notes JSON...
   Loaded 1552 notes

Creating semantic chunks...
   Created 4247 chunks from 1552 notes

Generating embeddings with Ollama...
   Generated 4247 embeddings

Storing in ChromaDB collection 'my_notes'...
   Stored 4247 chunks in collection 'my_notes'

Pipeline completed successfully!
============================================================
Collection: my_notes
Notes processed: 1552
Chunks created: 4247
Embeddings generated: 4247
Chunks stored: 4247
Processing time: 127.3 seconds

Collection 'my_notes' ready for RAG queries
   Database location: /path/to/chromadb_data
```

## Configuration

### Pipeline Configuration

**Collection Configuration (JSON)**:

- **Collection name**: Alphanumeric with `-` or `_`, 1-63 chars (validated)
- **Description**: Detailed description for AI routing, 10-1000 chars (optionally AI-validated)
- **Force recreate**: Control whether to delete/recreate existing collections
- **Skip AI validation**: Bypass AI quality checks for descriptions (use with caution)

**Chunking Strategy (LangChain)**:

- **Target size**: Configurable in config file (default: 1200 characters, range: 300-20000)
- **Overlap**: Auto-calculated (typically 200 characters)
- **Header processing**: MarkdownHeaderTextSplitter preserves heading structure
- **Recursive splitting**: RecursiveCharacterTextSplitter for large sections
- **Structure preservation**: Code blocks, tables, and paragraph boundaries maintained
- **Immutable**: Returns new chunk objects without modifying input

**Embedding Configuration (Ollama)**:

- **Model**: mxbai-embed-large:latest (1024 dimensions)
- **Processing**: Individual text chunks with batch coordination
- **Normalization**: L2 normalization for cosine similarity
- **Connection**: Local Ollama service (http://localhost:11434)
- **Immutable**: Returns enriched chunks without modifying input

**Storage Configuration (ChromaDB)**:

- **Multi-collection**: Supports multiple named collections in single database
- **Distance metric**: Cosine similarity
- **Index**: HNSW for efficient similarity search
- **Persistence**: File-based storage (not in-memory)
- **Collection metadata**: Name and description stored with collection
- **Immutable**: Explicit create/recreate operations, no mutations

### Performance

- **Overall pipeline**: ~50-100 chunks/second (depends on embedding generation)
- **Chunking alone**: ~1000+ notes/second
- **Embedding generation**: Rate-limited by Ollama model inference
- **ChromaDB storage**: ~500+ chunks/second insertion
- **Memory usage**: Efficient batch processing with progress tracking
- **Error tolerance**: Continues processing despite individual failures at any stage

## Examples

### Complete Workflow: Notes to RAG Database

```bash
# Step 1: Extract notes (e.g., from Bear Notes backup)
cd ../bear-notes-parser
python cli.py "Bear Notes 2025-10-04 at 15.00.bear2bk"

# Step 2: Ensure Ollama is running with required models
ollama serve  # In separate terminal
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b  # Optional: for AI validation

# Step 3: Create collection configuration
cd ../markdown-notes-cag-data-creator
cat > collections/my_bear_notes.json <<EOF
{
  "collection_name": "bear_notes_personal",
  "description": "Personal notes from Bear Notes app covering software development, research ideas, and technical documentation. Use when searching for programming concepts, architecture patterns, or past project notes.",
  "chromadb_path": "/Users/yourname/chromadb_data",
  "json_file": "/path/to/Bear Notes 2025-10-04 at 15.00.json",
  "chunk_size": 1200,
  "forceRecreate": false,
  "skipAiValidation": false
}
EOF

# Step 4: Run pipeline (dry-run first to validate)
source ../.venv/bin/activate
python full_pipeline.py --config collections/my_bear_notes.json --dry-run

# Step 5: Run actual pipeline with verbose output
python full_pipeline.py --config collections/my_bear_notes.json --verbose
```

### Multiple Collections Example

```bash
# Create separate collections for different note sources
python full_pipeline.py --config collections/bear_notes_config.json --verbose
python full_pipeline.py --config collections/wikipedia_history_config.json --verbose
python full_pipeline.py --config collections/project_docs_config.json --verbose

# All collections coexist in the same ChromaDB database
# AI can route queries to the right collection based on descriptions
```

### Sample Output

```text
Markdown Notes Multi-Collection RAG Pipeline
============================================================

Loading collection configuration...
   Configuration loaded from: collections/bear_notes_config.json
   Json file: /Users/michele/test-data/Bear Notes 2025-10-04 at 15.00.json
   ChromaDB path: /Users/michele/chromadb_data
   Chunk size: 1200
   Collection name: bear_notes_personal
   Description: Personal notes from Bear Notes app covering software development...
   Force recreate: False
   Skip AI validation: False

Validating collection metadata...
   Collection name validated: bear_notes_personal
   Description validated successfully
   AI Quality Score: 8/10

Loading notes JSON...
   Loaded 1552 notes
   Total content: 2,847,392 characters
   Average note size: 1,835 characters

Creating semantic chunks...
   Created 4247 chunks from 1552 notes

Generating embeddings with Ollama...
   Generated 4247 embeddings

Storing in ChromaDB collection 'bear_notes_personal'...
   Storing: 4247/4247 chunks (100.0%)
   Stored 4247 chunks in collection 'bear_notes_personal'

Pipeline completed successfully!
============================================================
Collection: bear_notes_personal
Description: Personal notes from Bear Notes app covering...
Notes processed: 1552
Chunks created: 4247
Embeddings generated: 4247
Chunks stored: 4247
Processing time: 127.3 seconds
Performance: 33.4 chunks/second

Collection 'bear_notes_personal' ready for RAG queries
   Database location: /Users/michele/chromadb_data
```

## Error Handling

The pipeline provides comprehensive error handling at every stage:

**Configuration Validation**:

- **File not found**: Clear error with expected file location and schema guide
- **Invalid JSON**: Detailed parsing error with line/column information
- **Schema validation**: Field-level validation with actionable fix suggestions
- **Collection name**: Pattern validation with correct format examples
- **Description quality**: AI-powered quality scoring (when enabled)

**File and Data Validation**:

- **Notes file not found**: Clear error with file path from config
- **Invalid notes JSON**: Detailed JSON parsing error with line information
- **Missing fields**: Validation of required markdown notes fields
- **Encoding issues**: UTF-8 encoding error handling

**AI and Storage Errors**:

- **Ollama connection**: Checks for running service with helpful error messages
- **Model availability**: Validates required models (embedding + validation) are pulled
- **Embedding failures**: Individual chunk failures don't stop pipeline
- **Collection conflicts**: Validates forceRecreate flag when collection exists
- **ChromaDB issues**: Database initialization and storage error handling

**Pipeline Resilience**:

- **Graceful degradation**: Continues processing despite individual failures
- **Progress preservation**: Partial results are preserved on interruption
- **Clear diagnostics**: Detailed error reporting with suggested fixes
- **Keyboard interrupt**: Clean shutdown with partial results summary
- **Dry-run mode**: Validate everything before making changes

## Integration

**Upstream Dependencies**:

- **Note extractors** - Any tool that produces markdown notes JSON (e.g., `bear-notes-parser`, `extract-zim-articles`)
- **Ollama Service** - Local AI model server for embeddings and validation
- **Required Models** - `mxbai-embed-large:latest` for embeddings, `llama3.1:8b` for validation

**Output Integration**:

- **ChromaDB Database** - Multi-collection database ready for intelligent routing
- **RAG Query Systems** - Collections with rich descriptions enable accurate routing
- **AI Chat Applications** - Can use collection descriptions to select appropriate context
- **Search Interfaces** - Enables semantic search across multiple note collections

**Related Tools**:

- **chroma-peek** - Visual exploration of ChromaDB collections and metadata
- **Future query tools** - Planned multi-collection RAG query interfaces with AI routing

## Development

### Testing

```bash
# Create test configuration
cat > collections/test_config.json <<EOF
{
  "collection_name": "test_collection",
  "description": "Test collection for development and validation purposes. Contains sample notes for testing the RAG pipeline.",
  "chromadb_path": "./test_chromadb",
  "json_file": "../test-data/sample.json",
  "skipAiValidation": true
}
EOF

# Test with dry-run first
python full_pipeline.py --config collections/test_config.json --dry-run

# Run actual test pipeline
python full_pipeline.py --config collections/test_config.json --verbose

# Test individual components (if needed)
python json_loader.py ../test-data/sample.json
python chunk_creator.py  # Runs built-in test
python embedding.py  # Test Ollama connection
python storage.py  # Test ChromaDB operations
```

### Programmatic Usage

```python
# Complete pipeline programmatically (using immutable APIs)
from config_loader import load_collection_config
from json_loader import load_json_notes
from chunk_creator import create_chunks_from_notes
from embedding import generate_embeddings
from storage import initialize_chromadb_client, create_collection, insert_chunks

# Load configuration
config = load_collection_config("collections/my_config.json")

# Load and process notes (immutable)
notes = load_json_notes(config.json_file)
chunks = create_chunks_from_notes(notes, target_chars=config.chunk_size)

# Generate embeddings (immutable - returns enriched chunks)
chunks_with_embeddings = generate_embeddings(chunks)

# Store in ChromaDB collection
client = initialize_chromadb_client(config.chromadb_path)
collection = create_collection(
    client,
    collection_name=config.collection_name,
    description=config.description
)
stats = insert_chunks(collection, chunks_with_embeddings)
print(f"Stored {stats['successful']} chunks in collection '{config.collection_name}'")
```

## Troubleshooting

### Common Issues

**"Configuration file not found"**

- Ensure config file path is correct
- Use `--config` with proper path to JSON file
- Check example configs in `collections/` directory

**"Collection already exists" (forceRecreate=false)**

- Either delete the collection manually or set `"forceRecreate": true` in config
- Use `--dry-run` to preview the operation first
- Be careful: `forceRecreate: true` deletes existing data!

**"Connection to Ollama failed"**

- Ensure Ollama is running: `ollama serve`
- Check embedding model: `ollama list | grep mxbai-embed-large`
- Check validation model (if used): `ollama list | grep llama3.1`
- Pull models if missing: `ollama pull mxbai-embed-large:latest`

**"Description validation failed" (AI validation)**

- Improve description to be more specific and detailed
- Avoid vague terms like "various topics" or "miscellaneous"
- Explain when to use this collection vs others
- Or set `"skipAiValidation": true` (use with caution)

**"Invalid collection name"**

- Must be 1-63 characters
- Start with alphanumeric, can contain `-` or `_`
- Examples: `bear_notes`, `project-docs`, `team123`

**"ChromaDB database issues"**

- Check write permissions for ChromaDB path in config
- Ensure sufficient disk space for vector storage
- Use absolute paths in config for clarity

**"JSON file must contain an array of notes"**

- Ensure input file is valid markdown notes JSON
- Check `json_file` path in config is correct
- Verify JSON format matches expected structure

**Slow embedding generation**

- Normal for large note collections (rate-limited by model inference)
- Use `--verbose` flag to monitor progress
- Use `--dry-run` to estimate time before running
- Consider faster hardware for large datasets

**Memory issues with large datasets**

- Pipeline uses immutable APIs but processes in batches
- For very large datasets (10k+ notes), monitor system resources
- Consider splitting into multiple collections

### Best Practices

**Collection Design**:

- Create focused collections with clear boundaries
- Write detailed descriptions for accurate AI routing
- Use consistent naming conventions
- Test with `--dry-run` before running

**Configuration Management**:

- Store configs in version control (`collections/` directory)
- Use absolute paths for production
- Document collection purposes in descriptions
- Keep `forceRecreate: false` by default

**Performance**:

- Use SSD storage for ChromaDB
- Ensure sufficient RAM for large collections
- Process in batches for very large datasets (10k+ notes)
- Monitor with `--verbose` for bottleneck identification

## License

Part of the Markdown Notes Search system. See parent repository for license information.
