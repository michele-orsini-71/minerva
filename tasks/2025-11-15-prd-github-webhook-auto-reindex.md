# PRD: GitHub Webhook Auto-Reindex for Minerva

**Status:** Draft
**Created:** 2025-11-15
**Author:** Generated from implementation plan
**Target Audience:** Junior developers

---

## Introduction/Overview

Minerva is a unified RAG (Retrieval-Augmented Generation) system for personal knowledge management. Currently, when developers update documentation in GitHub repositories, they must manually trigger the reindexing process (extract → validate → index) for the updated content to become searchable via Minerva's MCP server.

This feature automates the reindexing process by building a **GitHub Webhook Orchestrator** - a separate tool that listens for GitHub push events, detects markdown file changes, and automatically triggers the Minerva reindexing workflow.

### Problem Statement
Developers must manually reindex documentation after making changes, which:
- Takes time away from productive work
- Is easy to forget, leading to stale search results
- Requires understanding of Minerva CLI commands
- Creates friction in the documentation update workflow

### Solution
Build a webhook-based automation system that reindexes Minerva collections automatically when documentation is pushed to GitHub, eliminating manual work and ensuring search results are always fresh.

---

## Goals

### Primary Goals
1. **Increase adoption:** All team members (2-5 developers) actively use Minerva for documentation search
2. **Save time:** Eliminate manual reindexing work, reducing time from ~5 minutes per update to 0
3. **Maintain freshness:** Search results reflect latest documentation within 5 minutes of git push

### Secondary Goals
4. **Enable remote deployment:** Team can access Minerva from any location via HTTPS
5. **Simplify operations:** Deployment is repeatable and documented for DevOps handoff
6. **Preserve architecture:** Keep Minerva core source-agnostic (webhook logic separate)

---

## User Stories

### US-1: Automatic Reindexing
**As a** software developer
**I want** documentation to be automatically reindexed when I push changes to GitHub
**So that** I don't have to remember to manually trigger reindexing

**Acceptance Criteria:**
- Developer pushes commit with `.md` or `.mdx` file changes to GitHub
- GitHub webhook triggers reindex workflow automatically
- Updated content is searchable in Claude Desktop within 5 minutes
- No manual intervention required

### US-2: Concurrent Access
**As a** team member searching documentation
**I want** to search Minerva while reindexing is happening
**So that** I'm never blocked from accessing information

**Acceptance Criteria:**
- MCP server stays running during reindexing
- Search queries return results (may be stale for 2-3 minutes)
- No downtime or "service unavailable" errors
- Search performance is not degraded during reindexing

### US-3: Remote Access
**As a** team member
**I want** to access Minerva from any location via HTTPS
**So that** I can search documentation whether I'm in the office or working remotely

**Acceptance Criteria:**
- Team can access Minerva via `https://minerva.yourcompany.com`
- Connection is encrypted (HTTPS with valid SSL certificate)
- Authentication required (Bearer token)
- Works from any network location

### US-4: Docker Deployment
**As a** DevOps engineer
**I want** a containerized deployment package
**So that** I can deploy Minerva to any server with minimal configuration

**Acceptance Criteria:**
- Complete Docker Compose setup provided
- Environment variables clearly documented
- Volumes configured for data persistence
- Can deploy to AWS, local server, or developer laptop

---

## Functional Requirements

### FR-1: GitHub Webhook Orchestrator (Separate Tool)
**FR-1.1** Create new package `extractors/github-webhook-orchestrator/` separate from Minerva core
**FR-1.2** Orchestrator must be installable via `pip install -e .`
**FR-1.3** Orchestrator must run as standalone web server (FastAPI or Flask)
**FR-1.4** Orchestrator must run on port 8338 (different from Minerva MCP on 8337)
**FR-1.5** Orchestrator must use Minerva CLI via subprocess, not internal imports

### FR-2: Webhook Reception & Validation
**FR-2.1** Server must expose POST endpoint `/webhook` to receive GitHub push events
**FR-2.2** Server must validate GitHub webhook signatures using HMAC-SHA256
**FR-2.3** Server must reject webhooks with invalid signatures (403 Forbidden)
**FR-2.4** Server must accept only `push` events, ignore other event types
**FR-2.5** Server must log all webhook deliveries (timestamp, repo, outcome)

### FR-3: Markdown Change Detection
**FR-3.1** Parse webhook payload to extract list of changed files from commits
**FR-3.2** Detect if any files ending in `.md` or `.mdx` were added, modified, or removed
**FR-3.3** If no markdown files changed, return success without triggering reindex
**FR-3.4** If markdown files changed, proceed to reindex workflow

