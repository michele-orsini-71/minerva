# Adding minerva-doc for Document Collections

## Problem
`minerva-kb` is designed for Git repositories with a specific workflow: persistent source, file watching, automatic re-extraction. Trying to support pre-extracted documentation (records) in the same tool creates several issues:

1. **Ephemeral sources**: Records might come from temp folders (e.g., `/tmp/extracted-notes`), making automatic collection naming meaningless and sync operations impossible.
2. **Asymmetric features**: Watch and sync work fundamentally differently (or not at all) for records vs repos, creating confusing UX.
3. **Different lifecycles**: Repos are persistent sources that can be re-scanned; records are one-time extraction outputs that may not persist.
4. **Identity dilution**: minerva-kb's value proposition is "fast repo indexing" - adding records support muddies that message.

## Proposed Solution: minerva-doc

Create a **parallel tool** (`minerva-doc`) that follows the same conventions as `minerva-kb` but is purpose-built for pre-extracted documentation.

### Division of Responsibilities

**minerva-kb (repositories only):**
```bash
minerva-kb add /path/to/repo              # Auto-names collection, extracts & indexes
minerva-kb sync <collection>              # Re-extracts from repo, reindexes
minerva-kb watch <collection>             # Auto-sync on file changes
minerva-kb list                           # List all collections (any type)
minerva-kb status <collection>            # Show collection details
minerva-kb remove <collection>            # Remove collection
minerva-kb serve                          # Serve all collections via MCP
```

**minerva-doc (pre-extracted docs):**
```bash
minerva-doc add /path/to/records \        # Validates & indexes records
  --name my-notes                         # Name required (no auto-naming)
  [--description "..."]                   # Optional description

minerva-doc update my-notes \             # Revalidate & reindex with new records
  /path/to/new-records                    # Must provide new records path

minerva-doc list                          # List all collections (any type)
minerva-doc status <collection>           # Show collection details
minerva-doc remove <collection>           # Remove collection
minerva-doc serve                         # Serve all collections via MCP
```

### Key Differences

| Feature | minerva-kb (repos) | minerva-doc (docs) |
|---------|-------------------|-------------------|
| **Source type** | Git repositories | Pre-extracted records (JSON) |
| **Collection naming** | Auto-derived from repo path | User-specified (required) |
| **Add command** | Runs extractor + indexes | Validates + indexes only |
| **Sync/Update** | `sync` re-extracts from repo | `update` requires new records path |
| **Watch support** | Yes (file watcher) | No (records may be ephemeral) |
| **Source persistence** | Assumes permanent repo | No assumption about source |

### Shared Infrastructure

Both tools share a common directory structure under `~/.minerva/`:

```
~/.minerva/
├── chromadb/                    # Shared ChromaDB storage (both tools)
├── server.json                  # Shared server config (both tools)
├── apps/
│   ├── minerva-kb/             # minerva-kb specific
│   │   ├── collections.json    # KB collections registry
│   │   └── configs/            # Generated index configs
│   └── minerva-doc/            # minerva-doc specific
│       ├── collections.json    # Doc collections registry
│       └── configs/            # Generated index configs
```

**Shared components:**
- **ChromaDB storage**: `~/.minerva/chromadb/` - both tools write to the same ChromaDB instance
- **Server config**: `~/.minerva/server.json` - used by both tools' `serve` command

**Tool-specific components:**
- **Collection registry**: Each tool maintains its own registry (`apps/minerva-kb/collections.json` and `apps/minerva-doc/collections.json`)
- **Generated configs**: Each tool stores its generated index configs separately

