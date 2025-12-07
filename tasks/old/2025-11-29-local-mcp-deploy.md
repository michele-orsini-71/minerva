# Plan: pipx-Based Minerva Deployment with OS Keychain Security

## Executive Summary

Create a simplified, pipx-based deployment for Minerva using OS keychain for secure credential storage.

**Solution:** OS Keychain integration (Tier 2 only)
- API keys stored in OS-encrypted keychain
- Fallback to environment variables for CI/CD
- No wrapper scripts or credentials files needed
- Works with: Manual CLI, File Watcher, Claude Desktop MCP
- All deployment files in: `apps/local-repo-kb/` (source control)

## Decision: Tier 2 Only (OS Keychain)

After evaluation, we decided to implement **only Tier 2 (OS Keychain)** because:

1. ✅ **No legacy users** - Clean slate, no backwards compatibility needed
2. ✅ **Better security** - OS-encrypted vs plaintext files
3. ✅ **Simpler implementation** - No wrapper scripts needed
4. ✅ **Industry standard** - AWS CLI, gcloud all use keychain
5. ✅ **Better UX** - One command to store key: `minerva keychain set OPENAI_API_KEY`
6. ✅ **Claude Desktop compatible** - Works directly without wrapper scripts
7. ✅ **CI/CD compatible** - Environment variables still work as priority

**Tier 1 (credentials file)** was rejected because:
- ❌ More complex (wrapper scripts, shell profile modifications)
- ❌ Less secure (plaintext on disk)
- ❌ Unnecessary (keychain solves the same problem better)

## How It Works

### Credential Resolution Priority

```
1. Environment Variable (highest priority)
   export OPENAI_API_KEY="sk-..."
   Use case: CI/CD, scripts, manual overrides

2. OS Keychain (fallback)
   minerva keychain set OPENAI_API_KEY
   Use case: User workstations, persistent storage

3. Error (not found)
   Clear message suggesting both options
```

### Internal Flow

```
User Command
    ↓
Config File: "api_key": "${OPENAI_API_KEY}"
    ↓
resolve_env_variable("${OPENAI_API_KEY}")
    ↓
get_credential("OPENAI_API_KEY")
    ↓
Check: os.environ.get("OPENAI_API_KEY")
    ↓ (if not found)
Check: keyring.get_password("minerva", "OPENAI_API_KEY")
    ↓
Return: "sk-actual-key" or raise error
```

## Implementation Checklist

### Phase 1: Core Keychain Integration

#### 1. `setup.py` - Add keyring as required dependency

```python
install_requires=[
    # ... existing deps
    "keyring>=24.0.0",  # OS keychain integration (required)
]
```

**Note:** NOT optional - required for all installations

#### 2. `minerva/common/credential_helper.py` (NEW FILE)

Core credential resolution with keychain support:

```python
"""
Credential helper for retrieving API keys from multiple sources.
Priority: environment variables → OS keychain → error
"""
import os
import keyring
from typing import Optional
from minerva.common.logger import get_logger

logger = get_logger(__name__)
KEYRING_SERVICE = "minerva"

def get_credential(credential_name: str) -> Optional[str]:
    """
    Retrieve credential from env vars (priority) or keychain (fallback).

    Args:
        credential_name: "OPENAI_API_KEY"

    Returns:
        Credential value or None
    """
    # 1. Check environment variable (priority)
    value = os.environ.get(credential_name)
    if value:
        logger.debug(f"Loaded '{env_var_name}' from environment")
        return value

    # 2. Check OS keychain (fallback)
    try:
        value = keyring.get_password(KEYRING_SERVICE, credential_name)
        if value:
            logger.debug(f"Loaded '{credential_name}' from OS keychain")
            return value
    except Exception as e:
        logger.debug(f"Keychain access failed: {e}")

    return None

def set_credential(provider_name: str, api_key: str) -> None:
    """Store credential in OS keychain."""
    keyring.set_password(KEYRING_SERVICE, provider_name.lower(), api_key)
    logger.info(f"✓ Stored '{provider_name}' in OS keychain")

def delete_credential(provider_name: str) -> None:
    """Delete credential from OS keychain."""
    try:
        keyring.delete_password(KEYRING_SERVICE, provider_name.lower())
        logger.info(f"✓ Deleted '{provider_name}' from OS keychain")
    except keyring.errors.PasswordDeleteError:
        logger.warning(f"No credential found for '{provider_name}'")
```

#### 3. `minerva/common/ai_config.py` - Integrate credential helper

Modify `resolve_env_variable()` to use `get_credential()`:

