# Product Requirements Document: Minervium Refactoring

## Introduction/Overview

This PRD outlines the refactoring of the "search-markdown-notes" project into **Minervium**, a unified personal knowledge management RAG (Retrieval-Augmented Generation) system. The project currently suffers from inconsistent naming conventions, scattered entry points, and unclear architectural boundaries between core functionality and data extraction tools.

The refactoring will transform the codebase into a well-organized, developer-friendly tool with:
- A unified CLI interface under the `minervium` command
- Clear separation between core RAG functionality and independent extractor tools
- Standardized JSON schema for note ingestion
- Professional package structure ready for future expansion

**Problem Statement:** Current naming inconsistencies (`bear-notes-`, `markdown-notes-`, `zim-articles-` prefixes), verbose console commands, and tightly coupled components make the system difficult to use and extend. The refactoring addresses these issues while maintaining all existing functionality.

## Goals

1. **Unify CLI Interface:** Consolidate all core functionality under a single `minervium` command with intuitive subcommands (`index`, `serve`, `peek`, `validate`)

2. **Establish Clear Architecture:** Separate core RAG/MCP functionality from independent extractor tools through a standardized JSON contract

3. **Improve Developer Experience:** Create consistent naming conventions, clear entry points, and professional package structure using argparse

4. **Enable Extensibility:** Design extractor architecture that allows developers to build custom extractors in any programming language

5. **Maintain Backward Compatibility:** Preserve existing JSON schema and ChromaDB functionality to ensure smooth migration

6. **Complete Professional Documentation:** Provide comprehensive guides for users, extractor developers, and AI assistants

## User Stories

### Core User - Personal Knowledge Manager

**As a personal knowledge management user**, I want to:
- Install Minervium with a single pip command
- Index my notes using `minervium index --config index-config.json` (where config specifies the JSON file path and AI provider)
- Start the MCP server with `minervium serve --config server-config.json` (where config specifies ChromaDB path and settings)
- Inspect my collections with `minervium peek collection_name`
- **So that** I can efficiently manage and search my personal knowledge base without wrestling with complex CLI commands

### Extractor User - Bear Notes User

**As a Bear notes user**, I want to:
- Install Bear extractor separately: `pip install -e extractors/bear-notes-extractor`
- Extract notes with `bear-extractor backup.bear2bk -o notes.json`
- Validate the complete pipeline setup with `minervium validate --config config.json` before indexing
- **So that** I can convert my Bear notes into a searchable knowledge base using independent tools

### Extractor Developer - Custom Integration Builder

**As a developer building a custom extractor**, I want to:
- Understand the JSON schema specification from clear documentation
- Build extractors in any language (Python, Go, Rust, JavaScript)
- Test my complete pipeline setup with `minervium validate --config config.json`
- Use example extractors as reference implementations
- **So that** I can integrate any data source with Minervium without modifying core code

### Multi-Source User - Knowledge Aggregator

**As a user with multiple knowledge sources**, I want to:
- Extract from different sources: Bear notes, Zim articles, markdown books
- Index each source into separate collections with different AI providers
- Query all collections through a single MCP server
- **So that** I can build a comprehensive personal knowledge system from diverse sources

## Functional Requirements

### FR1: Unified Core Package Structure

**FR1.1** The system MUST create a single `minervium` Python package containing all core functionality

**FR1.2** The package MUST organize code into logical subpackages:
- `minervium/commands/` - CLI command implementations
- `minervium/indexing/` - RAG pipeline (chunking, embeddings, storage)
- `minervium/server/` - MCP server functionality
- `minervium/common/` - Shared utilities (AI provider, config, logging, schemas)

**FR1.3** The package MUST expose a single entry point `minervium` via setup.py console_scripts

**FR1.4** The package MUST use argparse for CLI framework (per user requirement)

### FR2: CLI Command Interface

