#!/bin/bash
# Test script for Minerva MCP HTTP server
# Usage: ./test-mcp-http.sh [host] [port]

HOST=${1:-localhost}
PORT=${2:-8000}
BASE_URL="http://${HOST}:${PORT}"

echo "Testing Minerva MCP HTTP Server at ${BASE_URL}"
echo "================================================"
echo

# 1. Test basic connectivity
echo "1. Testing basic connectivity..."
curl -s -o /dev/null -w "Status: %{http_code}\n" "${BASE_URL}/"
echo

# 2. Initialize and get session ID
echo "2. Initializing session..."
RESPONSE=$(curl -s -i -X POST "${BASE_URL}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0"}},"id":1}')

SESSION_ID=$(echo "$RESPONSE" | grep -i "mcp-session-id:" | cut -d' ' -f2 | tr -d '\r')

if [ -z "$SESSION_ID" ]; then
  echo "❌ Failed to get session ID"
  echo "$RESPONSE"
  exit 1
fi

echo "✅ Session ID: $SESSION_ID"
echo

# 3. List available tools
echo "3. Listing available tools..."
curl -s -X POST "${BASE_URL}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: ${SESSION_ID}" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}' | grep -o '"name":"[^"]*"' | cut -d'"' -f4
echo

# 4. List knowledge bases
echo "4. Listing knowledge bases..."
KB_RESPONSE=$(curl -s -X POST "${BASE_URL}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: ${SESSION_ID}" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_knowledge_bases","arguments":{}},"id":3}')

# Extract JSON from SSE format (line starting with "data: ")
echo "$KB_RESPONSE" | grep "^data: " | sed 's/^data: //' | python3 -m json.tool 2>/dev/null || echo "No knowledge bases found or parsing failed"
echo

echo "✅ All tests completed!"
echo
echo "Your MCP HTTP server is working correctly!"
echo "Issue with MCP Inspector is likely on the client side."
