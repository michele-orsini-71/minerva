#!/bin/bash
set -e

echo "Starting Minerva deployment..."
echo "Timestamp: $(date)"

cleanup() {
    echo "Shutting down services..."
    if [ ! -z "$MCP_PID" ]; then
        kill -TERM "$MCP_PID" 2>/dev/null || true
    fi
    if [ ! -z "$WEBHOOK_PID" ]; then
        kill -TERM "$WEBHOOK_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

echo "Checking database initialization..."
# Use minerva peek to list collections, count the results
COLLECTION_COUNT=$(minerva peek /data/chromadb --format json 2>/dev/null | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(len(data.get('collections', [])))
except:
    print('0')
")

echo "Found $COLLECTION_COUNT collection(s) in ChromaDB"

if [ "$COLLECTION_COUNT" -eq "0" ]; then
    echo "ChromaDB is empty - running initial indexing..."

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

    echo "[1/4] Cloning repository..."
    if [ -d "$LOCAL_PATH" ]; then
        echo "  Repository already exists, pulling latest changes..."
        cd "$LOCAL_PATH"
        git pull origin "$REPO_BRANCH"
    else
        echo "  Cloning fresh copy..."
        git clone --branch "$REPO_BRANCH" "$REPO_URL" "$LOCAL_PATH"
    fi

    echo "[2/4] Extracting documentation..."
    repository-doc-extractor "$LOCAL_PATH" -o "$EXTRACT_PATH"

    echo "[3/4] Validating extracted data..."
    minerva validate "$EXTRACT_PATH"

    echo "[4/4] Indexing into ChromaDB..."
    minerva index --config "$INDEX_CONFIG"

    echo "✓ Initial indexing complete"

    # Verify collection was created and is accessible
    COLLECTION_COUNT_AFTER=$(minerva peek /data/chromadb --format json 2>/dev/null | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print(len(data.get('collections', [])))
except:
    print('0')
")

    echo "✓ ChromaDB now has $COLLECTION_COUNT_AFTER collection(s)"
else
    echo "✓ ChromaDB already initialized, skipping initial indexing"
fi

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

echo "Starting webhook orchestrator..."
webhook-orchestrator --config /data/config/webhook.json &
WEBHOOK_PID=$!
echo "Webhook orchestrator started with PID $WEBHOOK_PID"

echo "All services started successfully"
echo "MCP server: http://localhost:8337"
echo "Webhook orchestrator: http://localhost:8338"

wait
