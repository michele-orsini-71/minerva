# Phase 3 Tasks: GitHub Webhook Auto-Reindex (Mac as Remote Server)

**ABORTED**

**PRD:** `/tasks/2025-11-15-prd-github-webhook-auto-reindex.md`
**Phase:** Phase 3 - Your Mac as Remote Server (Learn Reverse Proxy & HTTPS)
**Goal:** Expose Docker stack to network, add Caddy reverse proxy, enable HTTPS
**Prerequisites:** Phase 2 complete

---

## Relevant Files

### New Files to Create
- `deployment/Caddyfile` - Caddy reverse proxy configuration
- `deployment/docker-compose-phase3.yml` - Updated compose file with Caddy service
- `deployment/configs/server-phase3.json` - MCP server config with authentication enabled
- `deployment/test-https.sh` - Script to test HTTPS endpoints

### Modified Files
- `deployment/docker-compose.yml` - Add Caddy service, update network configuration
- `deployment/README.md` - Add Phase 3 deployment instructions

### Notes
- THIS is where Caddy enters the picture (NOT in Phase 2)
- Caddy handles: HTTPS, automatic SSL certificates, reverse proxy
- Self-signed certificates for local testing (Phase 3)
- Let's Encrypt certificates for production (Phase 4)
- Test on LAN before AWS deployment

---

## Tasks

- [ ] 1.0 Add Caddy Service to Docker Compose
    - [ ] 1.1 Create backup of working Phase 2 docker-compose.yml
    - [ ] 1.2 Add `caddy` service to docker-compose.yml
    - [ ] 1.3 Use `caddy:2-alpine` image (official Caddy image)
    - [ ] 1.4 Expose ports: `443:443` (HTTPS) and `80:80` (HTTP redirect)
    - [ ] 1.5 Remove port mappings from `minerva` service (Caddy will handle external access)
    - [ ] 1.6 Create named volumes: `caddy-data` and `caddy-config`
    - [ ] 1.7 Mount volume `caddy-data:/data`
    - [ ] 1.8 Mount volume `caddy-config:/config`
    - [ ] 1.9 Mount `./Caddyfile:/etc/caddy/Caddyfile:ro` (read-only config)
    - [ ] 1.10 Set `depends_on: - minerva` (Caddy starts after Minerva)
    - [ ] 1.11 Set restart policy: `unless-stopped`
    - [ ] 1.12 Add both services to same Docker network for internal communication

- [ ] 2.0 Create Caddyfile for Local HTTPS Testing
    - [ ] 2.1 Create `deployment/Caddyfile`
    - [ ] 2.2 Configure server block for `minerva.local` domain
    - [ ] 2.3 Use `tls internal` directive for self-signed certificate
    - [ ] 2.4 Add reverse proxy for MCP endpoints: `reverse_proxy /mcp/* minerva:8337`
    - [ ] 2.5 Add reverse proxy for webhook endpoint: `reverse_proxy /webhook minerva:8338`
    - [ ] 2.6 Add reverse proxy for health endpoint: `reverse_proxy /health minerva:8337`
    - [ ] 2.7 Enable access logging: `log { output file /data/access.log format json }`
    - [ ] 2.8 Add error handling configuration
    - [ ] 2.9 Test Caddyfile syntax (Caddy validates on startup)

- [ ] 3.0 Configure Local DNS for Testing
    - [ ] 3.1 Edit `/etc/hosts` file (requires sudo)
    - [ ] 3.2 Add entry: `127.0.0.1 minerva.local`
    - [ ] 3.3 Verify DNS resolution: `ping minerva.local`
    - [ ] 3.4 Verify resolves to localhost (127.0.0.1)
    - [ ] 3.5 Document this step in README (team members need to do this too)

- [ ] 4.0 Enable MCP Server Authentication
    - [ ] 4.1 Create `deployment/configs/server-phase3.json` (copy from Phase 2)
    - [ ] 4.2 Change `require_auth` from `false` to `true`
    - [ ] 4.3 Ensure `api_key` is set to `${MINERVA_API_KEY}`
    - [ ] 4.4 Update docker-compose.yml to use new config file for Phase 3
    - [ ] 4.5 Keep Phase 2 config file for reference/rollback