**FR2.1** The system MUST implement `minervium index` command that:
- Requires `--config` flag with configuration file path (config contains JSON file path, chunk size, provider settings, etc.)
- Supports `--verbose` flag for detailed progress output
- Supports `--dry-run` flag for configuration validation without processing
- Validates JSON schema before processing
- Shows provider initialization, chunking, embedding, and storage progress

**FR2.2** The system MUST implement `minervium serve` command that:
- Requires `--config` flag with server configuration file path (config contains chromadb_path, default_max_results, etc.)
- Starts the MCP server in stdio mode
- Auto-discovers collections from ChromaDB path specified in config
- Validates AI provider availability for each collection
- Logs collection availability status
- Config file format: JSON with required fields `chromadb_path` (absolute path) and `default_max_results` (integer)

**FR2.3** The system MUST implement `minervium peek` command that:
- Accepts collection name as positional argument
- Accepts optional `--chromadb` flag for database path
- Accepts optional `--format` flag (table or json output, default: table)
- Displays collection metadata, document count, provider info, and embedding dimensions
- Uses formatted table output for readability

**FR2.4** The system MUST implement `minervium validate` command that:
- Requires `--config` flag with configuration file path
- Accepts optional `--verbose` flag for detailed validation output
- Internally calls the same logic as `minervium index --config --dry-run` (comprehensive validation)
- Implementation note: Can be implemented as a simple wrapper that sets dry_run=True and calls the index command
- Validates the entire pipeline configuration:
  - Config file structure and required fields
  - JSON file path exists and is valid schema
  - AI provider availability (API keys, Ollama running, models available)
  - ChromaDB path is writable
  - Collection name validity
  - Notes schema compliance (all required fields, correct types)
- Provides detailed validation report showing what was checked
- Exits with code 0 for valid configuration, 1 for any validation failures
- Provides clear error messages with actionable troubleshooting steps

### FR3: File Reorganization

**FR3.1** The system MUST migrate RAG pipeline files:
- `chunk_creator.py` → `minervium/indexing/chunking.py`
- `embedding.py` → `minervium/indexing/embeddings.py`
- `storage.py` → `minervium/indexing/storage.py`
- `json_loader.py` → `minervium/indexing/json_loader.py`

**FR3.2** The system MUST migrate MCP server files:
- `server.py` → `minervium/server/mcp_server.py`
- `search_tools.py` → `minervium/server/search_tools.py`
- `collection_discovery.py` → `minervium/server/collection_discovery.py`
- `context_retrieval.py` → `minervium/server/context_retrieval.py`
- `startup_validation.py` → `minervium/server/startup_validation.py`

**FR3.3** The system MUST migrate shared components:
- `ai_provider.py` → `minervium/common/ai_provider.py`
- `config.py` → `minervium/common/config.py`
- `console_logger.py` → `minervium/common/logger.py`

**FR3.4** The system MUST create new files:
- `minervium/common/schemas.py` - JSON schema definition
- `minervium/cli.py` - Main CLI entry point with argparse
- `minervium/__init__.py` - Package initialization
- `minervium/__main__.py` - Enable `python -m minervium` execution

**FR3.5** All import paths MUST be updated to reflect the new `minervium.*` structure

**FR3.6** The codebase MUST be tested for circular dependency issues

### FR4: Extractor Independence

**FR4.1** Extractors MUST be reorganized into `extractors/` directory as independent packages:
- `extractors/bear-notes-extractor/`
- `extractors/zim-extractor/`
- `extractors/markdown-books-extractor/`

**FR4.2** Each extractor package MUST include:
- Standalone CLI entry point (no Minervium imports)
- Independent setup.py with console_scripts entry point
- README.md with usage instructions
- tests/ directory

**FR4.3** Extractor CLI commands MUST follow naming pattern: `{source}-extractor`
- Bear extractor: `bear-extractor`
- Zim extractor: `zim-extractor`
- Books extractor: `markdown-books-extractor`

**FR4.4** Extractors MUST output JSON conforming to the Minervium schema:
```json
[
  {
    "title": "string",
    "markdown": "string",
    "size": integer,
    "modificationDate": "ISO 8601 UTC timestamp string"
  }
]
```

