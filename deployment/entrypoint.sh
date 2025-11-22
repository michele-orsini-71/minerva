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

echo "Starting Minerva MCP server..."
minerva serve --config /data/config/server.json &
MCP_PID=$!
echo "MCP server started with PID $MCP_PID"

echo "Waiting for MCP server to be ready..."
for i in {1..10}; do
    if curl -f http://localhost:8337/health > /dev/null 2>&1; then
        echo "MCP server is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "MCP server failed to start"
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
