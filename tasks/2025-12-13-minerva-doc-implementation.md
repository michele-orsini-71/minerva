# minerva-doc Implementation Task List

Implementation tracking for PRD: `2025-12-13-prd-minerva-doc.md`

**Status**: In progress
**Started**: 2025-12-14
**Completed**: [Date TBD]

---

## Phase 1: Shared Library (minerva-common)

### Task 1.1: Create minerva-common Package Structure
- [x] Create `tools/minerva-common/` directory
- [x] Create `tools/minerva-common/src/minerva_common/` directory
- [x] Create `tools/minerva-common/tests/` directory
- [x] Create `tools/minerva-common/setup.py` with package metadata
- [x] Create `tools/minerva-common/README.md` with library overview
- [x] Create `tools/minerva-common/requirements.txt`

### Task 1.2: Implement paths.py
- [x] Create `src/minerva_common/paths.py`
- [x] Define `HOME_DIR` constant
- [x] Define `MINERVA_DIR` constant (`~/.minerva`)
- [x] Define `CHROMADB_DIR` constant (`~/.minerva/chromadb`)
- [x] Define `SERVER_CONFIG_PATH` constant (`~/.minerva/server.json`)
- [x] Define `APPS_DIR` constant (`~/.minerva/apps`)

### Task 1.3: Implement init.py
- [x] Create `src/minerva_common/init.py`
- [x] Implement `ensure_shared_dirs()` function
  - [x] Create `.minerva/` if not exists
  - [x] Create `chromadb/` if not exists
  - [x] Set permissions 0o700 on directories
  - [x] Handle PermissionError gracefully
- [x] Implement `ensure_server_config()` function
  - [x] Check if `server.json` exists
  - [x] Return (path, False) if exists
  - [x] Create default config if not exists
  - [x] Use atomic write (temp file + replace)
  - [x] Set permissions 0o600 on file
  - [x] Return (path, True) if created
- [x] Write unit tests for `ensure_shared_dirs()`
- [x] Write unit tests for `ensure_server_config()`

### Task 1.4: Implement registry.py
- [x] Create `src/minerva_common/registry.py`
- [x] Implement `Registry` class
  - [x] `__init__(registry_path: Path)`
  - [x] `load() -> dict` - load registry from JSON
  - [x] `save(data: dict) -> None` - save registry with atomic write
  - [x] `add_collection(name: str, metadata: dict) -> None`
  - [x] `get_collection(name: str) -> dict | None`
  - [x] `update_collection(name: str, metadata: dict) -> None`
  - [x] `remove_collection(name: str) -> None`
  - [x] `list_collections() -> list[dict]`
  - [x] `collection_exists(name: str) -> bool`
- [x] Write unit tests for Registry class

### Task 1.5: Implement config_builder.py
- [x] Create `src/minerva_common/config_builder.py`
- [x] Implement `build_index_config()` function
  - [x] Accept parameters: collection_name, json_file, chromadb_path, provider, description, chunk_size, force_recreate
  - [x] Generate index config dict matching minerva's schema
  - [x] Return config dict
- [x] Implement `save_index_config()` function
  - [x] Accept config dict and output path
  - [x] Use atomic write (temp file + replace)
  - [x] Set permissions 0o600
- [x] Write unit tests for config building

### Task 1.6: Implement minerva_runner.py
- [x] Create `src/minerva_common/minerva_runner.py`
- [x] Implement `run_validate()` function
  - [x] Accept json_file path
  - [x] Run `minerva validate` via subprocess
  - [x] Capture stdout/stderr
  - [x] Return (success: bool, output: str)
- [x] Implement `run_index()` function
  - [x] Accept config_path
  - [x] Run `minerva index --config` via subprocess
  - [x] Stream output to user
  - [x] Use timeout (default 600s)
  - [x] Return (success: bool, output: str)
- [x] Implement `run_serve()` function
  - [x] Accept server_config_path
  - [x] Run `minerva serve --config` via subprocess
  - [x] Handle server lifecycle
  - [x] Return subprocess handle
- [x] Write unit tests (mocked subprocess calls)

### Task 1.7: Implement provider_setup.py
- [x] Create `src/minerva_common/provider_setup.py`
- [x] Implement `select_provider_interactive()` function
  - [x] Prompt for provider type (OpenAI, Gemini, Ollama, LM Studio)
  - [x] Prompt for embedding model (with defaults per provider)
  - [x] Prompt for LLM model (with defaults per provider)
  - [x] Validate API keys if needed (cloud providers)
  - [x] Return provider config dict