- [ ] 5.0 Build and Start Services with Caddy
    - [ ] 5.1 Stop Phase 2 services if running: `docker-compose down`
    - [ ] 5.2 Build updated stack: `docker-compose build`
    - [ ] 5.3 Start services with envchain: `envchain openai envchain minerva docker-compose up -d`
    - [ ] 5.4 Verify all three processes start: Minerva MCP, webhook orchestrator, Caddy
    - [ ] 5.5 Check Caddy logs: `docker-compose logs caddy`
    - [ ] 5.6 Verify Caddy generated self-signed certificate
    - [ ] 5.7 Verify Caddy is listening on ports 80 and 443
    - [ ] 5.8 Check for any startup errors in logs

- [ ] 6.0 Test HTTPS Endpoints Locally
    - [ ] 6.1 Test health endpoint: `curl -k https://minerva.local/health`
    - [ ] 6.2 Verify response: 200 OK (note: `-k` flag ignores self-signed cert warning)
    - [ ] 6.3 Test without `-k` flag to see certificate warning (expected behavior)
    - [ ] 6.4 Inspect certificate: `curl -vI https://minerva.local/health 2>&1 | grep -A 10 "Server certificate"`
    - [ ] 6.5 Verify it's self-signed by Caddy
    - [ ] 6.6 Test HTTP redirect: `curl -I http://minerva.local/health`
    - [ ] 6.7 Verify redirect to HTTPS (301 or 302 response)

- [ ] 7.0 Test MCP Server with Authentication
    - [ ] 7.1 Test without Bearer token: `curl -k https://minerva.local/mcp/search -H "Content-Type: application/json" -d '{"query": "test"}'`
    - [ ] 7.2 Verify response: 401 Unauthorized
    - [ ] 7.3 Get MINERVA_API_KEY from envchain: `envchain minerva sh -c 'echo $MINERVA_API_KEY'`
    - [ ] 7.4 Test with Bearer token: `curl -k https://minerva.local/mcp/search -H "Authorization: Bearer <API_KEY>" -H "Content-Type: application/json" -d '{"query": "test"}'`
    - [ ] 7.5 Verify response: 200 OK (or appropriate search response)
    - [ ] 7.6 Test with invalid token
    - [ ] 7.7 Verify response: 401 Unauthorized
    - [ ] 7.8 Check Caddy access logs: `docker exec deployment_caddy_1 tail -f /data/access.log`
    - [ ] 7.9 Verify requests are being logged

- [ ] 8.0 Update Claude Desktop for HTTPS + Auth
    - [ ] 8.1 Update Claude Desktop MCP configuration
    - [ ] 8.2 Change URL from `http://localhost:8337/mcp/` to `https://minerva.local/mcp/`
    - [ ] 8.3 Add Authorization header: `"Authorization": "Bearer <MINERVA_API_KEY>"`
    - [ ] 8.4 Restart Claude Desktop
    - [ ] 8.5 Test search query
    - [ ] 8.6 If certificate error, add exception for self-signed cert (browser/Claude Desktop)
    - [ ] 8.7 Verify search works through HTTPS + Caddy reverse proxy
    - [ ] 8.8 Verify authentication is required (remove Bearer token to test failure)

- [ ] 9.0 Test Webhook Through Caddy
    - [ ] 9.1 Compute HMAC-SHA256 signature for test webhook payload
    - [ ] 9.2 Send webhook via Caddy: `curl -k -X POST https://minerva.local/webhook -H "Content-Type: application/json" -H "X-Hub-Signature-256: sha256=<signature>" -d @test-webhook-payload.json`
    - [ ] 9.3 Verify response: 200 OK or appropriate status
    - [ ] 9.4 Check webhook orchestrator logs for successful receipt
    - [ ] 9.5 Verify Caddy routed webhook request correctly
    - [ ] 9.6 Test webhook with invalid signature
    - [ ] 9.7 Verify response: 403 Forbidden
    - [ ] 9.8 Check Caddy access logs for webhook requests

- [ ] 10.0 Configure for LAN Access
    - [ ] 10.1 Get Mac's local IP address: `ifconfig en0 | grep "inet "`
    - [ ] 10.2 Note IP address (e.g., 192.168.1.100)
    - [ ] 10.3 Create separate Caddyfile for LAN testing: `Caddyfile.lan`
    - [ ] 10.4 Change server block from `minerva.local` to Mac's IP address (e.g., `192.168.1.100`)
    - [ ] 10.5 Keep `tls internal` for self-signed certificate
    - [ ] 10.6 Update docker-compose.yml to use new Caddyfile
    - [ ] 10.7 Restart Caddy: `docker-compose restart caddy`
    - [ ] 10.8 Verify Caddy generates certificate for IP address