**FR4.5** Extractors MUST NOT depend on Minervium core package (no coupling)

**FR4.6** Extractors MUST support output to file (`-o` flag) or stdout

**FR4.7** Extractors SHOULD support verbose mode (`-v` flag) for progress output

### FR5: JSON Schema Contract

**FR5.1** The system MUST define a strict JSON schema for note ingestion with required fields:
- `title` (string): Note title
- `markdown` (string): Full markdown content
- `size` (integer): Content size in bytes
- `modificationDate` (string): ISO 8601 UTC timestamp

**FR5.2** The schema definition MUST be centralized in `minervium/common/schemas.py`

**FR5.3** The schema MUST be validated by `minervium/indexing/json_loader.py` during indexing

**FR5.4** The schema MUST be validated by `minervium validate` command

**FR5.5** Schema validation errors MUST provide clear messages indicating which note and field failed validation

### FR6: Documentation

**FR6.1** The system MUST provide a comprehensive main README.md covering:
- Minervium overview and architecture
- Quick start guide
- Installation instructions with both pipx (recommended) and pip+alias methods
- Clear explanation that venv activation is not needed after initial setup
- Installation verification steps (`minervium --help`)
- Extractor installation instructions
- Basic usage examples
- Architecture diagram showing separation of concerns
- Link to extractor development guide

**FR6.2** The system MUST provide `docs/NOTE_SCHEMA.md` documenting:
- Complete JSON schema specification
- Field requirements and constraints
- Validation rules
- Example valid/invalid JSON

**FR6.3** The system MUST provide `docs/EXTRACTOR_GUIDE.md` covering:
- Step-by-step extractor creation tutorial
- JSON schema specification reference
- Example extractors walkthrough
- Multi-language examples (Python, Go, Rust, JavaScript)
- Testing guidelines using `minervium validate --config` to verify complete pipeline setup

**FR6.4** The system MUST provide `extractors/README.md` covering:
- Overview of all official extractors
- How to build custom extractors
- Link to extractor development guide
- Emphasis on language-agnostic approach

**FR6.5** Each extractor package MUST include its own README.md with:
- Usage instructions
- Supported file formats
- Installation steps
- Examples
- Output format reference (link to schema docs)

**FR6.6** The system MUST update CLAUDE.md with:
- New directory structure
- Updated command examples using `minervium` CLI
- Extractor development section
- Updated troubleshooting guide
- Removal of old component references

**FR6.7** The system MUST update CONFIGURATION_GUIDE.md with:
- Updated config file paths
- Updated command examples
- Multi-collection setup guide

### FR7: Testing

**FR7.1** The system MUST implement unit tests using pytest for:
- JSON schema validation logic
- CLI command parsing
- Import path validation
- Schema enforcement

**FR7.2** Integration tests are NOT required for initial release:
- The system components are simple enough that unit tests provide sufficient coverage
- Mocking AI providers and ChromaDB for integration tests adds complexity without significant value
- Manual end-to-end testing will verify workflows work correctly

**FR7.3** All tests MUST pass before considering migration complete

**FR7.4** Test coverage SHOULD exceed 70% for core package

**FR7.5** Each extractor package SHOULD include its own test suite

### FR8: Installation and Package Configuration

**FR8.1** The system MUST support two installation methods to avoid virtual environment activation issues:

**Primary Method: pipx (Recommended)**
- Users install pipx once: `pip install --user pipx && pipx ensurepath`
- Install Minervium: `pipx install -e /path/to/minervium`
- Commands work globally without venv activation: `minervium index --config config.json`
- Pipx automatically manages isolated environment
- Clean, modern approach used by popular CLI tools (black, pytest, poetry)