- [x] Implement `validate_provider_config()` function
  - [x] Check required fields are present
  - [x] Validate API keys exist in environment if needed
  - [x] Return (valid: bool, error: str | None)
- [x] Write unit tests for provider selection

### Task 1.8: Implement description_generator.py
- [x] Create `src/minerva_common/description_generator.py`
- [x] Implement `generate_description_from_records()` function
  - [x] Accept json_file path and provider config
  - [x] Sample representative records (e.g., first 10-20)
  - [x] Format prompt for AI: "Generate a concise description for this collection..."
  - [x] Call AI provider's LLM
  - [x] Return generated description
- [x] Implement `prompt_for_description()` function
  - [x] Display: "Collection description (press Enter to auto-generate):"
  - [x] If user enters text: return it
  - [x] If empty: call `generate_description_from_records()`
  - [x] Show generated description
  - [x] Confirm with user: "Use this description? (Y/n)"
  - [x] Return final description
- [x] Write unit tests (mocked AI calls)

### Task 1.9: Implement server_manager.py
- [x] Create `src/minerva_common/server_manager.py`
- [x] Implement `start_server()` function
  - [x] Load server.json config
  - [x] Call `run_serve()` from minerva_runner
  - [x] Display available collections (query ChromaDB)
  - [x] Show server URL and port
  - [x] Return subprocess handle
- [x] Write unit tests

### Task 1.10: Implement collection_ops.py
- [x] Create `src/minerva_common/collection_ops.py`
- [x] Implement `list_chromadb_collections()` function
  - [x] Connect to ChromaDB
  - [x] Query all collections
  - [x] Return list with metadata (name, count)
- [x] Implement `remove_chromadb_collection()` function
  - [x] Connect to ChromaDB
  - [x] Delete collection by name
  - [x] Handle errors gracefully
- [x] Implement `get_collection_count()` function
  - [x] Connect to ChromaDB
  - [x] Get chunk count for collection
  - [x] Return count or None
- [x] Write unit tests (mocked ChromaDB)

### Task 1.11: Implement collision detection
- [x] Create `src/minerva_common/collision.py`
- [x] Implement `check_collection_exists()` function
  - [x] Accept collection name
  - [x] Check ChromaDB for existing collection
  - [x] Check minerva-kb registry if exists (`~/.minerva/apps/minerva-kb/`)
  - [x] Check minerva-doc registry if exists (`~/.minerva/apps/minerva-doc/`)
  - [x] Return (exists: bool, owner: str | None) where owner is "minerva-kb", "minerva-doc", or None
- [x] Write unit tests

### Task 1.12: Package minerva-common
- [x] Install minerva-common in development mode: `pip install -e tools/minerva-common`
- [x] Verify all modules import correctly
- [x] Run full test suite: `pytest tools/minerva-common/tests`
- [x] Ensure all tests pass

### Task 1.13: Refactor minerva-kb to use minerva-common
- [x] Update `tools/minerva-kb/pyproject.toml` to include minerva-common
- [x] Replace `constants.py` imports with `minerva_common.paths`
- [x] Replace `ensure_server_config()` with `minerva_common.init.ensure_server_config()`
- [x] Update `serve` command to use `minerva_common.server_manager`
- [x] Install minerva-kb in development mode
- [x] Run minerva-kb test suite: 42 passing, 25 failing (integration tests need updates)
- [x] Fix integration tests (test failures due to architectural change: server config moved to shared location)
- [x] Replace provider selection logic with `minerva_common.provider_setup` (deferred - separate refactoring)
- [x] Update collision checks to use `minerva_common.collision.check_collection_exists()` (deferred - will implement in minerva-doc)
- [x] Test minerva-kb commands manually (add, list, serve, remove)

### Task 1.14: Fix pipx packaging for minerva-common dependency
**Problem**: minerva-kb depends on minerva-common (local library), but pipx only installs CLI applications, not libraries. When pipx tried to install minerva-kb, pip couldn't find minerva-common on PyPI and installation failed.

**Solution**: Use `pipx inject` to bundle minerva-common into minerva-kb's isolated venv (like static linking in C or bundling in JS).

**Implementation**:
- [x] Remove `minerva-common` from minerva-kb's `dependencies` in pyproject.toml
- [x] Add comment explaining minerva-common is injected, not a pip dependency
- [x] Update `tools/minerva-kb/install.sh`:
  - [x] Install minerva-kb first (without minerva-common dependency)
  - [x] Inject minerva-common into minerva-kb's venv: `pipx inject minerva-kb /path/to/minerva-common`
