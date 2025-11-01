# Audit: sys.exit Usage (2025-10-31 PRD)

## Scope

Modules scanned under `minerva/commands`, `minerva/indexing`, `minerva/common`, `minerva/server`, and `minerva/chat`.

## Summary

| Module | Count | Exit Codes |
| --- | ---: | --- |
| minerva/commands/index.py | 14 | 1 |
| minerva/commands/validate.py | 4 | 1 |
| minerva/indexing/json_loader.py | 9 | 1 |
| minerva/indexing/chunking.py | 2 | 1 |
| minerva/indexing/storage.py | 1 | 1 |
| minerva/indexing/updater.py | 1 | 1 |
| minerva/common/config_validator.py | 2 | 1 |
| minerva/common/config.py | 1 | 1 |
| minerva/common/validation.py | 5 | 1 |
| minerva/server/mcp_server.py | 10 | 0, 1 |
| minerva/server/collection_discovery.py | 2 | 1 |
| minerva/server/startup_validation.py | 3 | 0, 1 |
| minerva/chat/chat_engine.py | 1 | 0 |

_Total sys.exit usages identified: 55_

## Detailed Breakdown

### minerva/commands/index.py

1. `load_and_print_config` — exit 1 when `ConfigError` is raised; logs "Configuration Error" banner with the underlying message.
2. `load_and_print_notes` — exit 1 on any exception from `load_json_notes`; logs "Error loading notes" with exception text.
3. `initialize_and_validate_provider` — exit 1 when provider availability check fails; prints availability banner with suggestions.
4. `initialize_and_validate_provider` — exit 1 when `AIProviderError` surfaces; logs "Provider initialization error" with details.
5. `check_collection_early` — exit 1 if target collection is identified as legacy v1; logs formatted `format_v1_collection_error` guidance.
6. `check_collection_early` — exit 1 when incompatible configuration changes are detected; logs formatted `format_config_change_error` guidance.
7. `check_collection_early` — exit 1 on unexpected exceptions while checking ChromaDB; logs "ChromaDB check error" with exception text.
8. `run_incremental_indexing` — exit 1 if `initialize_chromadb_client` raises; logs "ChromaDB initialization error".
9. `run_incremental_indexing` — exit 1 when fetching the collection fails; logs "Failed to retrieve collection".
10. `run_incremental_indexing` — exit 1 when `run_incremental_update` raises; logs "Incremental update error" and optionally a traceback in verbose mode.
11. `run_full_indexing` — exit 1 when `generate_embeddings` raises `EmbeddingError`; logs "Embedding generation error".
12. `run_full_indexing` — exit 1 if `initialize_chromadb_client` raises; logs "ChromaDB initialization error".
13. `run_full_indexing` — exit 1 when collection creation/recreation fails; logs "Collection creation error".
14. `run_full_indexing` — exit 1 when `insert_chunks` encounters `StorageError`; logs "Storage error".

> Note: Several exits share the same error message; the list preserves each unique call site for completeness.

### minerva/commands/validate.py

1. `load_json_file` — exit 1 when the JSON file is missing; logs "Error: File not found" with remediation.
2. `load_json_file` — exit 1 on `JSONDecodeError`; logs "Error: Invalid JSON" and parsing error details.
3. `load_json_file` — exit 1 on `PermissionError`; logs "Error: Permission denied".
4. `load_json_file` — exit 1 on any other exception; logs "Error: Failed to read file" with exception message.

### minerva/indexing/json_loader.py

1. `load_json_notes` — exit 1 when target file does not exist; logs "JSON file not found".
2. `load_json_notes` — exit 1 when path is not a file; logs "Path is not a file".
3. `load_json_notes` — exit 1 when parsed JSON is not a list; logs "JSON file must contain an array of notes".
4. `load_json_notes` — exit 1 when first note is not a dict; logs "Notes must be objects".
5. `load_json_notes` — exit 1 when required fields are missing; logs "Notes missing required fields".
6. `load_json_notes` — exit 1 on `JSONDecodeError`; logs "Invalid JSON format" with decoder message.
7. `load_json_notes` — exit 1 on `UnicodeDecodeError`; logs "File encoding issue".
8. `load_json_notes` — exit 1 on `PermissionError`; logs "Permission denied reading".
9. `load_json_notes` — exit 1 on any other exception; logs "Unexpected error loading".

