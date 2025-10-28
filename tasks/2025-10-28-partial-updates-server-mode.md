# Version 2.0: Incremental Updates & HTTP Server Mode

**Date:** 2025-10-28
**Status:** Planning

## Overview

This document tracks the implementation of two major features for Minerva version 2.0:
1. **Incremental updates** for `minerva index` command
2. **HTTP transport mode** for MCP server via new `minerva serve-http` command

## Design Decisions

Based on exploration and user clarification:

- **Change detection:** Content hash comparison (SHA256 of title + markdown)
- **Deleted notes:** Automatically remove from collection
- **Metadata updates:**
  - Description only → metadata update (no re-embedding)
  - AI provider change → full reindex required
  - Chunk size change → full reindex required
- **HTTP transport:** Separate command (`serve-http`) rather than dual-mode

---

## Feature 1: Incremental Updates

### Current Behavior
- `forceRecreate: false` → fails if collection exists
- `forceRecreate: true` → deletes entire collection and rebuilds from scratch
- No change detection or update capability

### Target Behavior
- `forceRecreate: false` → enter update mode if collection exists
- Compare notes using content hashes
- Update only changed/new notes
- Remove deleted notes
- Update metadata without re-embedding if only description changed

### Implementation Tasks

#### Phase 1A: Content Hash Tracking
- [ ] **File:** `minerva/indexing/chunking.py`
  - Add `compute_note_content_hash(note: Dict) -> str` function
  - Hash: SHA256(title + markdown)
  - Update data structures to include `note_content_hash`

- [ ] **File:** `minerva/indexing/storage.py`
  - Modify `insert_chunks()` to store `note_content_hash` in metadata
  - Add `get_existing_note_hashes(collection) -> Dict[str, str]`
    - Returns: `{noteId: content_hash}` mapping
  - Add `delete_chunks_by_note_id(collection, note_id: str) -> int`
    - Returns: count of deleted chunks

#### Phase 1B: Update Logic
- [ ] **New file:** `minerva/indexing/updater.py`
  ```python
  @dataclass
  class UpdatePlan:
      notes_to_add: List[Dict]
      notes_to_update: List[Dict]
      notes_unchanged: List[Dict]
      notes_to_delete: List[str]  # noteIds
      metadata_only: bool
  ```

  - `compare_notes(json_notes, existing_hashes) -> UpdatePlan`
  - `should_force_full_reindex(old_metadata, new_config) -> Tuple[bool, str]`
    - Check: embedding_model, embedding_provider, chunk_size
    - Returns: (needs_reindex, reason)
  - `update_collection_metadata(collection, description: str) -> None`
  - `execute_update_plan(collection, plan, provider, config) -> UpdateStats`

- [ ] **File:** `minerva/commands/index.py`
  - Refactor `run_full_indexing()` into smaller functions
  - Add update mode path:
    ```python
    if collection_exists and not force_recreate:
        if is_v1_collection(collection):
            error("Collection has no hash metadata. Use forceRecreate: true")
        if should_force_full_reindex(collection.metadata, config):
            error("AI config changed. Use forceRecreate: true")
        run_incremental_update(collection, config)
    else:
        run_full_indexing(config)
    ```
  - Add progress reporting for updates

#### Phase 1C: Edge Cases & Validation
- [ ] **File:** `minerva/common/config.py`
  - Keep existing validation
  - Document `forceRecreate` behavior in docstrings

- [ ] Handle edge cases:
  - [ ] V1.0 collections (no hash metadata) → require forceRecreate
  - [ ] AI config changed → require forceRecreate
  - [ ] Partial failures → log and continue
  - [ ] Empty JSON file → warning about deleting all notes

#### Phase 1D: Testing
- [ ] Unit tests for hash comparison logic
- [ ] Integration test: add notes
- [ ] Integration test: modify notes
- [ ] Integration test: delete notes
- [ ] Integration test: description-only change
- [ ] Integration test: AI provider change (should fail)
- [ ] Integration test: v1.0 collection (should fail)

---

## Feature 2: HTTP Server Mode

### Current Behavior
- `minerva serve` runs FastMCP in stdio mode only
- Used for Claude Desktop integration
- No HTTP/web integration support

### Target Behavior
- Keep `minerva serve` for stdio mode (backward compatible)
- Add `minerva serve-http` for HTTP transport
- Both commands use same server initialization and tools
- HTTP command accepts `--host` and `--port` arguments

### Implementation Tasks

#### Phase 2A: Research FastMCP
- [ ] Investigate FastMCP HTTP support
  - Check `mcp.run()` API for transport parameters
  - Look for HTTP/SSE examples in FastMCP docs
  - Determine if any additional dependencies needed
  - Test locally with simple FastMCP HTTP example

