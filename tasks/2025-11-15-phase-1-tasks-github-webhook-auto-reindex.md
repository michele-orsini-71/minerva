# Phase 1 Tasks: GitHub Webhook Auto-Reindex (Local Development)

**PRD:** `/tasks/2025-11-15-prd-github-webhook-auto-reindex.md`
**Phase:** Phase 1 - Local Development & Testing (No Docker, No Network)
**Goal:** Build and validate webhook orchestrator locally on Mac

---

## Relevant Files

### Created Files
- `extractors/github-webhook-orchestrator/github_webhook_orchestrator/__init__.py` - Package initialization with version and author metadata
- `extractors/github-webhook-orchestrator/setup.py` - Package setup following repository-doc-extractor pattern
- `extractors/github-webhook-orchestrator/requirements.txt` - Dependencies (FastAPI, uvicorn, requests)
- `extractors/github-webhook-orchestrator/README.md` - Comprehensive usage documentation and examples
- `extractors/github-webhook-orchestrator/github_webhook_orchestrator/github_auth.py` - HMAC-SHA256 signature validation with constant-time comparison
- `extractors/github-webhook-orchestrator/tests/__init__.py` - Test package initialization
- `extractors/github-webhook-orchestrator/tests/test_github_auth.py` - Comprehensive unit tests for signature validation (11 test cases)
- `extractors/github-webhook-orchestrator/github_webhook_orchestrator/config.py` - Configuration loading with dataclasses, env var resolution, and validation
- `extractors/github-webhook-orchestrator/config.example.json` - Example configuration file with documentation
- `extractors/github-webhook-orchestrator/tests/test_config.py` - Comprehensive unit tests for configuration loading (22 test cases)

### Files to Create
- `extractors/github-webhook-orchestrator/github_webhook_orchestrator/server.py` - FastAPI webhook receiver
- `extractors/github-webhook-orchestrator/github_webhook_orchestrator/reindex.py` - Reindex workflow orchestration

### Test Files to Create
- `extractors/github-webhook-orchestrator/test_webhook_payload.json` - Sample GitHub webhook payload for testing
- `extractors/github-webhook-orchestrator/tests/test_reindex.py` - Unit tests for reindex workflow

### Test Data
- `~/test-webhook-repo/` - Test repository with markdown files
- `~/.minerva/configs/test-webhook-repo.json` - Index configuration for test repository
- `~/.minerva/extracted/test-webhook-repo.json` - Extracted notes from test repository

### Notes
- Unit tests will be written for core logic (signature validation, config parsing, markdown detection)
- E2E tests will be performed manually to avoid long-running/unstable tests
- Follow existing extractor package patterns (see `extractors/repository-doc-extractor/`)

---

## Tasks

- [x] 1.0 Create GitHub Webhook Orchestrator Package Structure
    - [x] 1.1 Create directory structure: `extractors/github-webhook-orchestrator/github_webhook_orchestrator/`
    - [x] 1.2 Create `__init__.py` with package metadata (version, author)
    - [x] 1.3 Create `setup.py` following pattern from `repository-doc-extractor/setup.py`
    - [x] 1.4 Create `requirements.txt` with dependencies: fastapi, uvicorn, requests
    - [x] 1.5 Create `README.md` with installation and usage instructions
    - [x] 1.6 Install package in editable mode: `pip install -e extractors/github-webhook-orchestrator/`

- [x] 2.0 Implement GitHub Webhook Signature Validation
    - [x] 2.1 Create `github_auth.py` module
    - [x] 2.2 Implement `validate_signature(payload_body: bytes, signature_header: str, secret: str) -> bool` function
    - [x] 2.3 Use HMAC-SHA256 to compute expected signature from payload and secret
    - [x] 2.4 Compare computed signature with provided signature (constant-time comparison)
    - [x] 2.5 Return True if signatures match, False otherwise
    - [x] 2.6 Handle edge cases: missing signature, invalid format, empty secret
    - [x] 2.7 Write unit tests in `tests/test_github_auth.py` covering valid/invalid signatures

- [x] 3.0 Implement Configuration Management
    - [x] 3.1 Create `config.py` module
    - [x] 3.2 Define `WebhookConfig` dataclass with fields: webhook_secret, repositories (list), log_file
    - [x] 3.3 Define `RepositoryConfig` dataclass with fields: name, github_url, local_path, collection, index_config
    - [x] 3.4 Implement `load_config(config_path: str) -> WebhookConfig` function
    - [x] 3.5 Parse JSON configuration file
    - [x] 3.6 Resolve environment variable substitutions (e.g., `${WEBHOOK_SECRET}`)
    - [x] 3.7 Validate configuration (required fields present, paths exist)
    - [x] 3.8 Create `config.example.json` with well-documented example configuration
    - [x] 3.9 Write unit tests in `tests/test_config.py` for config loading and validation

