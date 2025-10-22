# Task List: Minervium Refactoring

Generated from: `tasks/2025-10-17-prd-minervium-refactoring.md`

## Relevant Files

### New Core Package Files (to be created)
- `minervium/__init__.py` - Main package initialization
- `minervium/__main__.py` - Enable `python -m minervium` execution
- `minervium/cli.py` - Main CLI entry point with argparse
- `minervium/commands/__init__.py` - Commands subpackage init
- `minervium/commands/index.py` - Index command implementation
- `minervium/commands/serve.py` - Serve command implementation
- `minervium/commands/peek.py` - Peek command implementation
- `minervium/commands/validate.py` - Validate command implementation
- `minervium/common/__init__.py` - Common utilities subpackage init
- `minervium/common/schemas.py` - JSON schema definition
- `minervium/indexing/__init__.py` - Indexing subpackage init
- `minervium/server/__init__.py` - Server subpackage init
- `setup.py` - Root package configuration for Minervium

### Migrated Core Files (moved from existing locations)
- `minervium/indexing/chunking.py` - Migrated from `markdown-notes-cag-data-creator/chunk_creator.py`
- `minervium/indexing/embeddings.py` - Migrated from `markdown-notes-cag-data-creator/embedding.py`
- `minervium/indexing/storage.py` - Migrated from `markdown-notes-cag-data-creator/storage.py`
- `minervium/indexing/json_loader.py` - Migrated from `markdown-notes-cag-data-creator/json_loader.py`
- `minervium/server/mcp_server.py` - Migrated from `markdown-notes-mcp-server/server.py`
- `minervium/server/search_tools.py` - Migrated from `markdown-notes-mcp-server/search_tools.py`
- `minervium/server/collection_discovery.py` - Migrated from `markdown-notes-mcp-server/collection_discovery.py`
- `minervium/server/context_retrieval.py` - Migrated from `markdown-notes-mcp-server/context_retrieval.py`
- `minervium/server/startup_validation.py` - Migrated from `markdown-notes-mcp-server/startup_validation.py`
- `minervium/common/ai_provider.py` - Migrated from `markdown-notes-cag-data-creator/ai_provider.py`
- `minervium/common/config.py` - Migrated from `markdown-notes-mcp-server/config.py` (consolidate with config_loader.py)
- `minervium/common/logger.py` - Migrated from `markdown-notes-mcp-server/console_logger.py`

### Extractor Files (reorganized)
- `extractors/bear-notes-extractor/bear_extractor/__init__.py` - Bear extractor package
- `extractors/bear-notes-extractor/bear_extractor/parser.py` - Migrated from `bear-notes-extractor/bear_parser.py`
- `extractors/bear-notes-extractor/bear_extractor/cli.py` - Migrated from `bear-notes-extractor/cli.py`
- `extractors/bear-notes-extractor/setup.py` - Standalone setup for Bear extractor
- `extractors/bear-notes-extractor/README.md` - Bear extractor documentation
- `extractors/bear-notes-extractor/tests/test_parser.py` - Bear extractor tests
- `extractors/zim-extractor/zim_extractor/__init__.py` - Zim extractor package
- `extractors/zim-extractor/zim_extractor/parser.py` - Migrated from `zim-articles-parser/zim_parser.py`
- `extractors/zim-extractor/zim_extractor/cli.py` - Migrated from `zim-articles-parser/zim_cli.py`
- `extractors/zim-extractor/setup.py` - Standalone setup for Zim extractor
- `extractors/zim-extractor/README.md` - Zim extractor documentation
- `extractors/zim-extractor/tests/test_parser.py` - Zim extractor tests
- `extractors/markdown-books-extractor/markdown_books_extractor/__init__.py` - Books extractor package
- `extractors/markdown-books-extractor/markdown_books_extractor/parser.py` - Migrated from `markdown-books-extractor/book_parser.py`
- `extractors/markdown-books-extractor/markdown_books_extractor/cli.py` - New CLI implementation
- `extractors/markdown-books-extractor/setup.py` - Standalone setup for Books extractor
- `extractors/markdown-books-extractor/README.md` - Books extractor documentation
- `extractors/markdown-books-extractor/tests/test_parser.py` - Books extractor tests
- `extractors/README.md` - Overview of all extractors

