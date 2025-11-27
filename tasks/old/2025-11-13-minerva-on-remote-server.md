# Implementation Plan: Secure Team Deployment for Minerva

## Overview

Add Bearer token authentication to Minerva's HTTP server + deploy behind Caddy reverse proxy for HTTPS + use OpenAI for embeddings (no local model installation) + optional GitHub webhook orchestrator for automatic repository indexing.

**Key improvements over local deployment:**
- ✅ Centralized server accessible to team via HTTPS
- ✅ API key authentication for MCP clients
- ✅ Cloud-based embeddings (OpenAI) - no GPU/model management needed
- ✅ Fast batch embeddings with foundation models
- ✅ Optional GitHub webhook integration for automatic reindexing
- ✅ Docker deployment for easy setup and updates
- ✅ Smart markdown change detection (only reindex when needed)

## Architecture

```
Team Member (Claude Code/Cursor)
    ↓ HTTPS + Bearer Token
Caddy Reverse Proxy (Port 443)
    ↓ HTTP (localhost only)
Minerva MCP Server (Port 8337)
    └─ /mcp/* (MCP search endpoints ONLY)
    ↓
ChromaDB (Vector storage)
    ↓
OpenAI API (text-embedding-3-small, gpt-4o-mini)

┌─────────────────────────────────────────────────────────┐
│ OPTIONAL: GitHub Webhook Orchestrator (Separate Tool)  │
│ - Receives GitHub webhooks (separate port/service)     │
│ - Validates signatures                                  │
│ - Orchestrates: git pull → extract → minerva index     │
│ - Lives in extractors/github-webhook-orchestrator/     │
│ - NOT part of Minerva core                             │
└─────────────────────────────────────────────────────────┘
    ↓
GitHub Webhooks (auto-reindex on push)
```

**Key Architectural Decisions:**
- **Minerva MCP Server**: Search-only, no webhook endpoints (stays source-agnostic)
- **OpenAI**: Cloud embeddings, no local model management
- **Webhook Orchestrator**: Optional separate tool, not part of Minerva core
- **Concurrency**: MCP server stays running during reindexing (2-3 min stale results acceptable)

## Concurrency Strategy: MCP Server + Indexing

### The Question
Should the MCP server shut down during reindexing operations?

### The Answer: Keep Running (Accept Brief Inconsistency)

**Why it's safe:**
- ChromaDB uses SQLite with WAL (Write-Ahead Logging) mode
- Supports concurrent reads + single writer safely
- MCP server = reads only (searches)
- Indexing = single writer (updates)

**What happens during reindex:**
```
Time    | Indexing Process              | MCP Server Searches
--------|-------------------------------|-------------------------
10:00   | Start updating collection     | Returns current results
10:01   | Writing new chunks to DB      | May return mix of old/new
10:02   | Still indexing...             | Some stale, some fresh
10:03   | Indexing complete             | All results now fresh
```

**Trade-offs accepted:**
- ✅ **Uptime**: MCP server never goes down
- ✅ **Simplicity**: No complex blue-green deployment needed
- ✅ **Team size**: 2-5 devs, not high-traffic production system
- ⚠️ **Stale results**: 2-3 minutes of potentially inconsistent search results
- ⚠️ **Partial updates**: Mid-reindex queries may return incomplete data

**When this is acceptable:**
- Small team (2-5 developers)
- Reindexing is infrequent (on git pushes only)
- Reindexing is fast (~2-3 minutes with OpenAI batch embeddings)
- Use case is documentation search (not mission-critical transactions)

**When to reconsider:**
- Large team (>20 users) with constant queries
- Very large repositories (>1 hour reindex time)
- Mission-critical search results needed
- Consider blue-green deployment pattern instead

**Implementation notes:**
- Use `force_recreate: false` in index configs (upsert mode, not full recreate)
- ChromaDB handles locking automatically - no special code needed
- Log reindex start/end times for debugging
- Document expected behavior in team docs

## Phase 1: API Key Authentication (Core Feature)

### 1.1 Create authentication module (`minerva/server/auth.py`)
- Bearer token validation function
- Environment variable support (`MINERVA_API_KEY`)
- Clear error messages for auth failures
- Separate auth logic for reusability

