# Product Requirements Document: Minerva v2.0

## Incremental Updates & HTTP Server Mode

**Version:** 2.0
**Date:** 2025-10-28
**Status:** Draft
**Author:** Product Team

---

## 1. Introduction/Overview

Minerva v2.0 introduces two major features that address critical user pain points and expand integration capabilities:

1. **Incremental Updates**: Allow users to update existing note collections without full reindexing
2. **HTTP Server Mode**: Enable HTTP transport for MCP server alongside existing stdio mode

### Problem Statement

**Current Pain Points:**

- **Slow reindexing:** Users with large note collections (1000+ notes) must wait minutes to hours for full reindex when only a handful of notes changed
- **Limited integration options:** stdio-only MCP server prevents integration with web applications, remote access, and AI systems that don't support stdio transport

### Goal

Enable efficient, incremental updates to note collections and expand Minerva's integration capabilities through HTTP transport, making Minerva more practical for users with large, frequently-updated knowledge bases and diverse integration needs.

---

## 2. Goals

1. **Performance:** Reduce reindexing time by only processing changed, new, or deleted notes instead of rebuilding entire collections
2. **Efficiency:** Skip re-embedding and re-chunking for notes that haven't changed
3. **Compatibility:** Support both stdio and HTTP transport modes for maximum flexibility
4. **Reliability:** Automatically detect configuration changes that require full reindexing and guide users appropriately
5. **Adoption:** Make v2.0 compelling enough that users upgrade from v1.0 for the time savings and new capabilities

---

## 3. User Stories

### Feature 1: Incremental Updates

**Story 1: Frequent Note Updates**

> As a **knowledge worker** who updates my notes daily,
> I want to **reindex only the notes I changed**,
> So that **I can keep my searchable collection up-to-date without waiting for full reindexing**.

**Story 2: Large Collections**

> As a **researcher** with 5,000+ archived notes,
> I want to **add new notes to my collection quickly**,
> So that **I don't waste 30 minutes reindexing the entire collection every time I add a few notes**.

**Story 3: Collection Maintenance**

> As a **personal knowledge manager**,
> I want to **delete obsolete notes from my collection**,
> So that **my searches return only relevant, current information**.

### Feature 2: HTTP Server Mode

**Story 4: Web Application Integration**

> As a **developer building a custom knowledge base UI**,
> I want to **access Minerva search via HTTP API**,
> So that **I can integrate semantic search into my web application**.

**Story 5: AI System Compatibility**

> As a **user of AI assistants that don't support stdio MCP**,
> I want to **run Minerva MCP server in HTTP mode**,
> So that **I can use my knowledge base with any AI system that supports HTTP**.

**Story 6: Development and Testing**

> As a **Minerva contributor or power user**,
> I want to **test search queries with curl or Postman**,
> So that **I can debug issues and understand how the system works without requiring Claude Desktop**.

---

## 4. Functional Requirements

### Feature 1: Incremental Updates

#### FR1.1: Change Detection

The system must detect which notes have changed since the last indexing by computing and comparing content hashes (SHA256 of title + markdown content).

#### FR1.2: Selective Processing

The system must only re-chunk and re-embed notes that are new or have changed content, skipping unchanged notes entirely.

#### FR1.3: Note Deletion Handling

The system must automatically remove chunks from ChromaDB when their source notes are no longer present in the input JSON file.

#### FR1.4: Metadata-Only Updates

The system must allow updating collection description without re-embedding or re-chunking any notes.

#### FR1.5: Configuration Change Detection

The system must detect when critical configuration has changed (embedding model, embedding provider, or chunk size) and require the user to use `forceRecreate: true` for full reindexing.

#### FR1.6: Progress Reporting

The system must display a summary after update operations showing:

- Number of notes added
- Number of notes updated
- Number of notes deleted
- Number of notes skipped (unchanged)

#### FR1.7: Backward Compatibility Check

The system must detect v1.0 collections (lacking version metadata) and require users to use `forceRecreate: true` to upgrade to v2.0 format.

#### FR1.8: Partial Failure Handling

The system must stop processing other notes if individual notes fail during update, logging errors and reporting a summary of failures at the end.

### Feature 2: HTTP Server Mode

#### FR2.1: HTTP Command

The system must provide a new `minerva serve-http` command that starts the MCP server in HTTP mode.