- [ ] 11.0 Test from Another Device on LAN
    - [ ] 11.1 From another computer/phone on same network, test health endpoint: `curl -k https://192.168.1.100/health`
    - [ ] 11.2 Verify response: 200 OK
    - [ ] 11.3 Verify certificate warning (expected for self-signed cert)
    - [ ] 11.4 Test MCP endpoint with Bearer token
    - [ ] 11.5 Verify authentication works from remote device
    - [ ] 11.6 Send test webhook from remote device
    - [ ] 11.7 Verify webhook processing works
    - [ ] 11.8 If connection fails, check Mac firewall settings
    - [ ] 11.9 Allow incoming connections on port 443 if needed
    - [ ] 11.10 Test again after firewall configuration

- [ ] 12.0 Test Firewall and Network Configuration
    - [ ] 12.1 Check Mac firewall status: System Preferences → Security & Privacy → Firewall
    - [ ] 12.2 If firewall enabled, add Docker to allowed apps
    - [ ] 12.3 Test connectivity from another device again
    - [ ] 12.4 If still blocked, temporarily disable firewall for testing
    - [ ] 12.5 Document firewall configuration needed
    - [ ] 12.6 Re-enable firewall after confirming configuration
    - [ ] 12.7 Test final setup with firewall enabled and properly configured

- [ ] 13.0 Performance and Concurrency Testing
    - [ ] 13.1 Start continuous search queries in Claude Desktop (or via curl loop)
    - [ ] 13.2 Trigger webhook reindex while searches are running
    - [ ] 13.3 Verify searches continue to work during reindex (may return stale results)
    - [ ] 13.4 Verify MCP server doesn't crash or timeout
    - [ ] 13.5 Monitor Caddy access logs during concurrent operations
    - [ ] 13.6 Check resource usage: `docker stats`
    - [ ] 13.7 Verify CPU and memory usage are reasonable
    - [ ] 13.8 Test with multiple simultaneous webhook deliveries
    - [ ] 13.9 Verify webhook orchestrator handles concurrent requests correctly

- [ ] 14.0 Logging and Monitoring Setup
    - [ ] 14.1 Configure log rotation for Caddy access logs
    - [ ] 14.2 Configure log rotation for webhook orchestrator logs
    - [ ] 14.3 Set up log aggregation (all logs visible via `docker-compose logs`)
    - [ ] 14.4 Create helper script to view recent logs: `deployment/view-logs.sh`
    - [ ] 14.5 Create helper script to tail logs: `deployment/tail-logs.sh`
    - [ ] 14.6 Document log locations: Caddy (`/data/access.log`), webhook (`/data/logs/webhook-orchestrator.log`)
    - [ ] 14.7 Test viewing logs from host machine
    - [ ] 14.8 Document how to grep logs for errors

- [ ] 15.0 Backup and Restore Testing
    - [ ] 15.1 Create backup script: `deployment/backup-chromadb.sh`
    - [ ] 15.2 Script should: stop services, tar ChromaDB volume, restart services
    - [ ] 15.3 Test backup: run script and verify tar file created
    - [ ] 15.4 Verify backup file size is reasonable
    - [ ] 15.5 Create restore script: `deployment/restore-chromadb.sh`
    - [ ] 15.6 Script should: stop services, extract tar to volume, restart services
    - [ ] 15.7 Test restore: corrupt ChromaDB, restore from backup, verify data intact
    - [ ] 15.8 Document backup/restore procedures in README
    - [ ] 15.9 Test that MCP server can be stopped, DB restored, server restarted successfully

- [ ] 16.0 Security Hardening
    - [ ] 16.1 Verify Minerva services only listen on localhost in container
    - [ ] 16.2 Verify Caddy is only service exposed to external network
    - [ ] 16.3 Test that direct access to ports 8337 and 8338 is blocked from LAN (should only work via Caddy)
    - [ ] 16.4 Review Caddyfile for security best practices
    - [ ] 16.5 Ensure sensitive data (API keys) only in environment variables, not logs
    - [ ] 16.6 Review Docker security: no privileged containers, appropriate user permissions
    - [ ] 16.7 Document security considerations in README

