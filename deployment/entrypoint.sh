#!/bin/bash
set -e

echo "Starting Minerva deployment..."
echo "Timestamp: $(date)"

cleanup() {
    echo "Shutting down services..."
    if [ ! -z "$MCP_PID" ]; then
        kill -TERM "$MCP_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

echo "Ensuring repository is indexed and up-to-date..."
echo "(This catches any changes that occurred while the container was down)"

REPO_NAME=$(python3 -c "
import json
with open('/data/config/webhook.json') as f:
    config = json.load(f)
    print(config['repositories'][0]['name'])
")

REPO_URL=$(python3 -c "
import json
with open('/data/config/webhook.json') as f:
    config = json.load(f)
    print(config['repositories'][0]['github_url'])
")

REPO_BRANCH=$(python3 -c "
import json
with open('/data/config/webhook.json') as f:
    config = json.load(f)
    print(config['repositories'][0].get('branch', 'main'))
")

INDEX_CONFIG=$(python3 -c "
import json
with open('/data/config/webhook.json') as f:
    config = json.load(f)
    print(config['repositories'][0]['index_config'])
")

LOCAL_PATH="/data/repos/${REPO_NAME}"
EXTRACT_PATH="/data/extracted/${REPO_NAME}.json"

echo "  Repository: $REPO_NAME"
echo "  URL: $REPO_URL"
echo "  Branch: $REPO_BRANCH"

echo "[1/4] Syncing repository..."
if [ -d "$LOCAL_PATH" ]; then
    echo "  Repository exists, pulling latest changes..."
    cd "$LOCAL_PATH"
    git pull origin "$REPO_BRANCH"
else
    echo "  Cloning repository..."
    git clone --branch "$REPO_BRANCH" "$REPO_URL" "$LOCAL_PATH"
fi

echo "[2/4] Extracting documentation..."
repository-doc-extractor "$LOCAL_PATH" -o "$EXTRACT_PATH"

echo "[3/4] Validating extracted data..."
minerva validate "$EXTRACT_PATH"

echo "[4/4] Indexing into ChromaDB..."
echo "  (Will create collection if needed, or incrementally update if exists)"
minerva index --config "$INDEX_CONFIG"

echo "✓ Repository indexing complete"

echo "Starting Minerva MCP server (HTTP mode)..."
minerva serve-http --config /data/config/server.json &
MCP_PID=$!
echo "MCP server started with PID $MCP_PID"

echo "Waiting for MCP server to be ready..."
for i in {1..10}; do
    # Check if server is responding on port 8337 (any response means it's up)
    if curl -f http://localhost:8337/ > /dev/null 2>&1 || curl -f http://localhost:8337/mcp/ > /dev/null 2>&1; then
        echo "MCP server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "MCP server failed to start - no response on port 8337"
        exit 1
    fi
    sleep 1
done

echo "All services started successfully"
echo "MCP server: http://localhost:8337"

wait