### Test Files
- `tests/test_schema_validation.py` - Unit tests for JSON schema validation
- `tests/test_cli_parsing.py` - Unit tests for CLI argument parsing
- `tests/test_import_paths.py` - Unit tests to verify import paths work correctly
- `tests/test_index_command.py` - Unit tests for index command
- `tests/test_serve_command.py` - Unit tests for serve command
- `tests/test_peek_command.py` - Unit tests for peek command
- `tests/test_validate_command.py` - Unit tests for validate command
- `tests/test_logger.py` - Unit tests for logger output routing
- `tests/test_integration_bear_workflow.py` - Integration test: bear-extractor → validate → index → serve
- `tests/test_integration_multi_source.py` - Integration test: multi-source indexing
- `tests/conftest.py` - Pytest fixtures and configuration

### Documentation Files
- `README.md` - Main comprehensive README with installation and usage
- `docs/NOTE_SCHEMA.md` - JSON schema specification
- `docs/EXTRACTOR_GUIDE.md` - Step-by-step extractor development guide
- `CLAUDE.md` - Updated with new structure and commands
- `CONFIGURATION_GUIDE.md` - Updated with new config paths and examples

### Configuration Files
- `configs/index-ollama.json` - Example index configuration for Ollama
- `configs/index-openai.json` - Example index configuration for OpenAI
- `configs/server-config.json` - Example server configuration
- `.gitignore` - Updated for new structure

### Notes
- Unit tests should be placed in top-level `tests/` directory following standard Python convention
- Extractor tests should be placed in `extractors/{extractor-name}/tests/` within each extractor package
- Use `pytest` to run tests: `pytest tests/` for core tests, `pytest extractors/*/tests/` for extractor tests
- The migration involves ~20 core files being moved and ~10 new files being created
- All import paths will need updating from flat structure to `minervium.*` namespaced structure

## Tasks

- [x] 1.0 Core Package Reorganization - Create unified `minervium` package structure with all core RAG and MCP functionality
  - [x] 1.1 Create unified directory structure (`minervium/`, `minervium/commands/`, `minervium/indexing/`, `minervium/server/`, `minervium/common/`)
  - [x] 1.2 Create all `__init__.py` files for package initialization
  - [x] 1.3 Migrate RAG pipeline files from `markdown-notes-cag-data-creator/` to `minervium/indexing/` (chunk_creator.py → chunking.py, embedding.py → embeddings.py, storage.py, json_loader.py)
  - [x] 1.4 Migrate MCP server files from `markdown-notes-mcp-server/` to `minervium/server/` (server.py → mcp_server.py, search_tools.py, collection_discovery.py, context_retrieval.py, startup_validation.py)
  - [x] 1.5 Migrate shared components to `minervium/common/` (ai_provider.py, config files → config.py, console_logger.py → logger.py)
  - [x] 1.6 Create `minervium/common/schemas.py` with JSON schema definition and validation functions
  - [x] 1.7 Update all import paths throughout migrated files to use `minervium.*` namespace
  - [x] 1.8 Test for circular import dependencies by importing all modules
  - [x] 1.9 Verify all migrated modules can be imported without errors

- [x] 2.0 CLI Implementation - Build argparse-based CLI with all four commands (index, serve, peek, validate)
  - [x] 2.1 Create `minervium/cli.py` with argparse setup and subparser structure
  - [x] 2.2 Implement `minervium/commands/index.py` with --config, --verbose, --dry-run flags
  - [x] 2.3 Implement `minervium/commands/serve.py` with --config flag for MCP server startup
  - [x] 2.4 Implement `minervium/commands/peek.py` with collection_name positional arg and --chromadb, --format flags
  - [x] 2.5 Implement `minervium/commands/validate.py` as wrapper around index command with dry_run=True
  - [x] 2.6 Create `minervium/__main__.py` to enable `python -m minervium` execution
  - [x] 2.7 Create root `setup.py` with console_scripts entry point: `minervium = minervium.cli:main`
  - [x] 2.8 Test all four CLI commands work end-to-end with sample data
  - [x] 2.9 Verify `--help` text is clear and accurate for all commands and flags

