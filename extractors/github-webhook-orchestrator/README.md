# GitHub Webhook Orchestrator

FastAPI webhook server that automatically triggers Minerva reindexing when GitHub repositories are updated.

## Overview

This package provides a webhook endpoint that:
1. Receives GitHub push event webhooks
2. Validates webhook signatures using HMAC-SHA256
3. Detects markdown file changes in commits
4. Triggers automatic extraction and reindexing workflow for affected repositories

## Installation

```bash
cd extractors/github-webhook-orchestrator
pip install -e .
```

## Requirements

- Python 3.10+
- FastAPI
- uvicorn
- Minerva installed and configured
- repository-doc-extractor installed
- OpenAI API key (or other AI provider) configured via envchain

## Configuration

Create a configuration file (e.g., `~/.minerva/configs/webhook-config.json`):

```json
{
  "webhook_secret": "${WEBHOOK_SECRET}",
  "github_token": "${GITHUB_TOKEN}",
  "log_file": "~/.minerva/logs/webhook-orchestrator.log",
  "repositories": [
    {
      "name": "my-repo",
      "github_url": "https://github.com/user/my-repo",
      "local_path": "/path/to/local/clone",
      "index_config": "~/.minerva/configs/my-repo.json",
      "branch": "main"
    }
  ]
}
```

### Configuration Fields

- `webhook_secret`: GitHub webhook secret for signature validation (supports `${ENV_VAR}` substitution)
- `github_token`: GitHub personal access token (supports `${ENV_VAR}` substitution)
- `log_file`: Path to log file for webhook events
- `repositories`: Array of repository configurations
  - `name`: Repository name (must match GitHub repository name)
  - `github_url`: GitHub repository URL
  - `local_path`: Path to local git clone
  - `index_config`: Path to Minerva index configuration file
  - `branch`: Git branch to pull from (optional, defaults to `main`)

### Environment Variables

The orchestrator requires the following environment variables:

- `WEBHOOK_SECRET`: GitHub webhook secret (for signature validation)
- `GITHUB_TOKEN`: GitHub personal access token (for API access)
- `OPENAI_API_KEY`: OpenAI API key (or other AI provider key for indexing)

**Recommended: Use envchain for secret management**

```bash
# Store webhook secret and GitHub token
envchain --set github WEBHOOK_SECRET
envchain --set github GITHUB_TOKEN

# Store OpenAI API key (required for indexing)
envchain --set openai OPENAI_API_KEY

# Run orchestrator with both namespaces
envchain github:openai webhook-orchestrator --config ~/.minerva/configs/webhook-config.json
```

This approach keeps secrets out of your config files and shell history.

## Usage

### Start the Webhook Server

```bash
envchain github:openai webhook-orchestrator --config ~/.minerva/configs/webhook-config.json
```

The server listens on `http://localhost:8338` by default.

### Configure GitHub Webhook

1. Go to your GitHub repository settings
2. Navigate to **Webhooks** → **Add webhook**
3. Set **Payload URL**:
   - For production: `https://your-domain.com/webhook`
   - For local testing with ngrok: `https://abc123.ngrok-free.app/webhook` (see Local Testing section below)
   - **Important**: URL must end with `/webhook`
4. Set **Content type**: `application/json` (not `application/x-www-form-urlencoded`)
5. Set **Secret**: Same value as `WEBHOOK_SECRET` environment variable
6. Select events: **Just the push event**
7. Click **Add webhook**
8. Verify delivery: Check **Recent Deliveries** tab for green checkmark (200 OK)

### Local Testing with ngrok

For testing with real GitHub webhooks on your local machine:

1. **Install ngrok** (if not already installed):
   ```bash
   brew install ngrok
   ```

2. **Start ngrok tunnel**:
   ```bash
   ngrok http 8338
   ```

   Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

3. **Configure GitHub webhook**:
   - Set Payload URL to: `https://abc123.ngrok-free.app/webhook`
   - Set Content type to: `application/json`
   - Set Secret to your `WEBHOOK_SECRET` value
   - Select "Just the push event"

4. **Ensure orchestrator is running**:
   ```bash
   envchain github:openai webhook-orchestrator --config ~/.minerva/configs/webhook-config.json
   ```

5. **Test the workflow**:
   - Make a change to a markdown file in your repository
   - Commit and push: `git commit -am "Test webhook" && git push`
   - Check GitHub webhook "Recent Deliveries" for green checkmark
   - Monitor orchestrator logs: `tail -f ~/.minerva/logs/webhook-orchestrator.log`

6. **Monitor ngrok requests** (optional):
   - Visit `http://localhost:4040` to see request/response details

### Local Testing with curl

For testing without GitHub, you can simulate webhooks locally:

1. **Create test payload** (`test_payload.json`):
   ```json
   {
     "ref": "refs/heads/main",
     "repository": {
       "name": "my-repo"
     },
     "commits": [
       {
         "added": ["docs/new-file.md"],
         "modified": [],
         "removed": []
       }
     ]
   }
   ```

2. **Compute HMAC-SHA256 signature**:
   ```bash
   echo -n "$(cat test_payload.json)" | openssl dgst -sha256 -hmac "your-webhook-secret" | sed 's/^.* //'
   ```

3. **Send test webhook**:
   ```bash
   curl -X POST http://localhost:8338/webhook \
     -H "Content-Type: application/json" \
     -H "X-Hub-Signature-256: sha256=<computed-signature>" \
     -H "X-GitHub-Event: push" \
     -d @test_payload.json
   ```

### Health Check

```bash
curl http://localhost:8338/health
# Expected: {"status":"healthy","timestamp":"2025-11-21T..."}
```

## Reindex Workflow

