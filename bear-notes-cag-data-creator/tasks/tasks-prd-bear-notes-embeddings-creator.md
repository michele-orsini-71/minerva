# Tasks: Bear Notes Embeddings Creator

## Relevant Files

- `embeddings_creator.py` - Main CLI tool for processing Bear notes JSON and creating vector embeddings
- `embeddings_creator_test.py` - Comprehensive test suite for all pipeline phases
- `chunking.py` - Core chunking module extracted and enhanced from test-chunking.py
- `chunking_test.py` - Dedicated chunking algorithm tests (critical comprehensive coverage)
- `embedding.py` - Embedding generation module using Ollama and mxbai-embed-large
- `embedding_test.py` - Embedding generation and normalization tests
- `storage.py` - ChromaDB storage operations with metadata management
- `storage_test.py` - ChromaDB integration tests
- `chunk_optimizer.py` - Development tool for determining optimal chunk size (one-time research)
- `chunk_optimizer_test.py` - Tests for chunk size optimization methodology

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `embeddings_creator.py` and `embeddings_creator_test.py` in the same directory).
- Use `python -m pytest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by pytest discovery.

## Tasks

- [ ] 1.0 Create core chunking module with comprehensive markdown handling
  - [ ] 1.1 Extract and enhance chunking logic from test-chunking.py into dedicated chunking.py module
  - [ ] 1.2 Implement character-based sizing using ~4 characters per token approximation (PRD requirement)
  - [ ] 1.3 Add configurable chunk size (default 1200 characters) and overlap percentage (default 15%)
  - [ ] 1.4 Enhance code block preservation to handle fenced blocks, indented code, and inline code spans atomically
  - [ ] 1.5 Implement table integrity preservation for markdown tables
  - [ ] 1.6 Add heading path context capture in metadata for chunk provenance
  - [ ] 1.7 Improve boundary detection for paragraphs, sentences, and semantic units
  - [ ] 1.8 Add support for complex nested structures (lists, blockquotes, mixed content)
- [ ] 2.0 Implement embedding generation system using Ollama
  - [ ] 2.1 Create embedding.py module with Ollama service integration for mxbai-embed-large:latest
  - [ ] 2.2 Implement L2 normalization for cosine similarity compatibility in ChromaDB
  - [ ] 2.3 Add batch processing capabilities for efficient embedding generation
  - [ ] 2.4 Implement service discovery and clear error handling for unavailable Ollama service
  - [ ] 2.5 Add embedding consistency validation and retry logic for failed requests
- [ ] 3.0 Build ChromaDB storage layer with metadata management
  - [ ] 3.1 Create storage.py module with ChromaDB persistent client setup
  - [ ] 3.2 Implement collection configuration with HNSW index and cosine distance metric
  - [ ] 3.3 Add stable chunk ID generation using SHA256(note_id|modificationDate|chunk_index)
  - [ ] 3.4 Implement note_id generation using SHA1(title + creationDate) for uniqueness
  - [ ] 3.5 Add comprehensive metadata storage (note_id, title, dates, size, chunk_index, heading_path)
  - [ ] 3.6 Implement batch insertion with configurable batch size (default 64 chunks)
  - [ ] 3.7 Add incremental processing support with conflict resolution (create/append/update logic)
  - [ ] 3.8 Implement custom ChromaDB path support with default ../chromadb_data/bear_notes_embeddings
- [ ] 4.0 Develop command-line interface with progress reporting
  - [ ] 4.1 Create embeddings_creator.py main CLI script with argument parsing
  - [ ] 4.2 Add required JSON file input argument and optional configuration flags
  - [ ] 4.3 Implement --chunk-size, --overlap-percent, --chromadb-path, --verbose CLI options
  - [ ] 4.4 Add progress reporting showing current note processing (X/Y notes, percentage)
  - [ ] 4.5 Implement real-time status updates with note titles and processing phases
  - [ ] 4.6 Add comprehensive error handling with graceful continuation on individual note failures
  - [ ] 4.7 Create summary reporting with success/failure counts, processing time, and performance metrics
  - [ ] 4.8 Add optional --json flag for structured output format
  - [ ] 4.9 Implement proper exit codes for partial failures following Unix conventions
- [ ] 5.0 Create comprehensive test suite for all pipeline phases
  - [ ] 5.1 Create chunking_test.py with critical comprehensive coverage for chunking algorithm
  - [ ] 5.2 Add embedding_test.py for embedding generation, normalization, and Ollama integration tests
  - [ ] 5.3 Create storage_test.py for ChromaDB operations, metadata integrity, and persistence tests
  - [ ] 5.4 Add embeddings_creator_test.py for end-to-end CLI integration testing
  - [ ] 5.5 Implement JSON input processing tests with malformed data handling
  - [ ] 5.6 Add performance benchmarking tests for batch operations and large collections
  - [ ] 5.7 Create test data fixtures using real Bear notes for comprehensive validation
  - [ ] 5.8 Add edge case testing (empty notes, very large notes, Unicode content, special characters)
  - [ ] 5.9 Implement test database management with isolated test ChromaDB collections
