# Phase 2 Tasks: GitHub Webhook Auto-Reindex (Docker Local)

**PRD:** `/tasks/2025-11-15-prd-github-webhook-auto-reindex.md`
**Phase:** Phase 2 - Dockerize Locally (Docker on Mac, No Network Exposure)
**Goal:** Package everything in Docker, test locally before server deployment
**Prerequisites:** Phase 1 complete

---

## Relevant Files

### Created Files
- `deployment/Dockerfile` - Docker image for Minerva + webhook orchestrator with Python 3.13-slim, git, curl, health checks
- `deployment/entrypoint.sh` - Container startup script with signal handling, health checks, and graceful shutdown

### New Files to Create
- `deployment/docker-compose.yml` - Service orchestration (NO Caddy in Phase 2)
- `deployment/.dockerignore` - Exclude unnecessary files from Docker build
- `deployment/configs/server.json` - Minerva MCP server configuration for Docker
- `deployment/configs/webhook.json` - Webhook orchestrator configuration for Docker
- `deployment/configs/index-test-repo.json` - Example index configuration for Docker
- `deployment/entrypoint.sh` - Container startup script (runs both MCP server and webhook orchestrator)
- `deployment/README.md` - Docker deployment documentation

### Modified Files
- None (Phase 2 is additive, doesn't modify existing code)

### Test Files
- `deployment/test-webhook-payload.json` - Sample webhook payload for testing Docker deployment
- `deployment/test-docker.sh` - Shell script to test Docker deployment

### Notes
- NO Caddy reverse proxy in Phase 2 (that's Phase 3)
- Direct port access: 8337 (MCP), 8338 (webhook)
- Plain HTTP on localhost only
- Use envchain to inject secrets into docker-compose
- Follow Docker best practices: multi-stage builds, minimal layers, health checks

---

## Tasks

- [x] 1.0 Create Dockerfile for Minerva + Webhook Orchestrator
    - [x] 1.1 Create `deployment/Dockerfile`
    - [x] 1.2 Use `python:3.13-slim` as base image
    - [x] 1.3 Install system dependencies: git (for git pull in reindex workflow)
    - [x] 1.4 Copy Minerva source code to `/app/minerva`
    - [x] 1.5 Install Minerva in editable mode: `pip install -e /app/minerva`
    - [x] 1.6 Install repository-doc-extractor: `pip install -e /app/minerva/extractors/repository-doc-extractor`
    - [x] 1.7 Install github-webhook-orchestrator: `pip install -e /app/minerva/extractors/github-webhook-orchestrator`
    - [x] 1.8 Create data directories: `/data/chromadb`, `/data/repos`, `/data/extracted`, `/data/config`, `/data/logs`
    - [x] 1.9 Add HEALTHCHECK instruction for `/health` endpoint on port 8337
    - [x] 1.10 Expose ports 8337 (MCP) and 8338 (webhook)
    - [x] 1.11 Set working directory to `/app/minerva`

- [x] 2.0 Create Container Entrypoint Script
    - [x] 2.1 Create `deployment/entrypoint.sh`
    - [x] 2.2 Make script executable: `chmod +x deployment/entrypoint.sh`
    - [x] 2.3 Start Minerva MCP server in background: `minerva serve --config /data/config/server.json &`
    - [x] 2.4 Wait for MCP server to start (check health endpoint or wait 5 seconds)
    - [x] 2.5 Start webhook orchestrator in foreground: `webhook-orchestrator --config /data/config/webhook.json`
    - [x] 2.6 Add signal handling to gracefully shutdown both processes on SIGTERM
    - [x] 2.7 Log startup messages to stdout for docker logs visibility

- [ ] 3.0 Create Docker Compose Configuration
    - [ ] 3.1 Create `deployment/docker-compose.yml`
    - [ ] 3.2 Define single service: `minerva` (combined MCP server + webhook orchestrator)
    - [ ] 3.3 Build context: parent directory (`..`), dockerfile: `deployment/Dockerfile`
    - [ ] 3.4 Map environment variables: OPENAI_API_KEY, MINERVA_API_KEY, WEBHOOK_SECRET, GITHUB_TOKEN
    - [ ] 3.5 Create named volumes: chromadb-data, repos-data, extracted-data
    - [ ] 3.6 Mount volume `chromadb-data:/data/chromadb`
    - [ ] 3.7 Mount volume `repos-data:/data/repos`
    - [ ] 3.8 Mount volume `extracted-data:/data/extracted`
    - [ ] 3.9 Mount `./configs:/data/config:ro` (read-only config files from host)
    - [ ] 3.10 Expose ports: `8337:8337` and `8338:8338`
    - [ ] 3.11 Set restart policy: `unless-stopped`
    - [ ] 3.12 Set entrypoint: `/app/minerva/deployment/entrypoint.sh`

- [ ] 4.0 Create Docker Configuration Files
    - [ ] 4.1 Create `deployment/configs/server.json` for MCP server
    - [ ] 4.2 Set chromadb_path to `/data/chromadb`
    - [ ] 4.3 Set host to `0.0.0.0` (listen on all interfaces in container)
    - [ ] 4.4 Set port to `8337`
    - [ ] 4.5 Set api_key to `${MINERVA_API_KEY}` (resolved from environment)
    - [ ] 4.6 Set require_auth to `false` for Phase 2 (localhost testing only)
    - [ ] 4.7 Set default_max_results to `5`
    - [ ] 4.8 Create `deployment/configs/webhook.json` for webhook orchestrator
    - [ ] 4.9 Set webhook_secret to `${WEBHOOK_SECRET}`
    - [ ] 4.10 Add test repository to repositories list
    - [ ] 4.11 Set local_path to `/data/repos/test-repo`
    - [ ] 4.12 Set index_config to `/data/config/index-test-repo.json`
    - [ ] 4.13 Set log_file to `/data/logs/webhook-orchestrator.log`
    - [ ] 4.14 Create `deployment/configs/index-test-repo.json`
    - [ ] 4.15 Set chromadb_path to `/data/chromadb`
    - [ ] 4.16 Set collection name to `test_repo_docs`
    - [ ] 4.17 Set json_file to `/data/extracted/test-repo.json`
    - [ ] 4.18 Set provider to OpenAI with `${OPENAI_API_KEY}`

- [ ] 5.0 Create .dockerignore File
    - [ ] 5.1 Create `deployment/.dockerignore`
    - [ ] 5.2 Exclude `.git/` directory
    - [ ] 5.3 Exclude `chromadb_data/` directory
    - [ ] 5.4 Exclude `test-data/` directory
    - [ ] 5.5 Exclude `__pycache__/` and `*.pyc` files
    - [ ] 5.6 Exclude `.env` files
    - [ ] 5.7 Exclude `*.md` documentation files (keep in source, not needed in image)
    - [ ] 5.8 Keep only necessary files for runtime

- [ ] 6.0 Build and Test Docker Image
    - [ ] 6.1 Navigate to deployment directory: `cd deployment`
    - [ ] 6.2 Build Docker image: `docker-compose build`
    - [ ] 6.3 Verify image builds successfully (no errors)
    - [ ] 6.4 Check image size (should be reasonable, not multi-GB)
    - [ ] 6.5 Inspect image layers: `docker history <image-id>`
    - [ ] 6.6 Verify all dependencies installed correctly

- [ ] 7.0 Start Docker Services with envchain
    - [ ] 7.1 Ensure secrets are in envchain: OPENAI_API_KEY, WEBHOOK_SECRET
    - [ ] 7.2 Generate MINERVA_API_KEY: `openssl rand -hex 32`
    - [ ] 7.3 Store MINERVA_API_KEY in envchain
    - [ ] 7.4 Start services with envchain: `envchain openai envchain minerva docker-compose up`
    - [ ] 7.5 Verify both services start successfully (check logs)
    - [ ] 7.6 Verify MCP server logs: "Server running on port 8337"
    - [ ] 7.7 Verify webhook orchestrator logs: "Server running on port 8338"
    - [ ] 7.8 Check for any startup errors in logs

- [ ] 8.0 Test MCP Server from Host
    - [ ] 8.1 Test health endpoint: `curl http://localhost:8337/health`
    - [ ] 8.2 Verify response: 200 OK
    - [ ] 8.3 Update Claude Desktop config to use HTTP MCP server
    - [ ] 8.4 Set URL to `http://localhost:8337/mcp/`
    - [ ] 8.5 Set Authorization header with Bearer token (MINERVA_API_KEY)
    - [ ] 8.6 Restart Claude Desktop
    - [ ] 8.7 Test search query in Claude Desktop
    - [ ] 8.8 Verify search works (may return no results if no collections indexed yet)

- [ ] 9.0 Test Webhook Orchestrator from Host
    - [ ] 9.1 Test health endpoint: `curl http://localhost:8338/health`
    - [ ] 9.2 Verify response: 200 OK
    - [ ] 9.3 Copy test webhook payload to deployment directory
    - [ ] 9.4 Compute HMAC-SHA256 signature for payload using WEBHOOK_SECRET
    - [ ] 9.5 Send test webhook: `curl -X POST http://localhost:8338/webhook -H "Content-Type: application/json" -H "X-Hub-Signature-256: sha256=<signature>" -d @test-webhook-payload.json`
    - [ ] 9.6 Verify response: 200 OK or appropriate error message
    - [ ] 9.7 Check webhook orchestrator logs: `docker-compose logs minerva | grep webhook`
    - [ ] 9.8 Verify signature validation occurred
    - [ ] 9.9 If markdown changes in payload, verify reindex was attempted

- [ ] 10.0 Test Full Workflow in Docker
    - [ ] 10.1 Clone test repository into Docker volume: `docker exec deployment_minerva_1 git clone <test-repo-url> /data/repos/test-repo`
    - [ ] 10.2 Extract initial content: `docker exec deployment_minerva_1 repository-doc-extractor /data/repos/test-repo -o /data/extracted/test-repo.json`
    - [ ] 10.3 Index initial content: `docker exec deployment_minerva_1 minerva index --config /data/config/index-test-repo.json`
    - [ ] 10.4 Verify collection created: `docker exec deployment_minerva_1 minerva peek test_repo_docs --chromadb /data/chromadb`
    - [ ] 10.5 Search for content in Claude Desktop
    - [ ] 10.6 Verify search results include test repository content
    - [ ] 10.7 Make change to test repository (on host, if it's a local repo)
    - [ ] 10.8 Send webhook with updated payload (reflecting new commit)
    - [ ] 10.9 Verify webhook triggers reindex successfully (check logs)
    - [ ] 10.10 Verify updated content is searchable in Claude Desktop

- [ ] 11.0 Test Data Persistence
    - [ ] 11.1 Stop Docker containers: `docker-compose down`
    - [ ] 11.2 Verify volumes still exist: `docker volume ls | grep deployment`
    - [ ] 11.3 Restart containers: `envchain openai envchain minerva docker-compose up`
    - [ ] 11.4 Verify MCP server and webhook orchestrator start successfully
    - [ ] 11.5 Check that ChromaDB data persisted (collections still exist)
    - [ ] 11.6 Run peek command: `docker exec deployment_minerva_1 minerva peek test_repo_docs --chromadb /data/chromadb`
    - [ ] 11.7 Verify data is intact (same number of notes/chunks)
    - [ ] 11.8 Test search in Claude Desktop
    - [ ] 11.9 Verify search results match previous results (data persisted correctly)

- [ ] 12.0 Test Container Restart and Recovery
    - [ ] 12.1 Restart container: `docker-compose restart minerva`
    - [ ] 12.2 Verify both services restart cleanly (check logs)
    - [ ] 12.3 Test MCP server health: `curl http://localhost:8337/health`
    - [ ] 12.4 Test webhook orchestrator health: `curl http://localhost:8338/health`
    - [ ] 12.5 Send test webhook to verify orchestrator still processing
    - [ ] 12.6 Simulate crash: `docker kill deployment_minerva_1`
    - [ ] 12.7 Verify container restarts automatically (restart policy: unless-stopped)
    - [ ] 12.8 Check that services recover successfully after crash

- [ ] 13.0 Create Portable Docker Package
    - [ ] 13.1 Create `deployment/README.md` with comprehensive documentation
    - [ ] 13.2 Document prerequisites: Docker, Docker Compose, envchain
    - [ ] 13.3 Document environment variable setup with envchain
    - [ ] 13.4 Document build instructions: `docker-compose build`
    - [ ] 13.5 Document run instructions: `envchain <namespace> docker-compose up`
    - [ ] 13.6 Document how to check logs: `docker-compose logs -f`
    - [ ] 13.7 Document how to exec into container: `docker exec -it deployment_minerva_1 bash`
    - [ ] 13.8 Document how to manage volumes (backup, restore, cleanup)
    - [ ] 13.9 Create archive: `tar -czf minerva-docker-package.tar.gz deployment/`
    - [ ] 13.10 Test extracting and running archive on clean Docker environment
    - [ ] 13.11 Verify package is self-contained and works without source repository

- [ ] 14.0 Create Testing Script
    - [ ] 14.1 Create `deployment/test-docker.sh` shell script
    - [ ] 14.2 Automate build process
    - [ ] 14.3 Automate service startup
    - [ ] 14.4 Test health endpoints (MCP and webhook)
    - [ ] 14.5 Test basic webhook delivery
    - [ ] 14.6 Test data persistence (stop/start cycle)
    - [ ] 14.7 Output clear success/failure messages
    - [ ] 14.8 Make script executable: `chmod +x deployment/test-docker.sh`
    - [ ] 14.9 Run test script to validate: `./deployment/test-docker.sh`
    - [ ] 14.10 Verify all tests pass

- [ ] 15.0 Documentation and Cleanup
    - [ ] 15.1 Update main README.md with Docker deployment section
    - [ ] 15.2 Link to `deployment/README.md` for detailed instructions
    - [ ] 15.3 Document differences between Phase 1 (local) and Phase 2 (Docker)
    - [ ] 15.4 Add troubleshooting section for common Docker issues
    - [ ] 15.5 Document how to view logs: `docker-compose logs -f minerva`
    - [ ] 15.6 Document how to clean up: `docker-compose down -v` (removes volumes)
    - [ ] 15.7 Add notes about using envchain with Docker
    - [ ] 15.8 Commit all Docker files to git repository
    - [ ] 15.9 Tag as `phase-2-complete`

---

## Phase 2 Completion Criteria

Phase 2 is complete when:
- ✅ Docker image builds successfully
- ✅ docker-compose starts both services successfully
- ✅ MCP server accessible via HTTP from host machine (http://localhost:8337)
- ✅ Webhook orchestrator accessible from host machine (http://localhost:8338)
- ✅ Data persists across container restarts (volumes working)
- ✅ Full workflow tested: webhook → reindex → search
- ✅ Portable package created and tested
- ✅ Documentation complete and accurate
- ✅ All code committed to git repository

---

## Notes for Phase 3

After Phase 2 completion:
- Docker deployment is working and tested locally
- Ready to add Caddy reverse proxy for HTTPS
- Configuration patterns are established for containerized deployment
- Can expose to network with minimal additional work
- Ready to test Mac as remote server on LAN