- [ ] 17.0 Create Comprehensive Test Suite
    - [ ] 17.1 Create `deployment/test-phase3.sh` script
    - [ ] 17.2 Test HTTPS health endpoint
    - [ ] 17.3 Test authentication (valid and invalid tokens)
    - [ ] 17.4 Test webhook delivery via HTTPS
    - [ ] 17.5 Test MCP search via HTTPS with auth
    - [ ] 17.6 Test from localhost and LAN IP
    - [ ] 17.7 Test backup and restore procedures
    - [ ] 17.8 Make script executable: `chmod +x deployment/test-phase3.sh`
    - [ ] 17.9 Run full test suite
    - [ ] 17.10 Verify all tests pass

- [ ] 18.0 Documentation and Knowledge Capture
    - [ ] 18.1 Update `deployment/README.md` with Phase 3 instructions
    - [ ] 18.2 Document how Caddy reverse proxy works (conceptual explanation)
    - [ ] 18.3 Document self-signed certificate setup and browser warnings
    - [ ] 18.4 Document how to add SSL exception in browsers/Claude Desktop
    - [ ] 18.5 Document LAN access setup (IP address, firewall)
    - [ ] 18.6 Create troubleshooting guide for common issues
    - [ ] 18.7 Document how to debug SSL/TLS issues
    - [ ] 18.8 Document how to view Caddy logs and access logs
    - [ ] 18.9 Add section on backup/restore procedures
    - [ ] 18.10 Add section on security considerations
    - [ ] 18.11 Create diagram showing Caddy → Minerva architecture

- [ ] 19.0 Learnings and Reflection
    - [ ] 19.1 Document key learnings about reverse proxies
    - [ ] 19.2 Document key learnings about SSL/TLS certificates
    - [ ] 19.3 Document key learnings about Docker networking
    - [ ] 19.4 Document challenges encountered and solutions
    - [ ] 19.5 Note differences between self-signed certs (Phase 3) and Let's Encrypt (Phase 4)
    - [ ] 19.6 Create notes for Phase 4 preparation

- [ ] 20.0 Final Validation and Cleanup
    - [ ] 20.1 Run full end-to-end test: webhook → reindex → search via HTTPS
    - [ ] 20.2 Verify all services start cleanly after reboot
    - [ ] 20.3 Verify data persists across restarts
    - [ ] 20.4 Test from multiple devices on LAN
    - [ ] 20.5 Verify authentication is enforced
    - [ ] 20.6 Check for any error logs
    - [ ] 20.7 Verify Caddy access logs are being written
    - [ ] 20.8 Review all documentation for accuracy
    - [ ] 20.9 Commit all Phase 3 files to git repository
    - [ ] 20.10 Tag as `phase-3-complete`

---

## Phase 3 Completion Criteria

Phase 3 is complete when:
- ✅ Caddy reverse proxy is running and routing requests correctly
- ✅ HTTPS is enabled with self-signed certificates
- ✅ Bearer token authentication is working
- ✅ Accessible from another device on LAN via HTTPS
- ✅ Full workflow tested: HTTPS webhook → reindex → HTTPS MCP search
- ✅ Backup and restore procedures tested and documented
- ✅ Security hardening complete
- ✅ Comprehensive documentation written
- ✅ Deep understanding of reverse proxy, SSL, and networking concepts gained
- ✅ All code committed to git repository

---

## Key Learnings for Phase 4

After Phase 3 completion, you should understand:
- How reverse proxies work (Caddy routing to backend services)
- How SSL/TLS certificates work (self-signed vs CA-signed)
- How to debug certificate issues
- How to configure firewalls for HTTPS
- How Docker networking works (internal vs external access)
- How to test network services from remote devices
- Backup and restore strategies for stateful services

These learnings directly translate to Phase 4 (AWS deployment), where:
- Self-signed certs become Let's Encrypt (automatic, real SSL)
- LAN IP becomes public domain name
- Mac firewall becomes AWS security group
- Everything else stays the same!

---

## Notes for Phase 4

After Phase 3 completion:
- Caddy configuration is proven and working
- Authentication and security are tested
- Network exposure is understood
- Ready to deploy to AWS with minimal changes
- Main differences in Phase 4:
  - Real domain name instead of `minerva.local` or IP
  - Let's Encrypt instead of self-signed certs
  - AWS security groups instead of Mac firewall
  - Production environment variables from AWS Secrets Manager