#### FR2.2: Configuration Options

The command must accept:

- `--config` (required): Path to server configuration JSON
- `--host` (optional, default: localhost): Host to bind to
- `--port` (optional, default: 8000): Port to listen on

#### FR2.3: Identical Functionality

The HTTP mode must expose the exact same MCP tools as stdio mode:

- `list_knowledge_bases`: List available collections
- `search_knowledge_base`: Perform semantic search

#### FR2.4: Stdio Mode Preservation

The existing `minerva serve` command must continue to work exactly as before (stdio mode) for backward compatibility.

#### FR2.5: Concurrent Operation

The system must allow users to run both `minerva serve` (stdio) and `minerva serve-http` simultaneously if desired.

#### FR2.6: Startup Logging

The system must log the server mode, host, and port when starting:

- stdio: "Starting FastMCP server in stdio mode..."
- HTTP: "Starting FastMCP server in HTTP mode on http://localhost:8000..."

---

## 5. Non-Goals (Out of Scope)

The following features are explicitly **NOT** included in v2.0:

### NG1: Automatic Sync/Watch Mode

v2.0 will not include automatic file watching or background reindexing. Users must manually run `minerva index` when their notes change.

### NG2: Conflict Resolution UI

v2.0 will not include interactive conflict resolution or recovery wizards. Errors are logged, and processing continues with remaining notes.

### NG3: HTTP Authentication/Security

v2.0 will not include authentication, authorization, HTTPS, or any security features for HTTP mode. The HTTP server is designed for localhost use only. Network security is the user's responsibility if they choose to expose it.

### NG4: Migration Automation

v2.0 will not include automatic migration tools or scripts to upgrade v1.0 collections. Users must manually reindex with `forceRecreate: true` to upgrade.

### NG5: Performance Benchmarks

v2.0 does not commit to specific performance targets (e.g., "update 100 notes in X seconds"). Performance improvements are expected but not quantified.

### NG6: Rollback/Undo

v2.0 will not include the ability to undo an update or roll back to a previous collection state. Users should back up their ChromaDB directories if they want to preserve previous states.

### NG7: SQLite Index for Large Collections

v2.0 will not include a separate SQLite index for optimizing queries on very large collections (100K+ chunks). The bulk fetch approach is sufficient for the vast majority of users. A SQLite index may be considered for v2.1+ if users report performance issues with extremely large collections.

---

## 6. Design Considerations

### 6.1 User Experience

**Incremental Updates:**

- Default behavior changes: When `forceRecreate: false` (the default), the system now attempts incremental update instead of failing
- Error messages must be clear and actionable, especially for configuration change detection
- Progress indicators should help users understand time savings
- **Note identity:** Renaming a note (changing its title) will cause the system to treat it as a deletion + addition, resulting in re-embedding. This is expected behavior and documented in user guides

**HTTP Server Mode:**

- Command naming is explicit: `serve` = stdio, `serve-http` = HTTP
- Configuration file format remains unchanged; transport mode is CLI argument only
- Server logs should clearly indicate which mode is active

### 6.2 Configuration

**No changes to collection index configuration:**

```json
{
  "collection_name": "my_notes",
  "description": "...",
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json",
  "force_recreate": false,
  "chunk_size": 1200
}
```

**No changes to server configuration:**

```json
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
```

### 6.3 Data Model Changes

Collections created with v2.0 will include additional metadata:

- `version`: "2.0" (for v1.0 detection)
- `note_hash_algorithm`: "sha256"
- `last_updated`: ISO 8601 timestamp

**Hash Storage Optimization:**
The content hash is stored **only in the first chunk** of each note (`chunkIndex == 0`), not in every chunk. This eliminates redundancy while maintaining fast query performance.

Example:

- Note with 5 chunks → hash stored once (in chunk 0) instead of 5 times
- Query for all hashes: `collection.get(where={'chunkIndex': 0}, include=['metadatas'])`
- This reduces storage overhead from O(chunks) to O(notes)

---

## 7. Technical Considerations

### 7.1 Dependencies

- **FastMCP:** Must research HTTP support in current version (mcp >= 0.1.0)
- **ChromaDB:** Existing dependency, no changes required
- **LangChain:** Existing dependency for chunking, no changes required

### 7.2 Architecture

**Incremental Updates:**

