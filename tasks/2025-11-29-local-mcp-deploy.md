# Plan: Simplify Minerva Local Watcher Setup with Distribution Package

## Goal
Create a simple, distributable setup package that users can unzip and run with minimal configuration.

**Target User Experience:**
1. Download and unzip package
2. Run setup script
3. Answer 2 questions (repo path + OpenAI API key)
4. Everything works

## User Requirements (from questions)
- **AI Provider**: OpenAI (requires API key)
- **Docker Image**: Build on user's machine (smaller download)
- **Setup Questions**: Only ask for repo path and API key

## Current State Analysis

### What We Have
- **Watcher**: Pre-built in `tools/minerva-watcher/dist/` (~40KB compiled JS)
- **Docker Setup**: All files in `deployment/` directory
- **Configs**: 3 template configs in `deployment/configs/`

### Current Pain Points
1. User must clone entire Minerva repo
2. User must manually edit multiple config files
3. User must understand Docker volumes and bind mounts
4. User must know Node.js to build watcher
5. Setup requires 8+ manual steps

## Repository Restructuring (FIRST)

Before creating the distribution, we need to reorganize the repository to support multiple deployment types:

### Current Structure
```
deployment/          # Webhook-based remote repo indexing
```

### New Structure
```
apps/
├── webhook-remote-kb/      # Webhook-based remote repo (existing deployment/)
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── entrypoint.sh       # Git clone + webhook listener
│   └── configs/
│       ├── webhook.json
│       ├── server.json
│       └── index/...
└── local-repo-kb/          # Local watcher-based (NEW)
    ├── docker-compose.yml  # Simpler, no git/webhook
    ├── Dockerfile
    ├── entrypoint.sh       # Just MCP server
    └── configs/
        └── server.json
```

### Migration Steps
1. Rename `deployment/` → `apps/webhook-remote-kb/`
2. Create `apps/local-repo-kb/` with simplified Docker setup
3. Update all documentation references

## Proposed Solution: "minerva-local-setup.zip"

### Package Contents (~5-10MB)
```
minerva-local-setup/
├── setup.sh                    # Interactive setup script (NEW)
├── README.md                   # Quick start guide (NEW)
├── watcher/
│   ├── minerva-watcher.js      # Pre-built watcher (from dist/)
│   ├── package.json            # Runtime deps only
│   └── node_modules/           # chokidar + yargs
├── docker/                     # From apps/local-repo-kb/
│   ├── docker-compose.yml.template
│   ├── Dockerfile
│   ├── entrypoint.sh           # Simplified - only MCP server
│   └── .dockerignore
├── configs/
│   ├── server.json             # Pre-configured (no changes needed)
│   ├── index.json.template     # Template with {{OPENAI_API_KEY}}
│   └── watcher.json.template   # Template with {{WORKSPACE_PATH}}
└── .env.template               # Template with {{OPENAI_API_KEY}}
```

### Setup Script Flow

**setup.sh (bash for macOS/Linux):**

```bash
#!/bin/bash
set -e

echo "🚀 Minerva Local Watcher Setup"
echo "================================"

# 1. Check prerequisites
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker Desktop first."
        exit 1
    fi
}

check_node() {
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js not found. Please install Node.js 18+ first."
        exit 1
    fi
}

# 2. Ask user questions
read -p "📁 Path to your local repository: " WORKSPACE_PATH
read -p "🔑 OpenAI API Key: " OPENAI_API_KEY

# 3. Validate inputs
if [ ! -d "$WORKSPACE_PATH" ]; then
    echo "❌ Directory not found: $WORKSPACE_PATH"
    exit 1
fi

# 4. Generate configs from templates
sed "s|{{WORKSPACE_PATH}}|$WORKSPACE_PATH|g" configs/watcher.json.template > configs/watcher.json
sed "s|{{OPENAI_API_KEY}}|$OPENAI_API_KEY|g" configs/index.json.template > configs/index.json
sed "s|{{OPENAI_API_KEY}}|$OPENAI_API_KEY|g" .env.template > docker/.env
sed "s|{{WORKSPACE_PATH}}|$WORKSPACE_PATH|g" docker/docker-compose.yml.template > docker/docker-compose.yml

# 5. Build Docker image
echo "🐳 Building Docker image..."
cd docker && docker compose build

# 6. Start Docker container
echo "▶️  Starting Minerva MCP server..."
docker compose up -d

# 7. Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
sleep 5

# 8. Start watcher in background
echo "👁️  Starting file watcher..."
cd ../watcher
nohup node minerva-watcher.js --config ../configs/watcher.json > watcher.log 2>&1 &
WATCHER_PID=$!
echo $WATCHER_PID > watcher.pid

echo "
✅ Setup complete!

📊 Status:
  - MCP Server: http://localhost:8337
  - Watcher PID: $WATCHER_PID
  - Watching: $WORKSPACE_PATH

📝 Next steps:
  1. Configure Claude Desktop to use http://localhost:8337
  2. Edit files in $WORKSPACE_PATH
  3. Watch the magic happen!

🛠️  Commands:
  - View watcher logs: tail -f watcher/watcher.log
  - Stop watcher: kill \$(cat watcher/watcher.pid)
  - Stop Docker: cd docker && docker compose down
"
```

### Configuration Templates

