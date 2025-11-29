# Testing Guide - GitHub Webhook Orchestrator

This guide covers manual testing of the webhook orchestrator in Phase 1 (local development, no Docker, no network exposure).

## Prerequisites

1. **Environment Setup**
   ```bash
   # Install the webhook orchestrator package
   cd extractors/github-webhook-orchestrator
   pip install -e .

   # Verify installation
   webhook-orchestrator --help
   ```

2. **Environment Variables**

   Set up required secrets using envchain:
   ```bash
   # Store OpenAI API key
   envchain --set openai OPENAI_API_KEY

   # Store webhook secret (for testing)
   envchain --set openai WEBHOOK_SECRET

   # Optional: GitHub token (not needed for Phase 1)
   envchain --set openai GITHUB_TOKEN
   ```

3. **Configuration Files**

   The following configs should be in place:
   - `~/.minerva/configs/webhook-config.json` - Webhook orchestrator config
   - `~/.minerva/configs/test-webhook-repo.json` - Index config for test repository
   - `~/.minerva/configs/serve.json` - MCP server config

## Test Scenario 1: Local Webhook Simulation (No GitHub)

This test simulates a GitHub webhook locally without involving the actual GitHub API.

### Terminal 1: Start MCP Server

```bash
# Start the Minerva MCP server (stdio mode)
cd /Users/michele/my-code/minerva
envchain openai minerva serve --config ~/.minerva/configs/serve.json
```

**Expected output:**
- Server starts successfully
- No errors in logs
- Server listens on stdio (for Claude Desktop integration)

### Terminal 2: Start Webhook Orchestrator

```bash
# Start the webhook orchestrator
cd /Users/michele/my-code/minerva/extractors/github-webhook-orchestrator
envchain openai webhook-orchestrator --config ~/.minerva/configs/webhook-config.json
```

**Expected output:**
```
Webhook Orchestrator Starting
==============================
Config: /Users/michele/.minerva/configs/webhook-config.json
Repositories: 1
  - minerva (minerva_docs)
Log file: /Users/michele/.minerva/logs/webhook-orchestrator.log

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8338 (Press CTRL+C to quit)
```

### Terminal 3: Send Test Webhook

```bash
# Use the test script to send a webhook
cd /Users/michele/my-code/minerva/extractors/github-webhook-orchestrator
WEBHOOK_SECRET="test-secret" ./test_webhook_local.sh
```

**Or manually:**

```bash
# 1. Compute signature
python3 compute_signature.py test_webhook_payload.json "test-secret"
# Output: sha256=<hex_digest>

# 2. Send webhook with curl
curl -X POST http://localhost:8338/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<hex_digest>" \
  -H "X-GitHub-Event: push" \
  -d @test_webhook_payload.json
```

**Expected behavior:**

1. Webhook orchestrator logs show:
   ```
   Received webhook for repository: minerva
   Signature validation: PASSED
   Event type: push
   Detected markdown changes: True
   Starting reindex workflow...
   ```

2. Reindex workflow executes:
   ```
   [1/4] Git pull: SUCCESS
   [2/4] Extract: SUCCESS
   [3/4] Validate: SUCCESS
   [4/4] Index: SUCCESS
   Reindex complete in 45.2s
   ```

3. HTTP response: `200 OK`
   ```json
   {"status": "success", "message": "Reindex triggered successfully"}
   ```

### Verification Steps

**1. Check orchestrator logs:**
```bash
tail -f ~/.minerva/logs/webhook-orchestrator.log
```

Look for:
- Webhook received and validated
- Markdown changes detected
- All 4 reindex steps completed successfully
- No errors or warnings

**2. Check that MCP server stayed running:**

Switch to Terminal 1 and verify the MCP server is still running (no crashes, no errors).

**3. Verify indexed content:**

```bash
# Check that collection was updated
envchain openai minerva peek minerva_docs --chromadb ~/.minerva/chromadb --format table
```

Look for recently updated documents matching the test repository content.

**4. Test search in Claude Desktop:**

If Claude Desktop is connected to your MCP server:
1. Open Claude Desktop
2. Search for content from the minerva repository (e.g., "configuration guide")
3. Verify results include content from the test repository

## Test Scenario 2: Invalid Signature

Test that the orchestrator rejects webhooks with invalid signatures.

```bash
# Send webhook with wrong signature
curl -X POST http://localhost:8338/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=invalid_signature_here" \
  -H "X-GitHub-Event: push" \
  -d @test_webhook_payload.json
```

**Expected behavior:**
- HTTP response: `403 Forbidden`
- Response body: `{"detail": "Invalid signature"}`
- Orchestrator logs: `Signature validation failed`
- No reindex triggered

