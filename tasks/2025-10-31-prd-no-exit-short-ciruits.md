# 2025-10-31 PRD — Remove `sys.exit` Short-Circuits from Libraries & Command Helpers

## Introduction / Overview
The indexing, validation, and server helper modules currently call `sys.exit()` directly when they encounter errors. This pattern tightly couples reusable code to process termination, complicating readability, reusability, and unit testing. The goal of this initiative is to replace in-process exits across command helpers, shared libraries, and server utilities with structured exception handling, while preserving the existing CLI entrypoints and external tools that legitimately terminate the process.

## Goals
- Clarify error-handling flows by ensuring non-entrypoint modules raise descriptive exceptions instead of calling `sys.exit()`.
- Centralise exit-code translation inside CLI entrypoints so tests and downstream consumers can catch and assert on errors.
- Maintain full test coverage by updating or adding tests that cover new exception paths.
- Keep documentation/changelog accurate regarding the new error-handling contract.

## User Stories
- *As a developer maintaining Minerva’s indexing pipeline, I want helper modules to raise meaningful exceptions so I can reuse them in other contexts without unexpected process termination.*
- *As a tester, I want to assert on exception types rather than intercepting `SystemExit`, making negative-path tests clearer and more robust.*
- *As a developer implementing new CLI features, I want a single place that translates exceptions into exit codes so the command-line behaviour remains predictable.*

## Functional Requirements
1. **Audit**: Catalogue every `sys.exit()` call beneath `minerva/commands`, `minerva/indexing`, `minerva/common`, and `minerva/server`, flagging the surrounding context and current exit code.
2. **Exception Classes**: For each audited area, define or reuse domain-specific exception types (e.g., `IndexingError`, `ConfigValidationError`, `ServerStartupError`). Avoid generic `RuntimeError` unless no dedicated domain exists.
3. **Refactor**: Replace `sys.exit(...)` calls in the audited modules with raised exceptions, ensuring the exception message carries the original log/context.
4. **Central Handling**: Update CLI entrypoints (e.g., `run_index`, `run_validate`, server startup scripts) to catch the new exceptions, log appropriately, and call `sys.exit()` exactly once per entrypoint with the prior exit codes.
5. **Server Workflow**: For long-running services (MCP server, startup validation), bubble exceptions to their launcher so graceful shutdown logic lives in one place.
6. **Tests**: Update existing unit tests that currently expect `SystemExit` to instead assert on the new exception types and messages. Add coverage where gaps appear (e.g., server error paths).
7. **Documentation**: Record the behavioural change in the project changelog or docs (e.g., under “Error Handling”) specifying that helpers now raise exceptions.

## Non-Goals
- Changing behaviour of top-level CLI scripts or external extractor CLI entrypoints that intentionally call `sys.exit()`.
- Introducing new logging frameworks or altering logging formats beyond what is required for clarity.
- Refactoring business logic outside of error handling.

## Design Considerations
- Maintain existing log messages so operational visibility stays intact after the refactor.
- Introduce a shared base exception (`MinervaError`) for all domain-specific errors so entrypoints can catch one ancestor while tests target precise subclasses.
- Document exception hierarchies inline (docstrings or comments) so developers know which exceptions to catch.

## Technical Considerations
- **Dependencies**: No new third-party libraries should be required.
- **Backward Compatibility**: CLI commands must preserve their current exit codes to avoid breaking automation scripts or integrations.
- **Refactor Order**: Tackle modules with the heaviest `sys.exit()` usage first (e.g., `minerva/commands/index.py`, `minerva/indexing/json_loader.py`) to minimise merge conflicts.
- **Testing Strategy**: Replace `pytest.raises(SystemExit)` assertions with the new exceptions; consider parametrising tests to validate message content and exit-code mapping.

## Success Metrics
- All targeted modules raise domain-specific exceptions, with centralised translation to exit codes occurring only in CLI entrypoints and service launchers.
- All existing automated tests pass, and negative-path tests assert on the new exception types.

## Open Questions
- Should we add a formal `MinervaError` base class to simplify catching multiple domain exceptions at the entrypoint level? **Answer:** Yes; introduce `MinervaError` as the shared base class for all domain-specific exceptions so entrypoints can catch a single ancestor while still exposing specialised subclasses for tests.
- Do any downstream consumers import these helpers directly and rely on current `SystemExit` behaviour (e.g., external scripts)? If so, we may need a migration note. **Answer:** No migration note is required because no external consumers rely on the current behaviour.
- For server modules, do we need structured shutdown hooks (signals, cleanup) once exceptions bubble instead of exiting inline? **Answer:** No additional structured shutdown hooks are needed for the server modules.