- [ ] 4.0 Implement Reindex Workflow Orchestration
    - [ ] 4.1 Create `reindex.py` module
    - [ ] 4.2 Implement `detect_markdown_changes(commits: list) -> bool` function
    - [ ] 4.3 Parse commit list from webhook payload, extract added/modified/removed files
    - [ ] 4.4 Check if any files end with `.md` or `.mdx`
    - [ ] 4.5 Return True if markdown files changed, False otherwise
    - [ ] 4.6 Implement `execute_reindex(repo_config: RepositoryConfig) -> bool` function
    - [ ] 4.7 Execute `git pull origin main` in repository's local_path (using subprocess)
    - [ ] 4.8 Execute `repository-doc-extractor <local_path> -o <output_json>` (using subprocess)
    - [ ] 4.9 Execute `minerva validate <output_json>` (using subprocess)
    - [ ] 4.10 Execute `minerva index --config <index_config>` with OPENAI_API_KEY from envchain (using subprocess)
    - [ ] 4.11 Capture stdout/stderr from each command for logging
    - [ ] 4.12 Return True if all commands succeed (exit code 0), False otherwise
    - [ ] 4.13 Implement error handling: log failures, return appropriate exit codes
    - [ ] 4.14 Write unit tests in `tests/test_reindex.py` for markdown detection logic

- [ ] 5.0 Implement FastAPI Webhook Server
    - [ ] 5.1 Create `server.py` module
    - [ ] 5.2 Initialize FastAPI app
    - [ ] 5.3 Implement `POST /webhook` endpoint
    - [ ] 5.4 Extract raw request body for signature validation
    - [ ] 5.5 Extract `X-Hub-Signature-256` header from request
    - [ ] 5.6 Call `validate_signature()` with body, header, and config secret
    - [ ] 5.7 Return 403 Forbidden if signature validation fails
    - [ ] 5.8 Parse webhook payload JSON
    - [ ] 5.9 Check event type (only process `push` events, ignore others)
    - [ ] 5.10 Extract repository name from payload
    - [ ] 5.11 Find matching repository config by name
    - [ ] 5.12 Call `detect_markdown_changes()` with commits from payload
    - [ ] 5.13 If no markdown changes, return 200 OK with message "no markdown changes"
    - [ ] 5.14 If markdown changes detected, call `execute_reindex()` with repository config
    - [ ] 5.15 Return 200 OK if reindex succeeds, 500 Internal Server Error if reindex fails
    - [ ] 5.16 Log all webhook events (timestamp, repo, event type, outcome) to configured log file
    - [ ] 5.17 Implement `GET /health` endpoint for health checks (returns 200 OK)
    - [ ] 5.18 Create `main()` function to load config and run uvicorn server on port 8338

- [ ] 6.0 Create Test Repository and Configuration
    - [ ] 6.1 Create `~/test-webhook-repo/` directory
    - [ ] 6.2 Initialize git repository: `git init`
    - [ ] 6.3 Create `README.md` with initial content
    - [ ] 6.4 Create `docs/` directory
    - [ ] 6.5 Create `docs/getting-started.md` with sample content
    - [ ] 6.6 Commit initial files: `git add . && git commit -m "Initial commit"`
    - [ ] 6.7 Create `~/.minerva/configs/test-webhook-repo.json` index configuration
    - [ ] 6.8 Set provider to OpenAI with `${OPENAI_API_KEY}` from envchain
    - [ ] 6.9 Set chromadb_path to `~/.minerva/chromadb`
    - [ ] 6.10 Set collection name to `test_repo_docs`
    - [ ] 6.11 Set json_file to `~/.minerva/extracted/test-webhook-repo.json`

- [ ] 7.0 Manual Testing - Local Workflow (Before Automation)
    - [ ] 7.1 Start Minerva MCP server in Terminal 1: `envchain openai minerva serve --config <config>`
    - [ ] 7.2 Verify MCP server is running (check logs or health endpoint)
    - [ ] 7.3 In Terminal 2, manually extract test repository
    - [ ] 7.4 Run: `repository-doc-extractor ~/test-webhook-repo -o ~/.minerva/extracted/test-webhook-repo.json -v`
    - [ ] 7.5 Verify extraction succeeded (check JSON file exists and is valid)
    - [ ] 7.6 Run: `envchain openai minerva validate ~/.minerva/extracted/test-webhook-repo.json`
    - [ ] 7.7 Verify validation succeeded
    - [ ] 7.8 Run: `envchain openai minerva index --config ~/.minerva/configs/test-webhook-repo.json --verbose`
    - [ ] 7.9 Verify indexing succeeded (check logs for success message)
    - [ ] 7.10 In Claude Desktop, search for content from test repository
    - [ ] 7.11 Verify search results include content from test repository
    - [ ] 7.12 Verify Minerva MCP server stayed running during entire workflow (no downtime)