**configs/watcher.json.template:**
```json
{
  "workspacePath": "{{WORKSPACE_PATH}}",
  "composeDirectory": "../docker",
  "composeCommand": ["docker", "compose"],
  "serviceName": "minerva",
  "extractorCommand": ["repository-doc-extractor", "/workspace", "-o", "/data/extracted/local-repo.json"],
  "validateCommand": ["minerva", "validate", "/data/extracted/local-repo.json"],
  "indexCommand": ["minerva", "index", "--config", "/data/config/index.json"],
  "debounceMs": 2000,
  "includeExtensions": [".md", ".mdx"],
  "ignoreGlobs": ["**/.git/**", "**/node_modules/**", "**/.venv/**"],
  "logChangedFiles": true
}
```

**configs/index.json.template:**
```json
{
  "chromadb_path": "/data/chromadb",
  "collection": {
    "name": "my_local_repo",
    "description": "Local repository documentation",
    "json_file": "/data/extracted/local-repo.json",
    "chunk_size": 1200
  },
  "provider": {
    "provider_type": "openai",
    "api_key": "{{OPENAI_API_KEY}}",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini"
  }
}
```

**docker/docker-compose.yml.template:**
```yaml
services:
  minerva:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - chromadb-data:/data/chromadb
      - extracted-data:/data/extracted
      - ../configs:/data/config:ro
      - {{WORKSPACE_PATH}}:/workspace:ro
    ports:
      - "8337:8337"
    restart: unless-stopped
    entrypoint: /app/minerva/apps/local-repo-kb/entrypoint.sh

volumes:
  chromadb-data:
  extracted-data:
```

**docker/entrypoint.sh (simplified for local mode):**
```bash
#!/bin/bash
set -e

echo "Starting Minerva MCP Server (local mode)..."
echo "Timestamp: $(date)"

cleanup() {
    echo "Shutting down MCP server..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Just start the MCP server - watcher handles indexing via docker compose run
echo "Starting HTTP MCP server on port 8337..."
exec minerva serve-http --config /data/config/server.json
```

## Implementation Steps

### Step 0: Restructure Repository (DO THIS FIRST)
1. **Rename deployment directory:**
   ```bash
   mkdir -p apps
   mv deployment apps/webhook-remote-kb
   ```

2. **Create new local-repo-kb app:**
   ```bash
   mkdir -p apps/local-repo-kb
   ```

3. **Copy and simplify files for local-repo-kb:**
   - Copy Dockerfile from webhook-remote-kb (may need minor adjustments)
   - Create simplified entrypoint.sh (just MCP server, no git/webhook)
   - Copy .dockerignore
   - Create docker-compose.yml (simpler, no git volumes)
   - Create configs/server.json

4. **Update references in:**
   - All documentation (README.md, docs/*)
   - .gitignore (deployment/ → apps/)
   - Any scripts that reference deployment/

### Step 1: Create apps/local-repo-kb/ Structure
**Files to create:**
1. **`apps/local-repo-kb/Dockerfile`** - Based on webhook version but simpler
2. **`apps/local-repo-kb/entrypoint.sh`** - Just MCP server (see template above)
3. **`apps/local-repo-kb/docker-compose.yml`** - Simplified volumes
4. **`apps/local-repo-kb/.dockerignore`** - Copy from webhook version
5. **`apps/local-repo-kb/configs/server.json`** - Copy from webhook version
6. **`apps/local-repo-kb/README.md`** - Explain local mode

### Step 2: Create Distribution Package Builder
**File**: `tools/create-distribution.sh`
- Copies necessary files from apps/local-repo-kb/
- Copies pre-built watcher from `tools/minerva-watcher/dist/`
- Copies only runtime node_modules (chokidar, yargs)
- Creates templates with placeholders
- Packages into zip file

### Step 3: Create Setup Script
**File**: `distribution/setup.sh`
- For macOS/Linux (bash)
- Windows users can use WSL or Git Bash

### Step 4: Create User Documentation
**File**: `distribution/README.md`
- System requirements
- Quick start (3 steps)
- Troubleshooting
- How to stop/restart

## Files to Create/Modify

### Repository Restructuring
1. **Rename**: `deployment/` → `apps/webhook-remote-kb/`
2. **Update**: All docs and scripts referencing `deployment/`

### New Directory: apps/local-repo-kb/
1. **`Dockerfile`** - Simplified version
2. **`entrypoint.sh`** - MCP server only
3. **`docker-compose.yml`** - Template-ready version
4. **`.dockerignore`** - Copy from webhook version
5. **`configs/server.json`** - Pre-configured
6. **`README.md`** - Local mode documentation

### Distribution Package Files (NEW)
1. **`tools/create-distribution.sh`** - Package builder
2. **`distribution/setup.sh`** - Setup script
3. **`distribution/README.md`** - User guide
4. **`distribution/configs/watcher.json.template`**
5. **`distribution/configs/index.json.template`**
6. **`distribution/.env.template`**

## Success Criteria

**Before** (current):
- 8+ manual steps
- Must understand Docker, Node.js, config file formats
- 30+ minutes for first-time setup

**After** (with distribution):
- 3 steps: download, unzip, run setup
- Answer 2 questions
- 5 minutes to working system

## Distribution Size Estimate
- Watcher (compiled): ~40KB
- Node modules (chokidar + yargs): ~5MB
- Docker files: ~10KB
- Scripts and templates: ~20KB
- Total: **~5-6MB zipped**

## Future Enhancements (Out of Scope)
- Support for other AI providers (Ollama, Anthropic)
- GUI setup wizard
- Pre-built Docker image on Docker Hub
- Auto-update mechanism
