# PRD: Remote MCP Proxy for Minerva

**Status:** Draft
**Created:** 2025-11-27
**Author:** Codex (per create-prd instructions)
**Source Context:** Follow-up to `/tasks/2025-11-15-prd-github-webhook-auto-reindex.md` and Phase 1–2 implementations under `tasks/old/`

---

## 1. Introduction / Overview

Claude Desktop/Code only speaks MCP over stdio, yet the team needs a single Minerva instance that stays online, receives GitHub webhooks, and serves every developer without running Minerva locally. This PRD introduces a **Remote MCP Proxy**: a lightweight client+server pair that tunnels Claude's stdio traffic to the shared Minerva deployment, reusing the existing webhook orchestrator and Docker stack while keeping the reindex SLA (<5 minutes) intact.

Key ideas:
- Preserve the "one tool per job" philosophy by shipping two independent CLIs: `mcp-proxy-client` (local shim) and `mcp-proxy-server` (remote fan-out to Minerva tools).
- Keep the completed GitHub webhook orchestrator and most Docker assets; adapt them to spawn Minerva in stdio mode and expose proxy endpoints instead of the MCP HTTP API.
- Maintain remote deployments as the focus; local filesystem watchers and desktop-only flows remain future scope.

## 2. Goals

1. **Single Remote Instance:** Developers configure Claude Desktop once and reach a shared Minerva MCP over the proxy tunnel.
2. **Fast Reindexing:** Push-to-search latency stays under 5 minutes end-to-end using the existing webhook orchestrator.
3. **Secure Transport:** All proxy hops enforce auth (API key + signature) and run over TLS.
4. **Operational Simplicity:** Docker/Compose package installs `minerva serve` (stdio) + webhook + proxy server with minimal changes from Phase 2.
5. **Observability:** Operators can inspect health, request counts, and failures via dedicated endpoints/logging.

## 3. User Stories

### US-1: Remote Claude Access
As a developer using Claude Desktop, I want to connect a local MCP entry to a remote Minerva server via the proxy client so that I can search shared documentation without running Minerva locally.

### US-2: Automated Reindexing
As a documentation maintainer, I want GitHub pushes to trigger the existing webhook orchestrator so that new content is searchable in Claude within 5 minutes.

### US-3: Secure Operations
As a DevOps engineer, I want mutual authentication between proxy client and server so that only trusted laptops can reach internal Minerva tools.

### US-4: Deployment Health
As an operator, I want health and metrics endpoints for both webhook and proxy services so that I can detect failures before they impact developers.

## 4. Functional Requirements

### Proxy Client (`mcp-proxy-client` executable)
1. **FC-1:** Runs as an MCP server speaking stdio (Claude-compatible) and forwards every request to the proxy server over HTTPS/WebSocket or mTLS gRPC.
2. **FC-2:** Configurable via JSON/YAML file with remote endpoint, client ID, secrets, and retry/backoff settings.
3. **FC-3:** Streams Minerva tool responses back to Claude without buffering entire payloads (support SSE-style chunking).
4. **FC-4:** Handles auth by signing each forwarded request (HMAC or mTLS) and verifying server signatures on the response.
5. **FC-5:** Exposes local status logs for debugging (e.g., `--verbose`, `--health-port 0` optional HTTP health endpoint for launchd/systemd).

### Proxy Server (`mcp-proxy-server` executable)
6. **FS-1:** Listens on HTTPS endpoints (one per MCP tool) and forwards payloads to a colocated Minerva `serve` process running in stdio mode; also supports calling Minerva's HTTP mode when Claude eventually permits it.
7. **FS-2:** Authenticates incoming client requests (API keys, optional mutual TLS) and enforces per-client rate limits.
8. **FS-3:** Supports streaming responses back to the client using the same framing as MCP stdio (chunked JSON RPC or SSE framing).
9. **FS-4:** Provides `/health` and `/metrics` endpoints compatible with the docker health checks built in Phase 2; log traces include client ID, tool name, latency, status.
10. **FS-5:** Integrates with the existing docker-compose stack: new service definition, mounted configs, env vars, TLS cert path, and optional reverse proxy (Caddy/Nginx) for HTTPS termination.