### 1.2 ~~Add webhook signature validation~~ (MOVED TO SEPARATE TOOL)
**REMOVED FROM MINERVA CORE** - Webhook handling moved to `extractors/github-webhook-orchestrator/` (separate optional tool)

### 1.3 Add authentication middleware (`minerva/server/auth_middleware.py`)
- FastMCP request interceptor
- Validate `Authorization: Bearer <token>` header
- Only active in HTTP mode (stdio bypassed for local Claude Desktop)
- Apply to MCP endpoints only (no webhook endpoints in Minerva)

### 1.4 Update server config schema (`minerva/common/server_config.py`)
- Add optional `api_key` field (supports `${ENV_VAR}` syntax)
- Add `require_auth` boolean (default: true for HTTP)

### 1.5 Integrate auth into HTTP server (`minerva/server/mcp_server.py`)
- Apply API key middleware to MCP endpoints only
- Log auth events (success/failure)
- Return 401 Unauthorized for invalid tokens

### 1.6 Update exception handling (`minerva/common/exceptions.py`)
- Add `AuthenticationError` exception class

## Phase 2: HTTPS Reverse Proxy & Docker Deployment

### 2.1 Create Docker deployment files

#### 2.1.1 Dockerfile (`deployment/Dockerfile`)
- Multi-stage build for smaller image size
- Base: Python 3.13 slim
- Install Minerva and dependencies
- Install Caddy web server
- Install git (for repository cloning)
- Install repository-doc-extractor
- Configure healthcheck endpoint
- Expose ports 443 (HTTPS) and 8337 (Minerva HTTP)
- **NO Ollama installation** (uses OpenAI cloud embeddings)

#### 2.1.2 docker-compose.yml (`deployment/docker-compose.yml`)
- Service definition for Minerva + Caddy
- Volume mounts:
  - `/data/chromadb` → ChromaDB persistent storage
  - `/data/repos` → Cloned repositories
  - `/data/extracted` → Extracted JSON files
  - `/data/config` → Index configurations
- Environment variables:
  - `MINERVA_API_KEY` (for MCP client authentication)
  - `OPENAI_API_KEY` (for embeddings and LLM)
- Restart policy: `unless-stopped`
- Network configuration

#### 2.1.3 .dockerignore (`deployment/.dockerignore`)
- Exclude test data, chromadb_data, .git
- Keep image size minimal

