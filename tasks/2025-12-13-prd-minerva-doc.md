# PRD: minerva-doc - Document Collection Orchestrator

## Introduction/Overview

**minerva-doc** is a new command-line tool for managing pre-extracted document collections in Minerva's knowledge base system. It provides a simple, opinionated interface for indexing JSON records that have already been extracted by external tools (Bear extractor, Zim extractor, etc.).

### Problem Statement

Currently, users who have pre-extracted JSON records must manually:
1. Create index configuration files
2. Run `minerva index` with the config
3. Track which collections they've created
4. Manually manage ChromaDB paths and server configuration

This multi-step process is cumbersome compared to the streamlined `minerva-kb` experience for repositories.

### Solution

Create a parallel tool (`minerva-doc`) that follows the same "zero-config" conventions as `minerva-kb`, but designed specifically for pre-extracted documentation. The tool hides configuration complexity and provides simple commands like `minerva-doc add`, `minerva-doc update`, and `minerva-doc serve`.

## Goals

1. **Reduce time to index pre-extracted docs** from ~15 minutes (manual config) to <2 minutes (single command)
2. **Provide feature parity** with minerva-kb for common operations (list, status, remove, serve)
3. **Maintain clear separation** between repo-based collections (minerva-kb) and doc-based collections (minerva-doc)
4. **Enable code reuse** through a shared library (minerva-common) that both tools depend on
5. **Prevent name collisions** across both tools to avoid ChromaDB conflicts
6. **Support ephemeral source files** - don't assume input JSON files persist after indexing

## User Stories

### US-1: Add First Document Collection
**As a** user with pre-extracted notes from Bear,
**I want to** index them with a single command,
**So that** I can quickly make them searchable via Claude Desktop without editing config files.

**Acceptance Criteria:**
- User runs `minerva-doc add ~/extracted/bear-notes.json --name bear-notes`
- Tool validates the JSON file
- Tool prompts for AI provider selection (OpenAI, Gemini, Ollama, LM Studio)
- Collection is indexed and ready to serve
- Total time < 2 minutes

### US-2: Update Existing Collection with New Export
**As a** user who periodically exports updated notes,
**I want to** update my collection with new data,
**So that** my searches reflect the latest content.

**Acceptance Criteria:**
- User runs `minerva-doc update bear-notes ~/extracted/bear-notes-new.json`
- Tool asks if user wants to change AI provider (with option to keep current)
- Tool performs smart diff (only indexes changed/new records)
- Collection is updated without full recreation (unless provider changed)

### US-3: List All Collections Across Both Tools
**As a** user with both repo and doc collections,
**I want to** see all my collections in one view,
**So that** I understand what's available to serve.

**Acceptance Criteria:**
- User runs `minerva-doc list` or `minerva-kb list`
- Both tools show:
  - Managed collections (with full details)
  - Unmanaged collections (with warning: "created outside [tool]")
- Clear indication of which collections belong to which tool

### US-4: Serve All Collections via MCP
**As a** user,
**I want to** start an MCP server that exposes all collections,
**So that** Claude Desktop can search across both repo and doc collections.

**Acceptance Criteria:**
- User runs `minerva-doc serve` (or `minerva-kb serve`)
- Server starts on port 8337
- All ChromaDB collections are available for search (regardless of which tool created them)

### US-5: Remove Document Collection
**As a** user,
**I want to** remove a document collection I no longer need,
**So that** it doesn't clutter my searches.

**Acceptance Criteria:**
- User runs `minerva-doc remove bear-notes`
- Tool removes collection from ChromaDB
- Tool removes metadata from collections.json
- Tool errors if trying to remove a repo collection (suggest using minerva-kb)

## Functional Requirements

### Phase 1: Shared Library (minerva-common)

**FR1.1** - Create `tools/minerva-common` package with shared functionality
**FR1.2** - Implement `paths.py` with centralized path definitions (MINERVA_DIR, CHROMADB_DIR, etc.)
**FR1.3** - Implement `init.py` with idempotent directory/config creation:
  - `ensure_shared_dirs()` - creates `.minerva/` and `chromadb/` if they don't exist
  - `ensure_server_config()` - creates `server.json` if it doesn't exist (returns tuple indicating if created)
