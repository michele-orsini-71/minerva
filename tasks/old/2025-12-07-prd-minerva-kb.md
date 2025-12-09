# Product Requirements Document: minerva-kb

**Date:** 2025-12-07
**Status:** Draft
**Version:** 1.0

---

## 1. Introduction/Overview

### Problem Statement
Currently, users must run a monolithic setup wizard (`apps/local-repo-kb/setup.py`, 1,277 lines) to create their first Minerva collection. This wizard:
- Is designed for one-time use and lacks lifecycle management capabilities
- Cannot manage multiple collections efficiently
- Mixes setup concerns (package installation) with collection management
- Requires users to manually manage watchers via a separate `minerva-local-watcher` tool
- Provides no way to update, list, or remove collections after creation

Users who want to:
- Add a second repository to their knowledge base
- Change AI providers for an existing collection
- View all indexed collections
- Remove outdated collections

...must manually edit config files, stop processes, and run low-level `minerva` commands.

### Solution
**minerva-kb** is a standalone orchestrator tool that manages the complete lifecycle of repository-based knowledge base collections. It provides a unified CLI for adding, listing, updating, watching, and removing collections while delegating to existing Minerva core commands.

### Goal
Replace the setup wizard and watcher-manager with a single, composable tool that enables users to manage multiple Minerva collections through simple, memorable commands.

---

## 2. Goals

1. **Simplify onboarding**: Reduce setup wizard complexity from 1,277 lines to a thin wrapper calling `minerva-kb add`
2. **Enable multi-collection workflows**: Users can manage 5+ collections without reading documentation
3. **Reduce time-to-second-collection**: From manual config editing (15+ minutes) to single command (<2 minutes)
4. **Maintain plugin architecture**: minerva-kb calls existing tools (`minerva`, extractors, watchers) via subprocess—no reimplementation
5. **Improve discoverability**: Users can explore available collections via `list` and `status` commands
6. **Centralize collection state**: All collection metadata lives in `~/.minerva/apps/minerva-kb/` (rename from `local-repo-kb`)

---

## 3. User Stories

### Primary User: Developer with Local Repositories

**Story 1: Adding First Collection**
> As a new Minerva user, I want to index my first repository with a single command so that I can start using Claude to search my codebase without reading extensive documentation.

**Story 2: Adding Second Collection**
> As a Minerva user who already has one collection, I want to add a second repository to my knowledge base so that Claude can search across multiple projects.

**Story 3: Changing AI Provider**
> As a Minerva user, I want to switch from OpenAI to Ollama for an existing collection so that I can reduce costs and run embeddings locally.

**Story 4: Viewing Collections**
> As a Minerva user with multiple collections, I want to see all my indexed repositories, their providers, and watcher status so that I can understand my current setup at a glance.

**Story 5: Monitoring Collection Health**
> As a Minerva user, I want to check if a specific collection is healthy (indexed, watcher running, embeddings present) so that I can troubleshoot issues.

**Story 6: Manual Re-indexing**
> As a Minerva user, I want to manually trigger re-indexing for a collection after making bulk changes so that my embeddings are up-to-date.

**Story 7: Starting Watcher**
> As a Minerva user, I want to start a file watcher for my collection so that changes are automatically indexed without manual intervention.

**Story 8: Removing Collection**
> As a Minerva user, I want to delete an outdated collection and all its data (configs, embeddings, extracted files) so that I can free up disk space and declutter my setup.

---

## 4. Functional Requirements

### 4.1 Core Commands

#### FR-1: `minerva-kb add <repo-path>`
**Description:** Create a new collection or update an existing collection's AI provider.

**Behavior:**
1. Accept repository path as positional argument
2. Derive collection name from repository folder name (sanitized: lowercase, spaces→hyphens, alphanumeric+hyphens only)
3. **If collection does NOT exist:**
   - Generate description via AI by reading repository README.md or prompting user
   - Prompt for AI provider selection (OpenAI, Gemini, Ollama, LM Studio)
   - Check if API key exists in keychain (for cloud providers)
     - If missing: prompt for key and store via `minerva keychain set PROVIDER_API_KEY`
     - If exists: validate it works (test API call)
   - Create index config at `~/.minerva/apps/minerva-kb/<collection>-index.json`
   - Create watcher config at `~/.minerva/apps/minerva-kb/<collection>-watcher.json`
   - Call `repository-doc-extractor` to extract repository
   - Call `minerva index --config <index-config>` to create embeddings
   - Display success summary with next steps
4. **If collection ALREADY EXISTS:**
   - Detect by checking if watcher config exists for this repository path
   - Display: "Collection '<name>' already exists for this repository"
   - Display: Current AI provider (e.g., "OpenAI gpt-4o-mini + text-embedding-3-small")
   - Prompt: "Change AI provider? [y/N]"
     - **If NO:** Exit with message "No changes made"
     - **If YES:**
       - Prompt for new AI provider selection
       - Check/store API key if needed
       - Update index config with new provider settings
       - Stop running watcher for THIS collection only (match by config path to avoid killing other watchers)
       - Call `repository-doc-extractor` to re-extract
       - Call `minerva index --config <config> --force-recreate` to rebuild embeddings
       - Display: "Collection reindexed with <new-provider>"
       - Display: "Restart watcher with: minerva-kb watch <collection>"

**Exit Codes:**
- 0: Success
- 1: Invalid repository path
- 2: API key validation failed
- 3: Extraction/indexing failed

---

#### FR-2: `minerva-kb list [--format table|json]`
**Description:** Display all managed collections with status information.

**Behavior:**
1. Scan `~/.minerva/apps/minerva-kb/` for `*-watcher.json` files (managed collections)
2. Query ChromaDB to get all collections
3. For each collection, gather:
   - Collection name
   - Repository path (from watcher config)
   - AI provider type, embedding model, LLM model (from index config)
   - Chunk count (from ChromaDB metadata)
   - Watcher status: ✓ Running (PID) | ⚠ Not running | (not in ChromaDB)
   - Last indexed timestamp (from extracted JSON file mtime or ChromaDB metadata)