- [ ] 3.0 Logging System Migration - Migrate and standardize logging across the entire codebase
  - [x] 3.1 Migrate `markdown-notes-mcp-server/console_logger.py` to `minervium/common/logger.py`
  - [x] 3.2 Add context-aware output routing to logger (stdout for CLI commands, stderr for MCP server)
  - [x] 3.3 Implement both detailed mode (timestamp + module + level + message) and simple mode (message only)
  - [x] 3.4 Add semantic methods to logger: info(), success(), warning(), error()
  - [x] 3.5 Replace all `print()` statements in indexing modules with logger calls
  - [x] 3.6 Replace all `print()` statements in server modules with logger calls
  - [x] 3.7 Replace all `print()` statements in CLI commands with logger calls
  - [x] 3.8 Test logger output routing in different contexts (CLI vs MCP server)
  - [x] 3.9 Verify no `print()` statements remain in codebase (grep search)

- [x] 4.0 Extractor Independence - Reorganize extractors into standalone packages with independent CLIs
  - [x] 4.1 Create `extractors/` directory structure with subdirectories for each extractor
  - [x] 4.2 Reorganize Bear extractor: create `extractors/bear-notes-extractor/bear_extractor/` package structure
  - [x] 4.3 Migrate Bear extractor files (bear_parser.py → parser.py, cli.py) and remove any Minervium imports
  - [x] 4.4 Create `extractors/bear-notes-extractor/setup.py` with console_scripts entry point: `bear-extractor`
  - [x] 4.5 Reorganize Zim extractor: create `extractors/zim-extractor/zim_extractor/` package structure
  - [x] 4.6 Migrate Zim extractor files (zim_parser.py → parser.py, zim_cli.py → cli.py) and remove any Minervium imports
  - [x] 4.7 Create `extractors/zim-extractor/setup.py` with console_scripts entry point: `zim-extractor`
  - [x] 4.8 Reorganize Markdown Books extractor: create `extractors/markdown-books-extractor/markdown_books_extractor/` package structure
  - [x] 4.9 Migrate Books extractor files (book_parser.py → parser.py, create cli.py) and remove any Minervium imports
  - [x] 4.10 Create `extractors/markdown-books-extractor/setup.py` with console_scripts entry point: `markdown-books-extractor`
  - [x] 4.11 Verify all extractors support -o/--output flag for file output and stdout by default
  - [x] 4.12 Verify all extractors support -v/--verbose flag for progress output
  - [x] 4.13 Test each extractor CLI independently (install with `pip install -e` and run command)
  - [x] 4.14 Verify extractors output valid JSON conforming to Minervium schema (test with sample data)
  - [x] 4.15 Verify extractors have NO dependencies on Minervium core package (check imports)

- [x] 5.0 Documentation - Create comprehensive documentation covering installation, usage, and extractor development
  - [x] 5.1 Write comprehensive main `README.md` with Minervium overview, architecture diagram, and quick start
  - [x] 5.2 Add installation instructions to README for both pipx (recommended) and pip+alias methods
  - [x] 5.3 Add clear explanation to README that venv activation is not needed after initial setup
  - [x] 5.4 Add installation verification steps to README (`minervium --help` should work)
  - [x] 5.5 Add basic usage examples to README for all four commands with sample workflows
  - [x] 5.6 Create `docs/NOTE_SCHEMA.md` with complete JSON schema specification, field requirements, validation rules, and examples
  - [x] 5.7 Create `docs/EXTRACTOR_GUIDE.md` with step-by-step tutorial, multi-language examples, and testing guidelines using `minervium validate`
  - [x] 5.8 Create `extractors/README.md` with overview of all official extractors and links to development guide
  - [x] 5.9 Write `extractors/bear-notes-extractor/README.md` with usage instructions, supported formats, and examples
  - [x] 5.10 Write `extractors/zim-extractor/README.md` with usage instructions, supported formats, and examples
  - [x] 5.11 Write `extractors/markdown-books-extractor/README.md` with usage instructions, supported formats, and examples
  - [x] 5.12 Update `CLAUDE.md` with new directory structure, updated command examples, extractor development section, and updated troubleshooting
  - [x] 5.13 Update `CONFIGURATION_GUIDE.md` with new config file paths, updated command examples, and multi-collection setup guide
  - [x] 5.14 Verify all documentation links are valid and examples work when copy-pasted

