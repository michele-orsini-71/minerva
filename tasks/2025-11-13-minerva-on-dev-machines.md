# Implementation Plan: Minerva on Developer Machines

## Overview

Enable each team member to run Minerva locally on their MacBooks for fast, private, and offline-capable semantic search of company repositories.

**Why Local Instead of Server:**
- ✅ **10-50x faster** indexing and search (M1/M2 Neural Engine vs server CPU)
- ✅ **Zero cost** (no server fees, use existing hardware)
- ✅ **Private** (code never leaves developer's machine)
- ✅ **Offline-capable** (works without internet)
- ✅ **Simple** (15-min setup vs 4-6 hour server deployment)
- ✅ **Already works** with Claude Desktop (stdio mode)

**Target Users:** Developers with 16-32GB M1/M2 MacBooks

## Architecture

```
Developer's MacBook (M1/M2)
├── Ollama (local, port 11434)
│   ├── mxbai-embed-large (670MB)
│   └── llama3.1:8b (4.7GB)
│
├── Company Repositories (git clones)
│   ├── ~/repos/company-docs/
│   ├── ~/repos/api-docs/
│   └── ~/repos/internal-wiki/
│
├── Minerva (editable install: pip install -e)
│   ├── Source: ~/minerva/ (git clone)
│   ├── ChromaDB (~/.minerva/chromadb/)
│   │   ├── company_docs collection
│   │   ├── api_docs collection
│   │   └── internal_wiki collection
│   ├── Configs (~/.minerva/configs/)
│   └── Extracted JSON (~/.minerva/extracted/)
│
├── Git Hooks (per repository)
│   ├── post-commit → reindex if .md changed
│   └── post-merge → reindex if .md changed
│
└── Claude Desktop
    └── MCP config (stdio to minerva serve)
```

## Workflow

### Daily Usage
```
Developer makes changes:
1. Edit docs/api.md
2. git commit -m "Update API docs"
3. Git hook detects .md change
4. Auto-reindex (~30 seconds on M1/M2)
5. Search immediately available in Claude Desktop

Teammate pushed changes:
1. git pull
2. Git hook detects remote .md changes
3. Auto-reindex
4. Search teammate's updates in Claude Desktop
```

## Phase 1: Developer Setup Automation

### 1.1 Create setup script (`scripts/setup-developer-machine.sh`)

**Purpose:** One-command setup for new team members

**What it does:**
1. Check prerequisites (git, Python 3.10+)
2. Install Ollama (if not installed)
3. Pull required Ollama models
4. Clone Minerva repository to ~/minerva/
5. Install Minerva in editable mode (pip install -e ~/minerva/)
6. Install extractors in editable mode
7. Create directory structure (~/.minerva/)
8. Clone company repositories to ~/repos/
9. Generate config files
10. Perform initial indexing
11. Install git hooks
12. Configure Claude Desktop

**Note on editable install (-e):**
- Installs Minerva by linking to source directory (not copying)
- Code changes in ~/minerva/ are immediately active (no reinstall needed)
- Updates are simple: `cd ~/minerva && git pull` (no pip reinstall)
- Allows local modifications and contributions

**Script structure:**
```bash
#!/bin/bash
set -e

# Configuration (edit these for your company)
COMPANY_REPOS=(
    "https://github.com/company/docs:company-docs:company_docs"
    "https://github.com/company/api:api-docs:api_docs"
    "https://github.com/company/wiki:internal-wiki:internal_wiki"
)

MINERVA_HOME="$HOME/.minerva"
MINERVA_SOURCE="$HOME/minerva"
REPOS_DIR="$HOME/repos"

# Functions
check_prerequisites() {
    # Check git, python, brew (macOS)
}

install_ollama() {
    # Install if missing, skip if exists
}

clone_and_install_minerva() {
    # Clone Minerva repository
    git clone https://github.com/company/minerva "$MINERVA_SOURCE"

    # Install in editable mode (links to source directory)
    pip install -e "$MINERVA_SOURCE"

    # Install extractors in editable mode
    pip install -e "$MINERVA_SOURCE/extractors/repository-doc-extractor"

    # Create data directories
    mkdir -p "$MINERVA_HOME"/{chromadb,configs,extracted,logs}
}

clone_repositories() {
    # Clone each repo in COMPANY_REPOS
}

generate_configs() {
    # Create index config for each repo
}

install_git_hooks() {
    # Install post-commit/post-merge hooks
}

initial_indexing() {
    # Extract and index each repo
}

configure_claude_desktop() {
    # Add minerva to Claude Desktop config
}

# Main execution
main() {
    echo "🚀 Setting up Minerva for local development..."
    check_prerequisites
    install_ollama
    clone_and_install_minerva
    clone_repositories
    generate_configs
    install_git_hooks
    initial_indexing
    configure_claude_desktop
    echo "✅ Setup complete! Restart Claude Desktop to use Minerva."
    echo ""
    echo "📝 To update Minerva in the future:"
    echo "   cd ~/minerva && git pull"
    echo "   (No reinstall needed - editable install automatically uses latest code)"
}

main
```

**Features:**
- Idempotent (safe to run multiple times)
- Progress indicators
- Error handling with helpful messages
- Dry-run mode (`--dry-run`)
- Verbose mode (`--verbose`)

### 1.2 Create configuration template generator (`scripts/generate-repo-config.sh`)

**Purpose:** Generate index config for a repository

**Input:**
- Repository path
- Repository name (for collection)
- Description

**Output:**
- Index config JSON file
- Saved to `~/.minerva/configs/index-{repo_name}.json`

**Example:**
```bash
./scripts/generate-repo-config.sh \
    ~/repos/company-docs \
    "company-docs" \
    "Company documentation and guides"

# Generates: ~/.minerva/configs/index-company-docs.json
```

**Config template:**
```json
{
  "chromadb_path": "~/.minerva/chromadb",
  "collection": {
    "name": "{{COLLECTION_NAME}}",
    "description": "{{DESCRIPTION}}",
    "json_file": "~/.minerva/extracted/{{REPO_NAME}}.json",
    "chunk_size": 1200,
    "force_recreate": false
  },
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://localhost:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
```

### 1.3 Create repository list config (`configs/company-repos.json`)

**Purpose:** Central config listing all company repositories to index

**Format:**
```json
{
  "repositories": [
    {
      "name": "company-docs",
      "git_url": "https://github.com/company/docs",
      "local_path": "~/repos/company-docs",
      "collection": "company_docs",
      "description": "Company documentation and guides",
      "auto_index": true
    },
    {
      "name": "api-docs",
      "git_url": "https://github.com/company/api",
      "local_path": "~/repos/api-docs",
      "collection": "api_docs",
      "description": "API documentation and references",
      "auto_index": true
    },
    {
      "name": "internal-wiki",
      "git_url": "https://github.com/company/wiki",
      "local_path": "~/repos/internal-wiki",
      "collection": "internal_wiki",
      "description": "Internal wiki and knowledge base",
      "auto_index": true
    }
  ]
}
```

**Usage:**
- Setup script reads this file
- Easy to add new repos (just edit JSON)
- Shared across team (committed to minerva repo)

## Phase 2: Git Hook Implementation

### 2.1 Create smart git hook script (`scripts/git-hooks/minerva-auto-index`)

**Purpose:** Automatically reindex when markdown files change

**Features:**
- Detect if `.md` or `.mdx` files changed in commit/merge
- Skip if no markdown changes (fast)
- Extract → Validate → Index pipeline
- Error handling (don't break git operations)
- Logging for debugging
- Background execution (don't block git)

**Hook script:**
```bash
#!/bin/bash
# Minerva auto-index git hook
# Can be used as post-commit or post-merge hook

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOK_NAME=$(basename "$0")

# Source Minerva config if exists
if [ -f "$REPO_ROOT/.minerva-config" ]; then
    source "$REPO_ROOT/.minerva-config"
else
    echo "Warning: .minerva-config not found, skipping auto-index"
    exit 0
fi

# Determine what files changed
if [ "$HOOK_NAME" = "post-commit" ]; then
    # Check current commit
    CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD)
elif [ "$HOOK_NAME" = "post-merge" ]; then
    # Check merge changes
    CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD@{1} HEAD)
else
    CHANGED_FILES=""
fi

# Check for markdown file changes
MD_CHANGED=$(echo "$CHANGED_FILES" | grep -E '\.(md|mdx)$')

if [ -z "$MD_CHANGED" ]; then
    echo "⏭  No markdown files changed, skipping reindex"
    exit 0
fi

echo "📝 Markdown files changed, triggering reindex..."

# Run reindex in background (don't block git)
(
    # Extract markdown files
    repository-doc-extractor "$REPO_ROOT" -o "$EXTRACT_OUTPUT" 2>&1 | tee -a "$LOG_FILE"

    # Validate
    minerva validate "$EXTRACT_OUTPUT" 2>&1 | tee -a "$LOG_FILE"

    # Index
    minerva index --config "$INDEX_CONFIG" --verbose 2>&1 | tee -a "$LOG_FILE"

    echo "✅ Reindex complete ($(date))" | tee -a "$LOG_FILE"
) &

echo "🔄 Reindex started in background (PID: $!)"
echo "📋 Log: $LOG_FILE"

exit 0
```

### 2.2 Create hook installer (`scripts/install-git-hook.sh`)

**Purpose:** Install Minerva hooks into a repository

**Usage:**
```bash
./scripts/install-git-hook.sh ~/repos/company-docs ~/.minerva/configs/index-company-docs.json

# Installs:
# - .git/hooks/post-commit
# - .git/hooks/post-merge
# - .minerva-config (hook configuration)
```

**What it does:**
1. Copy hook script to `.git/hooks/post-commit`
2. Create symlink: `.git/hooks/post-merge` → `post-commit`
3. Make hooks executable
4. Create `.minerva-config` in repo root:
   ```bash
   EXTRACT_OUTPUT="$HOME/.minerva/extracted/company-docs.json"
   INDEX_CONFIG="$HOME/.minerva/configs/index-company-docs.json"
   LOG_FILE="$HOME/.minerva/logs/company-docs.log"
   ```

### 2.3 Create hook uninstaller (`scripts/uninstall-git-hook.sh`)

**Purpose:** Remove Minerva hooks from a repository

**Usage:**
```bash
./scripts/uninstall-git-hook.sh ~/repos/company-docs
```

**What it does:**
1. Remove `.git/hooks/post-commit` (if it's Minerva hook)
2. Remove `.git/hooks/post-merge` (if symlink to post-commit)
3. Remove `.minerva-config`
4. Preserve other hooks

## Phase 3: Repository Management Commands

### 3.1 Create `minerva add-repo` command

**Purpose:** Add a new repository to local Minerva setup

**Usage:**
```bash
minerva add-repo \
    --git-url https://github.com/company/new-repo \
    --name new-repo \
    --collection new_repo_docs \
    --description "New repository documentation"

# Does:
# 1. Clone repository to ~/repos/new-repo
# 2. Generate config ~/.minerva/configs/index-new-repo.json
# 3. Extract and index
# 4. Install git hooks
# 5. Update ~/.minerva/repos.json
```

**Implementation:**
- Add to `minerva/commands/add_repo.py`
- Use existing functions (clone, extract, index)
- Interactive mode (prompts for missing info)

### 3.2 Create `minerva update-repos` command

**Purpose:** Pull all repositories and reindex if needed

**Usage:**
```bash
# Update all repos
minerva update-repos

# Update specific repos
minerva update-repos company-docs api-docs

# Force reindex even if no changes
minerva update-repos --force
```

**What it does:**
```python
for repo in repos:
    cd repo.local_path
    git pull
    if has_markdown_changes() or force:
        extract_and_index(repo)
```

**Use cases:**
- Manual sync (if hooks didn't run for some reason)
- After pulling multiple repos at once
- Scheduled job (cron every hour)

### 3.3 Create `minerva list-repos` command

**Purpose:** Show status of all indexed repositories

**Usage:**
```bash
minerva list-repos

# Output:
# Repository            Collection         Last Indexed         Notes
# ─────────────────────────────────────────────────────────────────────
# company-docs          company_docs       2025-11-13 10:30     1,234 notes
# api-docs              api_docs           2025-11-13 09:15     567 notes
# internal-wiki         internal_wiki      2025-11-12 18:00     890 notes
```

**Features:**
- Show last index time
- Show note count
- Show git status (ahead/behind/dirty)
- Color-coded status (green=up-to-date, yellow=needs-update, red=error)

### 3.4 Create `minerva remove-repo` command

**Purpose:** Remove a repository from Minerva setup

**Usage:**
```bash
minerva remove-repo company-docs

# Options:
# --keep-repo: Don't delete git repository
# --keep-collection: Don't delete ChromaDB collection
```

**What it does:**
1. Uninstall git hooks
2. Delete ChromaDB collection (optional)
3. Delete config file
4. Delete extracted JSON
5. Update repos.json
6. Optionally delete git repository

## Phase 4: Documentation

### 4.1 Create developer onboarding guide (`docs/DEVELOPER_SETUP.md`)

**Sections:**

#### Prerequisites
- macOS (Intel or Apple Silicon)
- 16GB+ RAM recommended
- 20GB free disk space
- Python 3.10+
- Git

#### Quick Start (5 Minutes)
```bash
# 1. Clone Minerva
git clone https://github.com/company/minerva
cd minerva

# 2. Run setup script
./scripts/setup-developer-machine.sh

# 3. Restart Claude Desktop

# 4. Start searching!
```

#### What Gets Installed
- Ollama + models (~6GB)
- Minerva source repository (~/minerva/) - installed in editable mode
- Minerva extractors (~/minerva/extractors/) - installed in editable mode
- Company repositories (~/repos/) - varies by size
- ChromaDB indexes (~/.minerva/chromadb/) - ~1-5GB per repo

#### Understanding Editable Install

**What is `pip install -e`?**
- **Editable mode** (also called "development mode")
- Instead of copying code to site-packages, creates a link to source directory
- Python imports directly from ~/minerva/ (not a copy)
- Code changes in source are immediately active (no reinstall needed)

**Why use editable install for this setup?**
- ✅ Easy updates: Just `git pull` (no pip reinstall)
- ✅ Can make local fixes/changes immediately
- ✅ Can contribute back to Minerva easily
- ✅ Perfect for development teams
- ✅ Keeps source in one place (~/minerva/)

**How updates work with editable install:**
```bash
# Regular install (copies code)
pip install minerva     # Installs copy
git pull                # Does nothing (code is a copy)
pip install --upgrade   # Must reinstall to get updates

# Editable install (links to source)
pip install -e ~/minerva  # Creates link
git pull                  # Updates source
# Python automatically uses updated code (no reinstall!)
```

#### Manual Setup (If Script Fails)
Step-by-step instructions for manual installation

#### Troubleshooting
Common issues and solutions

### 4.2 Create usage guide (`docs/DEVELOPER_USAGE.md`)

**Sections:**

#### Daily Workflow
- Commit changes → auto-reindex
- Pull changes → auto-reindex
- Search in Claude Desktop

#### Managing Repositories
```bash
# Add new repository
minerva add-repo --git-url https://github.com/company/new

# Update all repositories
minerva update-repos

# List repositories
minerva list-repos

# Remove repository
minerva remove-repo old-repo
```

#### Manual Indexing
```bash
# Reindex specific repo
cd ~/repos/company-docs
repository-doc-extractor . -o ~/.minerva/extracted/company-docs.json
minerva index --config ~/.minerva/configs/index-company-docs.json
```

#### Checking Status
```bash
# View collections
minerva peek company_docs --chromadb ~/.minerva/chromadb

# Check Ollama
ollama list
ollama ps  # Running models

# Check disk usage
du -sh ~/.minerva/
du -sh ~/.ollama/
```

#### Updating Minerva

Since Minerva is installed in **editable mode** (`-e`), updates are simple:

```bash
# Pull latest changes from git
cd ~/minerva
git pull

# Done! Changes are immediately active (no reinstall needed)
```

**How editable install works:**
- `pip install -e` creates a link to the source directory (not a copy)
- Python imports directly from ~/minerva/
- When you `git pull`, the source updates
- Python automatically uses the updated code (no reinstall)

**When to reinstall (rare cases):**
```bash
# Only if new dependencies were added to setup.py
cd ~/minerva
git pull
pip install -e .  # Installs new dependencies

# Or if your Python environment changed
pip install -e ~/minerva  # Re-link in new environment
```

**Verify update:**
```bash
minerva --version
git log -1  # See latest commit
```

### 4.3 Create git hooks guide (`docs/GIT_HOOKS.md`)

**Sections:**

#### How Git Hooks Work
- Explanation of post-commit and post-merge hooks
- When they trigger
- What they do

#### Hook Behavior
- Only reindexes if .md/.mdx files changed
- Runs in background (doesn't block git)
- Logs to ~/.minerva/logs/

#### Disabling Hooks Temporarily
```bash
# Disable for one commit
git commit --no-verify

# Disable permanently
rm .git/hooks/post-commit .git/hooks/post-merge

# Re-enable
./scripts/install-git-hook.sh .
```

#### Debugging Hook Issues
```bash
# Check if hook is installed
ls -la .git/hooks/post-commit

# Check hook logs
tail -f ~/.minerva/logs/company-docs.log

# Test hook manually
.git/hooks/post-commit
```

### 4.4 Create team configuration guide (`docs/TEAM_CONFIGURATION.md`)

**Purpose:** For team lead to configure which repos to index

**Sections:**

#### Editing Company Repos List
Edit `configs/company-repos.json` to add/remove repositories

#### Committing Configuration
```bash
git add configs/company-repos.json
git commit -m "Add new-repo to Minerva setup"
git push
```

#### Team Members Update
```bash
cd minerva
git pull
./scripts/setup-developer-machine.sh  # Re-run to add new repos
```

#### Private Repositories
How to handle authentication:
- SSH keys (recommended)
- GitHub personal access tokens
- Company GitHub Enterprise

## Phase 5: Maintenance & Monitoring

### 5.1 Create health check command (`minerva doctor`)

**Purpose:** Diagnose issues with local setup

**Checks:**
```bash
minerva doctor

# Checks:
✓ Ollama is running
✓ Required models installed (mxbai-embed-large, llama3.1:8b)
✓ ChromaDB accessible
✓ All configured repos exist
✓ All configs valid
✓ Git hooks installed
✓ Disk space sufficient (>5GB free)
✓ Claude Desktop config valid

# Output:
✅ All checks passed
⚠️  Warning: company-docs is 3 days behind (git pull needed)
❌ Error: api-docs not found at ~/repos/api-docs
```

**Fix suggestions:**
- Offers to fix common issues
- Provides commands to run

### 5.2 Create cleanup command (`minerva cleanup`)

**Purpose:** Clean up disk space

**Usage:**
```bash
# Show what can be cleaned
minerva cleanup --dry-run

# Clean extracted JSON (can be regenerated)
minerva cleanup --extracted

# Clean old logs
minerva cleanup --logs

# Full cleanup (keeps ChromaDB, removes temp files)
minerva cleanup --full

# Nuclear option (removes everything except config)
minerva cleanup --nuclear
```

### 5.3 Create scheduled update (optional cron job)

**Purpose:** Auto-pull repositories periodically

**Crontab entry:**
```bash
# Update repos every 4 hours during work hours
0 9,13,17 * * 1-5 $HOME/.minerva/bin/update-repos.sh

# Script: ~/.minerva/bin/update-repos.sh
#!/bin/bash
cd $HOME && minerva update-repos --quiet
```

**Benefits:**
- Always have latest content
- Don't rely solely on manual pulls
- Backup in case hooks fail

## Phase 6: Testing & Validation

### 6.1 Create test script (`scripts/test-local-setup.sh`)

**Purpose:** Validate setup works correctly

**Tests:**
1. Create test repository with markdown files
2. Install Minerva hooks
3. Initial index
4. Make commit with markdown change
5. Verify reindex triggered
6. Verify search results updated
7. Test git pull with remote changes
8. Cleanup test repo

**Usage:**
```bash
./scripts/test-local-setup.sh

# Output:
🧪 Testing Minerva local setup...
✓ Created test repository
✓ Installed git hooks
✓ Initial indexing complete
✓ Commit hook triggered reindex
✓ Search results updated
✓ Pull hook triggered reindex
✓ All tests passed!
```

### 6.2 Create validation checklist

**For new team member onboarding:**

```
Developer Onboarding Checklist:

Prerequisites:
[ ] macOS with 16GB+ RAM
[ ] 20GB free disk space
[ ] Git installed
[ ] Python 3.10+ installed
[ ] GitHub access to company repos

Setup:
[ ] Cloned minerva repository
[ ] Ran ./scripts/setup-developer-machine.sh
[ ] No errors in setup
[ ] Ollama models downloaded
[ ] Company repos cloned
[ ] Initial indexing complete
[ ] Claude Desktop restarted

Validation:
[ ] minerva doctor passes all checks
[ ] minerva list-repos shows all repos
[ ] Can search in Claude Desktop
[ ] Make test commit → reindex works
[ ] Pull teammate changes → reindex works

Troubleshooting (if needed):
[ ] Checked logs in ~/.minerva/logs/
[ ] Ran minerva doctor for diagnostics
[ ] Consulted docs/DEVELOPER_SETUP.md
```

## Deliverables

### Scripts
✅ `scripts/setup-developer-machine.sh` - Automated setup
✅ `scripts/generate-repo-config.sh` - Config generator
✅ `scripts/install-git-hook.sh` - Hook installer
✅ `scripts/uninstall-git-hook.sh` - Hook remover
✅ `scripts/git-hooks/minerva-auto-index` - Smart reindex hook
✅ `scripts/test-local-setup.sh` - Setup validator

### Commands
✅ `minerva add-repo` - Add repository to setup
✅ `minerva remove-repo` - Remove repository
✅ `minerva update-repos` - Pull and reindex all repos
✅ `minerva list-repos` - Show repository status
✅ `minerva doctor` - Health check and diagnostics
✅ `minerva cleanup` - Disk space management

### Configuration
✅ `configs/company-repos.json` - Repository list
✅ Auto-generated index configs per repo
✅ `.minerva-config` per repository (hook config)

### Documentation
✅ `docs/DEVELOPER_SETUP.md` - Onboarding guide
✅ `docs/DEVELOPER_USAGE.md` - Daily usage guide
✅ `docs/GIT_HOOKS.md` - Git hooks reference
✅ `docs/TEAM_CONFIGURATION.md` - Team lead guide
✅ Onboarding checklist

## Implementation Timeline

### Week 1: Core Automation
- Day 1-2: Setup script (`setup-developer-machine.sh`)
- Day 3-4: Git hook implementation
- Day 5: Config generator

### Week 2: Commands & Testing
- Day 1-2: Repository management commands
- Day 3: Health check and cleanup commands
- Day 4-5: Testing and validation

### Week 3: Documentation & Polish
- Day 1-2: User documentation
- Day 3: Team configuration guide
- Day 4: Testing with team members
- Day 5: Fixes and improvements

## Comparison: Server vs Local

| Aspect | Server Deployment | Local Installation |
|--------|-------------------|-------------------|
| **Setup Time** | 4-6 hours | 15 minutes |
| **Indexing Speed** | 10-20 min | 2-3 min (M1/M2) |
| **Search Latency** | 100-500ms | 10-50ms |
| **Monthly Cost** | $10-50 | $0 |
| **Complexity** | High (Docker, Caddy, DNS, SSL) | Low (pip install) |
| **Privacy** | Code on server | Code stays local |
| **Offline** | No | Yes |
| **Maintenance** | Server admin needed | Self-service |
| **Single Point of Failure** | Yes | No |
| **Storage per User** | Centralized | 10-20GB per dev |

**For 2-5 developers with M1/M2 MacBooks: Local wins decisively!**

## Storage Requirements

### Per Developer Machine

| Component | Size | Notes |
|-----------|------|-------|
| Ollama models | ~6 GB | One-time download |
| ChromaDB (3 repos) | ~3-9 GB | Depends on repo size |
| Extracted JSON | ~50-200 MB | Regenerable |
| Logs | ~10-50 MB | Can be cleaned |
| **Total** | **~10-15 GB** | Well within modern Mac storage |

### Is This Acceptable?
✅ Yes! Modern MacBooks have 256GB-2TB storage
✅ 10-15GB is ~5% of 256GB base model
✅ Can be cleaned with `minerva cleanup` if needed

## Security Considerations

### Local Advantages
- ✅ Code never leaves developer's machine
- ✅ No network transmission of sensitive data
- ✅ No API keys to manage
- ✅ No server to secure
- ✅ Each developer controls their own data

### Best Practices
- Use SSH keys for private repos (not passwords)
- Don't commit `.minerva-config` to git (contains local paths)
- Use `.gitignore` for Minerva directories
- Regular backups of `~/.minerva/chromadb/` (optional)

## Future Enhancements

### Optional Features
- [ ] GUI for managing repositories (Electron app)
- [ ] Slack bot for sharing search results with team
- [ ] VS Code extension for inline search
- [ ] Browser extension for searching docs
- [ ] Mobile app (read-only search)
- [ ] Shared cache for embeddings (LAN sharing)
- [ ] Delta indexing (only reindex changed files, not entire repo)
- [ ] Multi-branch indexing (switch between branches)

### Advanced Git Hook Features
- [ ] Smart detection (only reindex changed files, not whole repo)
- [ ] Batch mode (queue multiple commits, index once)
- [ ] Parallel indexing (multiple repos at once)
- [ ] Progress notifications (macOS notification center)

## Notes

- **Editable install (-e)**: Minerva installed as link to source directory, not copy. Updates are just `git pull`, no reinstall needed. Only reinstall if new dependencies added to setup.py.
- **Apple Silicon optimization**: Ollama and ChromaDB are both optimized for M1/M2 Neural Engine
- **Background indexing**: Git hooks run in background, don't block git operations
- **Idempotent setup**: Can run setup script multiple times safely
- **No root required**: Everything installs in user space
- **Works offline**: Once set up, works without internet (except git pull)
- **Already compatible**: Uses existing Minerva commands (validate, index, peek)
- **Source location**: Minerva source lives at ~/minerva/, data at ~/.minerva/, repos at ~/repos/

## Migration Path (If Switching to Server Later)

If you later decide server deployment makes sense:

1. **Easy migration**: Configs are JSON, can be adapted
2. **Backup ChromaDB**: `tar -czf chromadb-backup.tar.gz ~/.minerva/chromadb/`
3. **Server indexing**: Use same commands, just on server
4. **Keep local option**: Some devs can stay local, others use server

**Local setup doesn't lock you in!**
