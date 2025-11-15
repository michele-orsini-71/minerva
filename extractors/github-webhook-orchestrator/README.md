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

Create a configuration file (e.g., `config.json`):

```json
{
  "webhook_secret": "${WEBHOOK_SECRET}",
  "log_file": "~/.minerva/logs/webhook-orchestrator.log",
  "repositories": [
    {
      "name": "my-repo",
      "github_url": "https://github.com/user/my-repo",
      "local_path": "/path/to/local/clone",
      "collection": "my_repo_docs",
      "index_config": "~/.minerva/configs/my-repo.json"
    }
  ]
}
```

### Configuration Fields

- `webhook_secret`: GitHub webhook secret for signature validation (supports `${ENV_VAR}` substitution)
- `log_file`: Path to log file for webhook events
- `repositories`: Array of repository configurations
  - `name`: Repository name (must match GitHub repository name)
  - `github_url`: GitHub repository URL
  - `local_path`: Path to local git clone
  - `collection`: ChromaDB collection name
  - `index_config`: Path to Minerva index configuration file

### Environment Variables

The orchestrator uses envchain to manage secrets:

```bash
# Store webhook secret
envchain --set webhook WEBHOOK_SECRET

# Store OpenAI API key (required for indexing)
envchain --set openai OPENAI_API_KEY
```

## Usage

### Start the Webhook Server

```bash
envchain openai webhook-orchestrator --config config.json
```

The server listens on `http://localhost:8338` by default.

### Configure GitHub Webhook

1. Go to your GitHub repository settings
2. Navigate to Webhooks → Add webhook
3. Set Payload URL: `https://your-domain.com/webhook` (use ngrok for local testing)
4. Set Content type: `application/json`
5. Set Secret: Same value as `webhook_secret` in config
6. Select events: "Just the push event"
7. Click "Add webhook"

### Local Testing with curl

Generate webhook signature:

```bash
# Compute HMAC-SHA256 signature
echo -n "$(cat test_payload.json)" | openssl dgst -sha256 -hmac "your-webhook-secret" | sed 's/^.* //'
```

Send test webhook:

```bash
curl -X POST http://localhost:8338/webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<computed-signature>" \
  -d @test_payload.json
```

### Health Check

```bash
curl http://localhost:8338/health
```

## Reindex Workflow

When a webhook is received with markdown changes, the orchestrator executes:

1. `git pull origin main` - Update local repository
2. `repository-doc-extractor <local_path> -o <output_json>` - Extract markdown files
3. `minerva validate <output_json>` - Validate extracted notes
4. `envchain openai minerva index --config <index_config>` - Reindex into ChromaDB

All commands are executed as subprocesses with stdout/stderr captured for logging.

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

### Signature Validation Fails

- Verify webhook secret matches between GitHub and config
- Check `X-Hub-Signature-256` header format is `sha256=<hex>`
- Ensure raw request body is used for signature computation

### Reindex Fails

- Check local repository path exists and is a valid git repository
- Verify repository-doc-extractor is installed
- Ensure Minerva index config file exists and is valid
- Check OpenAI API key is available via envchain

### Logs

Check orchestrator logs for detailed error messages:

```bash
tail -f ~/.minerva/logs/webhook-orchestrator.log
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