4. Display in table format (default):
   ```
   Collections (2):

   minerva
     Repository: /Users/michele/my-code/minerva
     Provider: OpenAI (gpt-4o-mini + text-embedding-3-small)
     Chunks: 1,234
     Watcher: ✓ Running (PID 12345)
     Last indexed: 2025-12-07 17:55:23

   my-docs
     Repository: /Users/michele/Documents/docs
     Provider: Ollama (llama3.1:8b + mxbai-embed-large)
     Chunks: 500
     Watcher: ⚠ Not running
     Last indexed: 2025-12-05 10:30:15
   ```
5. Support `--format json` for scripting:
   ```json
   {
     "collections": [
       {
         "name": "minerva",
         "repository_path": "/Users/michele/my-code/minerva",
         "provider": {
           "type": "openai",
           "embedding_model": "text-embedding-3-small",
           "llm_model": "gpt-4o-mini"
         },
         "chunks": 1234,
         "watcher": {
           "status": "running",
           "pid": 12345
         },
         "last_indexed": "2025-12-07T17:55:23Z"
       }
     ]
   }
   ```

**Out-of-Sync State Display:**

**Unmanaged collections** (in ChromaDB, no config files):
```
orphan-collection
  ⚠ Unmanaged (created outside minerva-kb)
  Chunks: 500
  (No config files found)
```

**Broken collections** (has config files, no ChromaDB):
```
broken-collection
  Repository: /Users/michele/code/broken
  ⚠ Not indexed (ChromaDB collection missing)
  Last attempt: Config files exist but collection not found
```

**Normal managed collections:**
Display repository path, provider, chunks, watcher status, last indexed timestamp as shown above

---

#### FR-3: `minerva-kb status <collection-name>`
**Description:** Display detailed status for a specific collection.

**Behavior:**
1. Load watcher config and index config for collection
2. Query ChromaDB for collection metadata
3. Check if watcher process is running (via `ps` + config path grep)
4. Display comprehensive status:
   ```
   Collection: minerva
   Repository: /Users/michele/my-code/minerva

   AI Provider:
     Type: OpenAI
     Embedding: text-embedding-3-small
     LLM: gpt-4o-mini
     API Key: ✓ Stored in keychain as OPENAI_API_KEY

   ChromaDB:
     ✓ Collection exists
     Chunks: 1,234
     Last modified: 2025-12-07 17:55:23

   Configuration Files:
     ✓ Index config: ~/.minerva/apps/minerva-kb/minerva-index.json
     ✓ Watcher config: ~/.minerva/apps/minerva-kb/minerva-watcher.json
     ✓ Extracted data: ~/.minerva/apps/minerva-kb/minerva-extracted.json (1.2 MB)

   Watcher:
     ✓ Running (PID 12345)
     Watch patterns: .md, .mdx, .rst, .txt
     Ignore patterns: .git, node_modules, .venv
   ```
5. If collection doesn't exist, show error with suggestion:
   ```
   ❌ Collection 'foo' not found

   Available collections:
     • minerva
     • my-docs

   Run 'minerva-kb list' to see all collections.
   ```

**Exit Codes:**
- 0: Collection exists and healthy
- 1: Collection not found
- 2: Collection exists but has issues (missing ChromaDB, config mismatch, etc.)

---

#### FR-4: `minerva-kb sync <collection-name>`
**Description:** Manually trigger re-indexing for a collection (without changing AI provider).

**Behavior:**
1. Load index config for collection
2. Get repository path from watcher config
3. Call `repository-doc-extractor <repo> -o <extracted-json>`
4. Call `minerva index --config <index-config>`
5. Display progress and success message
6. Do NOT restart watcher (user might have stopped it intentionally)

**Use case:** User made bulk changes to repository outside of watcher's scope (e.g., git pulled 100 commits while watcher was stopped).

**Exit Codes:**
- 0: Success
- 1: Collection not found
- 2: Extraction failed
- 3: Indexing failed

---

#### FR-5: `minerva-kb watch [<collection-name>]`
**Description:** Start file watcher for a collection (or interactively select one).

**Behavior:**
1. **If `<collection-name>` provided:**
   - Validate collection exists
   - Get watcher config path
   - Check if watcher already running
     - If YES: Display "Watcher already running (PID 12345)" and exit
     - If NO: Continue
   - Call `local-repo-watcher --config <watcher-config>`
   - Display: "▶️ Starting watcher for '<collection>'... Press Ctrl+C to stop."
   - Run watcher in foreground (user can Ctrl+C to stop)

2. **If NO `<collection-name>` provided (interactive mode):**
   - List all collections with watcher configs
   - Prompt user to select one (numbered list)
   - Proceed with selected collection

**Example:**
```bash
# Direct
minerva-kb watch minerva

# Interactive
minerva-kb watch
> Available collections:
>   1. minerva
>   2. my-docs
> Select collection [1-2]: 1
> ▶️ Starting watcher for 'minerva'...
```

**Requirements:**
- `local-repo-watcher` must be installed and available in `$PATH`
- Install via: `pipx install tools/local-repo-watcher`

**Exit Codes:**
- 0: Watcher stopped gracefully (Ctrl+C)
- 1: Collection not found
- 2: `local-repo-watcher` not found in PATH
- 3: Watcher crashed

---

#### FR-6: `minerva-kb remove <collection-name>`
**Description:** Delete collection and all associated data.

**Behavior:**
1. Check if collection is managed by minerva-kb (has config files in `~/.minerva/apps/minerva-kb/`)
   - **If NO config files found but collection exists in ChromaDB (unmanaged):**
     ```
     ❌ Collection 'orphan-collection' is not managed by minerva-kb

     This collection exists in ChromaDB but has no config files in:
       ~/.minerva/apps/minerva-kb/

     To remove it manually:
       minerva remove ~/.minerva/chromadb orphan-collection
     ```
     Exit with code 1

   - **If config files exist but ChromaDB collection missing:**
     ```
     ⚠️  Collection 'broken-collection' not found in ChromaDB

     Config files exist but collection is missing. This may happen if:
       • Indexing failed or was interrupted
       • Collection was manually deleted via 'minerva remove'

     Delete config files anyway? [y/N]:
     ```
     - If YES: Skip to step 6 (delete config files only)
     - If NO: Exit with "Deletion cancelled"

2. Display collection details (via `status` logic)
3. Display warning:
   ```
   ⚠️  This will permanently delete:
     • ChromaDB collection and all embeddings
     • Configuration files (index, watcher)
     • Extracted repository data

   Repository files will NOT be affected.
   ```