- [ ] 6.0 Testing & Validation - Implement unit tests and verify all workflows work end-to-end
  - [x] 6.1 Create top-level `tests/` directory and `tests/conftest.py` with pytest fixtures
  - [x] 6.2 Write unit tests for JSON schema validation logic in `tests/test_schema_validation.py`
  - [x] 6.3 Write unit tests for CLI argument parsing in `tests/test_cli_parsing.py`
  - [x] 6.4 Write unit tests for import path validation in `tests/test_import_paths.py`
  - [x] 6.5 Write unit tests for each CLI command (test_peek_command.py ✅ 24 tests, test_validate_command.py ✅ 29 tests, test_index_command.py ✅ 22 tests, test_serve_command.py ✅ 10 tests)
  - [x] 6.6 Write unit tests for logger output routing in `tests/test_logger.py` (✅ 32 tests)
  - [x] 6.7 Test error handling scenarios in `tests/test_error_handling.py` (✅ 30 tests: missing files, invalid config, provider unavailable, schema violations, keyboard interrupts, cascading errors)

- [ ] 7.0 Deployment Preparation - Finalize repository structure and verify installation methods
  - [ ] 7.1 Clean up old directories (archive or remove `markdown-notes-cag-data-creator/`, `markdown-notes-mcp-server/`, original extractor directories)
  - [ ] 7.2 Remove all docstring comments and review code comments in order to implement Clean Code comments policy (if a function is difficult to understand, rewrite it, use a better name, but do not add a commen)
  - [ ] 7.3 Update `.gitignore` for new structure (ignore `minervium.egg-info/`, `dist/`, `build/`, `*.pyc`, `__pycache__/`)
  - [ ] 7.4 Create installation testing script that verifies both pipx and pip+alias methods
  - [ ] 7.5 Test pipx installation method on fresh system (or fresh virtual environment)
  - [ ] 7.6 Verify `minervium --help` works without venv activation after pipx install
  - [ ] 7.7 Test pip+alias installation method on fresh system (or fresh virtual environment)
  - [ ] 7.8 Verify `minervium --help` works without venv activation after pip+alias setup
  - [ ] 7.9 Test all four commands (index, serve, peek, validate) work with both installation methods
  - [ ] 7.10 Verify MCP server integration with Claude Desktop using `minervium serve`
  - [ ] 7.11 Verify installation documentation matches actual installation process
  - [ ] 7.12 Run final end-to-end workflow test: extract → validate → index → peek → serve
  - [ ] 7.13 Create git tag for version 1.0.0 with release notes
  - [ ] 7.14 Mark migration as complete and celebrate! 🎉

---

**Status: Phase 2 Complete - Detailed sub-tasks generated**

The task list now contains 7 parent tasks broken down into 87 detailed sub-tasks, covering:
- **File reorganization**: ~20 core files migrated + ~10 new files created
- **Import path updates**: All imports changed to `minervium.*` namespace
- **CLI implementation**: 4 commands with argparse + 2 entry point mechanisms
- **Logging standardization**: Context-aware output routing (stdout for CLI, stderr for MCP)
- **Extractor independence**: 3 extractors as standalone packages with their own CLIs
- **Documentation**: 14 documentation files created/updated
- **Testing**: 70%+ coverage with unit and integration tests
- **Deployment verification**: Both pipx and pip+alias installation methods tested

This represents approximately 6-10 days of focused development work as estimated in the PRD.