- [x] Update `tools/minerva-kb/uninstall.sh` (minerva-common auto-removed with minerva-kb)
- [x] Test installation: `./tools/minerva-kb/uninstall.sh && ./tools/minerva-kb/install.sh`
- [x] Verify minerva-common is bundled: `pipx runpip minerva-kb list | grep minerva-common`
- [x] Verify minerva-kb works: `minerva-kb --version`

**Key learnings**:
- pipx is for applications (with CLI entry points), not libraries (no entry points)
- `pipx inject` is the standard way to add library dependencies to pipx-installed apps
- minerva-common is shared code, but NOT a separate PyPI package - it's bundled into each tool that needs it
- When minerva-doc is implemented, use the same pattern: `pipx install minerva-doc` then `pipx inject minerva-doc /path/to/minerva-common`

---

## Phase 2: minerva-doc Tool

### Task 2.1: Create minerva-doc Package Structure
- [x] Create `tools/minerva-doc/` directory
- [x] Create `tools/minerva-doc/src/minerva_doc/` directory
- [x] Create `tools/minerva-doc/src/minerva_doc/commands/` directory
- [x] Create `tools/minerva-doc/src/minerva_doc/utils/` directory
- [x] Create `tools/minerva-doc/tests/` directory
- [x] Create `tools/minerva-doc/pyproject.toml` with package metadata
- [x] Create `tools/minerva-doc/README.md`
- [x] Create `tools/minerva-doc/requirements.txt` (include minerva-common)

### Task 2.2: Implement constants and paths
- [x] Create `src/minerva_doc/constants.py`
- [x] Import shared paths from minerva_common.paths
- [x] Define `MINERVA_DOC_APP_DIR = APPS_DIR / "minerva-doc"`
- [x] Define `COLLECTIONS_REGISTRY_PATH = MINERVA_DOC_APP_DIR / "collections.json"`

### Task 2.3: Implement app initialization
- [x] Create `src/minerva_doc/utils/init.py`
- [x] Implement `ensure_app_dir()` function
  - [x] Call `minerva_common.init.ensure_shared_dirs()`
  - [x] Create `apps/minerva-doc/` if not exists
  - [x] Set permissions 0o700
  - [x] Return app dir path
- [x] Implement `ensure_registry()` function
  - [x] Create empty collections.json if not exists
  - [x] Use atomic write
  - [x] Set permissions 0o600
- [x] Write unit tests

### Task 2.4: Implement CLI entry point
- [x] Create `src/minerva_doc/cli.py`
- [x] Set up argparse with subcommands: add, update, list, status, remove, serve
- [x] Implement main() function
- [x] Add console_scripts entry point in pyproject.toml: `minerva-doc = minerva_doc.cli:main`

### Task 2.5: Implement add command
- [x] Create `src/minerva_doc/commands/add.py`
- [x] Implement `run_add()` function
  - [x] Parse arguments: json_file, --name
  - [x] Validate json_file exists and is readable
  - [x] Check collection name collision (use minerva_common.collision)
  - [x] Run `minerva validate` on json_file
  - [x] Prompt for AI provider selection
  - [x] Prompt for collection description (with auto-generate option)
  - [x] Build index config (use minerva_common.config_builder)
  - [x] Save index config to temp file
  - [x] Run `minerva index` via subprocess
  - [x] Register collection in collections.json
  - [x] Display success message
  - [x] Clean up temp config file
- [ ] Write integration tests

### Task 2.6: Implement update command
- [ ] Create `src/minerva_doc/commands/update.py`
- [ ] Implement `run_update()` function
  - [ ] Parse arguments: collection_name, json_file
  - [ ] Look up collection in registry
  - [ ] Error if not found: "Collection not managed by minerva-doc"
  - [ ] Validate new json_file
  - [ ] Prompt: "Change AI provider? (current: [provider])"
  - [ ] If provider change: set force_recreate=true, re-prompt for description
  - [ ] If provider unchanged: use existing description, force_recreate=false
  - [ ] Build index config with updated settings
  - [ ] Save index config to temp file
  - [ ] Run `minerva index` via subprocess
  - [ ] Update registry (indexed_at timestamp, records_path)
  - [ ] Display success message with diff stats
  - [ ] Clean up temp config file
- [ ] Write integration tests