**FR1.4** - Implement `registry.py` for collection registry management (CRUD operations)
**FR1.5** - Implement `config_builder.py` to generate minerva index config files
**FR1.6** - Implement `minerva_runner.py` for subprocess calls to `minerva` CLI commands
**FR1.7** - Implement `provider_setup.py` for interactive AI provider selection and validation
**FR1.8** - Implement `server_manager.py` for serve command logic (shared by both tools)
**FR1.9** - Implement `collection_ops.py` for list/status/remove operations (shared patterns)
**FR1.10** - Set restrictive permissions on created files/directories (0o700 for dirs, 0o600 for configs)
**FR1.11** - Refactor minerva-kb to depend on minerva-common and remove duplicated code

### Phase 2: minerva-doc Tool

**FR2.1** - Create `tools/minerva-doc` package structure with src/tests directories
**FR2.2** - Implement CLI with commands: add, update, list, status, remove, serve
**FR2.3** - Implement `collections.json` registry to track doc collection metadata:
  - Schema: `{type, name, records_path, chromadb_collection, description, created_at, indexed_at}`
  - Stored at: `~/.minerva/apps/minerva-doc/collections.json`
**FR2.4** - Implement `add` command:
  - Accept path to single JSON file (minerva validate format)
  - Require `--name` parameter (no auto-naming)
  - Validate JSON with `minerva validate`
  - Interactive prompts:
    - Prompt for AI provider selection (OpenAI, Gemini, Ollama, LM Studio)
    - Prompt for collection description:
      - Display: "Collection description (press Enter to auto-generate):"
      - If user provides text: use it as-is
      - If user presses Enter (empty): auto-generate using AI from records content
      - Show generated description and confirm: "Use this description? (Y/n)"
      - Time: ~5-15 seconds for auto-generation (saves user 30-60s of writing)
  - Generate temp index config with provider settings and description
  - Run `minerva index` via subprocess (validates description accuracy)
  - Register collection in collections.json with description
  - Error if collection name already exists (check both minerva-kb and minerva-doc)
**FR2.5** - Implement `update` command:
  - Accept collection name and new records path
  - Look up collection in collections.json
  - Validate new JSON file
  - Prompt: "Change AI provider? (current: [provider])" with yes/no options
  - If provider changed: set `force_recreate: true` in index config
  - If provider unchanged: use smart diff (minerva index default behavior)
  - Update `json_file` path in temp index config (ephemeral, not persisted)
  - Run `minerva index` via subprocess
  - Update `indexed_at` timestamp in collections.json
**FR2.6** - Implement `list` command:
  - Query ChromaDB for all collections
  - Load collections.json to identify managed doc collections
  - Display managed collections with full details (name, description, chunks, created/indexed dates)
  - Display unmanaged collections with warning: "⚠ Unmanaged (created outside minerva-doc)"
  - Support `--format table|json` output
**FR2.7** - Implement `status` command:
  - Accept collection name
  - Display detailed info: name, description, provider, chunk count, created/indexed dates
  - If collection not in registry: error "Collection not managed by minerva-doc"
**FR2.8** - Implement `remove` command:
  - Accept collection name
  - Check if collection is in collections.json
  - If not in registry but exists in ChromaDB: error "This is not a doc collection. Use minerva-kb remove or manually delete from ChromaDB"
  - Remove from ChromaDB
  - Remove from collections.json
  - Remove generated config files
**FR2.9** - Implement `serve` command:
  - Call shared `server_manager.py` logic
  - Read `~/.minerva/server.json`
  - Start MCP server exposing all ChromaDB collections
  - Display collections available (both managed and unmanaged)

### Phase 3: Collision Prevention

**FR3.1** - Update minerva-kb `add` command to check for existing collections:
  - Query ChromaDB for collection name before creating
  - Check minerva-doc collections.json (if exists)
  - Error if name collision detected: "Collection '[name]' already exists"