4. Prompt for confirmation:
   - "Type YES to confirm deletion: "
   - If input != "YES": Exit with "Deletion cancelled"
5. Stop running watcher (if any):
   - Find watcher process via `ps aux | grep <config-path>`
   - Send SIGTERM, wait for graceful shutdown
6. Delete files:
   - `~/.minerva/apps/minerva-kb/<collection>-watcher.json`
   - `~/.minerva/apps/minerva-kb/<collection>-index.json`
   - `~/.minerva/apps/minerva-kb/<collection>-extracted.json`
7. Delete ChromaDB collection:
   - Call `minerva remove <chromadb-path> <collection-name>` with auto-confirmation
8. Display success:
   ```
   ✓ Collection 'minerva' deleted

   API keys remain in keychain (other collections may use them).
   To remove: minerva keychain delete OPENAI_API_KEY
   ```

**Exit Codes:**
- 0: Success
- 1: Collection not found
- 2: User cancelled
- 3: Failed to delete ChromaDB collection
- 130: Ctrl+C during operation

---

### 4.2 Collection Naming Rules

#### FR-7: Automatic Collection Naming
**Description:** Collection names are derived from repository folder names, not user-prompted.

**Rules:**
1. Take repository folder name (e.g., `/Users/michele/my-code/My Cool Project` → `My Cool Project`)
2. Convert to lowercase: `my cool project`
3. Replace spaces with hyphens: `my-cool-project`
4. Remove non-alphanumeric characters (except hyphens): keep only `[a-z0-9-]`
5. Ensure name starts and ends with alphanumeric (trim leading/trailing hyphens)
6. Validate length: 3-512 characters (ChromaDB requirement)

**Examples:**
- `/code/minerva` → `minerva`
- `/code/My Cool Project` → `my-cool-project`
- `/code/React_Component-Library` → `react_component-library`
- `/code/project-123` → `project-123`

