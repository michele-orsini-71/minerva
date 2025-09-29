# Tasks: Bear Notes Embeddings Creator

## Relevant Files

### Completed
- `json_loader.py` - JSON file loading and validation for Bear notes data
- `chunk_creator.py` - LangChain text splitters wrapper optimized for Bear notes (MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter)
- `embeddings_creator.py` - Main CLI tool for processing Bear notes JSON and creating semantic chunks
- `README.md` - Comprehensive documentation and usage guide
- **PRD updated** - Reflects LangChain implementation approach with Future Enhancements section
- **Header metadata storage** - Already implemented and tested, chunks include `header_metadata` field with hierarchical header information
- `embedding.py` - Embedding generation module using Ollama and mxbai-embed-large with L2 normalization, batch processing, service discovery, and retry logic
- `storage.py` - ChromaDB storage operations with metadata management, batch insertion, collection configuration with HNSW index and cosine similarity

### To Be Implemented
- `embedding_test.py` - Embedding generation and normalization tests
- `storage_test.py` - ChromaDB integration tests

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `embeddings_creator.py` and `embeddings_creator_test.py` in the same directory).
- Use `python -m pytest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by pytest discovery.

## Tasks

- [x] 1.0 Create core chunking module using LangChain text splitters integration
  - [x] 1.1 Create json_loader.py for Bear notes JSON loading and validation
  - [x] 1.2 Create chunk_creator.py wrapper around LangChain MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter with optimal configuration (1200 char target, 200 char overlap, structure preservation)
  - [x] 1.3 Implement stable ID generation (SHA1 for note_id, SHA256 for chunk_id) and chunk metadata
  - [x] 1.4 Add comprehensive error handling with graceful continuation on note failures
  - [x] 1.5 Create embeddings_creator.py CLI entry point with progress reporting and statistics
  - [x] 1.6 Test with real Bear notes data (1552 notes processed successfully)
  - [x] 1.7 Create comprehensive README.md with usage examples and architecture documentation
  - [x] 1.8 Validate performance (1000+ chunks/second processing speed)
  - [x] 1.9 Update PRD and Tasks List to reflect LangChain implementation approach
  - [x] 1.10 Implement and test header metadata storage in chunks (header_metadata field captures hierarchical header information)
- [x] 2.0 Implement embedding generation system using Ollama
  - [x] 2.1 Create embedding.py module with Ollama service integration for mxbai-embed-large:latest
  - [x] 2.2 Implement L2 normalization for cosine similarity compatibility in ChromaDB
  - [x] 2.3 Add batch processing capabilities for efficient embedding generation
  - [x] 2.4 Implement service discovery and clear error handling for unavailable Ollama service
  - [x] 2.5 Add embedding consistency validation and retry logic for failed requests
- [x] 3.0 Build ChromaDB storage layer with metadata management
  - [x] 3.1 Create storage.py module with ChromaDB persistent client setup
  - [x] 3.2 Implement collection configuration with HNSW index and cosine distance metric
  - [x] 3.3 Add stable chunk ID generation using SHA256(note_id|modificationDate|chunk_index)
  - [x] 3.4 Implement note_id generation using SHA1(title + creationDate) for uniqueness
  - [x] 3.5 Add comprehensive metadata storage (note_id, title, dates, size, chunk_index, header_metadata)
  - [x] 3.6 Implement collection reset/wipe functionality for clean rebuilds (delete existing collection before processing)
  - [x] 3.7 Implement batch insertion with configurable batch size (default 64 chunks)
  - [x] 3.8 Implement custom ChromaDB path support with default ../chromadb_data/bear_notes_embeddings
- [x] 4.0 Develop command-line interface with progress reporting (implemented in Task 1.0)
  - [x] 4.1 Create embeddings_creator.py main CLI script with argument parsing
  - [x] 4.2 Add required JSON file input argument and optional configuration flags
  - [x] 4.3 Implement --chunk-size, --verbose, --output CLI options (overlap and chromadb-path deferred to later tasks)
  - [x] 4.4 Add progress reporting showing current note processing (X/Y notes, percentage)
  - [x] 4.5 Implement real-time status updates with processing phases and statistics
  - [x] 4.6 Add comprehensive error handling with graceful continuation on individual note failures
  - [x] 4.7 Create summary reporting with success/failure counts, processing time, and performance metrics
  - [ ] 4.8 Add optional --json flag for structured output format (basic --output implemented)
  - [x] 4.9 Implement proper exit codes for failures following Unix conventions

These steps are not needed

- [ ] 5.0 Create comprehensive test suite for all pipeline phases
  - [ ] 5.1 Create chunking_test.py with critical comprehensive coverage for LangChain chunking algorithm (MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter integration)
  - [ ] 5.2 Add embedding_test.py for embedding generation, normalization, and Ollama integration tests
  - [ ] 5.3 Create storage_test.py for ChromaDB operations, metadata integrity, and persistence tests
  - [ ] 5.4 Add embeddings_creator_test.py for end-to-end CLI integration testing
  - [ ] 5.5 Implement JSON input processing tests with malformed data handling
  - [ ] 5.6 Add performance benchmarking tests for batch operations and large collections
  - [ ] 5.7 Create test data fixtures using real Bear notes for comprehensive validation
  - [ ] 5.8 Add edge case testing (empty notes, very large notes, Unicode content, special characters) with LangChain splitters
  - [ ] 5.9 Implement test database management with isolated test ChromaDB collections
- [ ] 6.0 Future Enhancement: Metadata-Enhanced RAG (post-MVP)
  - [ ] 6.1 Implement metadata filtering in ChromaDB queries (pre-filtering and post-filtering)
  - [ ] 6.2 Add LLM-based query classification to automatically extract metadata filters from user queries
  - [ ] 6.3 Implement context-aware generation enhancement using header metadata in prompts
  - [ ] 6.4 Create hybrid search and re-ranking combining vector similarity with metadata relevance
  - [ ] 6.5 Add dynamic filter generation for automatic query intent routing
- [ ] 7.0 Future Enhancement: Smart Incremental Processing (post-MVP)
  - [ ] 7.1 Implement differential note detection (compare modificationDate against existing chunks)
  - [ ] 7.2 Add selective chunk replacement logic (update only changed chunks within a note)
  - [ ] 7.3 Implement conflict resolution strategies (append/merge/replace options)
  - [ ] 7.4 Add incremental processing CLI mode (--incremental flag vs. current full rebuild)
  - [ ] 7.5 Optimize batch operations for mixed create/update scenarios