**FR3.2** - Implement shared collision check function in minerva-common:
  - `check_collection_exists(name: str) -> tuple[bool, str | None]`
  - Returns (exists, owner) where owner is "minerva-kb", "minerva-doc", or None
**FR3.3** - Both tools use collision check before add/create operations

### Phase 4: Documentation & Polish

**FR4.1** - Create `docs/MINERVA_DOC_GUIDE.md`:
  - Beginner-friendly introduction (for users new to Minerva)
  - Quick start guide (add first collection in <2 min)
  - Complete command reference
  - Examples: Bear notes, Zim dumps, markdown exports
  - Troubleshooting section
**FR4.2** - Update main `README.md` to explain both tools:
  - When to use minerva-kb (repos)
  - When to use minerva-doc (pre-extracted docs)
  - Directory structure diagram
**FR4.3** - Create `docs/MINERVA_COMMON.md` documenting the shared library:
  - Architecture overview
  - API reference for each module
  - How both tools consume the library
**FR4.4** - Add comprehensive test coverage:
  - Unit tests for minerva-common modules
  - Integration tests for minerva-doc commands
  - E2E test: add → update → list → serve → remove workflow
**FR4.5** - Improve error messages:
  - Wrong tool errors: "my-notes is a doc collection, use minerva-doc update"
  - Missing dependencies: "minerva CLI not found, install with: pip install -e ."
  - Permission errors: clear guidance on fixing file permissions
**FR4.6** - Add `--help` text for all commands with examples

## Non-Goals (Out of Scope)