**Rationale:**
- User always knows the collection name (it's the folder name)
- Enables intuitive queries: "Search the minerva collection for..."
- Eliminates "what did I name this?" confusion
- Enforces 1:1 mapping between repository and collection

**Conflict Resolution:**

When derived collection name already exists in ChromaDB but has no config files in `~/.minerva/apps/minerva-kb/` (created outside minerva-kb):

```
minerva-kb add ~/code/minerva

❌ Collection 'minerva' already exists in ChromaDB

This collection was not created by minerva-kb (no config files found).
It may have been created manually via 'minerva index'.

Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]:
```

**Behavior:**
- **Choice 1**: Exit with error code 1, display available collection names via `minerva-kb list`
- **Choice 2**: Call `minerva remove <chromadb-path> <collection-name>` with auto-confirmation, then proceed with normal `add` flow

**Note:** This is a **technical limitation** of sharing a single ChromaDB instance. Users must either accept the wipe or manually rename their existing collection.

---

### 4.3 AI Provider Management

#### FR-8: Provider Selection Flow
**Description:** Interactive menu for selecting AI provider during `add` operation.

**Menu:**
```
Which AI provider do you want to use?

  1. OpenAI (cloud, requires API key)
     • Default embedding: text-embedding-3-small
     • Default LLM: gpt-4o-mini

  2. Google Gemini (cloud, requires API key)
     • Default embedding: text-embedding-004
     • Default LLM: gemini-1.5-flash

  3. Ollama (local, free, no API key)
     • You specify which models you've pulled

  4. LM Studio (local, free, no API key)
     • You specify which models you've loaded

Choice [1-4]:
```

**For cloud providers (1-2):**
1. Check if API key exists in keychain using hardcoded names:
   - OpenAI → `OPENAI_API_KEY`
   - Gemini → `GEMINI_API_KEY`
2. If missing: Call `minerva keychain set <KEY_NAME>` (interactive prompt)
3. If exists: Validate with test API call
4. If validation fails: Prompt to re-enter key
5. **Model customization:**
   ```
   Use default models? [Y/n]:
   ```
   - If **YES** (or just Enter): Use default models shown in menu
   - If **NO**: Prompt for custom models:
     ```
     Embedding model (text-embedding-3-small): <user enters custom model>
     LLM model (gpt-4o-mini): <user enters custom model>
     ```
   - Show confirmation:
     ```
     ✓ Selected: OpenAI
       • Embedding: text-embedding-3-large
       • LLM: gpt-4o
     ```

**For local providers (3-4):**
1. Ollama: Prompt for embedding model (default: `mxbai-embed-large:latest`) and LLM model (default: `llama3.1:8b`)
2. LM Studio: Prompt for embedding model (required) and LLM model (required)
3. Validate service is running:
   - Ollama: Check `http://localhost:11434/api/tags`
   - LM Studio: Check `http://localhost:1234/v1/models`
4. If not running: Display instructions and retry prompt

---

#### FR-9: Provider Update (Change Provider)
**Description:** When updating an existing collection's provider, handle index recreation.

**Behavior:**
1. Display current provider:
   ```
   Current provider: OpenAI (gpt-4o-mini + text-embedding-3-small)
   Change AI provider? [y/N]:
   ```
2. If YES:
   - Run same provider selection flow as FR-9
   - Update index config with new provider settings
   - **Important:** Stop watcher before re-indexing (prevents conflicts)
   - Call extraction and indexing with `--force-recreate` flag
   - Display: "⚠️ Watcher stopped. Restart with: minerva-kb watch <collection>"
3. If NO:
   - Exit with: "No changes made"

**Rationale:** Changing embedding model requires full re-indexing because embeddings are incompatible across models.

---

### 4.4 Repository Uniqueness Enforcement

#### FR-10: One Collection Per Repository
**Description:** Enforce 1:1 mapping between repository paths and collections.

**Rules:**
1. When user runs `minerva-kb add <repo-path>`, derive collection name from folder
2. Check if watcher config already exists for this exact repository path (resolved absolute path comparison)
3. If exists: Enter "update provider" flow (FR-10)
4. If not exists: Enter "create new collection" flow (FR-1)

**No support for:**
- Multiple collections from same repository with different names
- Multiple watchers on same repository
- Renaming collections (must `remove` + `add`)

**Rationale:**
- Simplifies mental model (1 repo = 1 collection)
- Avoids watcher conflicts
- Reduces configuration complexity
- Name is predictable (folder name)

---

### 4.5 Configuration Management

#### FR-11: Configuration File Structure
**Description:** All configuration files live in `~/.minerva/apps/minerva-kb/` (renamed from `local-repo-kb`).

**File naming:**
- Index config: `<collection-name>-index.json`
- Watcher config: `<collection-name>-watcher.json`
- Extracted data: `<collection-name>-extracted.json`
- Shared server config: `server.json` (used by all collections)

**Index config schema:**
```json
{
  "chromadb_path": "/Users/michele/.minerva/chromadb",
  "collection": {
    "name": "minerva",
    "description": "Python RAG system with vector search...",
    "json_file": "/Users/michele/.minerva/apps/minerva-kb/minerva-extracted.json",
    "chunk_size": 1200
  },
  "provider": {
    "provider_type": "openai",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini",
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

**Watcher config schema:**
```json
{
  "repository_path": "/Users/michele/my-code/minerva",
  "collection_name": "minerva",
  "extracted_json_path": "/Users/michele/.minerva/apps/minerva-kb/minerva-extracted.json",
  "index_config_path": "/Users/michele/.minerva/apps/minerva-kb/minerva-index.json",
  "debounce_seconds": 60.0,
  "include_extensions": [".md", ".mdx", ".markdown", ".rst", ".txt"],
  "ignore_patterns": [".git", "node_modules", ".venv", "__pycache__"]
}
```

---

#### FR-12: ChromaDB Path
**Description:** All collections share a single ChromaDB instance.

**Path:** `~/.minerva/chromadb/`

**Rationale:**
- Single source of truth for embeddings
- Simplifies backup (one directory)
- Enables future "list all ChromaDB collections" features

---

### 4.6 Watcher Integration

#### FR-13: Watcher Lifecycle Management
**Description:** minerva-kb manages watcher processes, replacing `local-repo-watcher-manager`.

**Start watcher:**
- Command: `minerva-kb watch <collection>`
- Calls: `local-repo-watcher --config <watcher-config>`
- Runs in foreground (user presses Ctrl+C to stop)

**Stop watcher:**
- Automatic during `remove` operation
- Automatic before `add --change-provider` re-indexing
- Manual: User presses Ctrl+C in `watch` foreground process

**Check watcher status:**
- Scan processes: `ps aux | grep local-repo-watcher | grep <config-path>`
- Extract PID for display in `list` and `status`

**Do NOT:**
- Run watchers as background daemons (out of scope for MVP)
- Auto-start watchers after `add` (user controls when to start)
- Implement systemd/launchd service files (future enhancement)

---

### 4.7 Migration from Old Setup

#### FR-14: No Migration Required
**Description:** There are no existing users of `apps/local-repo-kb/setup.py`, so no migration tooling is needed.

**Setup wizard transition:**
1. Slim down `apps/local-repo-kb/setup.py` to only:
   - Check prerequisites (Python, pipx)
   - Install Minerva core via pipx
   - Install extractors via pipx
   - Install minerva-kb via pipx
2. At end of setup, display:
   ```
   ✅ Installation complete!

   Next step: Create your first collection

   Run: minerva-kb add /path/to/your/repository

   This will:
     • Generate a description from your README
     • Prompt for AI provider selection
     • Index your repository
     • Create a searchable knowledge base

   After adding a collection, configure Claude Desktop:
   See: apps/minerva-kb/README.md
   ```

**Future:** If users are detected in `~/.minerva/apps/local-repo-kb/`, display a one-time migration notice on first run.

---

## 5. Non-Goals (Out of Scope)

### Phase 1 Exclusions

1. **Multi-type collections**: No support for `--type zim`, `--type bear`, `--type markdown-book`
   - **Rationale:** Focus on repository collections only. Document as future enhancement.
   - **Workaround:** Users can manually create non-repo collections via `minerva index`

2. **MCP server management**: No `minerva-kb serve` command
   - **Rationale:** MCP server is shared across all collections (single `server.json`)
   - **Workaround:** Users configure Claude Desktop manually (one-time setup)

3. **Claude Desktop config editing**: No auto-updating `claude_desktop_config.json`
   - **Rationale:** Out of scope for collection lifecycle management
   - **Workaround:** Provide copy-paste config snippet in `add` success message

4. **Collection renaming**: No `minerva-kb rename <old> <new>` command
   - **Rationale:** Collection name = repo folder name (immutable)
   - **Workaround:** `remove` + `add` if repo is renamed

5. **Batch operations**: No `minerva-kb sync --all` or `minerva-kb watch --all`
   - **Rationale:** Users manage collections individually for fine-grained control
   - **Future:** Could add in Phase 2 based on user feedback

6. **Remote repository support**: No support for watching GitHub repos without local clone
   - **Rationale:** Out of scope for "local" kb management
   - **Future:** Separate `minerva-remote-kb` tool for HTTP-based workflows

7. **Watcher daemon mode**: No `minerva-kb watch <collection> --daemon`
   - **Rationale:** Systemd/launchd integration requires OS-specific implementation
   - **Workaround:** Users can run `nohup minerva-kb watch <collection> &` manually

8. **Resume after failure**: No `--resume` flag for partial operation recovery
   - **Rationale:** Complex state machine, diminishing returns
   - **Workaround:** Re-run `add` (re-indexing takes <2 minutes for most repos)

9. **API key rotation**: No `minerva-kb rotate-key <provider>` command
   - **Rationale:** `minerva keychain set OPENAI_API_KEY` already handles this
   - **Workaround:** User updates via keychain, then runs `sync` if needed

10. **Collection export/import**: No backup/restore functionality
    - **Rationale:** ChromaDB and config files can be backed up via standard filesystem tools
    - **Future:** Could add `minerva-kb export/import` for portability

---

## 6. Design Considerations

### 6.1 User Experience

**Interactive First, Scriptable Second:**
- Default behavior: Interactive prompts (friendly for beginners)
- Support `--format json` on read operations for scripting
- Support `--yes` flag on destructive operations to skip confirmations (future)

**Memorable Command Names:**
- `add` (not `create` or `new`)
- `list` (not `ls` or `show`)
- `status` (not `info` or `describe`)
- `sync` (not `reindex` or `update`)
- `watch` (not `start-watcher` or `monitor`)
- `remove` (not `delete` or `rm`)

**Consistent Output:**
- Use ✓, ⚠️, ❌ symbols for visual status (CLI mode)
- Prefix logs with timestamps in verbose mode
- Display config paths relative to `~/.minerva/` for readability

**Error Messages:**
- Always suggest next action ("Run 'minerva-kb list' to see...")
- Show available options when user input is invalid
- Use exit codes consistently (0=success, 1=not found, 2=validation, 3=operation failed)

---

### 6.2 Architecture

**Delegation Over Reimplementation:**
- Call existing CLIs via `subprocess.run()`:
  - `minerva index --config <path>`
  - `minerva remove <chromadb> <collection>`
  - `minerva keychain set <key>`
  - `repository-doc-extractor <repo> -o <json>`
  - `local-repo-watcher --config <path>`
- Do NOT import minerva modules directly (maintain tool independence)

**Configuration as Source of Truth:**
- Derive all state from config files and ChromaDB
- No central metadata database (reduces sync issues)
- Watcher config existence = "is this repo managed?"
- ChromaDB presence = "is collection indexed?"

**Process Management:**
- Use `ps aux` to detect running watchers (portable across Unix systems)
- Use `os.kill(pid, signal.SIGTERM)` for graceful shutdown
- Do NOT use process managers (systemd, supervisor, etc.) in Phase 1

---

### 6.3 Security

**API Key Handling:**
- Never log or display API keys (show "✓ Stored in keychain" instead)
- Validate keys via test API calls before storing
- Store in OS keychain via `minerva keychain` (encrypted storage)
- Reference in configs as `${OPENAI_API_KEY}` (environment variable expansion)

**File Permissions:**
- Config files: `0600` (user read/write only)
- Extracted JSON: `0600` (may contain sensitive code snippets)
- ChromaDB directory: `0700` (user-only access)

---

## 7. Technical Considerations

### 7.1 Dependencies

**Required at Runtime:**
- Python 3.10+ (core language)
- `minerva` (core CLI, installed via pipx)
- `repository-doc-extractor` (extractor, installed via pipx)
- `local-repo-watcher` (watcher, installed via pipx)

**Optional (for specific providers):**
- Ollama service (for local embeddings)
- LM Studio app (for local embeddings)
- API keys in keychain (for cloud providers)

**Installation:**
```bash
# From minerva repo root
pipx install .                                    # minerva core
pipx install extractors/repository-doc-extractor  # extractor
pipx install tools/local-repo-watcher             # watcher
pipx install tools/minerva-kb                     # orchestrator (this tool)
```

---

### 7.2 Package Structure

**Location:** `tools/minerva-kb/`

**Directory layout:**
```
tools/minerva-kb/
├── minerva_kb/
│   ├── __init__.py
│   ├── cli.py                 # Main entry point (argparse)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── add.py             # FR-1
│   │   ├── list.py            # FR-2
│   │   ├── status.py          # FR-3
│   │   ├── sync.py            # FR-4
│   │   ├── watch.py           # FR-5
│   │   ├── edit.py            # FR-6
│   │   └── remove.py          # FR-7
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── collection_naming.py   # FR-8 (sanitization)
│   │   ├── provider_selection.py  # FR-9 (interactive menu)
│   │   ├── config_loader.py       # Read/write configs
│   │   ├── process_manager.py     # Watcher process detection
│   │   └── chromadb_query.py      # Query ChromaDB metadata
│   └── constants.py           # Paths, provider key names
├── setup.py
├── README.md
└── tests/
    ├── test_add.py
    ├── test_list.py
    ├── test_status.py
    └── ...
```

**Entry point in `setup.py`:**
```python
entry_points={
    'console_scripts': [
        'minerva-kb=minerva_kb.cli:main',
    ],
}
```

---

### 7.3 Provider Key Name Constants

**Hardcoded mapping (not discoverable):**
```python
# minerva_kb/constants.py
PROVIDER_KEY_NAMES = {
    'openai': 'OPENAI_API_KEY',
    'gemini': 'GEMINI_API_KEY',
}

PROVIDER_DISPLAY_NAMES = {
    'openai': 'OpenAI',
    'gemini': 'Google Gemini',
    'ollama': 'Ollama',
    'lmstudio': 'LM Studio',
}
```

**API key check logic:**
```python
def check_api_key_exists(provider_type: str) -> bool:
    key_name = PROVIDER_KEY_NAMES.get(provider_type)
    if not key_name:
        return True  # Local provider (ollama/lmstudio), no key needed

    result = subprocess.run(
        ['minerva', 'keychain', 'get', key_name],
        capture_output=True,
        text=True
    )
    return result.returncode == 0
```

---

### 7.4 Collection Name Sanitization

**Reference implementation:**
```python
import re
from pathlib import Path

def sanitize_collection_name(repo_path: Path) -> str:
    """
    Derive collection name from repository folder name.

    Rules:
    - Lowercase
    - Spaces → hyphens
    - Keep only [a-z0-9-]
    - Trim leading/trailing hyphens
    - 3-512 chars (ChromaDB requirement)

    Examples:
        /code/minerva → "minerva"
        /code/My Cool Project → "my-cool-project"
        /code/React_Component-Library → "react-component-library"
    """
    folder_name = repo_path.name
****
    # Lowercase
    name = folder_name.lower()

    # Replace spaces and underscores with hyphens
    name = name.replace(' ', '-').replace('_', '-')

    # Keep only alphanumeric and hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)

    # Collapse multiple consecutive hyphens
    name = re.sub(r'-+', '-', name)

    # Strip leading/trailing hyphens
    name = name.strip('-')

    # Validate length
    if len(name) < 3:
        raise ValueError(f"Collection name too short: '{name}' (minimum 3 characters)")
    if len(name) > 512:
        raise ValueError(f"Collection name too long: {len(name)} chars (maximum 512)")

    return name
```

---

### 7.5 Watcher Process Detection

**Reference implementation:**
```python
import subprocess
from pathlib import Path
from typing import Optional

def find_watcher_pid(config_path: Path) -> Optional[int]:
    """
    Find PID of local-repo-watcher process using this config.

    Returns:
        PID if running, None if not found
    """
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    search_term = str(config_path)

    for line in result.stdout.splitlines():
        if 'local-repo-watcher' not in line:
            continue
        if search_term not in line:
            continue

        # Extract PID (second column in ps aux output)
        parts = line.split()
        if len(parts) < 2:
            continue

        try:
            return int(parts[1])
        except ValueError:
            continue

    return None
```

---

## 8. Success Metrics

### Quantitative Metrics

1. **Time to Second Collection**
   - **Baseline:** 15+ minutes (manual config editing, stopping watchers, running commands)
   - **Target:** <2 minutes (single `minerva-kb add` command)
   - **Measurement:** Time from "I want to add a second repo" to "embeddings ready"

2. **Setup Wizard Complexity**
   - **Baseline:** 1,277 lines of Python
   - **Target:** <200 lines (prerequisites check + delegation to minerva-kb)
   - **Measurement:** Line count of `apps/local-repo-kb/setup.py`

3. **Collection Management Discoverability**
   - **Baseline:** 0% (no `list` command exists)
   - **Target:** 80% of users run `minerva-kb list` within first week
   - **Measurement:** Telemetry (if added) or user surveys

### Qualitative Metrics

1. **New User Onboarding**
   - **Success criteria:** Junior developer can add second collection without reading docs
   - **Test method:** User testing with 3 junior devs, observe task completion

2. **Error Recovery**
   - **Success criteria:** Failed `add` operation leaves no orphaned state
   - **Test method:** Ctrl+C during indexing, verify no partial configs exist

3. **Mental Model Simplicity**
   - **Success criteria:** Users understand "1 repo = 1 collection = folder name"
   - **Test method:** User interviews, ask "how would you add a third collection?"

---

## 9. Open Questions

### 9.1 Watcher Manager Package Deprecation

**Question:** Should we delete `tools/local-repo-watcher-manager/` immediately or deprecate gracefully?

**Options:**
- **A)** Delete package, update docs to point to `minerva-kb watch` (clean break)
- **B)** Keep package, print deprecation warning redirecting to `minerva-kb watch`
- **C)** Keep as alias (minerva-local-watcher calls minerva-kb watch internally)

**Recommendation:** Option A (no existing users, clean break)

---

### 9.2 Server Config Management

**Question:** Should `minerva-kb` manage the shared `server.json` config?

**Current behavior:**
- `apps/local-repo-kb/setup.py` creates `server.json` on first run
- All collections share this single config

**Options:**
- **A)** minerva-kb creates `server.json` if missing (on first `add`)
- **B)** minerva-kb assumes `server.json` exists (setup wizard creates it)
- **C)** minerva-kb has `init` command to create directory structure

**Recommendation:** Option A (auto-create with defaults if missing)

---

### 9.3 Collection Description Update

**Question:** Should users be able to update collection description without changing provider?

**Use case:** User improves README, wants to regenerate description to match.

**Options:**
- **A)** Add `minerva-kb update-description <collection>` command
- **B)** User edits `<collection>-index.json` manually via `minerva-kb edit`
- **C)** Not supported in Phase 1 (use `edit` command)

**Recommendation:** Option C (defer to Phase 2 based on user demand)

---

### 9.4 Partial Indexing Failures

**Question:** If indexing partially succeeds (e.g., 80% of chunks indexed before crash), should we keep partial state?

**Current behavior:** `minerva index` is atomic (all-or-nothing via transactions)

**Edge case:** Very large repos (100k+ files) where indexing takes 30+ minutes

**Options:**
- **A)** Trust minerva core's transaction handling (Phase 1)
- **B)** Add progress tracking and resume support (Phase 2+)

**Recommendation:** Option A (rely on ChromaDB's transaction guarantees)

---

### 9.5 Unmanaged Collection Handling

**Question:** Should `minerva-kb list` show collections created manually via `minerva index`?

**Scenario:** User ran `minerva index --config my-custom-config.json` outside of minerva-kb

**Options:**
- **A)** Show all ChromaDB collections, mark managed vs. unmanaged
- **B)** Only show collections with watcher configs in `apps/minerva-kb/`
- **C)** Add `--all` flag to include unmanaged collections

**Recommendation:** Option A (FR-2 already specifies this behavior)

---

### 9.6 Testing Strategy

**Question:** What level of integration testing is required before Phase 1 launch?

**Test coverage needed:**
- Unit tests for collection naming, provider selection, config parsing
- Integration tests for full `add` → `list` → `sync` → `remove` workflow
- E2E tests with real ChromaDB and file extraction
- Manual testing with all 5 AI providers

**Options:**
- **A)** Unit tests only (fast CI, manual E2E before release)
- **B)** Unit + integration tests (slower CI, automated E2E)
- **C)** Full test pyramid including E2E in CI

**Recommendation:** Option B (balance speed and confidence)

---

### 9.7 Documentation Location

**Question:** Where should minerva-kb documentation live?

**Options:**
- **A)** `tools/minerva-kb/README.md` (package-specific)
- **B)** `docs/MINERVA_KB_GUIDE.md` (centralized docs)
- **C)** Both (README for quickstart, docs for comprehensive guide)

**Recommendation:** Option C (README for installation, docs/ for full guide)

---

## 10. Acceptance Criteria

### Phase 1 Complete When:

1. ✅ User can run `minerva-kb add /path/to/repo` and get a working collection
2. ✅ User can run `minerva-kb list` and see all collections with status
3. ✅ User can run `minerva-kb status <collection>` and see detailed health info
4. ✅ User can run `minerva-kb sync <collection>` to manually re-index
5. ✅ User can run `minerva-kb watch <collection>` to start file watcher
6. ✅ User can run `minerva-kb edit <collection>` to modify advanced settings
7. ✅ User can run `minerva-kb remove <collection>` to delete everything
8. ✅ `apps/local-repo-kb/setup.py` is slimmed to <200 lines and delegates to minerva-kb
9. ✅ `tools/local-repo-watcher-manager/` is deprecated/removed
10. ✅ All commands have `--help` text with examples
11. ✅ Unit tests achieve >80% code coverage
12. ✅ Integration tests verify full add→remove workflow
13. ✅ Documentation exists in `tools/minerva-kb/README.md` and `docs/MINERVA_KB_GUIDE.md`
14. ✅ User can add second collection in <2 minutes

---

## 11. Implementation Phases

### Phase 1: Core Commands (Weeks 1-2)
- Implement `add` command (FR-1, FR-9, FR-10, FR-11)
- Implement `list` command (FR-2)
- Implement `remove` command (FR-7)
- Unit tests for collection naming (FR-8)
- Integration tests for add→list→remove

### Phase 2: Observability (Week 3)
- Implement `status` command (FR-3)
- Implement `sync` command (FR-4)
- Improve `list` output formatting
- Add `--format json` support

### Phase 3: Watcher Integration (Week 4)
- Implement `watch` command (FR-5, FR-14)
- Merge local-repo-watcher-manager functionality
- Test watcher lifecycle (start, stop, status check)
- Deprecate watcher-manager package

### Phase 4: Polish & Documentation (Week 5)
- Implement `edit` command (FR-6)
- Write comprehensive README
- Update setup wizard to delegate to minerva-kb
- User testing with 3 participants
- Bug fixes and UX improvements

---

## 12. Timeline

**Target Launch:** End of Week 5 (January 2026)

**Milestones:**
- Week 1: Core commands (`add`, `list`, `remove`) functional
- Week 2: Unit tests passing, basic integration test
- Week 3: Observability commands (`status`, `sync`) working
- Week 4: Watcher integration complete, manager deprecated
- Week 5: Documentation, polish, user testing, launch

**Dependencies:**
- No blockers (all tools already exist)
- Assumes 1 full-time developer

---

## Appendix A: Example Workflows

### Workflow 1: First-Time Setup
```bash
# User has just installed Minerva via setup wizard
# Setup wizard ends with message: "Run: minerva-kb add /path/to/repo"

$ minerva-kb add ~/code/my-project

📚 Collection Name
==================
Derived from repository folder name: my-project

💬 Collection Description
==========================
📄 Found README.md in repository
🤖 Generating optimized description from README...

✨ Generated description:
   Python web framework with REST API, GraphQL support, and comprehensive
   documentation. Best for questions about API design, code architecture,
   testing strategies, component interactions, and deployment workflows.

✓ Description ready

🤖 AI Provider Selection
=========================
Which AI provider do you want to use?

  1. OpenAI (cloud, requires API key)
     • Default embedding: text-embedding-3-small
     • Default LLM: gpt-4o-mini

  2. Google Gemini (cloud, requires API key)
     • Default embedding: text-embedding-004
     • Default LLM: gemini-1.5-flash

  3. Ollama (local, free, no API key)

  4. LM Studio (local, free, no API key)

Choice [1-4]: 1

🔑 API Key Configuration
=========================
Your OpenAI API key will be stored securely in OS keychain.
The key will be stored as: 'OPENAI_API_KEY'

Enter your OpenAI API key: sk-proj-xxxxx...

🔍 Validating API key...
✓ OpenAI API key is valid and working

🎯 Model Selection
==================
Use default models? [Y/n]: Y

✓ Selected: OpenAI
  • Embedding: text-embedding-3-small
  • LLM: gpt-4o-mini

📂 Creating configuration files...
✓ Created: ~/.minerva/apps/minerva-kb/my-project-index.json
✓ Created: ~/.minerva/apps/minerva-kb/my-project-watcher.json

🔍 Extracting and Indexing
============================
📚 Extracting repository contents...
✓ Extraction complete: 245 files processed

🔍 Indexing collection...
⏳ Generating embeddings... (this may take a few minutes)
✓ Indexed 1,234 chunks

✅ Collection 'my-project' created successfully!

📝 Next Steps
==============
1. Configure Claude Desktop to use this collection
   (See: apps/minerva-kb/README.md for instructions)

2. Start the file watcher (optional but recommended):
   minerva-kb watch my-project

3. Test by asking Claude:
   "Search the my-project collection for API documentation"
```

---

### Workflow 2: Adding Second Collection
```bash
$ minerva-kb add ~/code/internal-docs

📚 Collection Name
==================
Derived from repository folder name: internal-docs

💬 Collection Description
==========================
ℹ️  No README.md found in repository
Please describe what's in this repository.

Brief description: Company internal documentation for infrastructure and deployment

🤖 Generating optimized description...

✨ Generated description:
   Company internal documentation covering infrastructure setup, deployment
   procedures, and system administration. Best for questions about setup
   procedures, configuration, troubleshooting, deployment workflows, and
   infrastructure architecture.

🤖 AI Provider Selection
=========================
✓ Using existing OpenAI API key from keychain

Which AI provider do you want to use?

  1. OpenAI (current: gpt-4o-mini)
  2. Google Gemini
  3. Ollama
  4. LM Studio

Choice [1-5]: 4

✓ Selected: Ollama (local)

📝 Ollama Model Configuration
-------------------------------
Embedding model (mxbai-embed-large:latest):
LLM model (llama3.1:8b):

🔍 Validating AI provider availability...
✓ Ollama is running and accessible

📂 Creating configuration files...
✓ Created: ~/.minerva/apps/minerva-kb/internal-docs-index.json
✓ Created: ~/.minerva/apps/minerva-kb/internal-docs-watcher.json

🔍 Extracting and Indexing
============================
📚 Extracting repository contents...
✓ Extraction complete: 87 files processed

🔍 Indexing collection...
✓ Indexed 456 chunks

✅ Collection 'internal-docs' created successfully!

📝 Next Steps
==============
Start the file watcher:
  minerva-kb watch internal-docs

View all collections:
  minerva-kb list
```

---

### Workflow 3: Changing AI Provider
```bash
$ minerva-kb add ~/code/my-project

⚠️  Collection 'my-project' already exists for this repository

Current provider: OpenAI (gpt-4o-mini + text-embedding-3-small)
Change AI provider? [y/N]: y

🤖 AI Provider Selection
=========================
Which AI provider do you want to use?

  1. OpenAI (current)
  2. Google Gemini
  3. Ollama
  4. LM Studio

Choice [1-4]: 2

🔑 API Key Configuration
=========================
Your Gemini API key will be stored securely in OS keychain.
The key will be stored as: 'GEMINI_API_KEY'

Enter your Gemini API key: xxxxx...

🔍 Validating API key...
✓ Gemini API key is valid and working

🎯 Model Selection
==================
Use default models? [Y/n]: n

Embedding model (text-embedding-004): text-embedding-004
LLM model (gemini-1.5-flash): gemini-1.5-pro

✓ Selected: Gemini
  • Embedding: text-embedding-004
  • LLM: gemini-1.5-pro

📝 Updating configuration...
✓ Updated index config with new provider

⏸️  Stopping watcher (PID 12345)...
✓ Watcher stopped

🔍 Re-indexing with new provider...
📚 Extracting repository contents...
✓ Extraction complete

🔍 Indexing collection...
✓ Indexed 1,234 chunks

✅ Collection 'my-project' reindexed with Ollama

⚠️  Watcher stopped during re-indexing
Restart with: minerva-kb watch my-project
```

---

### Workflow 4: Listing Collections
```bash
$ minerva-kb list

Collections (3):

my-project
  Repository: /Users/michele/code/my-project
  Provider: Ollama (llama3.1:8b + mxbai-embed-large:latest)
  Chunks: 1,234
  Watcher: ✓ Running (PID 45678)
  Last indexed: 2025-12-07 18:30:15

internal-docs
  Repository: /Users/michele/code/internal-docs
  Provider: Ollama (llama3.1:8b + mxbai-embed-large:latest)
  Chunks: 456
  Watcher: ⚠ Not running
  Last indexed: 2025-12-07 17:22:45

company-kb
  Repository: /Users/michele/Documents/company-kb
  Provider: OpenAI (gpt-4o-mini + text-embedding-3-small)
  Chunks: 789
  Watcher: ✓ Running (PID 45690)
  Last indexed: 2025-12-06 09:15:30
```

---

### Workflow 5: Checking Collection Status
```bash
$ minerva-kb status my-project

Collection: my-project
Repository: /Users/michele/code/my-project

AI Provider:
  Type: Ollama
  Embedding: mxbai-embed-large:latest
  LLM: llama3.1:8b
  Base URL: http://localhost:11434

ChromaDB:
  ✓ Collection exists
  Chunks: 1,234
  Last modified: 2025-12-07 18:30:15

Configuration Files:
  ✓ Index config: ~/.minerva/apps/minerva-kb/my-project-index.json
  ✓ Watcher config: ~/.minerva/apps/minerva-kb/my-project-watcher.json
  ✓ Extracted data: ~/.minerva/apps/minerva-kb/my-project-extracted.json (1.8 MB)

Watcher:
  ✓ Running (PID 45678)
  Watch patterns: .md, .mdx, .rst, .txt
  Ignore patterns: .git, node_modules, .venv, __pycache__
```

---

### Workflow 6: Removing Collection
```bash
$ minerva-kb remove my-project

Collection: my-project
Repository: /Users/michele/code/my-project
Provider: Ollama (llama3.1:8b)
Chunks: 1,234

⚠️  This will permanently delete:
  • ChromaDB collection and all embeddings
  • Configuration files (index, watcher)
  • Extracted repository data

Repository files will NOT be affected.

Type YES to confirm deletion: YES

🧹 Removing collection 'my-project'...

⏸️  Stopping watcher (PID 45678)...
✓ Watcher stopped

📂 Deleting configuration files...
✓ Deleted: ~/.minerva/apps/minerva-kb/my-project-watcher.json
✓ Deleted: ~/.minerva/apps/minerva-kb/my-project-index.json
✓ Deleted: ~/.minerva/apps/minerva-kb/my-project-extracted.json

🗄️  Deleting ChromaDB collection...
✓ Deleted collection 'my-project' from ChromaDB

✅ Collection 'my-project' deleted

API keys remain in keychain (other collections may use them).
To remove: minerva keychain delete OPENAI_API_KEY
```

---

### Workflow 7: Handling Collection Name Conflicts
```bash
$ minerva-kb add ~/code/minerva

📚 Collection Name
==================
Derived from repository folder name: minerva

❌ Collection 'minerva' already exists in ChromaDB

This collection was not created by minerva-kb (no config files found).
It may have been created manually via 'minerva index'.

Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]: 1