### FR-4: Reindex Workflow Orchestration
**FR-4.1** Execute `git pull origin main` in repository's local clone
**FR-4.2** Call `repository-doc-extractor` CLI to extract markdown files to JSON
**FR-4.3** Call `minerva validate` CLI to validate extracted JSON schema
**FR-4.4** Call `minerva index` CLI to reindex collection with `force_recreate: false` (upsert mode)
**FR-4.5** Each command must be called via subprocess with proper error handling
**FR-4.6** All command output must be logged for debugging

### FR-5: Configuration Management
**FR-5.1** Orchestrator must read configuration from JSON file
**FR-5.2** Configuration must map GitHub repository names to:
  - Local clone path
  - Collection name
  - Index config file path
**FR-5.3** Configuration must support environment variable substitution (e.g., `${WEBHOOK_SECRET}`)
**FR-5.4** Example configuration file must be provided

### FR-6: Concurrent Operation
**FR-6.1** Minerva MCP server must stay running during reindexing
**FR-6.2** Search queries must return results during reindexing (stale results acceptable)
**FR-6.3** ChromaDB must handle concurrent read (MCP) + write (indexing) safely
**FR-6.4** No locking or shutdown of MCP server required

### FR-7: Docker Deployment
**FR-7.1** Provide `Dockerfile` that builds image with Minerva + webhook orchestrator
**FR-7.2** Provide `docker-compose.yml` orchestrating all services
**FR-7.3** Docker volumes must persist ChromaDB data across restarts
**FR-7.4** Environment variables must be provided via `envchain` or similar secure secret management (NOT plain `.env` files with unencrypted secrets)
**FR-7.5** Health check endpoint must be provided for monitoring

### FR-8: Reverse Proxy & HTTPS (Phase 3+)
**FR-8.1** Caddy reverse proxy must route HTTPS requests to backend services
**FR-8.2** Caddy must automatically obtain Let's Encrypt SSL certificate in production
**FR-8.3** All HTTP traffic must redirect to HTTPS
**FR-8.4** Reverse proxy must route:
  - `/mcp/*` → Minerva MCP server (port 8337)
  - `/webhook` → Webhook orchestrator (port 8338)

### FR-9: Authentication
**FR-9.1** Minerva MCP server must require Bearer token authentication in HTTP mode
**FR-9.2** API key must be configurable via environment variable `MINERVA_API_KEY`
**FR-9.3** Invalid or missing API key must return 401 Unauthorized
**FR-9.4** Webhook signature validation must use `WEBHOOK_SECRET` environment variable

### FR-10: Private Repository Support
**FR-10.1** System must support private GitHub repositories
**FR-10.2** GitHub personal access token must be used for authentication (decision: use tokens, not SSH keys)
**FR-10.3** Token must be configurable via environment variable `GITHUB_TOKEN`
**FR-10.4** Documentation must explain how to generate and configure GitHub personal access token

### FR-11: Multi-Provider AI Support
**Note:** This functionality is **already implemented** in Minerva core (`minerva/common/ai_provider.py`). No new work required, just documenting for completeness.

**FR-11.1** Indexing supports OpenAI API (primary provider)
**FR-11.2** Indexing supports Gemini API (secondary provider)
**FR-11.3** Indexing supports other OpenAI-compatible APIs (e.g., LM Studio)
**FR-11.4** AI provider configuration is specified in index config files via `provider` section

---

## Non-Goals (Out of Scope)

The following features are explicitly **out of scope** for this PRD:

**NG-1: Multi-User API Keys**
- Single shared API key for all team members (suitable for team of 2-5)
- Per-user API keys and access control deferred to future version

**NG-2: Rate Limiting**
- No rate limiting per user or per API key
- OpenAI rate limits handled by provider

**NG-3: Advanced Monitoring & Alerting**
- No Prometheus metrics, Grafana dashboards, or automated alerting
- Basic logging to files only
- Advanced monitoring deferred (see Technical Considerations - TBD items)

**NG-4: Branch-Specific Indexing**
- Only `main` branch is indexed automatically
- No support for indexing feature branches or tags

**NG-5: Real-Time Indexing**
- Target: reindexing completes within 5 minutes
- Sub-second latency not required

**NG-6: Non-GitHub Version Control**
- GitLab, Bitbucket, and other VCS webhooks not supported
- GitHub-specific webhook format assumed

**NG-7: Automatic Rollback**
- No automatic rollback on failed reindex
- Manual intervention required for recovery

---

## Design Considerations