**Alternative Method: pip + alias**
- Users activate venv once: `source .venv/bin/activate`
- Install with pip: `pip install -e .`
- Add alias to shell profile (~/.bashrc or ~/.zshrc): `alias minervium='/absolute/path/to/minervium/.venv/bin/minervium'`
- Commands work without venv activation: `minervium index --config config.json`
- Classic approach, works everywhere

**FR8.2** Documentation MUST include:
- Step-by-step installation instructions for both methods
- Explanation of why venv activation is not required after initial setup
- Troubleshooting section for PATH and alias issues
- Verification steps: `minervium --help` should work after installation

**FR8.3** The core package setup.py MUST:
- Define package name as "minervium"
- Set initial version to "1.0.0"
- List all dependencies (chromadb, litellm, numpy, langchain, tiktoken, nltk)
- Define single console_scripts entry point: `minervium = minervium.cli:main`
- Specify Python version requirement (>=3.8 for ChromaDB compatibility)
- Include package metadata (author, description, classifiers)

**FR8.4** Each extractor setup.py MUST:
- Define unique package name (e.g., "bear-notes-extractor")
- Set initial version to "1.0.0"
- NOT include Minervium as a dependency
- Define extractor-specific console_scripts entry point
- Include extractor-specific dependencies only

**FR8.5** The repository MUST use a monorepo structure with:
- `minervium/` - Core package
- `extractors/` - Independent extractor packages
- `configs/` - Example configurations
- `chromadb_data/` - Development database
- `docs/` - Comprehensive documentation

## Non-Goals (Out of Scope)

1. **PyPI Publishing:** Initial release will use local development installation only (`pip install -e`), not public PyPI distribution

2. **Async Support:** Extractors will use synchronous operations; async can be added in future versions if needed

3. **GUI Interface:** CLI-only; no graphical user interface

4. **Plugin System with Auto-Discovery:** Extractors are standalone tools, not plugins that integrate with core package through entry points or discovery mechanisms

5. **Configuration Format Changes:** Will continue using JSON for configuration files (no migration to TOML or YAML)

6. **Breaking Changes to JSON Schema:** Existing note schema remains unchanged to ensure backward compatibility

7. **ChromaDB Alternatives:** Will continue using ChromaDB as the vector database (no support for Pinecone, Weaviate, etc.)

8. **Multi-Repository Split:** Initial release uses monorepo; extractors can be split into separate repos later if community contributions grow

9. **Web API/REST Interface:** MCP server only; no HTTP API for remote queries

10. **Automated Data Source Monitoring:** No automatic re-indexing when source files change; users must manually re-run extraction and indexing

## Design Considerations

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         User Layer                           │
│  (Bear notes, Zim articles, Markdown books, Custom sources) │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Extractor Layer                           │
│  (Independent tools: bear-extractor, zim-extractor, etc.)    │
│             Output: Minervium JSON Schema                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ [JSON validation: minervium validate]
                       │
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│                    minervium CLI                             │
│  ┌────────────┬────────────┬──────────┬─────────────┐      │
│  │   index    │   serve    │   peek   │  validate   │      │
│  │  (RAG)     │   (MCP)    │  (Info)  │  (Schema)   │      │
│  └────────────┴────────────┴──────────┴─────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                              │
│         ChromaDB + Multi-Provider AI (Ollama/OpenAI/Gemini) │
└─────────────────────────────────────────────────────────────┘
```

### UI/UX Considerations

**CLI Design Principles:**
- Single unified command: `minervium`
- Intuitive subcommands named as verbs (index, serve, peek, validate)
- Consistent flag naming across commands (--config, --verbose, --chromadb)
- Help text accessible with --help at any level
- Rich terminal output using formatted tables and progress indicators
- Clear error messages with actionable suggestions

**Example User Workflow:**
```bash
# 1. Extract notes from source
bear-extractor backup.bear2bk -o notes.json

# 2. Validate complete pipeline setup (optional but recommended)
minervium validate --config configs/ollama.json --verbose

# 3. Index notes into collection (JSON path specified in config)
minervium index --config configs/ollama.json --verbose

# 4. Inspect collection
minervium peek bear_notes