#### Phase 2B: Implement HTTP Command
- [ ] **New file:** `minerva/commands/serve_http.py`
  ```python
  def run_serve_http(args):
      """Run MCP server in HTTP mode"""
      config_path = Path(args.config).resolve()
      host = args.host
      port = args.port
      mcp_main_http(config_path, host, port)
  ```

- [ ] **File:** `minerva/server/mcp_server.py`
  - Refactor: extract shared initialization
  - Keep `main(config_path)` for stdio mode
  - Add `main_http(config_path, host, port)` for HTTP mode
  - Update logging messages to indicate mode

- [ ] **File:** `minerva/cli.py`
  - Add `serve-http` subcommand
  ```python
  serve_http_parser = subparsers.add_parser(
      'serve-http',
      help='Start MCP server in HTTP mode'
  )
  serve_http_parser.add_argument('--config', required=True)
  serve_http_parser.add_argument('--host', default='localhost')
  serve_http_parser.add_argument('--port', type=int, default=8000)
  ```

#### Phase 2C: Documentation
- [ ] **File:** `CLAUDE.md`
  - Add `minerva serve-http` to command reference
  - Add HTTP mode examples
  - Explain use cases: stdio for Claude Desktop, HTTP for web

- [ ] **File:** `README.md`
  - Update server section with both modes
  - Add HTTP mode quick start

#### Phase 2D: Testing
- [ ] Manual test: start HTTP server
- [ ] Manual test: verify tools accessible via HTTP
- [ ] Manual test: run both stdio and HTTP simultaneously
- [ ] Test: CORS headers if needed
- [ ] Test: health check endpoint

---

## Implementation Order

1. ✅ Exploration and planning (completed)
2. ⬜ Feature 1: Incremental Updates (implement first - more complex)
   - Phase 1A → 1B → 1C → 1D
3. ⬜ Feature 2: HTTP Server Mode (implement second - simpler)
   - Phase 2A → 2B → 2C → 2D
4. ⬜ End-to-end testing of both features
5. ⬜ Update version number and CHANGELOG

---

## Open Questions

- [ ] FastMCP HTTP API details (need to research in Phase 2A)
- [ ] Should we support CORS configuration for HTTP mode?
- [ ] Do we need authentication for HTTP mode?
- [ ] Should HTTP mode have a health check endpoint?

---

## Notes

### Why Content Hash Instead of modificationDate?
- More reliable: handles file copies, timezone issues, manual edits
- Catches any content changes regardless of metadata
- Deterministic: same content always produces same hash

### Why Separate Commands?
- Backward compatibility: `minerva serve` behavior unchanged
- Simpler implementation: no transport multiplexing
- Clearer user intent: explicit choice of mode
- Easier testing: independent test suites

### Why Delete Orphaned Notes?
- Keeps collection in sync with source JSON
- Prevents stale data accumulation
- User can always keep notes by leaving them in JSON

---

## Technical Details

### Content Hash Computation
```python
def compute_note_content_hash(note: Dict) -> str:
    """Compute SHA256 hash of note content for change detection"""
    content = note['title'] + note['markdown']
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### Update Detection Flow
```
1. Load notes from JSON file
2. Get existing noteId → hash mappings from ChromaDB
3. For each note in JSON:
   - Compute noteId and content hash
   - If noteId not in ChromaDB → ADD
   - If noteId exists but hash differs → UPDATE
   - If noteId exists and hash matches → SKIP
4. For each noteId in ChromaDB not in JSON → DELETE
5. Execute plan: delete → update → add (in that order)
```

### Collection Metadata for Version Detection
Collections will store version metadata:
```python
{
    'version': '2.0',  # New field for v2.0 collections
    'note_hash_algorithm': 'sha256',
    'last_updated': ISO 8601 timestamp,
    # ... existing metadata ...
}
```

V1.0 collections lack the `version` field, which triggers the requirement for `forceRecreate`.

---

## Risk Mitigation

### Risk: Partial Update Failure
**Mitigation:**
- Wrap update operations in try-except blocks
- Log failures but continue processing
- Report summary at end: "Updated 10/12 notes (2 failed)"

### Risk: Hash Collision
**Mitigation:**
- SHA256 has astronomically low collision probability
- For 1M notes, collision probability < 1 in 10^60
- No special handling needed

### Risk: V1.0 Collection Compatibility
**Mitigation:**
- Detect by checking for `version` field in metadata
- Clear error message: "Collection was created with v1.0. Use forceRecreate: true to upgrade"
- Document migration path in upgrade guide

### Risk: FastMCP HTTP Mode Changes
**Mitigation:**
- Research FastMCP thoroughly before implementation
- Pin FastMCP version in setup.py if API unstable
- Consider vendoring if necessary