### Architecture Principles
1. **Separation of Concerns:** Webhook orchestrator is separate from Minerva core
2. **Source-Agnostic Core:** Minerva knows nothing about GitHub, webhooks, or VCS
3. **CLI-Based Integration:** Orchestrator uses Minerva CLI, not internal imports
4. **Stateless Operation:** No session state, each webhook handled independently

### Package Structure
```
extractors/github-webhook-orchestrator/
├── github_webhook_orchestrator/
│   ├── __init__.py
│   ├── server.py          # FastAPI/Flask webhook receiver
│   ├── github_auth.py     # HMAC-SHA256 signature validation
│   ├── reindex.py         # Orchestrates: git pull → extract → validate → index
│   └── config.py          # Configuration loading & validation
├── setup.py               # pip installable package
├── config.example.json    # Example configuration
├── README.md              # Usage documentation
└── requirements.txt       # Dependencies
```

### Deployment Architecture
```
Production (Phase 4):
  GitHub → Webhook → Caddy (443) → Webhook Orchestrator (8338)
                                 → Minerva MCP Server (8337)
                                      ↓
                                 ChromaDB + OpenAI API

Docker Local (Phase 2):
  Localhost:8337 → Minerva MCP Server
  Localhost:8338 → Webhook Orchestrator

Development (Phase 1):
  Two terminal windows:
    1. minerva serve (stdio or HTTP)
    2. webhook-orchestrator (HTTP)
```

### Configuration Example
```json
{
  "webhook_secret": "${WEBHOOK_SECRET}",
  "repositories": [
    {
      "name": "company-docs",
      "github_url": "https://github.com/company/docs",
      "local_path": "/data/repos/company-docs",
      "collection": "company_docs",
      "index_config": "/data/config/index-company-docs.json"
    }
  ],
  "log_file": "/data/logs/webhook-orchestrator.log"
}
```

---

## Technical Considerations

### Dependencies
- **Python:** 3.10+ (Minerva requirement)
- **FastAPI or Flask:** Web framework for webhook server
- **uvicorn:** ASGI server for FastAPI
- **Docker:** 20.10+ for containerized deployment
- **Caddy:** 2.x for reverse proxy (Phase 3+)

### ChromaDB Concurrency
- ChromaDB uses SQLite with WAL (Write-Ahead Logging) mode
- Supports concurrent reads + single writer safely
- MCP server = reads only (searches)
- Indexing = single writer (updates)
- No special locking code needed, ChromaDB handles it

### Error Handling
**Webhook Delivery Failures:**
- Log error details to file
- Return 500 status to GitHub (triggers automatic retry)
- GitHub retries failed webhooks automatically