### Task 2.7: Implement list command
- [ ] Create `src/minerva_doc/commands/list.py`
- [ ] Implement `run_list()` function
  - [ ] Parse arguments: --format (table|json)
  - [ ] Query ChromaDB for all collections
  - [ ] Load collections.json registry
  - [ ] Identify managed vs unmanaged collections
  - [ ] Format output (table or JSON)
  - [ ] Display managed collections with full details
  - [ ] Display unmanaged collections with warning
- [ ] Write integration tests

### Task 2.8: Implement status command
- [ ] Create `src/minerva_doc/commands/status.py`
- [ ] Implement `run_status()` function
  - [ ] Parse arguments: collection_name
  - [ ] Look up collection in registry
  - [ ] Error if not found
  - [ ] Query ChromaDB for chunk count
  - [ ] Display detailed info: name, description, provider, chunks, dates
- [ ] Write integration tests

### Task 2.9: Implement remove command
- [ ] Create `src/minerva_doc/commands/remove.py`
- [ ] Implement `run_remove()` function
  - [ ] Parse arguments: collection_name
  - [ ] Look up collection in registry
  - [ ] If not in registry: check ChromaDB and error with helpful message
  - [ ] Prompt for confirmation
  - [ ] Remove from ChromaDB
  - [ ] Remove from registry
  - [ ] Remove generated config files
  - [ ] Display success message
- [ ] Write integration tests

### Task 2.10: Implement serve command
- [ ] Create `src/minerva_doc/commands/serve.py`
- [ ] Implement `run_serve()` function
  - [ ] Call `minerva_common.server_manager.start_server()`
  - [ ] Display collections available (managed + unmanaged)
  - [ ] Show server URL/port
  - [ ] Keep server running until interrupt
- [ ] Write integration tests

### Task 2.11: Package minerva-doc
- [ ] Install minerva-doc in development mode: `pip install -e tools/minerva-doc`
- [ ] Verify CLI is accessible: `minerva-doc --help`
- [ ] Run full test suite: `pytest tools/minerva-doc/tests`
- [ ] Ensure all tests pass

### Task 2.12: End-to-End Testing
- [ ] Test complete workflow:
  - [ ] `minerva-doc add test.json --name test`
  - [ ] `minerva-doc list`
  - [ ] `minerva-doc status test`
  - [ ] `minerva-doc update test test-updated.json`
  - [ ] `minerva-doc serve` (start and verify collections visible)
  - [ ] `minerva-doc remove test`
- [ ] Test collision prevention:
  - [ ] Create collection with minerva-kb
  - [ ] Try to create same name with minerva-doc (should error)
- [ ] Test cross-tool visibility:
  - [ ] Create collection with minerva-kb
  - [ ] Run `minerva-doc list` (should show as unmanaged)
  - [ ] Run `minerva-doc serve` (should expose both collections)

---

## Phase 3: Collision Prevention in minerva-kb

### Task 3.1: Update minerva-kb add command
- [ ] Modify `tools/minerva-kb/src/minerva_kb/commands/add.py`
- [ ] Before extraction, call `minerva_common.collision.check_collection_exists()`
- [ ] If collection exists, error with message: "Collection '[name]' already exists"
- [ ] Display owner info if available
- [ ] Write test for collision detection

### Task 3.2: Test collision prevention
- [ ] Create doc collection with minerva-doc
- [ ] Try to create repo with same name in minerva-kb (should error)
- [ ] Verify error message is helpful

---

## Phase 4: Documentation & Polish

### Task 4.1: Write MINERVA_DOC_GUIDE.md
- [ ] Create `docs/MINERVA_DOC_GUIDE.md`
- [ ] Write introduction for beginners
- [ ] Write "What is minerva-doc?" section
- [ ] Write "When to use minerva-doc vs minerva-kb" section
- [ ] Write installation instructions
- [ ] Write quick start guide (<2 min to first collection)
- [ ] Write complete command reference
  - [ ] add command with examples
  - [ ] update command with examples
  - [ ] list command with examples
  - [ ] status command with examples
  - [ ] remove command with examples
  - [ ] serve command with examples
- [ ] Write examples section:
  - [ ] Bear notes workflow
  - [ ] Zim dumps workflow
  - [ ] Markdown books workflow
- [ ] Write troubleshooting section
  - [ ] Common errors and solutions
  - [ ] FAQ
- [ ] Write advanced usage section
  - [ ] Provider selection tips
  - [ ] Description best practices
  - [ ] Multi-collection management