- [ ] 8.0 Manual Testing - Webhook Orchestrator (Local, No GitHub)
    - [ ] 8.1 Create webhook orchestrator config: `extractors/github-webhook-orchestrator/config.json`
    - [ ] 8.2 Set webhook_secret to a test value (or use `${WEBHOOK_SECRET}` from envchain)
    - [ ] 8.3 Add test repository to repositories list
    - [ ] 8.4 Set log_file to `~/.minerva/logs/webhook-orchestrator.log`
    - [ ] 8.5 Create test webhook payload: `test_webhook_payload.json`
    - [ ] 8.6 Use real GitHub webhook payload format (search GitHub webhook docs)
    - [ ] 8.7 Include test repository name in payload
    - [ ] 8.8 Include commits with markdown file changes (added/modified)
    - [ ] 8.9 Start Minerva MCP server in Terminal 1
    - [ ] 8.10 Start webhook orchestrator in Terminal 2: `envchain openai webhook-orchestrator --config config.json`
    - [ ] 8.11 Verify orchestrator starts successfully on port 8338
    - [ ] 8.12 In Terminal 3, compute HMAC-SHA256 signature for test payload
    - [ ] 8.13 Send webhook with curl: `curl -X POST http://localhost:8338/webhook -H "Content-Type: application/json" -H "X-Hub-Signature-256: sha256=<signature>" -d @test_webhook_payload.json`
    - [ ] 8.14 Verify webhook orchestrator logs show: received webhook, validated signature, detected markdown changes
    - [ ] 8.15 Verify orchestrator triggered: git pull, extract, validate, index
    - [ ] 8.16 Verify Minerva MCP server stayed running (concurrent operation works)
    - [ ] 8.17 Make a change to test repository markdown file
    - [ ] 8.18 Commit change: `git commit -am "Test webhook trigger"`
    - [ ] 8.19 Send webhook again with updated payload
    - [ ] 8.20 Verify updated content is searchable in Claude Desktop within 5 minutes
    - [ ] 8.21 Check orchestrator logs for any errors or warnings

- [ ] 9.0 Manual Testing - Real GitHub Webhook (Optional, Requires ngrok)
    - [ ] 9.1 Install ngrok: `brew install ngrok` (if not already installed)
    - [ ] 9.2 Start ngrok tunnel: `ngrok http 8338`
    - [ ] 9.3 Copy ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)
    - [ ] 9.4 In GitHub repository settings, add webhook
    - [ ] 9.5 Set Payload URL to `<ngrok-url>/webhook`
    - [ ] 9.6 Set Content type to `application/json`
    - [ ] 9.7 Set Secret to value from webhook orchestrator config
    - [ ] 9.8 Select "Just the push event"
    - [ ] 9.9 Click "Add webhook"
    - [ ] 9.10 Ensure webhook orchestrator and Minerva MCP server are running
    - [ ] 9.11 Make a change to markdown file in test repository
    - [ ] 9.12 Commit and push: `git commit -am "Test real webhook" && git push origin main`
    - [ ] 9.13 In GitHub webhook settings, check "Recent Deliveries"
    - [ ] 9.14 Verify webhook was delivered successfully (green checkmark)
    - [ ] 9.15 Check orchestrator logs for webhook receipt and processing
    - [ ] 9.16 Verify reindex was triggered and completed successfully
    - [ ] 9.17 Verify updated content is searchable in Claude Desktop
    - [ ] 9.18 Delete webhook from GitHub when testing complete

- [ ] 10.0 Documentation and Cleanup
    - [ ] 10.1 Update `extractors/github-webhook-orchestrator/README.md` with:
        - Installation instructions
        - Configuration guide
        - Usage examples (local testing, ngrok testing)
        - Troubleshooting section
    - [ ] 10.2 Document environment variables needed (OPENAI_API_KEY, WEBHOOK_SECRET, GITHUB_TOKEN)
    - [ ] 10.3 Add example of using envchain for secret management
    - [ ] 10.4 Document manual testing procedures performed
    - [ ] 10.5 Create troubleshooting guide for common errors
    - [ ] 10.6 Add section on testing signature validation (how to compute HMAC-SHA256)
    - [ ] 10.7 Commit all code to git repository
    - [ ] 10.8 Tag as `phase-1-complete`

---

## Phase 1 Completion Criteria

Phase 1 is complete when:
- ✅ Webhook orchestrator package is installable and runnable
- ✅ Signature validation works correctly (unit tested)
- ✅ Configuration loading and validation works (unit tested)
- ✅ Reindex workflow executes successfully via subprocess calls
- ✅ Manual curl simulation triggers reindex successfully
- ✅ MCP server stays running during reindexing (concurrent operation verified)
- ✅ Optional: Real GitHub webhook via ngrok works successfully
- ✅ All code committed to git repository

---

## Notes for Phase 2

After Phase 1 completion:
- Webhook orchestrator code is working locally
- Ready to dockerize in Phase 2
- Configuration patterns are established
- Testing procedures are documented
- Can proceed to containerization without changing core logic
