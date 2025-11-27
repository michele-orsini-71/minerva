# Implementation Plan: Minerva Remote Server Deployment

**Date:** 2025-11-15
**Goal:** Deploy Minerva as a team server with GitHub webhook auto-reindexing
**Approach:** Iterative local-to-remote deployment with learning at each stage

## Context & Decisions

### Key Architectural Decisions
- **OpenAI for embeddings** (not Ollama) - company has API keys, fast batch embeddings
- **Webhook orchestrator is separate tool** - lives in `extractors/github-webhook-orchestrator/`, not Minerva core
- **MCP server stays running during reindexing** - ChromaDB handles concurrency safely, 2-3 min stale results acceptable
- **Source-agnostic principle** - Minerva core knows nothing about GitHub, webhooks, etc.

### Environment
- **Developer machine:** Mac (Michele's laptop)
- **OpenAI API key:** Available via `envchain openai`
- **Team size:** 2-5 developers
- **Final target:** AWS server (to be provisioned)

---

## Phase 1: Local Development & Testing (No Docker, No Network)

**Goal:** Build and validate webhook orchestrator locally on Mac

### Prerequisites
- [x] Minerva installed (editable mode)
- [x] OpenAI API key accessible via `envchain openai`
- [x] repository-doc-extractor installed
- [ ] Test repository created with markdown files

### Components to Build

#### 1.1 GitHub Webhook Orchestrator Package
**Location:** `extractors/github-webhook-orchestrator/`

**Package structure:**
```
extractors/github-webhook-orchestrator/
├── github_webhook_orchestrator/
│   ├── __init__.py
│   ├── server.py          # FastAPI/Flask webhook receiver
│   ├── github_auth.py     # HMAC-SHA256 signature validation
│   ├── reindex.py         # Orchestrates: extract → validate → index
│   └── config.py          # Load & parse config.json
├── setup.py               # pip installable package
├── config.example.json    # Example configuration
├── README.md              # Usage documentation
└── requirements.txt       # Dependencies (fastapi, uvicorn, etc.)
```

**Key implementation notes:**
- Use FastAPI for webhook server (modern, fast, easy to test)
- Server runs on port 8338 (different from Minerva MCP on 8337)
- Calls Minerva CLI via subprocess (does NOT import minerva internals)
- Validates GitHub webhook signatures (HMAC-SHA256)
- Detects markdown file changes in commit payload
- Logs everything to file for debugging

**Configuration format (`config.json`):**
```json
{
  "webhook_secret": "${WEBHOOK_SECRET}",
  "repositories": [
    {
      "name": "test-repo",
      "github_url": "https://github.com/company/test-repo",
      "local_path": "/Users/michele/test-webhook-repo",
      "collection": "test_repo_docs",
      "index_config": "/Users/michele/.minerva/configs/test-webhook-repo.json"
    }
  ],
  "log_file": "/Users/michele/.minerva/logs/webhook-orchestrator.log"
}
```

#### 1.2 Test Repository Setup
**Create test repo:**
```bash
mkdir -p ~/test-webhook-repo
cd ~/test-webhook-repo
git init
echo "# Test Documentation" > README.md
mkdir docs
echo "# Getting Started\n\nSome content here." > docs/getting-started.md
git add .
git commit -m "Initial commit"
```

**Create index config:**
```bash
mkdir -p ~/.minerva/configs
cat > ~/.minerva/configs/test-webhook-repo.json << 'EOF'
{
  "chromadb_path": "/Users/michele/.minerva/chromadb",
  "collection": {
    "name": "test_repo_docs",
    "description": "Test repository for webhook development",
    "json_file": "/Users/michele/.minerva/extracted/test-webhook-repo.json",
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
EOF
```

### Testing Steps

#### 1.3 Manual Workflow Test (Before Automation)
```bash
# Terminal 1: Start Minerva MCP server
cd ~/my-code/minerva
envchain openai minerva serve --config ~/.minerva/configs/server/local.json

# Terminal 2: Manual reindex test
cd ~/test-webhook-repo
echo "New content" >> docs/getting-started.md
git commit -am "Update docs"

# Trigger reindex manually
repository-doc-extractor ~/test-webhook-repo \
  -o ~/.minerva/extracted/test-webhook-repo.json -v

envchain openai minerva index \
  --config ~/.minerva/configs/test-webhook-repo.json --verbose

# Terminal 3: Test search in Claude Desktop
# Search for "New content" - should find it
```

#### 1.4 Webhook Orchestrator Test (Local, No GitHub)
```bash
# Terminal 1: Start Minerva MCP server
envchain openai minerva serve --config ~/.minerva/configs/server/local.json

# Terminal 2: Start webhook orchestrator
cd extractors/github-webhook-orchestrator
pip install -e .
envchain openai webhook-orchestrator --config config.json

# Terminal 3: Simulate webhook with curl
curl -X POST http://localhost:8338/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<calculated-signature>" \
  -d @test-webhook-payload.json

# Verify:
# - Orchestrator logs show: detected markdown changes
# - Orchestrator triggers: extract → validate → index
# - Minerva MCP server stays running
# - Search in Claude Desktop shows updated content
```

#### 1.5 Test with Real GitHub Webhooks (Optional)
**Requires ngrok or similar tunneling tool:**
```bash
# Terminal 1: Start ngrok
ngrok http 8338

# Terminal 2: Start webhook orchestrator
envchain openai webhook-orchestrator --config config.json

# In GitHub repo settings:
# - Add webhook URL: https://<ngrok-url>/webhook
# - Set secret from config.json
# - Select "push" events only

# Test:
cd ~/test-webhook-repo
echo "GitHub webhook test" >> docs/test.md
git add .
git commit -m "Test webhook"
git push origin main

# Verify in GitHub webhook delivery logs
# Verify in orchestrator logs
# Verify search in Claude Desktop
```

### Phase 1 Deliverables
- [x] Webhook orchestrator package (complete, tested)
- [x] Local testing without GitHub (curl simulation)
- [x] Optional: Real GitHub webhook test (ngrok)
- [x] Confidence in concurrent indexing while MCP server runs
- [x] Understanding of workflow: webhook → extract → index → search

---

## Phase 2: Dockerize Locally (Docker on Mac, No Network Exposure)

**Goal:** Package everything in Docker, test locally before server deployment

**Important:** NO Caddy in Phase 2! Just Docker services talking to each other locally.

### Prerequisites
- [ ] Docker Desktop installed on Mac
- [ ] Phase 1 complete and working
- [ ] Understanding of docker-compose basics

### Components to Build

#### 2.1 Dockerfile for Minerva + Webhook Orchestrator
**Location:** `deployment/Dockerfile`

**Multi-stage build:**
```dockerfile
FROM python:3.13-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Minerva
COPY . /app/minerva
WORKDIR /app/minerva
RUN pip install -e .

# Install extractors
RUN pip install -e extractors/repository-doc-extractor
RUN pip install -e extractors/github-webhook-orchestrator

# Create data directories
RUN mkdir -p /data/chromadb /data/repos /data/extracted /data/config /data/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8337/health || exit 1

EXPOSE 8337 8338
```

#### 2.2 Docker Compose Configuration
**Location:** `deployment/docker-compose.yml`

**Services:**
```yaml
version: '3.8'

services:
  minerva:
    build:
      context: ..
      dockerfile: deployment/Dockerfile
    environment:
      - MINERVA_API_KEY=${MINERVA_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - chromadb-data:/data/chromadb
      - repos-data:/data/repos
      - extracted-data:/data/extracted
      - ./configs:/data/config:ro
    ports:
      - "8337:8337"  # MCP server
      - "8338:8338"  # Webhook orchestrator
    command: >
      bash -c "
        minerva serve --config /data/config/server.json &
        webhook-orchestrator --config /data/config/webhook.json
      "
    restart: unless-stopped

volumes:
  chromadb-data:
  repos-data:
  extracted-data:
```

**Environment file (`.env`):**
```bash
MINERVA_API_KEY=your-generated-key-here
OPENAI_API_KEY=sk-your-key-here
```

**Important notes for Phase 2:**
- All services run in single container (simpler for now)
- Volumes persist data across restarts
- No reverse proxy yet - direct port access
- No HTTPS - plain HTTP on localhost
- Use `host.docker.internal` to access host machine if needed

#### 2.3 Configuration Files for Docker
**Location:** `deployment/configs/`

**Server config (`configs/server.json`):**
```json
{
  "chromadb_path": "/data/chromadb",
  "default_max_results": 5,
  "host": "0.0.0.0",
  "port": 8337,
  "api_key": "${MINERVA_API_KEY}",
  "require_auth": false
}
```
*Note: `require_auth: false` for Phase 2 local testing, will be `true` in Phase 3+*

**Webhook config (`configs/webhook.json`):**
```json
{
  "webhook_secret": "${WEBHOOK_SECRET}",
  "repositories": [
    {
      "name": "test-repo",
      "github_url": "https://github.com/company/test-repo",
      "local_path": "/data/repos/test-repo",
      "collection": "test_repo_docs",
      "index_config": "/data/config/index-test-repo.json"
    }
  ],
  "log_file": "/data/logs/webhook-orchestrator.log"
}
```

### Testing Steps

#### 2.4 Build and Run Docker Stack
```bash
cd deployment

# Build image
docker-compose build

# Start services
docker-compose up

# Verify services running
docker-compose ps

# Check logs
docker-compose logs -f minerva

# Test MCP server
curl http://localhost:8337/health

# Test webhook orchestrator
curl http://localhost:8338/health
```

#### 2.5 Test MCP Connection from Host
**Update Claude Desktop config to use HTTP (not stdio):**
```json
{
  "mcpServers": {
    "minerva-docker": {
      "url": "http://localhost:8337/mcp/",
      "headers": {
        "Authorization": "Bearer your-api-key-here"
      }
    }
  }
}
```

#### 2.6 Test Webhook in Docker
```bash
# Simulate webhook to Docker container
curl -X POST http://localhost:8338/webhook \
  -H "Content-Type: application/json" \
  -d @test-webhook-payload.json

# Verify logs
docker-compose logs minerva | grep webhook

# Verify reindex happened
docker exec -it deployment_minerva_1 \
  minerva peek test_repo_docs --chromadb /data/chromadb
```

#### 2.7 Test Data Persistence
```bash
# Stop containers
docker-compose down

# Start again
docker-compose up

# Verify data still there
docker exec -it deployment_minerva_1 \
  minerva peek test_repo_docs --chromadb /data/chromadb
```

### Phase 2 Deliverables
- [ ] Working Dockerfile
- [ ] Working docker-compose.yml
- [ ] MCP server accessible via HTTP from host
- [ ] Webhook orchestrator accessible from host
- [ ] Data persists across container restarts
- [ ] Portable package (can share with teammate)

**Portable Package Contents:**
```
minerva-docker-package/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── configs/
│   ├── server.json
│   ├── webhook.json
│   └── index-example.json
├── README.md
└── test-webhook-payload.json
```

---

## Phase 3: Your Mac as Remote Server (Learn Reverse Proxy & HTTPS)

**Goal:** Expose Docker stack to network, add Caddy reverse proxy, enable HTTPS

**THIS is where Caddy comes in!**

### Prerequisites
- [ ] Phase 2 complete and working
- [ ] Understanding of reverse proxy concept
- [ ] Willingness to deal with self-signed cert warnings (for local testing)

### New Components

#### 3.1 Add Caddy to Docker Compose
**Updated `docker-compose.yml`:**
```yaml
services:
  minerva:
    # ... (same as Phase 2)
    # Remove port mappings (Caddy will handle)
    # ports: (commented out)

  caddy:
    image: caddy:2-alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    depends_on:
      - minerva
    restart: unless-stopped

volumes:
  # ... (existing volumes)
  caddy-data:
  caddy-config:
```

#### 3.2 Caddyfile Configuration
**Location:** `deployment/Caddyfile`

**For local testing (self-signed cert):**
```
https://minerva.local {
    tls internal  # Self-signed cert

    # MCP server endpoints
    reverse_proxy /mcp/* minerva:8337

    # Webhook endpoint
    reverse_proxy /webhook minerva:8338

    # Health check
    reverse_proxy /health minerva:8337

    log {
        output file /data/access.log
        format json
    }
}
```

#### 3.3 Local DNS Setup
**Add to `/etc/hosts`:**
```
127.0.0.1 minerva.local
```

### Testing Steps

#### 3.4 Test HTTPS Locally
```bash
cd deployment
docker-compose up

# Test HTTPS (will get cert warning, that's OK)
curl -k https://minerva.local/health

# Test MCP via HTTPS
# Update Claude Desktop config:
# "url": "https://minerva.local/mcp/"
```

#### 3.5 Enable Authentication
**Update `configs/server.json`:**
```json
{
  "require_auth": true,
  "api_key": "${MINERVA_API_KEY}"
}
```

**Test with Bearer token:**
```bash
curl -k https://minerva.local/mcp/search \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

#### 3.6 Test from Another Device on LAN
**Get your Mac's IP address:**
```bash
ifconfig en0 | grep "inet "
# Example: 192.168.1.100
```

**Update Caddyfile for LAN access:**
```
https://192.168.1.100 {
    tls internal
    # ... (same reverse proxy config)
}
```

**From another computer:**
```bash
# Will get cert warning (self-signed)
curl -k https://192.168.1.100/health
```

### Phase 3 Deliverables
- [ ] Caddy reverse proxy working
- [ ] HTTPS enabled (self-signed cert)
- [ ] Authentication working (Bearer token)
- [ ] Accessible from other devices on LAN
- [ ] Understanding of how reverse proxy works
- [ ] Confidence in SSL/TLS setup

**Key Learnings:**
- How Caddy routes requests to backend services
- How SSL/TLS certificates work
- How to debug network connectivity issues
- How to test with self-signed certs

---

## Phase 4: AWS Deployment (Real Remote Server)

**Goal:** Deploy to production AWS instance with real SSL certificate

### Prerequisites
- [ ] Phase 3 complete and working
- [ ] AWS instance provisioned by DevOps
- [ ] Domain name pointing to server (e.g., minerva.yourcompany.com)

### AWS Instance Requirements
**Coordinate with DevOps:**
- **Instance type:** t3.medium or larger (2 vCPU, 4GB RAM)
- **OS:** Ubuntu 22.04 LTS
- **Storage:** 50GB+ EBS volume
- **Security group:**
  - Inbound: Port 443 (HTTPS) from anywhere
  - Inbound: Port 80 (HTTP) from anywhere (Caddy redirects to HTTPS)
  - Inbound: Port 22 (SSH) from your IP only
- **Elastic IP:** Static IP address assigned

### DNS Setup
**Coordinate with DevOps:**
```
A record: minerva.yourcompany.com → <AWS Elastic IP>
```
Wait for DNS propagation (5-60 minutes)

### Deployment Steps

#### 4.1 Prepare Server
**SSH to server:**
```bash
ssh ubuntu@<elastic-ip>

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose

# Create directories
mkdir -p ~/minerva-deployment
cd ~/minerva-deployment
```

#### 4.2 Transfer Docker Package
**From your Mac:**
```bash
# Create deployment archive
cd ~/my-code/minerva
tar -czf minerva-docker.tar.gz deployment/

# Copy to server
scp minerva-docker.tar.gz ubuntu@<elastic-ip>:~/minerva-deployment/

# SSH to server and extract
ssh ubuntu@<elastic-ip>
cd ~/minerva-deployment
tar -xzf minerva-docker.tar.gz
cd deployment
```

#### 4.3 Update Caddyfile for Production
**Edit `Caddyfile`:**
```
minerva.yourcompany.com {
    # Caddy automatically gets Let's Encrypt cert!

    reverse_proxy /mcp/* minerva:8337
    reverse_proxy /webhook minerva:8338

    log {
        output file /data/access.log
        format json
    }
}
```

#### 4.4 Configure Environment
**Create `.env` file:**
```bash
# Generate secure keys
MINERVA_API_KEY=$(openssl rand -hex 32)
WEBHOOK_SECRET=$(openssl rand -hex 32)
OPENAI_API_KEY=sk-your-company-key-here

# Save to .env
echo "MINERVA_API_KEY=$MINERVA_API_KEY" > .env
echo "WEBHOOK_SECRET=$WEBHOOK_SECRET" >> .env
echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env

# Secure the file
chmod 600 .env
```

**Save API key for distribution:**
```bash
echo "Minerva API Key for team: $MINERVA_API_KEY" > ~/api-key-for-team.txt
chmod 600 ~/api-key-for-team.txt
```

#### 4.5 Start Services
```bash
cd ~/minerva-deployment/deployment

# Pull/build images
docker-compose build

# Start in background
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify services
curl https://minerva.yourcompany.com/health
```

#### 4.6 Initial Indexing
**Clone company repositories:**
```bash
# Enter container
docker exec -it deployment_minerva_1 bash

# Inside container
cd /data/repos
git clone https://github.com/yourcompany/docs.git company-docs
git clone https://github.com/yourcompany/api.git api-docs

# Extract and index
repository-doc-extractor /data/repos/company-docs \
  -o /data/extracted/company-docs.json -v

minerva index --config /data/config/index-company-docs.json --verbose

# Repeat for other repos
```

#### 4.7 Setup GitHub Webhooks
**For each repository:**
1. Go to GitHub repo → Settings → Webhooks → Add webhook
2. **Payload URL:** `https://minerva.yourcompany.com/webhook`
3. **Content type:** `application/json`
4. **Secret:** (use `$WEBHOOK_SECRET` from `.env`)
5. **Events:** Just the push event
6. **Active:** ✓

**Test webhook:**
```bash
# Make a change to repo
cd ~/local/company-docs
echo "Test" >> README.md
git commit -am "Test webhook"
git push

# Check webhook delivery in GitHub
# Check logs on server
docker-compose logs minerva | grep webhook
```

#### 4.8 Team Onboarding
**Distribute to team:**
```
Minerva is now available!

MCP Server URL: https://minerva.yourcompany.com/mcp/
API Key: <from ~/api-key-for-team.txt>

Claude Desktop config:
{
  "mcpServers": {
    "minerva": {
      "url": "https://minerva.yourcompany.com/mcp/",
      "headers": {
        "Authorization": "Bearer <API_KEY>"
      }
    }
  }
}

Test by searching: "How do I configure X?"
```

### Phase 4 Deliverables
- [ ] Production server running on AWS
- [ ] Real SSL certificate (Let's Encrypt via Caddy)
- [ ] All company repos indexed
- [ ] GitHub webhooks configured and tested
- [ ] Team members onboarded and using Minerva
- [ ] Monitoring and logs accessible

---

## Operations to Perform Before Starting Implementation

### Pre-Implementation Checklist

**We need to discuss:**
- [ ] Which operations need to be done before Phase 1?
- [ ] Any existing code that needs to be reviewed/modified?
- [ ] Any dependencies to install?
- [ ] Any config files to create?

**Waiting for Michele's input on:**
> "we have a couple of operations to perform before starting the implementation, we will talk about them later"

---

## Notes & Reminders

### Important Principles
1. **Webhook orchestrator is separate from Minerva core** - keep this clean separation
2. **Use Minerva CLI, don't import internals** - orchestrator calls `minerva index` via subprocess
3. **Test incrementally** - don't skip phases, each builds confidence
4. **Document learnings** - especially for unfamiliar parts (Caddy, reverse proxy, SSL)

### Environment Variables Summary
| Variable | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|----------|---------|---------|---------|---------|
| `OPENAI_API_KEY` | envchain | .env | .env | .env |
| `MINERVA_API_KEY` | N/A | .env (optional) | .env (required) | .env (required) |
| `WEBHOOK_SECRET` | hardcoded | .env | .env | .env |

### Key Files to Track
- `extractors/github-webhook-orchestrator/` - New package we're building
- `deployment/Dockerfile` - Docker image definition
- `deployment/docker-compose.yml` - Service orchestration
- `deployment/Caddyfile` - Reverse proxy config (Phase 3+)
- `tasks/2025-11-15-implementation-plan.md` - This document

### Success Criteria
- [ ] Phase 1: Webhook triggers reindex while MCP server runs (local Mac)
- [ ] Phase 2: Everything works in Docker (local Mac)
- [ ] Phase 3: Accessible via HTTPS on LAN
- [ ] Phase 4: Team using production server

---

## Next Steps

**Current Status:** Planning complete, ready to implement Phase 1

**Immediate Next Actions:**
1. Michele to specify the "couple of operations to perform before starting"
2. Build webhook orchestrator package (Option A: complete implementation)
3. Test locally (Phase 1)
4. Iterate based on learnings