```python
from minerva.common.credential_helper import get_credential

def resolve_env_variable(value: Optional[str]) -> Optional[str]:
    """Resolve ${VAR_NAME} using env vars or keychain."""
    if value is None:
        return None

    env_var_pattern = re.compile(r'\$\{([^}]+)\}')

    def replace_env_var(match):
        var_name = match.group(1)
        credential = get_credential(var_name)  # ← Uses credential helper

        if credential is None:
            raise APIKeyMissingError(
                f"Credential '{var_name}' not found.\n\n"
                f"Options:\n"
                f"  1. Keychain: minerva keychain set {var_name}\n"
                f"  2. Environment: export {var_name}='your-key'\n"
                f"  3. Shell profile: Add export to ~/.zshrc"
            )

        return credential

    return env_var_pattern.sub(replace_env_var, value)
```

#### 4. `minerva/cli.py` - Add keychain subcommand

```python
# Add keychain subparser
keychain_parser = subparsers.add_parser(
    'keychain',
    help='Manage API keys in OS keychain'
)
keychain_subs = keychain_parser.add_subparsers(dest='keychain_action')

# keychain set
set_p = keychain_subs.add_parser('set', help='Store API key')
set_p.add_argument('provider', help='Credential name (e.g., OPENAI_API_KEY)')
set_p.add_argument('--key', help='API key (prompted if not provided)')

# keychain get
get_p = keychain_subs.add_parser('get', help='Show API key (masked)')
get_p.add_argument('provider', help='Provider name')

# keychain delete
del_p = keychain_subs.add_parser('delete', help='Delete API key')
del_p.add_argument('provider', help='Provider name')

# keychain list
list_p = keychain_subs.add_parser('list', help='List stored providers')
```

#### 5. `minerva/commands/keychain.py` (NEW FILE)

CLI command implementation - see credential_helper.py above for full code.

### Phase 2: Deployment Package (apps/local-repo-kb/)

#### File Structure

```
apps/local-repo-kb/
├── README.md                       # Complete deployment guide
├── setup.sh                        # Interactive setup script
├── SECURITY.md                     # Security documentation
└── configs/
    ├── server.json.template        # MCP server config
    └── index.json.template         # Indexing config
```

**Note:** No `bin/` directory - no wrapper scripts needed!

#### 1. `apps/local-repo-kb/README.md`

Complete pipx deployment guide with:
- Prerequisites (Python 3.10+, pipx, OpenAI API key)
- Quick start (3 commands)
- Step-by-step setup
- Claude Desktop configuration
- File watcher setup (if applicable)
- Troubleshooting
- Advanced: environment variable usage
- Advanced: envchain usage

#### 2. `apps/local-repo-kb/setup.sh`

```bash
#!/bin/bash
set -e

echo "🚀 Minerva Setup (pipx + OS Keychain)"
echo ""

# 1. Check prerequisites
if ! command -v pipx &> /dev/null; then
    echo "❌ pipx not found"
    echo "Install: python -m pip install --user pipx"
    exit 1
fi

# 2. Install minerva (includes keyring)
echo "📦 Installing Minerva..."
pipx install minerva

# 3. Store API key in keychain
echo ""
echo "🔑 Storing API key in OS keychain"
echo "This is secure and OS-encrypted (Touch ID, Windows Hello, etc.)"
echo ""
minerva keychain set OPENAI_API_KEY
# ↑ This prompts: "Enter API key for OPENAI_API_KEY: "

# 4. Create directory structure
mkdir -p ~/.minerva/{configs,chromadb,data}

# 5. Generate configs from templates
echo ""
echo "📝 Creating configuration files..."

cat > ~/.minerva/configs/server.json << EOF
{
  "chromadb_path": "$HOME/.minerva/chromadb",
  "default_max_results": 5
}
EOF

cat > ~/.minerva/configs/index.json << EOF
{
  "chromadb_path": "$HOME/.minerva/chromadb",
  "collection": {
    "name": "my_repo",
    "description": "Local repository documentation",
    "json_file": "$HOME/.minerva/data/repo.json",
    "chunk_size": 1200
  },
  "provider": {
    "provider_type": "openai",
    "api_key": "\${OPENAI_API_KEY}",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini"
  }
}
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Configure Claude Desktop MCP:"
echo "   Edit: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
cat << 'CLAUDE_CONFIG'
{
  "mcpServers": {
    "minerva": {
      "command": "/Users/YOUR_USERNAME/.local/bin/minerva",
      "args": ["serve", "--config", "/Users/YOUR_USERNAME/.minerva/configs/server.json"]
    }
  }
}
CLAUDE_CONFIG
echo ""
echo "2. Test the setup:"
echo "   minerva index --config ~/.minerva/configs/index.json"
echo ""
echo "🔐 Your API key is securely stored in OS keychain"
echo "   View: minerva keychain get OPENAI_API_KEY"
echo "   Update: minerva keychain set OPENAI_API_KEY"
echo "   Delete: minerva keychain delete OPENAI_API_KEY"
```

