# Personal Local Knowledge Base Setup

This guide helps you set up Minerva for indexing your code repositories and making them searchable through Claude Desktop.

## What This Does

The setup wizard (`setup.sh`) automates the complete deployment of a personal knowledge base:

1. **Installs Minerva** via pipx (isolated, global installation)
2. **Configures AI provider** (OpenAI, Google Gemini, Ollama, or LM Studio)
3. **Securely stores credentials** in OS keychain (macOS Keychain, Linux Secret Service, Windows Credential Manager)
4. **Indexes a repository** with AI-powered embeddings
5. **Generates optimized descriptions** using AI to analyze your README
6. **Prepares Claude Desktop integration** with MCP server configuration

## Prerequisites

Before running the setup wizard, ensure you have:

- **Python 3.10+** installed
- **pipx** installed (`python -m pip install --user pipx && python -m pipx ensurepath`)
- **AI Provider** (choose one):
  - **OpenAI**: API key from [platform.openai.com](https://platform.openai.com)
  - **Google Gemini**: API key from [ai.google.dev](https://ai.google.dev)
  - **Ollama**: Local installation from [ollama.ai](https://ollama.ai) with models pulled
  - **LM Studio**: Desktop app from [lmstudio.ai](https://lmstudio.ai) with models loaded
- **Repository to index**: A local git repository or code directory

## Quick Start

```bash
# From the minerva repository root
./apps/local-repo-kb/setup.sh
```

The wizard will guide you through:

### 1. Minerva Installation

```
📦 Installing Minerva...
This will install Minerva and all dependencies (including keyring for secure credential storage)
Continue? [Y/n]:
```

- Installs via pipx (isolated environment)
- Detects if already installed (offers reinstall option)
- Includes keyring for OS-level credential encryption

### 2. AI Provider Selection

```
🤖 AI Provider Selection
Which AI provider do you want to use?
  1. OpenAI (cloud, requires API key)
  2. Google Gemini (cloud, requires API key)
  3. Ollama (local, free, no API key)
  4. LM Studio (local, free, no API key)
Choice [1-4]:
```

**Cloud Providers (OpenAI, Gemini):**
- Require API key (securely stored in OS keychain)
- Default models pre-configured
- Can customize models after selection

**Local Providers (Ollama, LM Studio):**
- No API key required
- Must have service running and models loaded
- You specify which models to use

### 3. API Key Storage (Cloud Providers Only)

```
🔑 API Key Configuration
Your OpenAI API key will be stored securely in OS keychain
  • macOS: Keychain Access (encrypted)
  • Linux: Secret Service (encrypted)
  • Windows: Credential Manager (encrypted)

The key will be stored as: 'OPENAI_API_KEY'
Config files will reference: ${OPENAI_API_KEY}
```

- Keys stored using OS encryption (Touch ID, Windows Hello, etc.)
- Never stored in plaintext files
- Can be updated/deleted later with `minerva keychain` commands

### 4. Repository Selection

```
📁 Repository to Index
Path to repository: ~/code/my-project
✓ Repository found: /Users/you/code/my-project
```

- Provide path to your code repository
- Can use `~` for home directory
- Script validates directory exists

### 5. Collection Naming

```
📚 Collection Name
Collection name (my-project):
✓ Collection: my-project
```

- Default: sanitized repository folder name
- Used to identify this knowledge base
- Must be unique (alphanumeric, hyphens, underscores only)
- If a name already exists, setup prompts you to rename or rebuild the old collection

### 6. AI-Generated Description

```
💬 Collection Description
📄 Found README.md in repository
🤖 Using AI to generate optimized description from README...

✨ Generated description:
   Python RAG system with vector search, embeddings, and MCP server
   integration for personal knowledge management. Best for questions
   about code architecture, component interactions, testing strategies,
   API design, indexing strategies, and search implementation.

✓ Description ready
```

**How it works:**
- If README.md exists → AI analyzes it and generates description
- If no README → You describe the repo, AI optimizes the description
- No manual editing (AI ensures description meets quality criteria)
- Optimized for semantic search effectiveness

### 7. Indexing

```
🔍 Extracting and Indexing
📚 Extracting repository contents...
✓ Extraction complete: ~/.minerva/apps/local-repo-kb/my-project-extracted.json

🔍 Indexing collection...
✓ Indexing complete
```

- Extracts documentation and code
- Generates embeddings using selected AI provider
- Stores in ChromaDB vector database

### 8. Configuration Summary

```
════════════════════════════════════════════════════════════
✅ Setup Complete!
════════════════════════════════════════════════════════════

📊 Configuration Summary
------------------------
  Provider:    OpenAI
  API Key:     Stored in keychain as 'OPENAI_API_KEY'
  Embedding:   text-embedding-3-small
  LLM:         gpt-4o-mini
  Collection:  my-project
  Repository:  /Users/you/code/my-project

📝 Files Created
----------------
  Server config:  ~/.minerva/apps/local-repo-kb/server.json
  Index config:   ~/.minerva/apps/local-repo-kb/my-project-index.json
  Watcher config: ~/.minerva/apps/local-repo-kb/my-project-watcher.json
  Extracted:      ~/.minerva/apps/local-repo-kb/my-project-extracted.json
  ChromaDB:       ~/.minerva/chromadb
```

## Configuring Claude Desktop

After setup completes, configure Claude Desktop to use your knowledge base:

### 1. Locate Claude Desktop Configuration

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

### 2. Add MCP Server Configuration

Edit the file and add your Minerva server:

```json
{
  "mcpServers": {
    "minerva-my-project": {
      "command": "/Users/you/.local/bin/minerva",
      "args": ["serve", "--config", "/Users/you/.minerva/apps/local-repo-kb/server.json"]
    }
  }
}
```

**Replace:**
- `minerva-my-project` → `minerva-YOUR-COLLECTION-NAME`
- `/Users/you/.local/bin/minerva` → Output of `which minerva`
- `/Users/you/.minerva/...` → Actual path from setup summary

### 3. Restart Claude Desktop

Completely quit and restart Claude Desktop to load the MCP server.

### 4. Test the Integration

In Claude Desktop, ask:

```
Search the my-project collection for API documentation
```

Claude will use the MCP server to search your indexed repository.

## File Structure

After setup, your files are organized as:

```
~/.minerva/
├── chromadb/                           # ChromaDB vector database
│   └── [collection data]
└── apps/
    └── local-repo-kb/
        ├── server.json                 # MCP server config (shared)
        ├── my-project-index.json       # Collection-specific index config
        ├── my-project-extracted.json   # Extracted documentation
        ├── other-repo-index.json       # Additional collections...
        └── other-repo-extracted.json
```

**Key points:**
- All data under `~/.minerva/` (easy to backup/delete)
- One `server.json` shared across all collections
- Each collection has its own `{name}-index.json` and `{name}-extracted.json`
- Supports multiple repositories (run wizard again for each)

## Managing API Keys

The wizard stores API keys in OS keychain. You can manage them using `minerva keychain` commands:

### View Stored Key (Masked)

```bash
minerva keychain get OPENAI_API_KEY
# Output: Stored credential for 'OPENAI_API_KEY': sk-proj-...abc (masked)
```

### Update Key

```bash
minerva keychain set OPENAI_API_KEY
# Prompts: Enter API key for OPENAI_API_KEY:
```

### Delete Key

```bash
minerva keychain delete OPENAI_API_KEY
# Output: ✓ Deleted 'OPENAI_API_KEY' from OS keychain
```

### List All Stored Providers

```bash
minerva keychain list
# Output: Stored providers: OPENAI_API_KEY, GEMINI_API_KEY
```

## Adding More Repositories

To index additional repositories, run the wizard again:

```bash
./apps/local-repo-kb/setup.sh
```

- Skip installation (already installed)
- Select same or different AI provider
- Provide different repository path
- Use different collection name

Each collection is independent and can use different AI providers or models.

## Troubleshooting

### Setup Wizard Fails to Install Minerva

**Error:** `Cannot find minerva setup.py`

**Solution:** Ensure you're running the script from a clone of the minerva repository:

```bash
git clone <minerva-repo-url>
cd minerva
./apps/local-repo-kb/setup.sh
```

### API Key Not Found During Indexing

**Error:** `Credential 'OPENAI_API_KEY' not found`

**Solution:** Re-run keychain storage:

```bash
minerva keychain set OPENAI_API_KEY
```

Then retry indexing:

```bash
minerva index --config ~/.minerva/apps/local-repo-kb/my-project-index.json
```

### Ollama Connection Errors

**Error:** `Provider unavailable: connection refused`

**Solution:** Ensure Ollama is running:

```bash
# Start Ollama service
ollama serve

# In another terminal, verify models
ollama list
```

### LM Studio Connection Errors

**Error:** `LM Studio unreachable`

**Solution:**
1. Start LM Studio desktop app
2. Load your embedding and LLM models
3. Ensure server is running (check LM Studio UI)

### Collection Not Found in Claude Desktop

**Symptoms:** Claude says "I don't have access to that collection"

**Solution:**
1. Check MCP server config path is correct
2. Verify collection name matches (`minerva peek <name> --chromadb ~/.minerva/chromadb`)
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for MCP server errors

### Re-indexing a Repository

To update an existing collection after repository changes:

```bash
# Re-run extraction
cd /path/to/your/repo
repository-doc-extractor . -o ~/.minerva/apps/local-repo-kb/my-project-extracted.json

# Re-run indexing (will recreate collection)
minerva index --config ~/.minerva/apps/local-repo-kb/my-project-index.json
```

## Advanced Configuration

### Using Environment Variables Instead of Keychain

If you prefer environment variables (for CI/CD, scripts, etc.):

```bash
# Set API key in environment
export OPENAI_API_KEY="sk-..."

# Run indexing (will use env var, not keychain)
minerva index --config ~/.minerva/apps/local-repo-kb/my-project-index.json
```

**Priority:** Environment variables > OS keychain

### Using envchain (Third-Party Tool)

If you use [envchain](https://github.com/sorah/envchain) for credential management:

```bash
# Store key with envchain
envchain --set openai OPENAI_API_KEY

# Run commands
envchain openai minerva index --config ~/.minerva/apps/local-repo-kb/my-project-index.json
```

### Customizing Models

Edit the index config to use different models:

```bash
# Edit config file
nano ~/.minerva/apps/local-repo-kb/my-project-index.json

# Change models:
{
  "provider": {
    "provider_type": "openai",
    "api_key": "${OPENAI_API_KEY}",
    "embedding_model": "text-embedding-3-large",  # ← Change this
    "llm_model": "gpt-4"                          # ← Change this
  }
}

# Re-index with new models
minerva index --config ~/.minerva/apps/local-repo-kb/my-project-index.json
```

## Security Considerations

### How API Keys Are Stored

- **OS Keychain:** Encrypted by operating system
- **macOS:** Keychain Access with Touch ID/password protection
- **Linux:** Secret Service (GNOME Keyring, KWallet)
- **Windows:** Credential Manager with Windows Hello

### What's Stored Where

**Encrypted (OS Keychain):**
- API keys for cloud providers

**Plaintext (Config Files):**
- Provider type, model names, paths
- Collection descriptions
- ChromaDB paths
- API key references like `${OPENAI_API_KEY}` (not actual keys)

**Not Stored Anywhere:**
- Repository source code (only extracted documentation)
- Your data is never sent to Minerva developers

### Best Practices

1. **Use dedicated API keys** for Minerva (easier to rotate/revoke)
2. **Set usage limits** on API keys (prevent unexpected charges)
3. **Regularly rotate keys** (update with `minerva keychain set`)
4. **Don't commit configs** with resolved keys to version control
5. **Backup ChromaDB** (`~/.minerva/chromadb/`) separately if critical

For detailed security information, see [SECURITY.md](SECURITY.md).

## Uninstalling

To completely remove Minerva and all data:

```bash
# 1. Remove Minerva installation
pipx uninstall minerva

# 2. Remove data and configs
rm -rf ~/.minerva

# 3. Remove API keys from keychain
minerva keychain delete OPENAI_API_KEY  # Run before uninstalling if you want to clean up keychain
```

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/yourusername/minerva/issues)
- **Documentation:** [Main README](../../README.md)
- **Security:** [SECURITY.md](SECURITY.md)

## Using the File Watcher

The setup wizard installs `local-repo-watcher`, a tool that automatically re-indexes your repository when files change.

### Starting the Watcher

```bash
# Run in a terminal
local-repo-watcher --config ~/.minerva/apps/local-repo-kb/my-project-watcher.json

# With verbose logging
local-repo-watcher --config ~/.minerva/apps/local-repo-kb/my-project-watcher.json --verbose
```

The watcher will:
- **Run initial indexing** on startup (ensures index is synced with repository)
- **Watch for file changes** in your repository
- **Automatically extract and re-index** when files change
- **Batch rapid changes** with 2-second debouncing

### Running as a Background Service

For automatic startup when you log in:

#### macOS (launchd)

Create `~/Library/LaunchAgents/com.minerva.watcher.my-project.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.minerva.watcher.my-project</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/you/.local/bin/local-repo-watcher</string>
        <string>--config</string>
        <string>/Users/you/.minerva/apps/local-repo-kb/my-project-watcher.json</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/you/.minerva/logs/watcher-my-project.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/you/.minerva/logs/watcher-my-project-error.log</string>
</dict>
</plist>
```

Then:

```bash
# Create logs directory
mkdir -p ~/.minerva/logs

# Load the service
launchctl load ~/Library/LaunchAgents/com.minerva.watcher.my-project.plist

# Check status
launchctl list | grep minerva

# View logs
tail -f ~/.minerva/logs/watcher-my-project.log
```

#### Linux (systemd)

Create `~/.config/systemd/user/local-repo-watcher@.service`:

```ini
[Unit]
Description=Local Repository Watcher for %i
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/local-repo-watcher --config %h/.minerva/apps/local-repo-kb/%i-watcher.json
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Then:

```bash
# Enable and start
systemctl --user enable local-repo-watcher@my-project
systemctl --user start local-repo-watcher@my-project

# Check status
systemctl --user status local-repo-watcher@my-project

# View logs
journalctl --user -u local-repo-watcher@my-project -f
```

For more details, see [tools/local-repo-watcher/README.md](../../tools/local-repo-watcher/README.md).

## Next Steps

After setup:

1. **Test searching** in Claude Desktop
2. **Start the file watcher** (recommended for keeping index up-to-date)
3. **Index more repositories** (run wizard again)
4. **Explore manual configuration** (see main README for advanced usage)