### 2.2 Create Caddy configuration (`deployment/Caddyfile`)
- Automatic HTTPS certificate (Let's Encrypt)
- Reverse proxy to Minerva on `localhost:8337`
- Example domain: `minerva.yourcompany.com`
- Proxy both MCP endpoints and webhook endpoint
- Request logging for debugging

### 2.3 Create deployment guide (`docs/TEAM_DEPLOYMENT.md`)

#### Option A: Docker Deployment (Recommended)
- Prerequisites (Docker, domain name)
- Building the Docker image
- Running with docker-compose
- Environment variable configuration
- Volume management
- Updating the deployment

#### Option B: Ubuntu Native Installation
- Install Python, Caddy, git
- Clone Minerva repository
- Install dependencies
- Configure systemd service
- Configure Caddy manually
- Set up environment variables

#### Common Steps
- DNS configuration (A record)
- Firewall configuration (open port 443)
- SSL certificate verification
- API key generation and distribution to team
- Webhook secret generation
- Testing the deployment

## Phase 3: GitHub Webhook Auto-Indexing (OPTIONAL SEPARATE TOOL)

**IMPORTANT ARCHITECTURAL DECISION:**
Webhook handling is **NOT part of Minerva core**. It's implemented as a separate optional tool in `extractors/github-webhook-orchestrator/` to keep Minerva source-agnostic.

### 3.1 Create GitHub Webhook Orchestrator (`extractors/github-webhook-orchestrator/`)

**New separate package structure:**
```
extractors/github-webhook-orchestrator/
├── github_webhook_orchestrator/
│   ├── __init__.py
│   ├── server.py                 # Flask/FastAPI webhook receiver
│   ├── github_auth.py            # HMAC signature validation
│   ├── reindex_workflow.py       # Orchestration logic
│   └── config.py                 # Repo mapping config
├── setup.py
├── README.md
└── config.example.json           # Example configuration
```

**Webhook endpoint** (`server.py`):
- POST `/webhook` endpoint receives GitHub push events
- Parse GitHub webhook payload
- Validate HMAC-SHA256 signature
- Extract list of changed files from commits
- Check if any `.md` or `.mdx` files changed
- If markdown files changed: trigger reindex workflow via Minerva CLI
- Return success/failure status to GitHub
- Detailed logging for debugging
- Runs on separate port (e.g., 8338) or as separate service

**Webhook payload handling:**
```python
# Pseudocode
def handle_github_webhook(payload):
    # 1. Validate signature (done by middleware)

    # 2. Check event type
    if payload['event'] != 'push':
        return "ignored"

    # 3. Extract changed files
    changed_files = []
    for commit in payload['commits']:
        changed_files.extend(commit['added'])
        changed_files.extend(commit['modified'])
        changed_files.extend(commit['removed'])

    # 4. Check for markdown files
    markdown_files = [f for f in changed_files
                      if f.endswith('.md') or f.endswith('.mdx')]

    # 5. If no markdown changes, skip
    if not markdown_files:
        return "no markdown changes"

    # 6. Trigger reindex
    repo_name = payload['repository']['name']
    reindex_repository(repo_name)

    return "success"
```

### 3.2 Webhook configuration management (`config.py`)
- Load webhook configuration from file
- Map GitHub repository names to index configs
- Repository metadata (URL, collection name, index config path)

**Configuration format** (webhook orchestrator's `config.json`):
```json
{
  "repositories": [
    {
      "name": "company-docs",
      "github_url": "https://github.com/yourcompany/docs",
      "local_path": "/repos/company-docs",
      "collection": "company_docs",
      "index_config": "/config/index-company-docs.json"
    },
    {
      "name": "api-docs",
      "github_url": "https://github.com/yourcompany/api",
      "local_path": "/repos/api-docs",
      "collection": "api_documentation",
      "index_config": "/config/index-api-docs.json"
    }
  ]
}
```

### 3.3 Repository indexing workflow (`reindex_workflow.py`)
- Git operations: clone (first time) or pull (updates)
- Extract markdown using existing `repository-doc-extractor`
- Validate extracted JSON (calls `minerva validate`)
- Index into ChromaDB using existing config (calls `minerva index`)
- Error handling and rollback
- Notification/logging of results

**Key principle:** Webhook orchestrator **uses Minerva CLI**, doesn't import Minerva internals

**Workflow steps:**
```bash
# 1. Update repository
cd /repos/company-docs
git pull origin main

# 2. Extract markdown (using existing extractor!)
repository-doc-extractor /repos/company-docs \
  -o /extracted/company-docs.json \
  --verbose

# 3. Validate (calls Minerva CLI)
minerva validate /extracted/company-docs.json

# 4. Index (calls Minerva CLI)
minerva index --config /config/index-company-docs.json --verbose

# Note: Minerva MCP server stays running during this process
# Brief (2-3 min) stale results are acceptable
```

### 3.4 Manual reindex endpoint (optional) (`POST /reindex/{repo_name}`)
- Allow manual triggering of reindex (in webhook orchestrator)
- Protected by webhook secret or separate API key
- Useful for testing and manual updates
- Returns job status and logs
- **Note:** This is part of the webhook orchestrator, NOT Minerva core

## Phase 4: Documentation & Configuration

### 4.1 Create GitHub webhook setup guide (`docs/GITHUB_WEBHOOK_SETUP.md`)
- Prerequisites (admin access to GitHub repo/org)
- Step-by-step webhook creation
  - Navigate to repo settings → Webhooks
  - Add webhook URL: `https://minerva.yourcompany.com/webhook`
  - Set content type: `application/json`
  - Set secret: (your `WEBHOOK_SECRET`)
  - Select events: `push` only
- Testing webhook delivery
- Viewing delivery history and debugging
- Troubleshooting failed deliveries
- Organization-wide webhook setup (for multiple repos)

### 4.2 Create team member setup guide (`docs/CLIENT_SETUP.md`)

#### For Claude Code
```json
{
  "mcpServers": {
    "minerva": {
      "url": "https://minerva.yourcompany.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY_HERE"
      }
    }
  }
}
```

#### For Cursor
```json
{
  "mcp": {
    "servers": {
      "minerva": {
        "url": "https://minerva.yourcompany.com/mcp/",
        "apiKey": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

#### Troubleshooting
- Connection refused → Check server is running
- 401 Unauthorized → Check API key is correct
- Timeout → Check firewall/network
- No results → Check collections are indexed

### 4.3 Create example configurations

#### Server config (`configs/server/team-deployment.json`)
```json
{
  "chromadb_path": "/chromadb",
  "default_max_results": 5,
  "host": "0.0.0.0",
  "port": 8337,
  "api_key": "${MINERVA_API_KEY}",
  "require_auth": true
}
```

**Note:** No `webhook_secret` in Minerva config - webhooks handled by separate orchestrator tool

#### Index config example (`configs/index/repository-example.json`)
```json
{
  "chromadb_path": "/chromadb",
  "collection": {
    "name": "company_docs",
    "description": "Company documentation from GitHub",
    "json_file": "/extracted/company-docs.json",
    "chunk_size": 1200,
    "force_recreate": false
  },
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini"
  }
}
```

**Key changes from local setup:**
- Uses OpenAI instead of Ollama (cloud embeddings)
- No `base_url` needed (uses OpenAI's API)
- API key from environment variable
- Fast batch embeddings supported automatically

#### Environment variables (`.env.example`)
```bash
# Required: API key for MCP client authentication
MINERVA_API_KEY=your-secret-api-key-here

# Required: OpenAI API key for embeddings and LLM
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Webhook secret (only if using github-webhook-orchestrator)
# WEBHOOK_SECRET=your-webhook-secret-here
```

**Key changes:**
- `OPENAI_API_KEY` is now required (was optional)
- `OLLAMA_HOST` removed (not using Ollama)
- `WEBHOOK_SECRET` moved to optional (separate tool)

### 4.4 Update main documentation

#### README.md updates
- Add "Team Deployment" section
- Link to deployment guides
- Quick start for team members

#### Security best practices guide (`docs/SECURITY.md`)
- API key generation: `openssl rand -hex 32`
- Webhook secret generation: `openssl rand -hex 32`
- Key rotation procedures
- TLS/HTTPS requirements
- Network security (firewall rules)
- Environment variable management
- Secrets storage (GitHub Secrets, AWS Secrets Manager, etc.)

#### Backup and recovery guide (`docs/BACKUP.md`)
- What to backup (ChromaDB data, configs)
- Backup schedule recommendations
- Restore procedures
- Disaster recovery plan

## Deliverables

### Code Components

**Minerva Core:**
✅ API key authentication for MCP endpoints
✅ Authentication middleware (FastMCP integration)

**Separate Tool (github-webhook-orchestrator):**
✅ GitHub webhook signature validation
✅ Webhook handler (`/webhook` endpoint)
✅ Repository reindex workflow
✅ Webhook configuration management
✅ Manual reindex endpoint (optional)

### Deployment Infrastructure
✅ Dockerfile (multi-stage, optimized)
✅ docker-compose.yml (full orchestration)
✅ Caddyfile (automatic HTTPS)
✅ .dockerignore (optimized builds)

### Configuration Files
✅ Server config with auth (`team-deployment.json`)
✅ Repository index config examples
✅ Webhook repository mapping config
✅ Environment variables template (`.env.example`)

### Documentation
✅ Team deployment guide (Docker + Ubuntu options)
✅ GitHub webhook setup guide
✅ Client setup guide (Claude Code, Cursor, etc.)
✅ Security best practices
✅ Backup and recovery procedures
✅ Troubleshooting guide

## Security Architecture

### Layer 1: Network Security
- **HTTPS encryption** (Caddy + Let's Encrypt)
- **Firewall**: Only port 443 exposed
- **Localhost binding**: Minerva only accepts connections from Caddy

### Layer 2: Authentication
- **API keys** for MCP clients (Bearer token)
- **Webhook signatures** for GitHub webhooks (HMAC-SHA256)
- **Environment variables** for secrets (not in config files)

### Layer 3: Authorization
- **Single shared API key** (suitable for small team 2-5)
- **Audit logging** for all authentication events
- **Rate limiting** (optional, future enhancement)

### Layer 4: Data Security
- **Encrypted in transit** (HTTPS)
- **Isolated storage** (Docker volumes)
- **Backup strategy** (ChromaDB data persistence)

## Environment Variables Reference

**Minerva Server:**

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `MINERVA_API_KEY` | Yes | MCP client authentication | `abc123...` |
| `OPENAI_API_KEY` | Yes | OpenAI embeddings & LLM | `sk-proj-...` |

**GitHub Webhook Orchestrator (optional separate tool):**

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `WEBHOOK_SECRET` | Yes | GitHub webhook validation | `xyz789...` |
| `OPENAI_API_KEY` | Yes | Shared with Minerva | `sk-proj-...` |

## Deployment Workflow

### Initial Setup (One Time)

```bash
# 1. Clone repository on server
git clone https://github.com/yourcompany/minerva.git
cd minerva

# 2. Create environment file
cp .env.example .env
# Edit .env with your secrets

# 3. Create data directories
mkdir -p /data/chromadb
mkdir -p /data/repos
mkdir -p /data/extracted
mkdir -p /data/config

# 4. Build and run with Docker
cd deployment
docker-compose up -d

# 5. Configure DNS (A record)
# minerva.yourcompany.com → your-server-ip

# 6. Test HTTPS
curl https://minerva.yourcompany.com/health

# 7. Configure GitHub webhooks
# Follow docs/GITHUB_WEBHOOK_SETUP.md
```

### Adding a New Repository

```bash
# 1. Create index config
cat > /data/config/index-newrepo.json << 'EOF'
{
  "chromadb_path": "/chromadb",
  "collection": {
    "name": "new_repo_docs",
    "json_file": "/extracted/newrepo.json",
    ...
  },
  ...
}
EOF

# 2. Add to webhook config
# Edit /data/config/webhook-repos.json

# 3. Configure GitHub webhook
# In repo settings → Add webhook

# 4. Initial index (manual)
docker exec minerva sh -c "
  git clone https://github.com/company/newrepo /repos/newrepo &&
  repository-doc-extractor /repos/newrepo -o /extracted/newrepo.json &&
  minerva index --config /config/index-newrepo.json --verbose
"

# 5. Future updates happen automatically via webhook!
```

### Updating Minerva

```bash
# 1. Pull latest code
git pull

# 2. Rebuild Docker image
cd deployment
docker-compose build

# 3. Restart with zero downtime
docker-compose up -d

# ChromaDB data persists (mounted volumes)
```

## Testing Checklist

### Pre-Deployment
- [ ] Dockerfile builds successfully
- [ ] docker-compose starts all services
- [ ] Caddy generates HTTPS certificate
- [ ] Minerva HTTP server responds
- [ ] ChromaDB is accessible

### Authentication
- [ ] MCP client with valid API key → Success
- [ ] MCP client with invalid API key → 401 Unauthorized
- [ ] MCP client without API key → 401 Unauthorized
- [ ] GitHub webhook with valid signature → Success
- [ ] GitHub webhook with invalid signature → 403 Forbidden

### Webhook Integration
- [ ] Push to repo (no markdown changes) → No reindex
- [ ] Push to repo (with markdown changes) → Reindex triggered
- [ ] GitHub shows successful delivery
- [ ] Minerva logs show reindex completion
- [ ] Updated content searchable via MCP

### Client Integration
- [ ] Claude Code can connect and search
- [ ] Search results include updated content
- [ ] Multiple collections accessible
- [ ] Token limits respected

## Future Enhancements (Optional)

- [ ] Per-user API keys (multi-key support)
- [ ] Key rotation automation
- [ ] Rate limiting per API key
- [ ] Webhook delivery retry logic
- [ ] Reindex status dashboard
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Slack/Discord notifications on reindex
- [ ] Support for private GitHub repositories (SSH keys)
- [ ] Branch-specific indexing (e.g., only index `main` branch)

## Notes

- **Use existing `repository-doc-extractor`**: Don't create a new extractor, the existing one works perfectly!
- **Docker is recommended**: Easier setup, updates, and isolation
- **Ubuntu native option**: Available for those who prefer it
- **GitHub webhooks are better than git hooks**: Centralized, easier to manage, built-in retry logic
- **Manual testing always available**: `docker exec` commands work even with webhooks enabled