# 5. Start MCP server (config specifies chromadb_path and settings)
minervium serve --config server-config.json
```

**Output Format Examples:**

Validation success:
```
Minervium Configuration Validation (DRY-RUN MODE)
═══════════════════════════════════════════════════════════

Configuration File: configs/ollama.json
✓ Config file structure valid
✓ All required fields present

Collection Settings:
✓ Collection name: bear_notes (valid)
✓ ChromaDB path: ./chromadb_data (writable)
✓ Chunk size: 1200 characters

JSON Notes File: ./test-data/notes.json
✓ File exists and is readable
✓ Valid JSON format
✓ Array of 142 notes
✓ All notes have required fields (title, markdown, size, modificationDate)
✓ Field types correct

AI Provider: ollama
✓ Ollama service available at http://localhost:11434
✓ Embedding model: mxbai-embed-large:latest (dimension: 1024)
✓ LLM model: llama3.1:8b
✓ Provider status: Available

✓ All validation checks passed!
Configuration is ready for indexing.
```

Peek command output:
```
Collection: bear_notes
─────────────────────────────────────
Documents:       1,247
Provider:        ollama (mxbai-embed-large:latest)
Embedding Dim:   1024
Status:          ✓ Available
Created:         2025-10-16 10:30:00 UTC
Last Modified:   2025-10-17 08:15:23 UTC
```

### Component Interaction

**Indexing Flow:**
1. User runs `minervium index --config ollama.json` (config file contains JSON file path and all settings)
2. CLI parses arguments with argparse
3. `commands/index.py` loads configuration file
4. `indexing/json_loader.py` loads and validates JSON schema from path specified in config
5. `indexing/chunking.py` creates semantic chunks
6. `common/ai_provider.py` initializes AI provider from config
7. `indexing/embeddings.py` generates embeddings using provider
8. `indexing/storage.py` stores chunks + embeddings + metadata in ChromaDB
9. CLI reports success with statistics

**Server Flow:**
1. User runs `minervium serve --config server-config.json`
2. CLI loads server configuration (chromadb_path, default_max_results)
3. CLI starts MCP server in stdio mode
4. `server/collection_discovery.py` finds all collections from configured ChromaDB path
5. For each collection, `server/startup_validation.py` validates provider availability
6. `server/mcp_server.py` exposes search tools via MCP protocol
7. When query received, `server/search_tools.py` generates query embedding using collection's provider
8. `server/context_retrieval.py` retrieves relevant chunks from ChromaDB
9. Results returned to Claude Desktop via MCP protocol

## Technical Considerations

### Minimum Python Version
- **Requirement:** Python 3.8+ (ChromaDB dependency)
- **Recommendation:** Python 3.10+ for better type hints and performance
- **Testing:** Verify compatibility with Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13

### Core Dependencies
```
chromadb>=0.4.0        # Vector database
litellm>=1.0.0         # Multi-provider AI abstraction
numpy>=1.21.0          # Vector operations
langchain>=0.1.0       # Text splitting framework
langchain-text-splitters>=0.0.1
tiktoken>=0.4.0        # Token counting
nltk>=3.8              # NLP utilities
```

### Argparse CLI Structure
The CLI will use argparse with subparsers for commands:
```python
# minervium/cli.py pseudo-code
parser = argparse.ArgumentParser(prog='minervium')
subparsers = parser.add_subparsers(dest='command')

# Index command
index_parser = subparsers.add_parser('index', help='Create vector embeddings')
index_parser.add_argument('-c', '--config', required=True, help='Config file (specifies JSON file path and settings)')
index_parser.add_argument('-v', '--verbose', action='store_true')
index_parser.add_argument('--dry-run', action='store_true')

# Serve command
serve_parser = subparsers.add_parser('serve', help='Start MCP server')
serve_parser.add_argument('-c', '--config', required=True, help='Server config file (contains chromadb_path, default_max_results)')