❌ Collection creation aborted

Existing collections in ChromaDB:
  • minerva (unmanaged - created outside minerva-kb)
  • my-project (managed)
  • docs (managed)

To use a different name, rename the repository folder or manually:
  1. Remove existing collection: minerva remove ~/.minerva/chromadb minerva
  2. Try again: minerva-kb add ~/code/minerva
```

**Alternative: User chooses to wipe and recreate**
```bash
Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]: 2

⚠️  Deleting existing collection 'minerva' from ChromaDB...
✓ Collection deleted

💬 Collection Description
==========================
# ... continues with normal add flow ...
```

---

## Appendix B: Error Handling Examples

### Error: Repository Path Invalid
```bash
$ minerva-kb add /nonexistent/path

❌ Repository path does not exist: /nonexistent/path

Please provide a valid directory path.
```

### Error: API Key Validation Failed
```bash
$ minerva-kb add ~/code/project

# ... provider selection ...
Choice [1-5]: 1

Enter your OpenAI API key: sk-invalid-key

🔍 Validating API key...
❌ Failed to connect to OpenAI: Invalid API key

Possible issues:
  • API key is invalid or expired
  • No internet connection
  • API service is down

Try again with a different API key? [y/N]: n

⚠️  Setup cancelled
```

### Error: Ollama Not Running
```bash
$ minerva-kb add ~/code/project

