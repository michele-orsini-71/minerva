# Security Guide: API Key Management

## Overview

Minerva provides secure API key storage using your operating system's encrypted keychain. This guide explains how the security model works and best practices for managing credentials.

## How Keychain Encryption Works

### macOS: Keychain Access

- **Storage**: macOS Keychain (encrypted with your login password)
- **Encryption**: AES-256 encryption
- **Biometric unlock**: Touch ID / Face ID support
- **Location**: `~/Library/Keychains/`
- **Access**: Apps must request permission to access stored credentials

To view stored credentials:

```bash
# Open Keychain Access app
open -a "Keychain Access"

# Search for "minerva" to see stored API keys
```

### Linux: Secret Service

- **Storage**: GNOME Keyring, KWallet, or compatible keyring
- **Encryption**: Backend-dependent (typically AES-256)
- **Location**: Varies by desktop environment
- **Access**: D-Bus Secret Service API

Supported backends:
- GNOME Keyring (GNOME desktop)
- KWallet (KDE desktop)
- kwallet (alternative)

### Windows: Credential Manager

- **Storage**: Windows Credential Manager
- **Encryption**: Windows Data Protection API (DPAPI)
- **Biometric unlock**: Windows Hello support
- **Location**: Encrypted in user profile
- **Access**: Windows Credential Vault API

To view stored credentials:

```powershell
# Open Credential Manager
control /name Microsoft.CredentialManager
```

## Credential Resolution Priority

Minerva resolves API keys in this order:

```
1. Environment Variable (highest priority)
   ↓
2. OS Keychain
   ↓
3. Error: Credential not found
```

This priority system allows:
- **Development**: Use environment variables for quick testing
- **CI/CD**: Use environment variables in pipelines
- **Production**: Use keychain for secure persistent storage
- **Override**: Temporarily override keychain with environment variable

### Examples

```bash
# Default: Uses keychain
minerva index --config config.json

# Override: Uses environment variable instead
OPENAI_API_KEY=sk-test-key minerva index --config config.json

# CI/CD: Only environment variables available
export OPENAI_API_KEY="${{ secrets.OPENAI_API_KEY }}"
minerva index --config config.json
```

## Best Practices

### 1. Use Dedicated API Keys

Create separate API keys for different purposes:

```bash
# Development key (lower rate limits)
minerva keychain set OPENAI_DEV_API_KEY

# Production key (higher rate limits)
minerva keychain set OPENAI_PROD_API_KEY
```

Then reference in config:

```json
{
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_DEV_API_KEY}"
  }
}
```

### 2. Regular Key Rotation

Rotate API keys periodically for security:

```bash
# Generate new key in provider dashboard
# Update in keychain
minerva keychain set OPENAI_API_KEY

# Old key is automatically replaced
```

### 3. Set Rate Limits

Configure conservative rate limits to prevent abuse:

```json
{
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "rate_limit": {
      "requests_per_minute": 60,
      "concurrency": 1
    }
  }
}
```

### 4. Monitor API Usage

Regularly check your API provider dashboard for:
- Unexpected usage spikes
- Failed authentication attempts
- Geographic anomalies
- Cost overruns

### 5. Revoke Compromised Keys Immediately

If a key is compromised:

```bash
# 1. Revoke in provider dashboard (immediate)
# 2. Generate new key
# 3. Update keychain
minerva keychain set OPENAI_API_KEY

# 4. Verify old key no longer works
```

## Advanced Options

### Using envchain (macOS/Linux)

For additional security, use `envchain` to manage environment variables:

```bash
# Install envchain
brew install envchain  # macOS
# or build from source on Linux

# Store API key in envchain's keychain namespace
envchain --set openai OPENAI_API_KEY

# Use with minerva
envchain openai minerva index --config config.json
```

Benefits:
- Environment variables never stored in shell history
- Separate keychain namespace
- Per-application credential isolation

### Using 1Password CLI

For teams using 1Password:

```bash
# Install 1Password CLI
brew install 1password-cli

# Reference secrets in config
export OPENAI_API_KEY="op://vault/item/field"

# Run with 1Password shell plugin
op run -- minerva index --config config.json
```

Benefits:
- Centralized team credential management
- Audit logs
- Fine-grained access control
- Secret rotation automation

### Shell Profile Integration

For persistent environment variables (less secure than keychain):

```bash
# ~/.zshrc or ~/.bashrc
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
```

⚠️ **Warning**: This stores credentials in plaintext. Only use for:
- Development environments
- Non-production keys
- Keys with strict rate limits

## CI/CD Usage

In CI/CD pipelines, use environment variables (keychain not available):

### GitHub Actions

```yaml
jobs:
  index:
    runs-on: ubuntu-latest
    steps:
      - name: Index with Minerva
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          minerva index --config config.json
```

### GitLab CI

```yaml
index:
  script:
    - minerva index --config config.json
  variables:
    OPENAI_API_KEY: $OPENAI_API_KEY
```

### Jenkins

```groovy
withCredentials([string(credentialsId: 'openai-api-key', variable: 'OPENAI_API_KEY')]) {
    sh 'minerva index --config config.json'
}
```

## Troubleshooting

### Keychain Access Denied (macOS)

If you see "access denied" errors:

```bash
# Grant terminal access to keychain
# System Preferences → Security & Privacy → Privacy → Automation
# Enable Terminal.app

# Or reset keychain permissions
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

### No Keyring Backend Available (Linux)

If keyring backend is not available:

```bash
# Install GNOME Keyring
sudo apt-get install gnome-keyring  # Debian/Ubuntu
sudo dnf install gnome-keyring      # Fedora

# Or use environment variables as fallback
export OPENAI_API_KEY="sk-..."
```

### Credential Not Found

If minerva can't find your credential:

```bash
# Verify credential is stored
minerva keychain get OPENAI_API_KEY

# Check environment variable name matches
# Config uses: ${OPENAI_API_KEY}
# Keychain stores as: OPENAI_API_KEY
# Environment variable: OPENAI_API_KEY

# Re-store if needed
minerva keychain set OPENAI_API_KEY
```

## Security Considerations

### What's Encrypted

✅ **Encrypted**:
- API keys in OS keychain (AES-256)
- API keys in memory during execution (process-isolated)

### What's Not Encrypted

❌ **Not encrypted**:
- Configuration files (paths, model names, URLs)
- API requests over HTTPS (but encrypted in transit)
- API responses and cached embeddings in ChromaDB

### Network Security

All API requests use HTTPS by default:
- OpenAI: `https://api.openai.com`
- Gemini: `https://generativelanguage.googleapis.com`
- Anthropic: `https://api.anthropic.com`

Local providers (Ollama, LM Studio) use HTTP on localhost only.

### Multi-User Systems

On shared systems:
- Each user has isolated keychain
- API keys not shared between users
- ChromaDB data is user-specific (file permissions)

## Compliance & Auditing

### Audit Trail

Keychain operations are logged:

```bash
# macOS: Check security logs
log show --predicate 'process == "securityd"' --last 1h

# Linux: Check keyring access logs (varies by backend)
journalctl -u gnome-keyring -f
```

### Data Residency

API keys are stored:
- **Keychain**: Locally on your machine only
- **API Providers**: Keys sent to provider servers (OpenAI, Gemini, etc.)
- **Embeddings**: Stored locally in ChromaDB

For compliance, ensure:
- Use self-hosted models (Ollama, LM Studio) for sensitive data
- Cloud providers (OpenAI, Gemini) process data on their infrastructure
- Review provider data processing agreements

## Getting Help

If you encounter security issues:

1. **Check logs**: Run with `--verbose` flag for detailed output
2. **Verify keychain**: Use `minerva keychain list` to check stored credentials
3. **Test priority**: Use environment variable to bypass keychain for testing
4. **Report issues**: [GitHub Issues](https://github.com/yourusername/minerva/issues)

For security vulnerabilities, please report privately to the maintainers.
