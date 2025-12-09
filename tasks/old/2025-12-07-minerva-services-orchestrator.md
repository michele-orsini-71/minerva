# Minerva Services Orchestrator

Goal: Replace the bespoke setup wizard with a unified CLI (working name: `minerva-local-runner`) that orchestrates the lifecycle of local Minerva collections and services. The orchestrator should take over management of repositories/collections, watchers, and future pipelines while reusing existing Minerva CLIs.

## Phase 0 – Foundations (done)
- CLI entry point exists (`minerva`), watcher package and manager prototype (`minerva-local-watcher`).
- Setup script currently installs pipx deps, stores API keys, builds configs, runs extraction/indexing, and installs watcher.

## Phase 1 – Orchestrator CLI Skeleton
1. Create `tools/minerva-local-runner/` package with subcommands:
   - `add`: bootstrap a new collection (asks provider/repo/name, stores key, generates configs, optionally indexes).
   - `list`: show all known collections with repo paths, watcher status, last indexed timestamp.
   - `watch`: list collections and start watcher (reuse current manager logic).
   - `index`: run extraction + indexing once for a chosen collection.
   - `remove`: stop watcher, delete configs, wipe Chromadb collection.
2. Implement shared helpers (config discovery, repo metadata) so each subcommand works consistently.
3. Keep all “business logic” as thin wrappers around existing tools:
   - call `minerva keychain`, `minerva index`, `minerva peek/remove`, `local-repo-watcher` rather than reimporting modules.

## Phase 2 – Setup Integration
1. Slim down `apps/local-repo-kb/setup.py`:
   - Only checks/installs pipx packages (minerva, watcher, orchestrator), validates prerequisites.
   - At the end, prompt “Run `minerva-local-runner add` to create your first collection.”
2. Update docs to point users to the orchestrator CLI rather than the wizard.

## Phase 3 – Feature Parity & Enhancements
1. Ensure `add` replicates current setup flow (AI provider selection, description generation, config creation, extraction/indexing, watcher install prompt).
2. `list` shows watchers (running vs stopped) and references repo paths + config locations.
3. Offer `--no-index`/`--watch` flags to tailor `add` workflow.
4. Allow future pipelines by adding a `--type` option (e.g., `repo`, `zim`, `notes-import`), with defaults for repo watcher.

## Phase 4 – Transition & Cleanup
1. Deprecate the old setup wizard once the orchestrator covers all functionality.
2. Update documentation, demos, and screenshots to refer to `minerva-local-runner`.
3. Remove redundant scripts (e.g., watcher manager CLI becomes part of the orchestrator).

## Open Questions
- Naming: `minerva-local-runner`, `minerva-orchestrator`, `minerva-localctl`?
- Should the orchestrator track metadata (e.g., last indexed timestamp) in a central file?
- How to handle non-repo collections (future)? Possibly plug in additional “add” flows.

## Next Steps
1. Prototype the orchestrator CLI structure with stub subcommands.
2. Port existing watcher manager functionality into `watch` subcommand.
3. Incrementally migrate setup logic into `add` subcommand.