### minerva/indexing/chunking.py

1. Module import guard — exit 1 when `langchain-text-splitters` is missing; logs install instruction.
2. `create_chunks_from_notes` — exit 1 when no chunks are generated; logs "No chunks were successfully created".

### minerva/indexing/storage.py

1. Module import guard — exit 1 when `chromadb` is missing; logs install instruction.

### minerva/indexing/updater.py

1. Module import guard — exit 1 when `chromadb` is missing; logs install instruction.

### minerva/common/config_validator.py

1. `load_and_validate_config` — exit 1 when `ConfigError` occurs; logs "CONFIGURATION ERROR" banner with remediation steps.
2. `load_and_validate_config` — exit 1 on `ValidationError`; logs "VALIDATION ERROR" banner with remediation steps.

### minerva/common/config.py

1. `__main__` execution — exit 1 when config loading raises `ConfigError` or `ConfigValidationError`; logs "Configuration error" banner.

### minerva/common/validation.py

1. `__main__` test harness — exit 1 when valid collection name tests unexpectedly fail.
2. `__main__` test harness — exit 1 when invalid collection names are accepted (inside loop).
3. `__main__` test harness — exit 1 when short descriptions are not rejected.
4. `__main__` test harness — exit 1 when missing required phrases are not rejected.
5. `__main__` test harness — exit 1 when valid description validation raises unexpectedly.

### minerva/server/mcp_server.py

1. `initialize_server` — exit 1 on `ConfigError`/`ConfigValidationError`; logs "Configuration Error" banner.
2. `initialize_server` — exit 1 when `validate_server_prerequisites` reports failure; logs "Server Validation Failed" with details.
3. `initialize_server` — exit 1 on generic exception during prerequisite validation; logs "Validation Error".
4. `initialize_server` — exit 1 when no collections are available; logs multi-line troubleshooting guidance.
5. `initialize_server` — exit 1 on `CollectionDiscoveryError`; logs "Collection Discovery Error" with details.
6. `initialize_server` — exit 1 on unexpected exception while discovering collections; logs "Collection Discovery Error".
7. `main` — exit 0 on keyboard interrupt; logs shutdown notice.
8. `main` — exit 1 on server runtime exception; logs "Server error".
9. `main_http` — exit 0 on keyboard interrupt; logs shutdown notice.
10. `main_http` — exit 1 on server runtime exception; logs "Server error".

### minerva/server/collection_discovery.py

1. CLI usage guard — exit 1 when run without required `chromadb_path` argument; logs usage message.
2. CLI execution — exit 1 when `CollectionDiscoveryError` is raised; logs "Collection discovery error".

### minerva/server/startup_validation.py

1. CLI execution — exit 0 when validation passes; logs success summary.
2. CLI execution — exit 1 when validation fails; logs failure reason.
3. CLI execution — exit 1 when unexpected exception occurs; logs "Validation error".

### minerva/chat/chat_engine.py

1. `_handle_interrupt` — exit 0 after saving conversation on SIGINT; prints "Conversation saved" message.

## Shared Patterns (Initial Observations)

- Import guards for optional dependencies (`chromadb`, `langchain-text-splitters`, `FastMCP`) all exit 1 after logging installation guidance.
- File/config loading helpers exit 1 after logging structured banners (`Configuration Error`, `Validation Error`).
- ChromaDB-related helpers exit 1 with operational context (`ChromaDB initialization error`, `Collection creation error`).
- CLI entrypoints exit 0/1 to communicate success/failure while logging final status banners.
- Test harness `__main__` blocks use exit codes to signal success/failure when modules are executed directly.

These patterns will inform the exception hierarchy design and CLI translation strategy in subsequent tasks.