When a webhook is received with markdown changes, the orchestrator executes these steps:

1. **[1/4] Git Pull**: `git pull origin <branch>` - Update local repository (branch from config)
2. **[2/4] Extract**: `repository-doc-extractor <local_path> -o <output_json>` - Extract markdown files
3. **[3/4] Validate**: `minerva validate <output_json>` - Validate extracted notes
4. **[4/4] Index**: `minerva index --config <index_config>` - Reindex into ChromaDB

All commands are executed as subprocesses with stdout/stderr captured for logging.

**Note**: The Minerva MCP server continues running during reindexing. Updated content becomes searchable in Claude Desktop once indexing completes.

## API Endpoints

### POST /webhook

Receives GitHub webhook events.

**Headers:**
- `Content-Type: application/json`
- `X-Hub-Signature-256: sha256=<signature>`

**Response:**
- `200 OK`: Webhook processed successfully
- `403 Forbidden`: Invalid signature
- `500 Internal Server Error`: Reindex workflow failed

### GET /health

Health check endpoint.

**Response:**
- `200 OK`: Server is running

## Testing

Run unit tests:

```bash
pytest tests/
```

Run tests with coverage:

```bash
pytest --cov=github_webhook_orchestrator tests/
```

## Troubleshooting

### Common Issues

#### 404 Not Found

**Symptom**: GitHub shows "Last delivery was not successful. Invalid HTTP Response: 404"

**Cause**: Webhook URL doesn't include `/webhook` endpoint path

**Solution**:
- Update GitHub webhook Payload URL to include `/webhook` at the end
- Example: `https://abc123.ngrok-free.app/webhook` (not just `https://abc123.ngrok-free.app/`)

#### 403 Forbidden - Invalid Signature

**Symptom**: Logs show "Invalid signature received"

**Causes**:
1. Webhook secret mismatch between GitHub and config
2. Orchestrator was started with old secret, then secret was changed in GitHub
3. Content type is `application/x-www-form-urlencoded` instead of `application/json`

**Solutions**:
- Verify `WEBHOOK_SECRET` environment variable matches GitHub webhook secret
- Restart orchestrator after changing webhook secret
- In GitHub webhook settings, set Content type to `application/json`
- Check `X-Hub-Signature-256` header format is `sha256=<hex>`

#### 400 Bad Request - Invalid JSON

**Symptom**: Logs show "Invalid JSON payload"

**Cause**: GitHub webhook is configured with wrong Content type

**Solution**:
- In GitHub webhook settings, change Content type to `application/json`
- The orchestrator expects JSON, not form-encoded data

#### Git Pull Failed - couldn't find remote ref

**Symptom**: Logs show "Git pull failed: fatal: couldn't find remote ref master"

**Cause**: Repository uses `main` branch but config specifies `master` (or vice versa)

**Solution**:
- Update `branch` field in config file to match your repository's default branch
- Most modern repos use `main`, older repos use `master`
- Example: `"branch": "main"`

#### Reindex Fails - Command Not Found

**Symptom**: Logs show "Extraction failed" or "Indexing failed" with command not found

**Cause**: Missing dependencies (repository-doc-extractor or minerva not installed)

**Solution**:
```bash
# Verify repository-doc-extractor is installed
which repository-doc-extractor

# Verify minerva is installed
which minerva

# Install if missing
pip install -e /path/to/minerva
pip install -e /path/to/repository-doc-extractor
```

#### Environment Variables Not Set

**Symptom**: Config loading fails with "Environment variable X is not set"

**Cause**: Required environment variables are not available

**Solution**:
```bash
# Verify environment variables are set
envchain github printenv | grep -E 'WEBHOOK_SECRET|GITHUB_TOKEN'
envchain openai printenv | grep OPENAI_API_KEY

# Run with both namespaces
envchain github:openai webhook-orchestrator --config config.json
```

### Debugging Tips

**Check orchestrator logs**:
```bash
tail -f ~/.minerva/logs/webhook-orchestrator.log
```

**Check GitHub webhook deliveries**:
- Go to repository Settings → Webhooks
- Click on your webhook
- Check "Recent Deliveries" tab
- Click on a delivery to see request/response details

**Monitor ngrok requests** (if using ngrok):
```bash
# Visit ngrok web interface
open http://localhost:4040
```

**Test signature validation manually**:
```bash
# Compute signature for test payload
PAYLOAD='{"test":"data"}'
SECRET="your-webhook-secret"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')
echo "sha256=$SIGNATURE"

# Test with curl
curl -X POST http://localhost:8338/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -H "X-GitHub-Event: push" \
  -d "$PAYLOAD"
```

### Logs

All webhook events and errors are logged with timestamps:

```bash
# Follow logs in real-time
tail -f ~/.minerva/logs/webhook-orchestrator.log

# View recent errors
grep ERROR ~/.minerva/logs/webhook-orchestrator.log | tail -20

# View successful reindexes
grep "Reindex completed successfully" ~/.minerva/logs/webhook-orchestrator.log
```

## Architecture

```
GitHub Push Event
       ↓
GitHub Webhook
       ↓
Webhook Orchestrator (FastAPI)
       ↓
[Validate Signature] → [Parse Payload] → [Detect Markdown Changes]
       ↓
[Execute Reindex Workflow]
       ↓
  git pull → extract → validate → index
       ↓
ChromaDB Updated
       ↓
Minerva MCP Server (continues running)
```

## Security

- HMAC-SHA256 signature validation protects against unauthorized webhooks
- Constant-time comparison prevents timing attacks
- Secrets managed via envchain (not stored in config files)
- Subprocess execution uses explicit command arrays (no shell injection)

## License

MIT License - See project root for details.
