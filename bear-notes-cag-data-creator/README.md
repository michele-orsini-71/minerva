# Bear Notes CAG Data Creator

A high-performance data pipeline for creating semantic chunks from Bear notes JSON data, preparing them for embedding generation and vector storage in a RAG (Retrieval-Augmented Generation) system.

## Overview

This tool processes Bear notes exported from the Bear Notes parser and creates semantic chunks using the `markdown-chunker` library. It's designed to be the first stage in a complete Bear Notes RAG pipeline.

## Features

- **Semantic Chunking**: Uses `markdown-chunker` library for intelligent markdown structure preservation
- **Optimized for Bear Notes**: Configured specifically for Bear's markdown format and content patterns
- **High Performance**: Processes 1500+ notes efficiently with progress reporting
- **Robust Error Handling**: Graceful handling of malformed notes with detailed error reporting
- **Flexible Configuration**: Configurable chunk sizes and processing options
- **Clean Architecture**: Modular design with single-responsibility components

## Installation

### Prerequisites

- Python 3.6 or higher
- Virtual environment activated (recommended)

### Dependencies

```bash
pip install markdown-chunker
```

## Usage

### Basic Usage

```bash
python embeddings_creator.py path/to/bear_notes.json
```

### Advanced Usage

```bash
# Custom chunk size
python embeddings_creator.py --chunk-size 800 notes.json

# Verbose output with detailed statistics
python embeddings_creator.py --verbose notes.json

# Save enriched output for further processing
python embeddings_creator.py --output enriched_notes.json notes.json
```

### Command Line Options

- `json_file` - Path to Bear notes JSON file (required)
- `--chunk-size` - Target chunk size in characters (default: 1200)
- `--verbose, -v` - Enable verbose output with detailed progress
- `--output, -o` - Output file path for enriched notes with chunks

## Architecture

### Components

1. **`json_loader.py`** - JSON file loading and validation
   - Handles file validation and error reporting
   - Validates Bear notes structure requirements
   - UTF-8 encoding support

2. **`chunk_creator.py`** - Markdown chunking using markdown-chunker library
   - Optimized configuration for Bear notes
   - Stable ID generation for chunks and notes
   - Progress reporting and error handling

3. **`embeddings_creator.py`** - CLI orchestrator and entry point
   - Command-line argument parsing
   - Pipeline coordination
   - Statistics and performance reporting

### Data Flow

```
Bear JSON → json_loader → chunk_creator → enriched_notes
    ↓            ↓             ↓              ↓
  Load &      Parse &      Create         Statistics
 Validate     Chunk      Metadata        & Output
```

### Output Format

Each note is enriched with chunking metadata:

```json
{
  "title": "Note Title",
  "markdown": "Original markdown content...",
  "size": 1234,
  "modificationDate": "2025-01-01T10:00:00Z",
  "creationDate": "2025-01-01T09:00:00Z",
  "note_id": "sha1_hash_of_title_and_date",
  "chunks": [
    {
      "id": "sha256_hash_of_note_id_date_index",
      "content": "Chunk content...",
      "chunk_index": 0,
      "note_id": "parent_note_id",
      "title": "Note Title",
      "modificationDate": "2025-01-01T10:00:00Z",
      "size": 456
    }
  ]
}
```

## Configuration

### Chunking Strategy

The tool uses optimized settings for Bear notes:

- **Target size**: 1200 characters (configurable)
- **Maximum size**: 1.5x target (allows structure preservation)
- **Minimum size**: 0.25x target
- **Structure preservation**: Enabled for headings, code blocks, tables
- **Metadata overhead**: Disabled for clean content

### Performance

- **Processing speed**: ~1000+ notes/second (typical Bear notes)
- **Memory usage**: Efficient streaming processing
- **Error tolerance**: Continues processing despite individual note failures

## Examples

### Processing a Bear backup

```bash
# Extract notes first using bear-notes-parser
cd ../bear-notes-parser
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"

# Process the generated JSON
cd ../bear-notes-cag-data-creator
python embeddings_creator.py "../bear-notes-parser/Bear Notes 2025-09-20 at 08.49.json"
```

### Sample Output

```
🚀 Bear Notes Embeddings Creator
==================================================
📖 Loading Bear notes JSON...
✅ Loaded 1552 notes from Bear Notes 2025-09-20 at 08.49.json
✂️  Creating semantic chunks...
🔄 Processing 1552 notes with markdown-chunker...
  Progress: 1552/1552 notes (100.0%) - 4247 chunks created
✅ Chunking complete:
  Successfully processed: 1552 notes
  Failed: 0 notes
  Total chunks created: 4247
  Average chunks per note: 2.7

📊 Processing Summary:
==================================================
✅ Successfully processed: 1552 notes
📦 Total chunks created: 4247
📏 Average chunk size: 891 characters
⏱️  Processing time: 3.2 seconds
🚀 Chunks per second: 1327.2

🎉 Chunking completed successfully!
   Ready for embedding generation and vector storage.
```

## Error Handling

The tool provides comprehensive error handling:

- **File not found**: Clear error message with file path
- **Invalid JSON**: Detailed JSON parsing error with line information
- **Missing fields**: Validation of required Bear notes fields
- **Encoding issues**: UTF-8 encoding error handling
- **Individual note failures**: Continues processing with failure reporting

## Integration

This tool is designed to integrate with:

- **Bear Notes Parser** (upstream) - provides the JSON input
- **Embedding Generation** (downstream) - processes the chunked output
- **ChromaDB Storage** (downstream) - stores the embedded chunks
- **RAG Query System** (downstream) - queries the vector database

## Development

### Testing

```bash
# Test with sample data
python embeddings_creator.py --verbose ../test-data/sample.json

# Test individual components
python json_loader.py ../test-data/sample.json
python chunk_creator.py  # Runs built-in test
```

### Module Usage

```python
from json_loader import load_bear_notes_json
from chunk_creator import create_chunks_for_notes

# Load notes
notes = load_bear_notes_json("notes.json")

# Create chunks
enriched_notes = create_chunks_for_notes(notes, target_chars=1200)
```

## Troubleshooting

### Common Issues

**"markdown-chunker library not installed"**
- Run: `pip install markdown-chunker`

**"JSON file must contain an array of notes"**
- Ensure input file is valid Bear notes JSON from bear-notes-parser

**Content loss warnings**
- These are normal library warnings about structure optimization
- Actual content is preserved, warnings refer to metadata calculations

**Large processing times**
- Normal for large note collections (1000+ notes)
- Use `--verbose` flag to monitor progress

### Performance Tips

- Use SSD storage for faster file I/O
- Ensure sufficient RAM for large note collections
- Consider processing in batches for very large datasets (10k+ notes)

## License

Part of the Bear Notes RAG system. See parent repository for license information.