- New module: `minerva/indexing/updater.py` for update logic
- Modified modules: `minerva/commands/index.py`, `minerva/indexing/storage.py`, `minerva/indexing/chunking.py`

**HTTP Server Mode:**

- New module: `minerva/commands/serve_http.py`
- Modified module: `minerva/server/mcp_server.py` (refactor for shared initialization)
- New CLI command: `serve-http` subparser in `minerva/cli.py`

### 7.3 Hash Algorithm

SHA256 is chosen for content hashing due to:

- Extremely low collision probability (< 1 in 10^60 for 1M notes)
- Fast computation
- Standard library support (no additional dependencies)

### 7.4 Update Execution Order

To ensure consistency, updates execute in this order:

1. Delete chunks for removed notes
2. Update chunks for modified notes
3. Add chunks for new notes

### 7.5 V1.0 Collection Detection

v1.0 collections lack the `version` field in metadata. v2.0 will check for this field and require `forceRecreate: true` if absent.

### 7.6 Query Strategy and Performance

**Bulk Fetch Approach:**
v2.0 uses a single bulk fetch to retrieve all chunk metadata at the start of an update operation, then performs all comparison and deletion operations in-memory. This avoids multiple slow metadata queries.

```python
# One ChromaDB query at start
all_chunks = collection.get(include=['metadatas'])

# Build in-memory maps
noteId_to_chunks = {}  # {noteId: [chunkId1, chunkId2, ...]}
noteId_to_hash = {}    # {noteId: content_hash}

# All subsequent operations use in-memory data
# Compare hashes, identify changes, determine deletions
```

**Performance characteristics:**

- Small collections (< 10K chunks): Query completes in ~2 seconds, uses ~10MB memory
- Medium collections (< 50K chunks): Query completes in ~15-30 seconds, uses ~100MB memory
- Large collections (100K+ chunks): May take 60+ seconds, uses ~1GB memory

**Why this approach:**

1. Embedding time (minutes) dominates total time, making query optimization secondary
2. Even "slow" bulk queries (30 seconds) are negligible compared to embedding savings (5+ minutes)
3. Simple implementation with single source of truth (no sync issues)
4. Memory usage is acceptable for modern systems

**Future optimization:**
For very large collections (100K+ chunks), a separate SQLite index could reduce query time from minutes to milliseconds. This optimization is deferred to v2.1+ based on user feedback.

### 7.7 Note ID Stability and Limitations

**How noteId is generated:**
`noteId = SHA1(title + creationDate)`

**Stability assumptions:**

- Title and creationDate are expected to be **immutable** for a note
- If either changes, the system treats it as a different note (delete old + add new)

**Known limitations:**

- **Renaming notes:** Changing a note's title will cause re-embedding (treated as delete + add)
- **Missing creationDate:** If some notes lack creationDate, they use empty string, which may cause ID conflicts
- **Date format changes:** creationDate must be consistent across extractions

**Acceptable behavior:**
These limitations are documented and considered acceptable for v2.0. Renaming a note causing re-embedding is a reasonable trade-off for the simplicity of the design. Users who frequently reorganize notes can still use `forceRecreate: true` for a clean rebuild.

**Future consideration:**
Optional stable IDs from extractors could be considered for v2.1+ if user feedback indicates renaming is a common pain point.

---

## 8. Success Metrics

### Primary Metrics

**M1: Indexing Time Reduction**

- Measure reindexing time for collections where <20% of notes changed
- Expected: Incremental update should be significantly faster than full reindex
- How: User reports, benchmark tests with sample collections

**M2: HTTP Mode Adoption**

- Track number of users who successfully run `minerva serve-http`
- Track integrations built using HTTP mode (via community feedback, GitHub issues, discussions)
- Goal: Enable MCP for AI systems that don't support stdio

### Secondary Metrics

**M3: User Satisfaction**

- Qualitative feedback via GitHub issues, discussions, and direct communication
- Key themes: time savings, ease of use, reliability, flexibility

**M4: Upgrade Rate**

- Track how many existing v1.0 users upgrade to v2.0
- Survey reasons for not upgrading if adoption is low

---

## 9. Open Questions

### Q1: FastMCP HTTP Support

**Question:** Does the current version of FastMCP support HTTP transport? What is the API?
**Action:** Research during Phase 2A implementation
**Impact:** High - determines HTTP mode feasibility