1. **Built-in extractors** - minerva-doc will NOT include extractors for various formats (PDF, Word, etc.). Users must run extractors separately.
2. **Multi-file input** - Will NOT accept directories or multiple JSON files. Input is a single JSON file conforming to minerva validate schema.
3. **JSONL format** - Will NOT support JSON Lines format (only standard JSON arrays)
4. **Automatic re-extraction** - Unlike minerva-kb which can re-extract from repos, minerva-doc requires users to provide updated files manually
5. **File watching** - No `watch` command (source files are ephemeral, watching doesn't make sense)
6. **Collection merging** - Will NOT support merging multiple collections into one
7. **Rollback/versioning** - Will NOT track collection history or allow rollback to previous versions

## Design Considerations

### Directory Structure

```
~/.minerva/
├── chromadb/                    # Shared ChromaDB storage
├── server.json                  # Shared server config
└── apps/
    ├── minerva-kb/              # minerva-kb specific
    │   ├── [collection]-watcher.json
    │   ├── [collection]-index.json
    │   └── [collection]-extracted.json
    └── minerva-doc/             # minerva-doc specific
        ├── collections.json     # Doc collections registry
        └── [collection]-index.json
```

### collections.json Schema

```json
{
  "collections": {
    "bear-notes": {
      "type": "docs",
      "name": "bear-notes",
      "records_path": "/Users/me/extracted/bear-notes.json",
      "chromadb_collection": "bear-notes",
      "description": "Personal notes from Bear app",
      "provider": {
        "provider_type": "ollama",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b"
      },
      "created_at": "2025-12-13T11:00:00Z",
      "indexed_at": "2025-12-13T14:30:00Z"
    }
  }
}
```

**Notes:**
- `records_path` is stored but NOT validated on subsequent operations (files may be ephemeral)
- `indexed_at` is updated on every `update` command
- `provider` is stored to show current settings and enable provider change prompts

### CLI Examples

```bash
# Add first collection (with auto-generated description)
$ minerva-doc add ~/extracted/bear-notes.json --name bear-notes
✓ Validated 450 records
? Select AI provider: (Use arrow keys)
  > Ollama (recommended for local)
    OpenAI
    Google Gemini
    LM Studio
? Embedding model: mxbai-embed-large:latest
? LLM model: llama3.1:8b
? Collection description (press Enter to auto-generate): _
⏳ Generating description from content...
✓ Description: "Personal notes exported from Bear app covering software
  development, Python programming, and system architecture. Contains 450
  notes with code snippets, design patterns, and technical references."
? Use this description? (Y/n) y
✓ Indexed 450 records → 1,237 chunks
✓ Collection ready: bear-notes

# Add with custom description
$ minerva-doc add ~/extracted/wiki.json --name wiki-articles
✓ Validated 1,200 records
? Select AI provider: OpenAI
? Embedding model: text-embedding-3-small
? LLM model: gpt-4o-mini
? Collection description (press Enter to auto-generate): Wikipedia articles on history
✓ Using your description
✓ Indexed 1,200 records → 3,456 chunks
✓ Collection ready: wiki-articles

# Update with new export
$ minerva-doc update bear-notes ~/extracted/bear-notes-new.json
✓ Validated 475 records
? Change AI provider? (current: Ollama - llama3.1:8b + mxbai-embed-large:latest)
  > No, keep current provider
    Yes, select new provider
✓ Smart diff: 25 new, 12 updated, 0 deleted
✓ Reindexed: 37 records → 89 new chunks
✓ Collection updated: bear-notes

# List all collections
$ minerva-doc list
Collections (2):

bear-notes
  Type:        docs
  Description: Personal notes from Bear app
  Provider:    Ollama (llama3.1:8b + mxbai-embed-large:latest)
  Chunks:      1,326
  Created:     2025-12-13 11:00:00
  Indexed:     2025-12-13 14:30:00

zim-notes
  Type:        docs
  Description: Wikipedia articles
  Provider:    OpenAI (gpt-4o-mini + text-embedding-3-small)
  Chunks:      5,432
  Created:     2025-12-13 12:00:00
  Indexed:     2025-12-13 12:15:00

Unmanaged collections (1):

my-repo-kb
  ⚠ Unmanaged (created outside minerva-doc)
  Chunks: 2,150
  (Use minerva-kb for repo collections)

# Serve all collections
$ minerva-doc serve
ℹ Starting MCP server...
ℹ Collections available:
  - bear-notes (docs, 1,326 chunks)
  - zim-notes (docs, 5,432 chunks)
  - my-repo-kb (unmanaged, 2,150 chunks)
✓ Server ready at http://127.0.0.1:8337

# Remove collection
$ minerva-doc remove bear-notes
? Remove collection 'bear-notes'? (y/N) y
✓ Removed from ChromaDB
✓ Removed from registry
✓ Collection deleted: bear-notes
```

## Technical Considerations

### Dependencies

- **minerva-common**: Shared library (both tools depend on it)
- **minerva**: Core Minerva package (for `minerva validate`, `minerva index`, `minerva serve`)
- **ChromaDB**: Vector database (already a minerva dependency)
- **Python 3.10+**: Target version

### Subprocess Management

All calls to core `minerva` commands should use `subprocess.run()` with:
- Explicit timeout (default: 600 seconds for indexing)
- Capture stdout/stderr for error reporting
- Check return codes and handle failures gracefully
- Stream output to user for long-running operations

### Error Handling Patterns

1. **Validation errors**: Run `minerva validate` first, surface errors before indexing
2. **Name collisions**: Check before starting expensive operations
3. **Missing files**: Validate input file exists and is readable
4. **ChromaDB errors**: Catch and provide helpful messages
5. **Permission errors**: Guide user to fix permissions

### Smart Diff Behavior

The `update` command relies on minerva's existing smart diff logic:
- Compare new records against indexed chunks using content hashing
- Only re-index changed/new content
- Delete chunks for removed records
- If `force_recreate: true` (provider change), full recreation occurs

This is already implemented in `minerva index` - no new logic needed.

## Success Metrics

### Primary Metric
**Reduction in support questions** about manual indexing workflow:
- Baseline: Track GitHub issues/discussions about "how to index JSON files"
- Target: 80% reduction in these questions after minerva-doc release
- Measurement: Compare 3 months pre-release vs 3 months post-release

### Secondary Metrics
- **Time to first doc collection**: <2 minutes (measured via user testing)
- **Adoption rate**: % of minerva users using minerva-doc vs manual commands
- **Error rate**: <5% of add/update operations fail (excluding user errors like invalid JSON)

## Design Decisions

### Input Method
**Decision**: File path only, no stdin support
- Rationale: Maintains meaningful `records_path` in registry; simpler implementation
- Users must save JSON to a file before running `add` or `update`

### Collection Naming Rules
**Decision**: Accept any name that ChromaDB accepts (permissive)
- No artificial restrictions on naming conventions
- Allows spaces, unicode, special characters
- Examples: `my-notes`, `My Bear Notes`, `我的笔记` are all valid
- ChromaDB will enforce its own validation

### Collection Description
**Decision**: Interactive prompt with auto-generation option
- During `add` command, prompt: "Collection description (press Enter to auto-generate):"
- If user provides text: use as-is
- If user presses Enter (empty): auto-generate using AI from records content
- Auto-generation benefits:
  - Time savings: ~5-15s for AI vs 30-60s for user to write
  - Quality: AI-generated descriptions pass minerva index validation
  - Accuracy: Same AI provider ensures description matches content
- Rationale: Multi-line descriptions are awkward as CLI flags; interactive prompt is more natural

### Update Command Flags
**Decision**: No `--force` flag
- Provider change prompt is always interactive
- Encourages users to make deliberate decisions about re-indexing
- Scripting users can modify collections.json + run minerva index directly if needed

### Dry-Run Mode
**Decision**: Not included in v1.0
- Can be added later if users request it
- Focus on core functionality first

### Serve Port Configuration
**Decision**: No port override flag
- Users must edit `~/.minerva/server.json` to change port
- Keeps serve command simple and consistent with configuration-based approach

## Implementation Phases

### Phase 1: Shared Library (Week 1-2)
- Create minerva-common package structure
- Implement core modules (paths, init, registry, config_builder, etc.)
- Write unit tests for each module
- Refactor minerva-kb to use minerva-common
- Verify minerva-kb still works correctly

### Phase 2: minerva-doc Core (Week 3-4)
- Create minerva-doc package structure
- Implement add command with provider selection
- Implement update command with smart diff
- Implement collections.json registry management
- Write integration tests for add/update

### Phase 3: Full Feature Set (Week 5)
- Implement list/status/remove/serve commands
- Implement collision prevention in both tools
- Write E2E tests for complete workflows
- Polish error messages and help text

### Phase 4: Documentation & Release (Week 6)
- Write MINERVA_DOC_GUIDE.md
- Update main README.md
- Create tutorial videos/screenshots
- Beta testing with 5-10 users
- Address feedback and polish
- Release v1.0.0

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| minerva-kb refactor breaks existing functionality | High | Medium | Comprehensive test coverage before refactor; gradual migration |
| Users confused about which tool to use | Medium | High | Clear documentation; tool suggests other when appropriate |
| Registry corruption (collections.json) | High | Low | Atomic writes with temp files; backup on every write |
| ChromaDB breaking changes | High | Low | Pin ChromaDB version; test upgrades thoroughly |
| Provider selection UX is clunky | Low | Medium | User testing during Phase 2; iterate based on feedback |

## Appendix: Comparison with minerva-kb

| Feature | minerva-kb | minerva-doc |
|---------|------------|-------------|
| **Input source** | Git repository | JSON file (pre-extracted) |
| **Collection naming** | Auto-derived from repo path | User-specified (required) |
| **Source persistence** | Assumes repo is permanent | Assumes file is ephemeral |
| **Registry** | Implicit (presence of -watcher.json files) | Explicit (collections.json) |
| **Sync command** | Re-extracts from repo | Requires new file path |
| **Watch support** | Yes (file watcher) | No (not meaningful for ephemeral files) |
| **Provider change** | Via sync with force_recreate | Via update with force_recreate |
| **Target user** | Developers with codebases | Users with exported notes/docs |
