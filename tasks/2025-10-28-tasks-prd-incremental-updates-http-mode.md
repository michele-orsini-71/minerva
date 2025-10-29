# Task List: Minerva v2.0 - Incremental Updates & HTTP Server Mode

Generated from: `tasks/prd-incremental-updates-http-mode.md`
Date: 2025-10-28

---

## Relevant Files

### New Files (to be created)
- `minerva/indexing/updater.py` - Core incremental update logic (change detection, deletion, update, add operations)
- `minerva/commands/serve_http.py` - HTTP server mode command implementation
- `tests/test_content_hash.py` - Unit tests for content hash computation
- `tests/test_updater.py` - Unit tests for incremental update logic
- `tests/test_config_change_detection.py` - Unit tests for configuration change detection
- `tests/test_serve_http.py` - Unit tests for HTTP server mode
- `tests/test_incremental_integration.py` - Integration tests for full incremental update workflow
- `docs/UPGRADE_v2.0.md` - Migration guide for v1.0 users

### Modified Files
- `minerva/common/models.py` - Added content_hash field to Chunk model (Optional[str], only for chunkIndex==0) and convenience property to ChunkWithEmbedding
- `minerva/indexing/chunking.py` - Added compute_content_hash() function and integrated content hash computation in build_chunks_from_note()
- `minerva/indexing/storage.py` - Updated build_collection_metadata() to v2.0 (version="2.0", note_hash_algorithm="sha256", last_updated timestamp); Updated prepare_chunk_batch_data() to store content_hash metadata
- `minerva/commands/index.py` - Integrate incremental update logic, modify collection checking (TODO)
- `minerva/cli.py` - Add serve-http subparser, update version to 2.0.0 (TODO)
- `minerva/server/mcp_server.py` - Refactor for stdio/HTTP mode support (TODO)
- `README.md` - Document v2.0 features and usage examples (TODO)
- `CLAUDE.md` - Update with new commands and workflows (TODO)

### Notes
- Unit tests should be placed alongside the modules they test in the `tests/` directory
- Use `pytest` to run tests: `pytest tests/` or `pytest tests/test_specific.py`
- Follow existing code patterns in the codebase for consistency

---

## Tasks

- [x] 1.0 Implement Content Hash Tracking and Storage Schema Updates
  - [x] 1.1 Add compute_content_hash() function in chunking.py (SHA256 of title + markdown)
  - [x] 1.2 Update Note processing in chunking.py to compute and attach content_hash to first chunk
  - [x] 1.3 Add content_hash field to Chunk model in common/models.py (Optional[str], only set for chunkIndex == 0)
  - [x] 1.4 Update storage.py to store content_hash metadata field (only when chunkIndex == 0)
  - [x] 1.5 Update build_collection_metadata() in storage.py to include v2.0 fields: version="2.0", note_hash_algorithm="sha256", last_updated=ISO8601 timestamp
  - [x] 1.6 Verify content_hash storage by testing with peek command

- [x] 2.0 Implement Incremental Update Detection and Processing Logic
  - [x] 2.1 Create new minerva/indexing/updater.py module with UpdateStats class
  - [x] 2.2 Implement fetch_existing_state() function to bulk fetch all chunks and build in-memory maps (noteId_to_chunks, noteId_to_hash)
  - [x] 2.3 Implement detect_changes() function to compare new vs existing notes and categorize as added/updated/deleted/unchanged
  - [x] 2.4 Implement delete_note_chunks() function to remove chunks for deleted notes from ChromaDB
  - [x] 2.5 Implement update_note_chunks() function to delete old chunks and add new chunks for modified notes
  - [x] 2.6 Implement add_note_chunks() function to process and add chunks for new notes
  - [x] 2.7 Implement run_incremental_update() orchestrator function that calls fetch→detect→delete→update→add in sequence
  - [x] 2.8 Add progress reporting and summary output (added/updated/deleted/skipped counts, time comparison)
  - [x] 2.9 Integrate incremental update into commands/index.py as alternative to full reindex
  - [x] 2.10 Handle metadata-only updates (description changes without note changes)

- [x] 3.0 Implement Configuration Change Detection and Version Migration
  - [x] 3.1 Implement is_v1_collection() function in updater.py to check for missing 'version' field
  - [x] 3.2 Implement detect_config_changes() function to compare current config vs stored metadata (embedding_model, embedding_provider, chunk_size)
  - [x] 3.3 Add error message template for v1.0 collections requiring forceRecreate (see PRD Appendix B)
  - [x] 3.4 Add error message template for critical config changes requiring forceRecreate (see PRD Appendix B)
  - [x] 3.5 Update check_collection_early() in commands/index.py to detect v1.0 and config changes before expensive operations
  - [x] 3.6 Modify collection existence handling to allow incremental updates when forceRecreate=false (default behavior change)

- [ ] 4.0 Implement HTTP Server Mode
  - [ ] 4.1 Research FastMCP HTTP transport support (check mcp library documentation and examples)
  - [ ] 4.2 Create minerva/commands/serve_http.py with run_serve_http() function
  - [ ] 4.3 Add serve-http subparser to cli.py with arguments: --config (required), --host (default: localhost), --port (default: 8000)
  - [ ] 4.4 Refactor server/mcp_server.py: extract initialize_server() logic into reusable function, add transport_mode parameter
  - [ ] 4.5 Add transport-specific logging: "Starting FastMCP server in stdio mode..." vs "Starting FastMCP server in HTTP mode on http://localhost:8000..."
  - [ ] 4.6 Implement HTTP mode startup in run_serve_http() using FastMCP HTTP API
  - [ ] 4.7 Test that both stdio and HTTP servers can run concurrently on different ports
  - [ ] 4.8 Add error handling for port already in use (see PRD Appendix B Error 3)

- [ ] 5.0 Testing, Documentation, and Release Preparation
  - [ ] 5.1 Write unit tests for compute_content_hash() in tests/test_content_hash.py
  - [ ] 5.2 Write unit tests for updater.py functions in tests/test_updater.py (fetch_existing_state, detect_changes, delete/update/add operations)
  - [ ] 5.3 Write unit tests for configuration change detection in tests/test_config_change_detection.py
  - [ ] 5.4 Write integration tests for full incremental update workflow in tests/test_incremental_integration.py
  - [ ] 5.5 Write unit tests for HTTP server mode in tests/test_serve_http.py
  - [ ] 5.6 Update README.md with v2.0 feature sections, incremental update examples, HTTP mode examples
  - [ ] 5.7 Update CLAUDE.md with new commands (serve-http), updated workflows, and troubleshooting sections
  - [ ] 5.8 Create docs/UPGRADE_v2.0.md with migration instructions, breaking changes, and v1.0 to v2.0 upgrade guide
  - [ ] 5.9 Manual end-to-end testing: create v1.0 collection, attempt incremental update (should fail), recreate with v2.0, perform incremental updates
  - [ ] 5.10 Update version number in cli.py from '1.0.0' to '2.0.0'
  - [ ] 5.11 Run full test suite and verify all tests pass: pytest tests/ --cov=minerva
  - [ ] 5.12 Prepare release notes summarizing features, breaking changes, and upgrade instructions