#### 3. `apps/local-repo-kb/SECURITY.md`

Document security model:
- How keychain encryption works (macOS, Linux, Windows)
- Priority system (env vars override keychain)
- Best practices (dedicated keys, rotation, limits)
- Advanced options (envchain, 1Password CLI)
- CI/CD usage (environment variables)

#### 4. Config Templates

**`apps/local-repo-kb/configs/server.json.template`:**
```json
{
  "chromadb_path": "{{HOME}}/.minerva/chromadb",
  "default_max_results": 5
}
```

**`apps/local-repo-kb/configs/index.json.template`:**
```json
{
  "chromadb_path": "{{HOME}}/.minerva/chromadb",
  "collection": {
    "name": "my_repo",
    "description": "Local repository documentation",
    "json_file": "{{HOME}}/.minerva/data/repo.json",
    "chunk_size": 1200
  },
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini"
  }
}
```

### Phase 3: Documentation Updates

#### 1. Update main `README.md`

Add section on pipx deployment:

```markdown
## Installation

### Option 1: pipx (Recommended)

Easiest installation with OS keychain security:

\`\`\`bash
# Install
pipx install minerva

# Store API key securely
minerva keychain set OPENAI_API_KEY

# Done! Use minerva commands
minerva --help
\`\`\`

See [apps/local-repo-kb/README.md](apps/local-repo-kb/README.md) for complete setup guide.
```

## User Workflows

### Recommended Workflow (Keychain)

```bash
# One-time setup
pipx install minerva
minerva keychain set OPENAI_API_KEY

# Use normally
minerva index --config config.json
minerva serve --config config.json
```

### CI/CD Workflow (Environment Variables)

```bash
# In pipeline
export OPENAI_API_KEY="${{ secrets.OPENAI_API_KEY }}"
minerva index --config config.json
```

### Advanced Workflow (envchain)

```bash
# Still works! Env vars have priority
envchain openai minerva index --config config.json
```

### Power User Workflow (Session Override)

```bash
# Temporary different key
OPENAI_API_KEY="sk-different" minerva index --config config.json
```

All workflows work seamlessly because of the priority system!

## Benefits Over Tier 1

| Aspect | Tier 1 (File + Wrapper) | Tier 2 (Keychain) | Winner |
|--------|--------------------------|-------------------|--------|
| Security | File mode 600 (plaintext) | OS-encrypted | ✅ Tier 2 |
| Complexity | Wrapper + file + shell profile | Just keychain | ✅ Tier 2 |
| Claude Desktop | Needs wrapper script | Direct execution | ✅ Tier 2 |
| File Watcher | Works | Works | ✅ Tie |
| Manual Commands | Works | Works | ✅ Tie |
| Biometric Unlock | No | Yes (Touch ID, etc.) | ✅ Tier 2 |
| Key Rotation | Edit file, restart | One command | ✅ Tier 2 |
| Files to Manage | 3 (credentials, wrapper, profile) | 0 | ✅ Tier 2 |

**Result: Tier 2 is superior in every measurable way**

## Testing Checklist

- [ ] Install with pipx
- [ ] Store key: `minerva keychain set OPENAI_API_KEY`
- [ ] Manual command: `minerva index --config ~/.minerva/configs/index.json`
- [ ] Verify keychain storage: `minerva keychain get OPENAI_API_KEY`
- [ ] Test env var priority: `OPENAI_API_KEY=test minerva index ...`
- [ ] Claude Desktop MCP: Server starts and responds
- [ ] File watcher: Can trigger indexing
- [ ] Key rotation: `minerva keychain set OPENAI_API_KEY` with new key
- [ ] Delete key: `minerva keychain delete OPENAI_API_KEY`
- [ ] Error message quality: Run without key, verify helpful message

## Implementation Order

1. ✅ Core keychain integration (setup.py, credential_helper.py, ai_config.py)
2. ✅ CLI command (cli.py, commands/keychain.py)
3. ✅ Test keychain functionality
4. ✅ Create apps/local-repo-kb/ structure
5. ✅ Write setup.sh script
6. ✅ Write README.md and SECURITY.md
7. ✅ Test complete deployment flow
8. ✅ Update main README.md

## Sources

- [Python keyring library](https://pypi.org/project/keyring/) - OS keychain integration
- [AWS CLI Credential Security](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [1Password AWS CLI Integration](https://developer.1password.com/docs/cli/shell-plugins/aws/)
- [API Key Security Best Practices](https://blog.gitguardian.com/api-key-security-7/)
