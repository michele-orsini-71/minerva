#!/bin/bash
#
# Local webhook orchestrator testing script
#
# This script helps test the webhook orchestrator locally without requiring
# a real GitHub webhook. It computes the HMAC-SHA256 signature and sends
# a test webhook payload to the locally running orchestrator.
#
# Prerequisites:
# - Webhook orchestrator running on http://localhost:8338
# - WEBHOOK_SECRET environment variable set (or use default "test-secret")
#
# Usage:
#   ./test_webhook_local.sh
#   WEBHOOK_SECRET="my-secret" ./test_webhook_local.sh

set -e

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8338}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-test-secret}"
PAYLOAD_FILE="${PAYLOAD_FILE:-test_webhook_payload.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}GitHub Webhook Local Testing${NC}"
echo -e "${YELLOW}=====================================${NC}"
echo ""

# Check if payload file exists
if [ ! -f "$SCRIPT_DIR/$PAYLOAD_FILE" ]; then
    echo -e "${RED}Error: Payload file not found: $SCRIPT_DIR/$PAYLOAD_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Payload file: $PAYLOAD_FILE"
echo -e "${GREEN}✓${NC} Webhook secret: $WEBHOOK_SECRET"

# Check if orchestrator is running
echo -n "Checking if orchestrator is running... "
if ! curl -s -f "$ORCHESTRATOR_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}FAILED${NC}"
    echo ""
    echo -e "${RED}Error: Webhook orchestrator is not running at $ORCHESTRATOR_URL${NC}"
    echo ""
    echo "Please start the orchestrator in another terminal:"
    echo "  cd $SCRIPT_DIR"
    echo "  envchain openai webhook-orchestrator --config ~/.minerva/configs/webhook-config.json"
    echo ""
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# Compute signature
echo -n "Computing HMAC-SHA256 signature... "
SIGNATURE=$(python3 "$SCRIPT_DIR/compute_signature.py" "$SCRIPT_DIR/$PAYLOAD_FILE" "$WEBHOOK_SECRET")
echo -e "${GREEN}OK${NC}"
echo "  Signature: $SIGNATURE"

# Send webhook
echo ""
echo "Sending webhook to $ORCHESTRATOR_URL/webhook..."
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$ORCHESTRATOR_URL/webhook" \
    -H "Content-Type: application/json" \
    -H "X-Hub-Signature-256: $SIGNATURE" \
    -H "X-GitHub-Event: push" \
    --data-binary @"$SCRIPT_DIR/$PAYLOAD_FILE")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "Response code: $HTTP_CODE"
echo "Response body: $BODY"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Webhook processed successfully!${NC}"
    echo ""
    echo "Check the orchestrator logs for details:"
    echo "  tail -f ~/.minerva/logs/webhook-orchestrator.log"
    exit 0
elif [ "$HTTP_CODE" = "403" ]; then
    echo -e "${RED}✗ Webhook rejected (403 Forbidden)${NC}"
    echo ""
    echo "This usually means signature validation failed."
    echo "Make sure WEBHOOK_SECRET matches the config file:"
    echo "  WEBHOOK_SECRET=\"$WEBHOOK_SECRET\""
    exit 1
else
    echo -e "${RED}✗ Webhook failed with HTTP $HTTP_CODE${NC}"
    exit 1
fi