# ... provider selection ...
Choice [1-5]: 4

🔍 Validating AI provider availability...
❌ Cannot connect to Ollama at http://localhost:11434

Please start Ollama before continuing:
  ollama serve

Retry connection? [y/N]: n

⚠️  Setup cancelled
```

### Error: Collection Not Found
```bash
$ minerva-kb status nonexistent

❌ Collection 'nonexistent' not found

Available collections:
  • my-project
  • internal-docs

Run 'minerva-kb list' to see all collections.
```

### Error: Watcher Already Running
```bash
$ minerva-kb watch my-project

⚠️  Watcher already running for 'my-project' (PID 45678)

To stop the watcher, find the process and terminate it:
  kill 45678
```

---

### Error: Collection Name Already Exists
```bash
$ minerva-kb add ~/code/minerva

📚 Collection Name
==================
Derived from repository folder name: minerva

❌ Collection 'minerva' already exists in ChromaDB

This collection was not created by minerva-kb (no config files found).
It may have been created manually via 'minerva index'.

Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]:
```

---

### Error: Trying to Remove Unmanaged Collection
```bash
$ minerva-kb remove orphan-collection

❌ Collection 'orphan-collection' is not managed by minerva-kb

This collection exists in ChromaDB but has no config files in:
  ~/.minerva/apps/minerva-kb/

To remove it manually:
  minerva remove ~/.minerva/chromadb orphan-collection
```