### Task 4.2: Update main README.md
- [ ] Add minerva-doc overview to README
- [ ] Add "Tools Ecosystem" section explaining:
  - [ ] minerva (core CLI)
  - [ ] minerva-kb (repo orchestrator)
  - [ ] minerva-doc (doc orchestrator)
- [ ] Add quick comparison table: minerva-kb vs minerva-doc
- [ ] Update directory structure diagram
- [ ] Add links to MINERVA_KB_GUIDE.md and MINERVA_DOC_GUIDE.md
- [ ] Update installation instructions

### Task 4.3: Create MINERVA_COMMON.md
- [ ] Create `docs/MINERVA_COMMON.md`
- [ ] Write architecture overview
- [ ] Document shared infrastructure (`~/.minerva/` structure)
- [ ] Document each module:
  - [ ] paths.py API reference
  - [ ] init.py API reference
  - [ ] registry.py API reference
  - [ ] config_builder.py API reference
  - [ ] minerva_runner.py API reference
  - [ ] provider_setup.py API reference
  - [ ] description_generator.py API reference
  - [ ] server_manager.py API reference
  - [ ] collection_ops.py API reference
  - [ ] collision.py API reference
- [ ] Explain how both tools consume the library
- [ ] Add examples of using minerva-common directly

### Task 4.4: Improve error messages
- [ ] Review all error messages in minerva-doc
- [ ] Ensure wrong-tool errors are helpful (e.g., "Use minerva-kb for repo collections")
- [ ] Ensure missing dependency errors are clear
- [ ] Ensure permission errors have guidance
- [ ] Add suggestions to all error messages

### Task 4.5: Add comprehensive help text
- [ ] Add `--help` text for main command
- [ ] Add `--help` text for each subcommand
- [ ] Include examples in help text
- [ ] Test help text formatting and clarity

### Task 4.6: Write comprehensive tests
- [ ] Ensure >80% code coverage for minerva-common
- [ ] Ensure >80% code coverage for minerva-doc
- [ ] Add edge case tests:
  - [ ] Empty JSON files
  - [ ] Malformed JSON
  - [ ] Missing permissions
  - [ ] ChromaDB connection failures
  - [ ] Invalid provider configs
  - [ ] Name collision edge cases
- [ ] Add performance tests (indexing speed)

### Task 4.7: Final integration testing
- [ ] Test on clean system (fresh `~/.minerva/`)
- [ ] Test with both tools installed
- [ ] Test with only minerva-doc installed
- [ ] Test upgrade scenario (existing minerva-kb collections)
- [ ] Test all example workflows from documentation
- [ ] Verify all help text is accurate
- [ ] Check for typos and formatting issues

### Task 4.8: Run full test suite
- [ ] Run `pytest tools/minerva-common/tests -v --cov`
- [ ] Run `pytest tools/minerva-kb/tests -v --cov`
- [ ] Run `pytest tools/minerva-doc/tests -v --cov`
- [ ] Verify all tests pass
- [ ] Verify coverage meets targets (>80%)

---

## Relevant Files