### Webhook Orchestrator (Existing Phase 1 Asset)
11. **FW-1:** Continue consuming GitHub push events, triggering extractor → validate → index workflows exactly as in Phase 1.
12. **FW-2:** Emit events or log hooks that the proxy server can surface (e.g., broadcast "collection X reindexed" for operator dashboards).

### Docker / Deployment (Existing Phase 2 Asset)
13. **FD-1:** Update `deployment/Dockerfile`, `docker-compose.yml`, and entrypoint to run three processes: `minerva serve` (stdio), `webhook-orchestrator`, and `mcp-proxy-server`.
14. **FD-2:** Document how clients obtain TLS cert fingerprints / API keys and how to distribute `mcp-proxy-client` binaries.
15. **FD-3:** Provide scripts/config to run proxy client inside launchd/systemd user service with automatic reconnect.

### Security & Observability
16. **FSec-1:** Secrets (API keys, TLS private keys) sourced from env vars or secret stores; nothing hard-coded.
17. **FSec-2:** Audit logging for authentication success/failure and command invocations.
18. **FO-1:** Latency, throughput, and error metrics exported (Prometheus or structured logs) for both proxy components and webhook orchestrator.

## 5. Non-Goals

- NG-1: Local filesystem watchers or desktop-only Minerva deployments (future opportunity).
- NG-2: Native HTTP MCP client support inside Claude (blocked until Anthropic ships it).
- NG-3: Multi-tenant RBAC or per-user collections; all clients share the same Minerva instance and auth key for now.
- NG-4: Replacing the webhook orchestrator with another change-detection mechanism; existing CLI remains the source of truth.

## 6. Design Considerations

- **Tool Separation:** Implement proxy CLIs outside the core `minerva/` package (e.g., `tools/mcp-proxy-client/` + `tools/mcp-proxy-server/`) to mirror extractors/webhook separation and allow independent release cadence.
- **Transport:** Prefer a simple JSON-RPC-over-HTTPS POST with streaming support (HTTP chunked transfer or WebSocket). Keep abstraction thin so future HTTP MCP support can bypass the proxy entirely.
- **Backward Compatibility:** Docker compose should continue to work for teams using only the webhook; proxy additions must not break existing scripts.
- **Client Distribution:** Provide prebuilt binaries or `pipx install mcp-proxy-client` instructions plus a sample Claude Desktop config snippet.

## 7. Technical Considerations

- **Minerva Stdio Management:** Proxy server should spawn `minerva serve --config server.json` via subprocess, monitor stdout/stderr, and restart on failure. Reuse Phase 2 entrypoint patterns for signal handling.
- **Scaling:** Support multiple proxy-client connections concurrently; ensure Minerva server handles simultaneous tool requests (possibly by queuing or running multiple worker processes).
- **Webhooks Coordination:** Ensure webhook-triggered reindexing does not conflict with in-flight proxy queries—document ChromaDB concurrency expectations and retry strategy if writes temporarily block reads.
- **Certificates:** Recommend Caddy or another reverse proxy inside Docker for automatic TLS; document manual cert upload if running behind corporate load balancers.
- **Testing:** Provide end-to-end test plan (curl → proxy server → Minerva) plus integration tests for auth failures, streaming, and timeouts.

## 8. Success Metrics

- **Latency:** Time from GitHub push webhook receipt to updated results available via proxy < 5 minutes (P95) as already achieved in Phase 1.
- **Availability:** Proxy server uptime ≥ 99% during business hours; auto-reconnect success rate ≥ 99% for clients.
- **Adoption:** 100% of Claude Desktop users connect through the proxy (zero requests for local installs).
- **Security:** Zero unauthenticated proxy requests accepted during testing; all traffic encrypted.

## 9. Open Questions

1. Which streaming protocol (HTTP chunked vs WebSocket vs gRPC) best matches Claude’s MCP framing without excessive glue code?
2. Should the proxy server expose a queue/status API so the webhook orchestrator can announce reindex progress to clients?
3. Do we need per-client usage quotas or is a single shared API key sufficient initially?
4. How will we distribute client secrets securely to each developer laptop?
5. Should we keep Docker Compose single-service (supervisord-style) or split into multiple containers (proxy, webhook, Minerva) for easier scaling?

---

**Next Steps:**
- Align stakeholders on transport/auth choices (open questions).
- Update Phase 1/2 docs to note the proxy pivot and reference this PRD.
- Begin implementation tickets for proxy client/server CLIs, Docker updates, and documentation.