**How collections are discovered:**
- When either tool runs `serve`, it:
  1. Reads `~/.minerva/server.json` for server settings
  2. Lists all collections from `~/.minerva/chromadb/` (ChromaDB's native list)
  3. Serves all collections regardless of which tool created them

This means:
- Add a repo with `minerva-kb`, add docs with `minerva-doc`, run either tool's `serve` command - both expose all collections
- Each tool manages its own registry independently (no cross-tool coordination needed)
- The `serve` command duplication isn't an issue since most users will only use one tool

## Implementation Strategy

### Shared Library (minerva-common or minerva-orchestrator)

Factor common functionality into a shared library that both tools import:

```
tools/minerva-common/           # New shared library
├── src/minerva_common/
│   ├── paths.py               # Shared path constants and directory creation
│   ├── init.py                # Initialize shared infrastructure
│   ├── registry.py            # Collection registry management
│   ├── config_builder.py      # Generate minerva config files
│   ├── minerva_runner.py      # Subprocess calls to minerva CLI
│   ├── provider_setup.py      # AI provider selection/validation
│   ├── server_manager.py      # Serve command logic
│   └── collection_ops.py      # List/status/remove operations
└── setup.py

tools/minerva-kb/              # Repo orchestrator (existing)
├── src/minerva_kb/
│   ├── cli.py
│   ├── commands/
│   │   ├── add.py             # Repo-specific: run repository-doc-extractor
│   │   ├── sync.py            # Repo-specific: re-extract & reindex
│   │   └── watch.py           # Repo-specific: file watching
│   └── utils/
└── requirements.txt           # Depends on: minerva-common

tools/minerva-doc/             # New docs orchestrator
├── src/minerva_doc/
│   ├── cli.py
│   ├── commands/
│   │   ├── add.py             # Docs-specific: validate & index
│   │   └── update.py          # Docs-specific: revalidate & reindex
│   └── utils/
└── requirements.txt           # Depends on: minerva-common
```

### Shared Infrastructure Initialization

**minerva-common** provides shared initialization logic that both tools use:

**`minerva_common/paths.py`** - Shared path definitions:
```python
from pathlib import Path

HOME_DIR = Path.home()
MINERVA_DIR = HOME_DIR / ".minerva"
CHROMADB_DIR = MINERVA_DIR / "chromadb"
SERVER_CONFIG_PATH = MINERVA_DIR / "server.json"
APPS_DIR = MINERVA_DIR / "apps"
```

**`minerva_common/init.py`** - Initialize shared components:
```python
import json
import os
from pathlib import Path
from .paths import MINERVA_DIR, CHROMADB_DIR, SERVER_CONFIG_PATH

def ensure_shared_dirs() -> None:
    """Create shared directories if they don't exist."""
    MINERVA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMADB_DIR.mkdir(parents=True, exist_ok=True)

    # Set restrictive permissions
    try:
        os.chmod(MINERVA_DIR, 0o700)
        os.chmod(CHROMADB_DIR, 0o700)
    except PermissionError:
        pass

def ensure_server_config() -> tuple[Path, bool]:
    """
    Create server.json if it doesn't exist.
    Returns (path, created) where created=True if file was created.
    """
    ensure_shared_dirs()

    if SERVER_CONFIG_PATH.exists():
        return SERVER_CONFIG_PATH, False

    config = {
        "chromadb_path": str(CHROMADB_DIR),
        "default_max_results": 5,
        "host": "127.0.0.1",
        "port": 8337,
    }

    # Atomic write
    temp_path = SERVER_CONFIG_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    temp_path.replace(SERVER_CONFIG_PATH)

    # Set restrictive permissions
    try:
        os.chmod(SERVER_CONFIG_PATH, 0o600)
    except PermissionError:
        pass

    return SERVER_CONFIG_PATH, True
```

**Each tool** creates its own app-specific directory:

**minerva-kb:**
```python
from minerva_common.paths import APPS_DIR
from minerva_common.init import ensure_shared_dirs

MINERVA_KB_APP_DIR = APPS_DIR / "minerva-kb"

def ensure_app_dir() -> Path:
    ensure_shared_dirs()  # Ensure parent dirs exist
    MINERVA_KB_APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(MINERVA_KB_APP_DIR, 0o700)
    except PermissionError:
        pass
    return MINERVA_KB_APP_DIR
```

**minerva-doc:**
```python
from minerva_common.paths import APPS_DIR
from minerva_common.init import ensure_shared_dirs

MINERVA_DOC_APP_DIR = APPS_DIR / "minerva-doc"

def ensure_app_dir() -> Path:
    ensure_shared_dirs()  # Ensure parent dirs exist
    MINERVA_DOC_APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(MINERVA_DOC_APP_DIR, 0o700)
    except PermissionError:
        pass
    return MINERVA_DOC_APP_DIR
```

This approach:
- Shared components (chromadb/, server.json) are created once by whichever tool runs first
- Both tools call `ensure_shared_dirs()` and `ensure_server_config()` which are idempotent
- Each tool manages its own app-specific directory independently
- No conflicts if both tools are used on the same system

### Common Operations via Shared Library

Both tools perform similar operations but with different source handling:

**Add operation pattern:**
```python
# minerva-kb: add repo
1. Run repository-doc-extractor -> temp records
2. minerva_common.config_builder.create_index_config(...)
3. minerva_common.minerva_runner.run_index(config)
4. minerva_common.registry.register_collection(type="repo", ...)

# minerva-doc: add docs
1. Validate records exist at path
2. minerva_common.config_builder.create_index_config(...)
3. minerva_common.minerva_runner.run_index(config)
4. minerva_common.registry.register_collection(type="docs", ...)
```

**Shared operations:**
```python
# Both use identical implementations from minerva_common
- list: minerva_common.collection_ops.list_collections()
- status: minerva_common.collection_ops.get_status(name)
- remove: minerva_common.collection_ops.remove_collection(name)
- serve: minerva_common.server_manager.start_server()
```

### Collection Registry Schema

Each tool maintains its own registry with tool-specific metadata:

**minerva-kb registry** (`~/.minerva/apps/minerva-kb/collections.json`):
```json
{
  "collections": {
    "my-repo-kb": {
      "type": "repo",
      "name": "my-repo-kb",
      "source_path": "/Users/me/code/my-repo",
      "chromadb_collection": "my-repo-kb",
      "description": "Code repository documentation",
      "created_at": "2025-12-13T10:00:00Z",
      "indexed_at": "2025-12-13T10:05:00Z"
    }
  }
}
```

**minerva-doc registry** (`~/.minerva/apps/minerva-doc/collections.json`):
```json
{
  "collections": {
    "my-notes": {
      "type": "docs",
      "name": "my-notes",
      "records_path": "/Users/me/notes/records.json",
      "chromadb_collection": "my-notes",
      "description": "Personal notes collection",
      "created_at": "2025-12-13T11:00:00Z",
      "indexed_at": "2025-12-13T11:02:00Z"
    }
  }
}
```

Each registry only tracks collections created by its respective tool. Collections are discovered at serve-time by querying ChromaDB directly.

## Benefits of This Approach

1. **Conceptual clarity**: Each tool has a clear, focused purpose
2. **No asymmetric features**: No confusing "why doesn't watch work?" within a single tool
3. **Clean UX**: Each tool's commands make sense for its domain
4. **Shared infrastructure**: Minimal duplication via common library
5. **Future extensibility**: New source types (S3, Google Docs) get their own focused tools
6. **Preserved identity**: minerva-kb keeps its "fast repo indexing" message

## User Experience

### Adding a Repository
```bash
$ minerva-kb add ~/code/my-project
✓ Detected Git repository: my-project
✓ Extracted 127 documents
✓ Indexed as collection: my-project-kb
✓ Ready to serve

$ minerva-kb watch my-project-kb
👁  Watching /Users/me/code/my-project for changes...
```

### Adding Pre-extracted Docs
```bash
$ minerva-doc add ~/extracted/bear-notes.json \
    --name bear-notes \
    --description "Personal notes from Bear app"
✓ Validated 450 records
✓ Indexed as collection: bear-notes
✓ Ready to serve

# Later, after re-running extractor with new export
$ minerva-doc update bear-notes ~/extracted/bear-notes-new.json
✓ Validated 475 records
✓ Reindexed collection: bear-notes
```

### Serving All Collections
```bash
$ minerva-kb serve
# or
$ minerva-doc serve

ℹ Starting MCP server...
ℹ Collections available:
  - my-project-kb (repo, 127 documents)
  - bear-notes (docs, 475 records)
✓ Server ready at http://127.0.0.1:8337
```

## Next Steps

### Phase 1: Shared Library
1. Create `tools/minerva-common` package
2. Extract common operations from minerva-kb:
   - Registry management
   - Config file generation
   - Subprocess calls to `minerva` CLI
   - Provider setup/validation
   - Serve/list/status/remove logic
3. Update minerva-kb to depend on minerva-common
4. Test that minerva-kb still works with refactored code

### Phase 2: minerva-doc Tool
1. Create `tools/minerva-doc` package structure
2. Implement `add` command (validate + index)
3. Implement `update` command (revalidate + reindex)
4. Import shared operations from minerva-common (list, status, remove, serve)
5. Update registry schema to track collection type
6. Add tests for minerva-doc

### Phase 3: Documentation
1. Create `docs/MINERVA_DOC_GUIDE.md` (parallel to MINERVA_KB_GUIDE.md)
2. Update main README to explain both tools
3. Add examples showing repo + docs workflows
4. Document the shared ~/.minerva infrastructure

### Phase 4: Polish
1. Ensure both tools handle edge cases (missing collections, corrupt registry)
2. Add validation that prevents name collisions
3. Improve error messages when wrong tool is used (e.g., "my-notes is a docs collection, use minerva-doc update")
4. Consider adding `minerva-doc watch` that prints helpful error explaining why it doesn't work