## Test Scenario 3: No Markdown Changes

Test that the orchestrator skips reindexing when no markdown files changed.

1. Edit `test_webhook_payload.json`
2. Change the `added`, `modified`, `removed` arrays to contain only non-markdown files:
   ```json
   "added": ["src/main.py"],
   "modified": ["setup.py"],
   "removed": []
   ```
3. Send the webhook

**Expected behavior:**
- HTTP response: `200 OK`
- Response body: `{"status": "skipped", "message": "No markdown changes detected"}`
- No reindex triggered
- Orchestrator logs: `No markdown changes, skipping reindex`

## Test Scenario 4: Repository Not Found

Test behavior when webhook is received for an unknown repository.

1. Edit `test_webhook_payload.json`
2. Change `repository.name` to `"unknown-repo"`
3. Send the webhook

**Expected behavior:**
- HTTP response: `200 OK` (GitHub expects 200 even if we skip processing)
- Response body: `{"status": "ignored", "message": "Repository not configured"}`
- Orchestrator logs: `Repository 'unknown-repo' not in configuration, ignoring`

## Test Scenario 5: Health Check

Test the health endpoint:

```bash
curl http://localhost:8338/health
```

**Expected behavior:**
- HTTP response: `200 OK`
- Response body: `{"status": "healthy"}`

## Troubleshooting

### Webhook orchestrator won't start

**Error:** `Address already in use`

**Solution:** Another process is using port 8338
```bash
# Find the process
lsof -i :8338

# Kill it
kill <PID>
```

### Signature validation fails

**Error:** `403 Forbidden - Invalid signature`

**Causes:**
1. WEBHOOK_SECRET mismatch between config and test script
2. Payload file was modified after signature computation
3. Wrong secret used in compute_signature.py

**Solution:**
```bash
# Check what secret is in the config
cat ~/.minerva/configs/webhook-config.json | grep webhook_secret

# Make sure you use the same secret when computing signature
WEBHOOK_SECRET="test-secret" ./test_webhook_local.sh
```

### Reindex fails

**Error:** `Reindex failed` in logs

**Check:**
1. Is the repository path correct? `ls /Users/michele/my-code/minerva`
2. Is git working? `cd /Users/michele/my-code/minerva && git status`
3. Is repository-doc-extractor installed? `which repository-doc-extractor`
4. Is minerva installed? `which minerva`
5. Is OPENAI_API_KEY set? `envchain openai env | grep OPENAI_API_KEY`

**Debug:**
```bash
# Run each step manually to see where it fails
cd /Users/michele/my-code/minerva
git pull origin main
repository-doc-extractor . -o ~/.minerva/extracted/test-webhook-repo.json -v
envchain openai minerva validate ~/.minerva/extracted/test-webhook-repo.json
envchain openai minerva index --config ~/.minerva/configs/test-webhook-repo.json --verbose
```

### MCP server crashes during reindex

**Expected behavior:** MCP server should stay running

**If it crashes:**
1. Check MCP server logs for errors
2. Check system resources (RAM, disk space)
3. Ensure ChromaDB isn't corrupted
4. Try running reindex manually first to isolate the issue

### ChromaDB errors

**Error:** `Collection not found` or `ChromaDB connection failed`

**Solution:**
```bash
# Check ChromaDB directory exists
ls -la ~/.minerva/chromadb

# List collections
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='/Users/michele/.minerva/chromadb')
print([c.name for c in client.list_collections()])
"

# If corrupted, delete and recreate collection
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='/Users/michele/.minerva/chromadb')
try:
    client.delete_collection('minerva_docs')
    print('Collection deleted')
except:
    print('Collection did not exist')
"
```

## Success Criteria for Task 8

Task 8 is complete when:

- ✅ Webhook orchestrator starts successfully with config
- ✅ Test webhook is received and signature validated
- ✅ Markdown changes are detected correctly
- ✅ Reindex workflow executes all 4 steps successfully
- ✅ MCP server stays running during reindex (concurrent operation)
- ✅ Invalid signatures are rejected (403)
- ✅ Non-markdown changes are skipped
- ✅ Health check endpoint works
- ✅ All logs are written correctly

## Next Steps

After completing Task 8 (local testing), proceed to:

**Task 9** (Optional): Test with real GitHub webhook via ngrok
- Set up ngrok tunnel
- Configure GitHub repository webhook
- Test end-to-end with real push events

**Task 10**: Documentation and cleanup
- Update README
- Document troubleshooting procedures
- Commit all code
- Tag as `phase-1-complete`