# Peek command
peek_parser = subparsers.add_parser('peek', help='Inspect collection metadata')
peek_parser.add_argument('collection_name', help='Collection to inspect')
peek_parser.add_argument('--chromadb', default='./chromadb_data', help='ChromaDB path')
peek_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')

# Validate command (alias for index --dry-run)
validate_parser = subparsers.add_parser('validate', help='Validate pipeline configuration')
validate_parser.add_argument('-c', '--config', required=True, help='Config file (same as index command)')
validate_parser.add_argument('-v', '--verbose', action='store_true')
```

### Import Path Migration
All imports must change from current scattered structure to unified package:
```python
# Old imports (before refactoring)
from chunk_creator import create_chunks_for_notes
from embedding import generate_embeddings_batch
from storage import initialize_chromadb_client

# New imports (after refactoring)
from minervium.indexing.chunking import create_chunks_for_notes
from minervium.indexing.embeddings import generate_embeddings_batch
from minervium.indexing.storage import initialize_chromadb_client
```

### Error Handling Strategy
- **Validation errors:** Clear messages with field/note location, exit code 1
- **Provider unavailable:** Log warning, mark collection unavailable, continue (don't crash server)
- **File not found:** Friendly error with path check suggestion
- **Schema violations:** Detailed validation report with fix suggestions
- **Network errors:** Retry once, then fail gracefully with troubleshooting hint

### Logging Standardization

The system MUST adopt the existing MCP server logging pattern with context-aware output routing.

**Logger Implementation (`minervium/common/logger.py`):**
- Migrate `markdown-notes-mcp-server/console_logger.py` to `minervium/common/logger.py`
- Maintain the facade pattern over Python's logging module
- Support two formatting modes:
  - **Detailed mode** (default): `timestamp - module - level - message`
  - **Simple mode** (simple=True): Just the message (for user-facing output)
- Provide semantic methods: `info()`, `success()`, `warning()`, `error()`
- Avoid duplicate handlers with `if not logger.handlers:` check
- Set `propagate = False` to prevent root logger interference

**Context-Aware Output Routing:**
- **MCP server (`serve` command):** All output to stderr (prevents stdio JSON-RPC contamination)
- **CLI commands (`index`, `validate`, `peek`):** Normal output to stdout, errors to stderr
- Implement via configurable StreamHandler based on execution context

**Usage Pattern:**
```python
# In library modules (detailed logging)
from minervium.common.logger import get_logger
logger = get_logger(__name__)
logger.info("Processing started...")