### Created Files
- `tools/minerva-common/` - Shared library package (Task 1.1 ✓)
- `tools/minerva-common/setup.py` - Package metadata and dependencies (Task 1.1 ✓)
- `tools/minerva-common/README.md` - Library overview and documentation (Task 1.1 ✓)
- `tools/minerva-common/requirements.txt` - Package dependencies (Task 1.1 ✓)
- `tools/minerva-common/src/minerva_common/__init__.py` - Package initialization (Task 1.1 ✓)
- `tools/minerva-common/src/minerva_common/paths.py` - Shared path constants (Task 1.2 ✓)
- `tools/minerva-common/src/minerva_common/init.py` - Infrastructure initialization (Task 1.3 ✓)
- `tools/minerva-common/tests/__init__.py` - Test package initialization (Task 1.3 ✓)
- `tools/minerva-common/tests/test_init.py` - Unit tests for init module (Task 1.3 ✓)
- `tools/minerva-common/src/minerva_common/registry.py` - Collection registry management (Task 1.4 ✓)
- `tools/minerva-common/tests/test_registry.py` - Unit tests for registry module (Task 1.4 ✓)
- `tools/minerva-common/src/minerva_common/config_builder.py` - Index config generation (Task 1.5 ✓)
- `tools/minerva-common/tests/test_config_builder.py` - Unit tests for config_builder module (Task 1.5 ✓)
- `tools/minerva-common/src/minerva_common/minerva_runner.py` - Subprocess wrapper for minerva CLI (Task 1.6 ✓)
- `tools/minerva-common/tests/test_minerva_runner.py` - Unit tests for minerva_runner module (Task 1.6 ✓)
- `tools/minerva-common/src/minerva_common/provider_setup.py` - AI provider selection (Task 1.7 ✓)
- `tools/minerva-common/tests/test_provider_setup.py` - Unit tests for provider_setup module (Task 1.7 ✓)
- `tools/minerva-common/src/minerva_common/description_generator.py` - AI description generation (Task 1.8 ✓)
- `tools/minerva-common/tests/test_description_generator.py` - Unit tests for description_generator module (Task 1.8 ✓)
- `tools/minerva-common/src/minerva_common/server_manager.py` - MCP server management (Task 1.9 ✓)
- `tools/minerva-common/tests/test_server_manager.py` - Unit tests for server_manager module (Task 1.9 ✓)
- `tools/minerva-common/src/minerva_common/collection_ops.py` - ChromaDB operations (Task 1.10 ✓)
- `tools/minerva-common/tests/test_collection_ops.py` - Unit tests for collection_ops module (Task 1.10 ✓)
- `tools/minerva-common/src/minerva_common/collision.py` - Collection name collision detection (Task 1.11 ✓)
- `tools/minerva-common/tests/test_collision.py` - Unit tests for collision module (Task 1.11 ✓)
- `tools/minerva-doc/` - Document orchestrator package
- `tools/minerva-doc/src/minerva_doc/cli.py` - CLI entry point
- `tools/minerva-doc/src/minerva_doc/commands/add.py` - Add command implementation
- `tools/minerva-doc/src/minerva_doc/commands/update.py` - Update command implementation
- `tools/minerva-doc/src/minerva_doc/commands/list.py` - List command implementation
- `tools/minerva-doc/src/minerva_doc/commands/status.py` - Status command implementation
- `tools/minerva-doc/src/minerva_doc/commands/remove.py` - Remove command implementation
- `tools/minerva-doc/src/minerva_doc/commands/serve.py` - Serve command implementation
- `docs/MINERVA_DOC_GUIDE.md` - Complete guide for minerva-doc
- `docs/MINERVA_COMMON.md` - Shared library documentation

### Modified Files
- `tools/minerva-kb/src/minerva_kb/constants.py` - Updated to use minerva_common.paths
- `tools/minerva-kb/src/minerva_kb/commands/add.py` - Uses shared provider + collision detection logic across tools
- `tools/minerva-kb/src/minerva_kb/commands/serve.py` - Refactored to use minerva_common
- `tools/minerva-kb/pyproject.toml` - Removed minerva-common from dependencies (now injected via pipx)
- `tools/minerva-kb/install.sh` - Updated to use `pipx inject` for bundling minerva-common into minerva-kb's venv
- `tools/minerva-kb/uninstall.sh` - Removed minerva-common (auto-removed when minerva-kb is uninstalled)
- `README.md` - Added minerva-doc overview and tool ecosystem explanation
- `tools/minerva-kb/tests/conftest.py` - Test harness patches shared paths for minerva-common integration
- `tools/minerva-kb/tests/test_add_command_integration.py` - Validates '-kb' naming, provider reuse, and cross-tool collision handling
- `tools/minerva-kb/tests/test_remove_command_integration.py` - Validated removal flows with sanitized collection names
- `tools/minerva-kb/tests/test_watch_command_integration.py` - Ensured watcher tests target sanitized collection identifiers
- `tools/minerva-kb/tests/test_sync_command_integration.py` - Synced reindex tests with new collection naming scheme
- `tools/minerva-kb/tests/test_status_command_integration.py` - Adjusted status checks for '-kb' names and shared config
- `tools/minerva-kb/tests/test_list_command_integration.py` - Reflected sanitized names in list output assertions
- `tools/minerva-kb/tests/test_e2e_workflow.py` - Updated end-to-end scenarios for renamed collections
- `tools/minerva-kb/src/minerva_kb/utils/provider_selection.py` - Delegates provider selection to minerva-common with keychain/env bridging
- `tools/minerva-kb/src/minerva_kb/utils/description_generator.py` - Resolved provider API keys via env vars or keychain for shared config
- `tools/minerva-kb/tests/test_provider_selection.py` - Covers new provider selection wrapper behavior
- `tools/minerva-kb/tests/conftest.py` - Patches minerva-common helpers for shared collision detection
