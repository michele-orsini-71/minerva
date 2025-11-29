# Task List: Local MCP Stack with Automatic Reindexing

## Tasks
- [ ] Update Docker deployment for host-mounted workspace
  - [ ] Adjust `deployment/docker-compose.yml` (and docs) to describe binding a local repo path into the container alongside existing data volumes.
  - [ ] Verify `deployment/entrypoint.sh` works without webhook orchestration and documents expectations for extractor/index commands invoked via `docker compose run`.
- [x] Implement host-side watcher CLI
  - [x] Scaffold a `tools/minerva-watcher/` package with a CLI entry point that watches a single workspace path, reads config, and emits CLI logs only.
  - [x] Add file watching + debounce + ignore rules.
  - [x] Execute, in order, `repository-doc-extractor`, optional `minerva validate`, and `minerva index` inside Docker using `docker compose run --rm minerva ...`.
  - [x] Ensure failures are logged (no automatic retry) and overlapping runs are prevented.
- [ ] Provide sample configs and documentation
  - [ ] Create a sample watcher config (path, debounce, compose directory, command templates) under `configs/` or `docs/` as reference.
  - [ ] Write `docs/local-watcher.md` with setup instructions (Docker install, config placement, compose up, watcher launch, workflow verification).
  - [ ] Include troubleshooting tips (permissions, Docker Desktop, verifying bind mounts).
- [ ] Validate end-to-end workflow
  - [ ] Run through setup on a clean machine (or scripted test) to confirm watcher triggers extractor/validate/index and Claude can reach `minerva serve`.
  - [ ] Capture logs/notes needed for future PR or onboarding.

## Relevant Files
- `tasks/2025-11-27-prd-local-mcp-with-auto-reindex.md` – Source PRD describing requirements.
- `tasks/2025-11-27-prd-local-mcp-with-auto-reindex-tasks.md` – This task list.
- `deployment/docker-compose.yml` – Docker stack requiring host workspace bind mount instructions.
- `deployment/entrypoint.sh` – Container startup script (no webhook, `minerva serve-http`).
- `.gitignore` – Ignore list updated to skip watcher build artifacts and node modules.
- `tools/minerva-watcher/package.json` – Node/TypeScript watcher package manifest and scripts.
- `tools/minerva-watcher/package-lock.json` – Locked dependency versions for the watcher package.
- `tools/minerva-watcher/tsconfig.json` – TypeScript compiler settings for the watcher.
- `tools/minerva-watcher/src/index.ts` – CLI entry point wiring config parsing and watcher startup.
- `tools/minerva-watcher/src/config.ts` – Config loader and validation helpers.
- `tools/minerva-watcher/src/watcher.ts` – Filesystem watcher and pipeline coordination logic.
- `tools/minerva-watcher/src/composeRunner.ts` – Docker Compose command runner for extractor/validate/index steps.
- `tools/minerva-watcher/src/types.ts` – Shared TypeScript interfaces for config and runtime structures.
- `docs/local-watcher.md` – Planned documentation for setup and troubleshooting.
- `configs/` – Placeholder for watcher sample config.