# In CLI commands (simple user-facing output)
from minervium.common.logger import get_logger
logger = get_logger(__name__, simple=True)
logger.success("✓ Pipeline completed!")
```

**Migration Requirements:**
- Replace all `print()` statements with appropriate logger calls
- Use `logger.success()` for positive outcomes (✓ checkmarks)
- Use `logger.error()` for failures with optional stderr fallback
- Use `logger.warning()` for non-fatal issues
- Use `logger.info()` for progress and general messages

### Configuration File Formats

**Index Configuration (for `minervium index` and `minervium validate`):**
```json
{
  "collection_name": "bear_notes",
  "description": "Personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "json_file": "./test-data/notes.json",
  "chunk_size": 1200,
  "forceRecreate": false,
  "skipAiValidation": false,
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest",
      "base_url": "http://localhost:11434",
      "api_key": null
    },
    "llm": {
      "model": "llama3.1:8b",
      "base_url": "http://localhost:11434",
      "api_key": null
    }
  }
}
```

**Server Configuration (for `minervium serve`):**
```json
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "default_max_results": 3
}
```

**Configuration Validation:**
The system should validate configuration files before processing:
- Check required fields exist (for index: collection_name, json_file, ai_provider; for serve: chromadb_path, default_max_results)
- Validate provider type is supported (ollama/openai/gemini)
- Validate chromadb_path is absolute path for server config
- Check for API key environment variables when using cloud providers
- Provide helpful error messages for missing/invalid config
- Support `--dry-run` flag to validate index config without processing data

## Success Metrics

### Developer Experience Metrics
- Installation completes with either pipx or pip+alias method in <5 minutes
- Commands work immediately without venv activation after setup
- `minervium --help` shows all capabilities with clear descriptions
- All four core commands (index, serve, peek, validate) work end-to-end
- Error messages suggest fixes in 90%+ of common failure scenarios
- New extractor can be created by copying example and modifying in <2 hours

### User Workflow Metrics
- Complete workflow (extract → validate → index → serve) requires <5 commands
- Multi-source indexing is straightforward with clear collection separation
- Custom extractor development possible with <100 lines of code
- Migration from old structure to new structure completes without data loss

### Technical Quality Metrics
- All commands have --help documentation
- Test coverage exceeds 70% for core package
- No circular import dependencies
- Clean separation: core package doesn't import extractor code
- Backward compatible: existing JSON files work without modification
- All integration tests pass

### Documentation Metrics
- Main README covers 80% of common use cases
- Extractor development guide includes working example
- Migration guide exists for users with existing installations
- All CLI commands documented in README
- Schema specification complete with examples

## Open Questions

### 1. Logging Format Standardization ✓ RESOLVED
**Decision:** Adopt existing MCP server logging pattern (ConsoleLogger facade)

**Implementation:**
- Migrate `console_logger.py` to `minervium/common/logger.py`
- Use facade pattern with semantic methods (info, success, warning, error)
- Support two modes: detailed (with timestamps) and simple (message only)
- Context-aware output routing: stderr for MCP server, stdout for CLI commands
- Human-readable by default (structured JSON logging deferred to future version)

### 2. Configuration File Validation Strictness ✓ RESOLVED
**Decision:** Strict validation - fail on unknown fields to catch typos

**Rationale:**
- Catches configuration errors early (typos, outdated fields)
- Makes config files self-documenting (only valid fields accepted)
- Prevents silent failures from misconfigured options
- Future compatibility: new fields added with schema version bumps

### 3. Extractor Output Validation ✓ RESOLVED
**Decision:** Extractors do NOT validate against Minervium schema

**Rationale:**
- **Separation of concerns:** Extractors extract, Minervium validates
- **No coupling:** Extractors remain independent, don't import Minervium code
- **Schema evolution:** Schema changes don't require extractor updates
- **Clear workflow:** Extract → Validate → Index (explicit validation step)
- **Standard pattern:** Programs typically don't validate against external schemas

**User Workflow:**
```bash
# 1. Extract data (no validation)
bear-extractor backup.bear2bk -o notes.json

# 2. Explicitly validate (user chooses to run this)
minervium validate --config config.json

