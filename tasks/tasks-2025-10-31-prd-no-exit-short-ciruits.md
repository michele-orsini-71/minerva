## Relevant Files

- `minerva/indexing/json_loader.py` - Current JSON loading helper that terminates with `sys.exit`; needs refactor to raise exceptions.
- `minerva/indexing/chunking.py` - Chunking helpers that exit on configuration errors; must emit exceptions instead.
- `minerva/indexing/storage.py` - Storage setup helper containing inline exits to replace with exceptions.
- `minerva/indexing/updater.py` - Updater utilities that should raise domain errors rather than exiting.
- `minerva/common/validation.py` - Validation helpers to switch from `sys.exit` to structured exceptions.
- `minerva/common/config_validator.py` - Config validation module requiring exception-based error reporting.
- `minerva/common/config.py` - Config loader that currently calls `sys.exit` on failure.
- `minerva/commands/index.py` - CLI command that must catch new exceptions and preserve exit codes.
- `minerva/commands/validate.py` - Validation command entrypoint to handle new exception hierarchy.
- `minerva/cli.py` - CLI aggregator that should centralize exit code handling.
- `minerva/common/exceptions.py` - Central exception hierarchy with default exit codes for CLI translation.
- `minerva/server/startup_validation.py` - Startup checks now emitting `StartupValidationError`.
- `minerva/server/collection_discovery.py` - Collection discovery now raising `CollectionDiscoveryError`.
- `minerva/server/mcp_server.py` - MCP server launcher handling `MinervaError` for exit translation.
- `tests/test_server_exceptions.py` - Coverage for new server exception pathways.
- `docs/RELEASE_NOTES_v2.0.md` - Documents the exception contract updates.
- `minerva/chat/chat_engine.py` - Chat engine helper that currently issues `sys.exit` and should align with new error contract.
- `tests/test_validate_command.py` - Existing tests asserting on `SystemExit`; must be updated for new exception types.
- `tests/` (additional modules TBD) - Expand or add tests covering new error handling paths.
- `docs/` (changelog or error handling guide) - Update documentation to describe the new exception contract.
- `tasks/audit-sys-exit-2025-10-31.md` - Audit log capturing every current `sys.exit` call with context and exit codes.

### Notes

- Keep `chromadb_data/` untracked and avoid modifying extractor CLIs that intentionally call `sys.exit()`.
- Preserve existing log messages while converting exits to exceptions so operational visibility stays the same.
- Ensure new exceptions derive from the shared `MinervaError` base class for consistent catching at entrypoints.
- Validate updated CLI behaviour by running relevant `pytest` suites and, if practical, smoke-testing commands locally.

## Tasks

- [x] 1.0 Audit current `sys.exit` usage and document exit codes
  - [x] 1.1 Enumerate all `sys.exit` calls under `minerva/commands`, `minerva/indexing`, `minerva/common`, `minerva/server`, and `minerva/chat`.
  - [x] 1.2 Capture the surrounding context, messages, and exit codes in an audit document (e.g., markdown in `tasks/` or project notes).
  - [x] 1.3 Identify any shared patterns (e.g., repeated validation checks) that can reuse a single exception type.
- [x] 2.0 Design the `MinervaError` exception hierarchy
  - [x] 2.1 Create a new module (e.g., `minerva/common/exceptions.py`) defining `MinervaError` and domain-specific subclasses drawn from the audit.
  - [x] 2.2 Document each exception’s intended usage and default exit code mapping for CLI translation.
  - [x] 2.3 Update package exports (`minerva/common/__init__.py` or relevant modules) so helpers can import the new classes.
- [ ] 3.0 Refactor indexing and common helpers to raise exceptions
  - [x] 3.1 Replace `sys.exit` calls in `minerva/indexing/json_loader.py`, `chunking.py`, `storage.py`, and `updater.py` with appropriate exceptions.
  - [x] 3.2 Update `minerva/common/validation.py`, `config_validator.py`, and `config.py` to raise the new exception types.
  - [x] 3.3 Maintain or improve logging to ensure error messages remain informative after the refactor.
- [x] 4.0 Refactor server modules to bubble exceptions to launchers
  - [x] 4.1 Update `minerva/server/collection_discovery.py` and `startup_validation.py` to raise server-specific exceptions.
  - [x] 4.2 Refactor `minerva/server/mcp_server.py` and `minerva/chat/chat_engine.py` to raise exceptions instead of exiting, ensuring long-running services can manage shutdown elsewhere.
  - [x] 4.3 Confirm no additional shutdown hooks are required per the PRD guidance.
- [x] 5.0 Centralize CLI entrypoint error handling and exit codes
  - [x] 5.1 Modify `minerva/commands/index.py` and `validate.py` to catch `MinervaError` (and subclasses) and translate them into the correct exit codes.
  - [x] 5.2 Review top-level `minerva/cli.py` (and related entrypoints) to ensure they only call `sys.exit` once and log errors appropriately.
  - [x] 5.3 Add shared helper(s) if valuable for mapping exceptions to exit codes to avoid duplication.
- [x] 6.0 Update tests and documentation for new error contracts
  - [x] 6.1 Update existing tests (e.g., `tests/test_validate_command.py`) to expect the new exception types and messages.
  - [x] 6.2 Add targeted unit tests covering refactored helpers and server modules, including edge cases previously terminating the process.
  - [x] 6.3 Refresh documentation or changelog entries to describe the new exception handling model.
  - [x] 6.4 Run `pytest` (and linting if impacted) to confirm the refactor passes automated checks.