### Q2: CORS Support

**Question:** Should HTTP mode support CORS headers for browser-based integrations?
**Action:** Defer to user feedback after initial release
**Impact:** Medium - affects web integration use cases

### Q3: Health Check Endpoint

**Question:** Should HTTP mode include a `/health` or `/status` endpoint for monitoring?
**Action:** Consider for v2.1 if users request it
**Impact:** Low - nice-to-have for production deployments

### Q4: HTTP Error Handling

**Question:** What HTTP status codes should be returned for different error conditions?
**Action:** Research FastMCP defaults during implementation
**Impact:** Medium - affects client integration patterns

---

## 10. Release Plan

### Version Numbering

- **v2.0** - Both features ship together

### Implementation Order

1. **Feature 1: Incremental Updates** (implement first, more complex)

   - Phase 1A: Content Hash Tracking
   - Phase 1B: Update Logic
   - Phase 1C: Edge Cases & Validation
   - Phase 1D: Testing

2. **Feature 2: HTTP Server Mode** (implement second, simpler)

   - Phase 2A: Research FastMCP
   - Phase 2B: Implement HTTP Command
   - Phase 2C: Documentation
   - Phase 2D: Testing

3. **Integration Testing** - Test both features together
4. **Documentation Updates** - Update README.md, CLAUDE.md, add upgrade guide
5. **Release** - Tag v2.0, publish release notes

### Documentation Requirements

- Update README.md with both features
- Update CLAUDE.md with new commands and workflows
- Create UPGRADE_v2.0.md guide for v1.0 users
- Update any tutorials or examples

---

## Appendix A: Example Workflows

### Example 1: Daily Note Updates

```bash
# Initial index
minerva index --config my-notes-config.json

# ... user edits 5 notes, adds 2 new ones, deletes 1 ...

# Update (incremental)
minerva index --config my-notes-config.json

# Output:
# ✓ Update complete:
#   - Added: 2 notes (8 chunks)
#   - Updated: 5 notes (23 chunks)
#   - Deleted: 1 note (4 chunks)
#   - Skipped: 1,234 notes (unchanged)
#   - Total time: 15 seconds (vs. 8 minutes for full reindex)
```

### Example 2: HTTP Mode for Web App

```bash
# Start HTTP server
minerva serve-http --config server-config.json --port 8080

# From another terminal or application:
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "my_notes",
    "query": "machine learning fundamentals",
    "max_results": 5
  }'
```

### Example 3: Description-Only Update

```bash
# Update collection config (only description changed)
cat my-notes-config.json
{
  "collection_name": "my_notes",
  "description": "Updated description for my personal notes",  # Changed
  "chromadb_path": "./chromadb_data",
  "json_file": "./notes.json"
}

# Run update
minerva index --config my-notes-config.json

# Output:
# ✓ Metadata update complete:
#   - Description updated
#   - No notes re-processed (metadata-only change)
#   - Total time: 1 second
```

---

## Appendix B: Error Messages

### Error 1: V1.0 Collection

```
❌ Error: Collection 'my_notes' was created with Minerva v1.0
   and cannot be incrementally updated.

   To upgrade to v2.0 format, set "force_recreate": true in your
   configuration file. This will rebuild the collection from scratch.

   Backup recommendation: Copy ./chromadb_data to a safe location
   before upgrading.
```

### Error 2: AI Configuration Changed

```
❌ Error: Critical configuration change detected

   The following settings have changed since the collection was created:
   - Embedding model: mxbai-embed-large:latest → text-embedding-3-small
   - Provider: ollama → openai

   Incremental update is not possible because embeddings are incompatible.

   To reindex with new AI settings, set "force_recreate": true in your
   configuration file.
```

### Error 3: HTTP Port Already in Use

```
❌ Error: Cannot start HTTP server on port 8000

   Port 8000 is already in use by another process.

   Try:
   - Use a different port: minerva serve-http --config config.json --port 8001
   - Stop the process using port 8000
   - Check: lsof -i :8000 (macOS/Linux) or netstat -ano | findstr :8000 (Windows)
```

---

## Appendix C: Technical Implementation References

For detailed technical implementation, see companion document:

- `tasks/2025-10-28-partial-updates-server-mode.md`

This PRD focuses on **what** and **why**. The companion document covers **how** at the code level.