# 3. Index (validation happens automatically during indexing anyway)
minervium index --config config.json
```

**Note:** Extractors MAY include basic sanity checks (e.g., "did we extract any notes?") but should NOT validate against the full Minervium schema.

### 4. Test Organization ✓ RESOLVED
**Decision:** Top-level `tests/` directory

**Rationale:**
- Standard Python convention (pytest, setuptools default)
- Cleaner package structure (tests not bundled in distribution)
- Easier to exclude from package installation
- Follows pattern used by most Python projects

### 5. Entry Point for Commands ✓ RESOLVED
**Decision:** Support both console scripts and module execution

**Implementation:**
- Console scripts via setup.py: `minervium = minervium.cli:main`
- Module execution via `__main__.py`: `python -m minervium`
- Both call the same `cli:main()` function

**Rationale:**
- Maximum flexibility for users
- Module execution useful for development and testing
- Console scripts provide clean user experience
- Minimal implementation overhead (just add `__main__.py`)

### 6. Installation Method Documentation Priority
**Question:** Should we emphasize pipx or pip+alias in the main README quick start?

**Options:**
- Emphasize pipx (modern, cleaner, but requires pipx pre-install)
- Emphasize pip+alias (works everywhere, more familiar)
- Show both equally

**Recommendation:** Emphasize pipx as primary with pip+alias as "Alternative Method" - aligns with modern Python CLI tool practices

## Implementation Phases

### Phase 1: Core Reorganization (2-3 days)
- Create unified directory structure
- Migrate all core files to new locations
- Migrate `markdown-notes-mcp-server/console_logger.py` to `minervium/common/logger.py`
- Update logger to support context-aware output routing (stdout for CLI, stderr for MCP)
- Replace all `print()` statements with logger calls across codebase
- Update all import paths
- Create CLI with argparse
- Implement all four commands (index, serve, peek, validate)
- Create unified setup.py
- Test that all core functionality works

**Acceptance Criteria:**
- `minervium index` command works end-to-end
- `minervium serve` starts MCP server successfully
- `minervium peek` displays collection information
- `minervium validate` checks JSON schema correctly
- Logger outputs to correct streams (stdout for CLI, stderr for MCP server)
- No `print()` statements remain in codebase (all use logger)
- No import errors or circular dependencies

### Phase 2: Extractor Reorganization (1-2 days)
- Create `extractors/` directory structure
- Migrate Bear extractor to standalone package
- Migrate Zim extractor to standalone package
- Migrate Books extractor to standalone package
- Create setup.py for each extractor
- Implement standalone CLI for each extractor
- Test extractors independently

**Acceptance Criteria:**
- Each extractor installs independently with `pip install -e`
- Each extractor CLI works without Minervium installed
- Extractor output validates successfully with `minervium validate`
- No dependencies between extractors

### Phase 3: Documentation (1-2 days)
- Write comprehensive main README.md with installation instructions
- Document both pipx (recommended) and pip+alias installation methods
- Include clear explanation that venv activation is not needed after setup
- Add installation verification steps
- Create docs/NOTE_SCHEMA.md
- Create docs/EXTRACTOR_GUIDE.md
- Create extractors/README.md
- Write README.md for each extractor
- Update CLAUDE.md
- Update CONFIGURATION_GUIDE.md
- Add code examples to all documentation

**Acceptance Criteria:**
- All documentation files exist and are complete
- Installation instructions for both methods are clear and tested
- README examples work when copy-pasted
- Schema specification includes valid/invalid examples
- Extractor guide includes step-by-step tutorial
- All links in documentation are valid
- Installation verification steps work correctly

### Phase 4: Testing & Validation (1-2 days)
- Write unit tests for JSON schema validation
- Write unit tests for CLI argument parsing
- Write integration test: bear-extractor → validate → index → serve
- Write integration test: multi-source indexing
- Test extractor independence
- Test error handling scenarios
- Run manual testing with real data
- Verify test coverage meets 70% threshold

**Acceptance Criteria:**
- All unit tests pass
- All integration tests pass
- Test coverage ≥70% for core package
- Manual testing confirms all workflows work
- Error handling tested for common failures

### Phase 5: Deployment Preparation (1 day)
- Finalize repository structure
- Clean up old directories and files
- Update .gitignore for new structure
- Create installation testing script
- Test pipx installation method on fresh system
- Test pip+alias installation method on fresh system
- Verify commands work without venv activation for both methods
- Verify MCP server integration with Claude Desktop
- Create release checklist
- Tag version 1.0.0

**Acceptance Criteria:**
- Repository structure matches specification
- Old files removed or archived
- Both installation methods work on fresh system
- Commands accessible without venv activation
- Installation documentation matches actual process
- All workflows tested end-to-end
- Version 1.0.0 tagged in git
- Migration considered complete

## Migration Timeline

**Total Estimated Time:** 6-10 days of focused work

- **Phase 1:** 2-3 days (Core reorganization)
- **Phase 2:** 1-2 days (Extractor reorganization)
- **Phase 3:** 1-2 days (Documentation)
- **Phase 4:** 1-2 days (Testing & validation)
- **Phase 5:** 1 day (Deployment preparation)

**Recommendation:** Execute phases sequentially as specified to ensure quality at each stage

---

**End of PRD**