**Reindex Failures:**
- Log full error output from CLI commands
- Notification system: **TBD** (pending DevOps discussion - see Open Questions)
- Collection remains in previous state (failed reindex doesn't corrupt data)

**Git Pull Failures:**
- Log error (network issue, merge conflict, etc.)
- Skip reindex, return error to GitHub
- Require manual intervention

### Security Considerations
**API Key Storage:**
- Store in `.env` file (development/Docker)
- Store in AWS Secrets Manager or equivalent (production)
- Never commit secrets to version control

**API Key Rotation:**
- Manual rotation process
- SOC2 compliance requirements apply
- Frequency: **TBD** (security team decision)
- Process: Update `.env` → restart Docker containers → distribute new key to team

**GitHub Webhook Secrets:**
- Generated via `openssl rand -hex 32`
- Stored same as API keys
- Validated via HMAC-SHA256 signature on every webhook

**Private Repository Access:**
- Use GitHub personal access token with `repo` scope
- Store token in environment variable `GITHUB_TOKEN`
- Configure git to use token: `git config --global credential.helper store`
- Alternative: SSH key authentication

### Monitoring & Health Checks
**TBD** (pending DevOps discussion - see Open Questions)

Potential options to explore:
- CloudWatch Logs (AWS)
- Datadog
- Custom log aggregation
- Slack/email notifications on errors

Task will be added during implementation planning to research and select monitoring solution.

### Testing Strategy
**Unit Tests:**
- Webhook signature validation logic
- Configuration parsing and validation
- Markdown file change detection

**Integration Tests:**
- Not automated (avoid long-running, unstable E2E tests)
- Manual testing at each phase gate
- Documented test procedures in implementation plan

**Manual E2E Testing:**
- Simulate webhook with `curl` and test payload
- Real GitHub webhook via ngrok (Phase 1)
- Docker deployment test (Phase 2)
- LAN access test (Phase 3)
- Production deployment test (Phase 4)

---

## Success Metrics

### Primary Metrics
1. **Adoption Rate:** 100% of team members (2-5 developers) actively using Minerva for documentation search
   - Measured by: Claude Desktop MCP connection logs, informal team survey
   - Timeline: Within 2 weeks of Phase 4 completion

2. **Time Saved:** Reduce manual reindexing time from ~5 minutes per update to 0
   - Measured by: Developer self-reporting, webhook success logs
   - Target: 95%+ of documentation updates automatically reindexed

### Secondary Metrics
3. **Freshness:** Search results updated within 5 minutes of git push
   - Measured by: Webhook delivery timestamp → reindex completion timestamp
   - Target: 90% of reindexes complete within 5 minutes

4. **Reliability:** 99% webhook success rate (GitHub → reindex → searchable)
   - Measured by: Webhook delivery logs, error logs
   - Target: <1% webhook failures requiring manual intervention

### Qualitative Metrics
5. **Developer Satisfaction:** Team finds Minerva useful and easy to use
   - Measured by: Informal feedback, continued usage
   - Target: Positive feedback from majority of team

---

## Implementation Phases

This PRD covers all 4 phases, but implementation will proceed incrementally with deliverables at each phase gate.

### Phase 1: Local Development & Testing
**Deliverable:** Working webhook orchestrator tested locally on Mac (no Docker, no network)

**Success Criteria:**
- Webhook orchestrator package complete and installable
- Manual curl simulation of webhook triggers reindex successfully
- Optional: Real GitHub webhook test via ngrok
- MCP server stays running during reindexing (verified)

### Phase 2: Dockerize Locally
**Deliverable:** Docker package runnable on any machine with Docker installed

**Success Criteria:**
- Dockerfile and docker-compose.yml working
- MCP server accessible via HTTP from host machine
- Webhook orchestrator accessible from host machine
- Data persists across container restarts
- Portable package ready to share with teammates

### Phase 3: Mac as Remote Server
**Deliverable:** Your Mac accessible on LAN via HTTPS with Caddy reverse proxy

**Success Criteria:**
- Caddy reverse proxy routing requests correctly
- HTTPS enabled (self-signed cert acceptable)
- Bearer token authentication working
- Accessible from another device on LAN
- Deep understanding of reverse proxy and SSL concepts gained

### Phase 4: AWS Production Deployment
**Deliverable:** Team actively using production Minerva server on AWS

**Success Criteria:**
- Production server running on AWS
- Real SSL certificate (Let's Encrypt via Caddy)
- All company repositories indexed
- GitHub webhooks configured and tested
- Team members onboarded and actively searching
- All success metrics (adoption, time saved, freshness, reliability) achieved

---

## Open Questions

### OQ-1: Monitoring & Alerting Solution
**Question:** Which monitoring/alerting system should we use for production?

**Context:** Need to detect:
- Webhook delivery failures
- Reindex failures
- System unhealthy (MCP server down, disk full, etc.)

**Next Steps:**
- Michele to discuss with DevOps team
- Explore options: CloudWatch, Datadog, Slack webhooks, email, custom solution
- Task will be added to implementation plan to research and decide
- Not required for Phases 1-2, can be added incrementally

**Priority:** Medium (needed before Phase 4 production deployment)

### OQ-2: API Key Rotation Frequency
**Question:** How often should API keys be rotated for SOC2 compliance?

**Next Steps:**
- Michele to confirm with security team
- Document rotation procedure
- Add to operational runbook

**Priority:** Low (can be determined after initial deployment)

### OQ-3: Rollback Procedure
**Question:** What's the manual rollback procedure if a reindex corrupts data?

**Decision:** Use ChromaDB backup/restore approach

**Rationale:**
- Determining the cause of failure requires investigation of logs
- Safest solution is to restore from backup, then debug the problem
- Collection remains usable immediately (minimal downtime)

**Backup Requirements:**
- ✅ ChromaDB file contains all data (flushed) - not a problem since no continuous writes
- ⚠️ **Critical concern:** Minerva MCP server may have lock on ChromaDB file during restore
- **Restore procedure:** Stop MCP server → swap corrupted DB with backup → restart server

**Implementation Notes:**
- Backup ChromaDB volumes regularly (frequency TBD)
- Document step-by-step restore procedure
- Test restore procedure during Phase 2/3 (before production)
- Hope this won't be necessary, but be prepared

**Next Steps:**
- Define backup schedule (daily? after each successful reindex?)
- Create restore procedure runbook
- Add backup/restore to operational documentation
- Test restore procedure in Phase 2 (Docker) environment

**Priority:** Medium (should be tested before Phase 4)

### OQ-4: Private Repository Authentication Method
~~**Question:** Should we use GitHub personal access token or SSH key for private repo access?~~

**RESOLVED - Decision:** Use GitHub personal access tokens

**Implementation:**
- Generate GitHub personal access token with `repo` scope
- Store token in `GITHUB_TOKEN` environment variable (via envchain)
- Configure git to use token for HTTPS authentication
- Document token generation and configuration process

**Next Steps:**
- Create documentation for generating GitHub PAT
- Add token configuration to deployment guides
- Test with private repository in Phase 1

**Priority:** ~~High~~ **RESOLVED** (required for Phase 1 if using private repos)

### OQ-5: Error Notification Recipients
**Question:** Who should receive error notifications (failed webhooks, failed reindexes)?

**Options:**
- Michele only (admin)
- DevOps team
- Entire development team
- On-call rotation

**Next Steps:**
- Define notification recipients
- Configure alerting system accordingly

**Priority:** Medium (needed before Phase 4)

---

## Appendix: Environment Variables

**Security Note:** Do NOT use plain `.env` files with unencrypted secrets. Use `envchain` or similar secure secret management.

### Development (Phase 1)
```bash
# Store secrets in envchain
envchain --set openai OPENAI_API_KEY
# Enter: sk-your-key-here

envchain --set github GITHUB_TOKEN
# Enter: ghp_your-token-here (for private repos)

# Use secrets
envchain openai minerva index --config config.json
```

### Docker Local (Phase 2)
```bash
# Option A: envchain with docker-compose
envchain openai docker-compose up

# Option B: Pass environment variables explicitly
OPENAI_API_KEY=$(envchain openai sh -c 'echo $OPENAI_API_KEY') \
MINERVA_API_KEY=$(openssl rand -hex 32) \
WEBHOOK_SECRET=$(openssl rand -hex 32) \
docker-compose up
```

### Production (Phase 4)
```bash
# Store in AWS Secrets Manager, then retrieve and inject
# OR use envchain on server

# Generate secure keys
MINERVA_API_KEY=$(openssl rand -hex 32)
WEBHOOK_SECRET=$(openssl rand -hex 32)

# Store in envchain on server
ssh ubuntu@server
envchain --set minerva OPENAI_API_KEY
envchain --set minerva MINERVA_API_KEY
envchain --set minerva WEBHOOK_SECRET
envchain --set minerva GITHUB_TOKEN  # For private repos

# Run with envchain
envchain minerva docker-compose up -d
```

---

## Appendix: References

- **Implementation Plan:** `/tasks/2025-11-15-implementation-plan.md`
- **Original Design Doc:** `/tasks/2025-11-13-minerva-on-remote-server.md`
- **Minerva Documentation:** `/docs/CLAUDE.md`
- **Extractor Guide:** `/docs/EXTRACTOR_GUIDE.md`
- **Configuration Guide:** `/docs/configuration.md`

---

## Document History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-15 | 1.0 | Initial PRD created from implementation plan | AI Assistant |
| 2025-11-15 | 1.1 | Updated per Michele's feedback: envchain, FR-11 clarified, OQ-3 expanded, OQ-4 resolved, task list approach added | AI Assistant |

---

## Implementation Approach

### Detailed Task Lists Per Phase

This PRD covers all 4 phases, but implementation will proceed incrementally. **Detailed task lists will be created separately for each phase:**

1. **Phase 1 Task List** (`tasks/phase-1-local-webhook-tasks.md`)
   - All TBD items for Phase 1 must be resolved before creating this list
   - Current status: ✅ Ready (OQ-4 resolved, envchain approach defined)

2. **Phase 2 Task List** (`tasks/phase-2-docker-tasks.md`)
   - Can be created in parallel with Phase 1 work
   - Current status: ✅ Ready (no blocking TBD items for Phase 2)

3. **Phase 3 Task List** (`tasks/phase-3-mac-server-tasks.md`)
   - Can be created in parallel
   - Current status: ✅ Ready (Caddy setup is well-defined)

4. **Phase 4 Task List** (`tasks/phase-4-aws-deployment-tasks.md`)
   - Requires resolution of monitoring/alerting approach (OQ-1)
   - Current status: ⚠️ Blocked by OQ-1 (Michele to discuss with DevOps)

### TBD Resolution Status

**Phases 1-3:** All TBD items resolved or documented, ready for task list creation
**Phase 4:** Requires OQ-1 (monitoring solution) and OQ-5 (notification recipients) before task list creation

---

**Next Steps:**
1. ✅ Review and approve this PRD
2. ❌ Do NOT start implementation until PRD approved
3. ✅ Create detailed task lists for Phases 1-3
4. ⏸️ Resolve OQ-1 and OQ-5 before creating Phase 4 task list
5. 🚀 Proceed with Phase 1 implementation once task list approved
