# PRD: Local MCP Stack with Automatic Reindexing

**Status:** Draft
**Created:** 2025-11-27
**Author:** Codex (per create-prd instructions)
**Source Context:** Hybrid host watcher + Dockerized Minerva discussion

---

## 1. Introduction / Overview

We need a local-first Minerva experience where each developer runs Minerva's dockerized stack, but a lightweight host watcher automatically rebuilds the index whenever a local workspace changes. This bridges the gap between complex remote orchestration (previous PRD) and the immediate need for a simple local workflow: developers edit docs/code in their repo, a host process detects those changes, and it triggers `minerva index` inside the Docker deployment, so Claude can query an up-to-date MCP server without manual commands.

## 2. Goals

1. Provide a straightforward path for teammates (dev and non-dev) to spin up the Minerva docker stack locally with automatic reindexing.
2. Ensure the host watcher captures workspace edits, debounces them, and triggers reindex via Docker commands, keeping the MCP server current.
3. Deliver documentation/instructions so setup takes under 10 minutes for most users.

## 3. User Stories

- **US-1:** As a teammate who edits the repo on my laptop, I want a local watcher that notices file changes and automatically runs `minerva index` inside the Docker stack so Claude sees updated content.
- **US-2:** As a teammate setting up Minerva for the first time, I want to install Docker, clone the repo, follow concise instructions, and rely on the watcher to keep Minerva indexed without manipulating virtualenvs or config files.

## 4. Functional Requirements

1. **FR-1:** Provide a host-side watcher CLI/binary that monitors a target workspace directory for file changes (respecting ignore rules) and debounces events (configurable cooldown).
2. **FR-2:** When the watcher observes a change, it must execute `docker compose run --rm minerva repository-doc-extractor …` followed by validation (if configured) and `docker compose run --rm minerva minerva index --config <config>` against the local stack.
3. **FR-3:** The watcher must handle failure modes gracefully (log failure, avoid concurrent index runs, but do not auto-retry; subsequent runs only occur when new changes are detected).
4. **FR-4:** Include sample configuration defining workspace path, docker-compose project directory, index configuration path, debounce timing, and ignore patterns.
5. **FR-5:** Provide instructions/docs covering installing Docker, obtaining required config files, running `docker compose up`, and launching the watcher.
6. **FR-6:** Container entrypoint must only start `minerva serve` (no webhook orchestrator) and be compatible with watcher-triggered indexing runs.

## 5. Non-Goals (Out of Scope)

- **NG-1:** Remote MCP proxy or webhook automation remains out of scope (see previous PRD).
- **NG-2:** Shipping installers/binaries for the watcher (initial iteration can be a script/CLI run manually).

## 6. Design Considerations

- Keep the watcher thin and OS-agnostic; prefer a single entry point with optional wrappers for launchd/systemd in future iterations.
- Compose deployment already handles Minerva + Chroma; watcher should not require knowledge of internal directories beyond the compose project and config file location.
- Provide sensible defaults in the watcher config to minimize user customization.

## 7. Technical Considerations

- Watcher implementation options: Python (`watchdog`), Node (`chokidar`), Go (fsnotify). Choose whichever offers easy packaging for future automation.
- Debounce strategy should prevent overlapping indexing: queue events and wait for stack to finish before retriggering.
- `docker compose run` must share the same volumes as `docker compose up`, ensuring consistent Chroma and repo state.
- Document required env vars (API keys, config mounts) that compose expects.

## 8. Success Metrics

- **SM-1:** Teammates can follow the docs and have watcher + docker stack running within 10 minutes (subjective feedback).
- **SM-2:** After a local edit, the watcher triggers `minerva index` and updates Chroma within a few minutes (e.g., <2 minutes typical, <5 minutes worst case).
- **SM-3:** Zero manual reindex commands needed during normal editing sessions.

## 9. Open Questions

1. (Resolved) Watcher will focus on a single repository per instance.
2. (Resolved) Watcher exposes status via CLI output only; no extra UI/log shipping for now.
3. (Resolved) No `--dry-run` mode is required in this iteration.
4. (Resolved) Watcher triggers extraction via `repository-doc-extractor` (or shell script wrapper), and Minerva commands can run validate before index.

---

**Next Steps:**
- Decide watcher implementation language and scaffold CLI.
- Update deployment docs and entrypoint to reflect the watcher-driven workflow.
- Prototype watcher + compose integration and document installation steps.
