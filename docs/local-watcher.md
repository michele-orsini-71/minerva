# Local Repository Watcher with Automatic Reindexing

This guide explains how to set up automatic reindexing of a local repository using `minerva-watcher` and Docker.

## Overview

The local watcher workflow allows you to:
- Edit files in your local repository
- Have changes automatically detected and indexed into ChromaDB
- Query the updated content via Claude Desktop using the MCP server

**Architecture:**
```
Local Files → Watcher (host) → Docker Commands → Extractor → Index → ChromaDB
                                                                           ↓
Claude Desktop ← MCP Server ← ChromaDB (queries)
```

## Prerequisites

### 1. Docker Desktop

Install Docker Desktop for your platform:
- **macOS**: [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Linux**: [Docker Engine](https://docs.docker.com/engine/install/)
- **Windows**: [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

Verify installation:
```bash
docker --version
docker compose version
```

### 2. Node.js (for the watcher)

The watcher is a Node.js application. Install Node.js 18 or later:
- [Node.js Downloads](https://nodejs.org/)

Verify installation:
```bash
node --version  # Should be v18 or later
npm --version
```

### 3. Minerva Repository

Clone and set up the Minerva repository:
```bash
git clone <minerva-repo-url>
cd minerva
```

## Setup

### Step 1: Build the Watcher

```bash
cd tools/minerva-watcher
npm install
npm run build
cd ../..
```

### Step 2: Configure Docker Bind Mount

Edit `deployment/docker-compose.yml` and add a volume mount for your local repository:

```yaml
volumes:
  # ... existing volumes ...

  # Mount your local repository (read-only recommended)
  - /absolute/path/to/your/local/repo:/workspace:ro
```

**Example:**
```yaml
volumes:
  - chromadb-data:/data/chromadb
  - repos-data:/data/repos
  - extracted-data:/data/extracted
  - ./configs:/data/config:ro
  - /Users/you/code/my-project:/workspace:ro  # Your local repo
```

**Important:**
- Use an **absolute path** for the host directory
- The container path should be `/workspace` (this is what the watcher will reference)
- Use `:ro` (read-only) to prevent the container from modifying your files

### Step 3: Create Index Configuration

Create an index config for your local repository at `deployment/configs/index/local-repo.json`:

```json
{
  "chromadb_path": "/data/chromadb",
  "collection": {
    "name": "my_local_repo",
    "description": "Local repository documentation",
    "json_file": "/data/extracted/local-repo.json",
    "chunk_size": 1200,
    "force_recreate": false
  },
  "provider": {
    "provider_type": "ollama",
    "base_url": "http://host.docker.internal:11434",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b"
  }
}
```

**Notes:**
- `json_file` matches the output path in the watcher config (step 4)
- Use `host.docker.internal` to access services on your host machine from Docker
- Adjust provider settings based on your AI setup (Ollama, LM Studio, OpenAI, etc.)

### Step 4: Create Watcher Configuration

Copy the example watcher config:

```bash
cp configs/watcher/local-repo-example.json configs/watcher/my-repo.json
```

Edit `configs/watcher/my-repo.json`:

```json
{
  "workspacePath": "/absolute/path/to/your/local/repo",
  "composeDirectory": "../../deployment",
  "composeCommand": ["docker", "compose"],
  "serviceName": "minerva",
  "extractorCommand": [
    "repository-doc-extractor",
    "/workspace",
    "-o",
    "/data/extracted/local-repo.json"
  ],
  "validateCommand": [
    "minerva",
    "validate",
    "/data/extracted/local-repo.json"
  ],
  "indexCommand": [
    "minerva",
    "index",
    "--config",
    "/data/config/index/local-repo.json"
  ],
  "debounceMs": 2000,
  "includeExtensions": [".md", ".mdx"],
  "ignoreGlobs": [
    "**/.git/**",
    "**/node_modules/**",
    "**/.venv/**",
    "**/__pycache__/**"
  ],
  "logChangedFiles": true
}
```

**Important:**
- `workspacePath`: Absolute path on your **host** machine
- Extractor reads from `/workspace` (the **container** path)
- Output paths use container paths (`/data/extracted/...`)

### Step 5: Build and Start Docker Stack

```bash
cd deployment
docker compose build
docker compose up -d
```

Verify the container is running:
```bash
docker compose ps
```

You should see the `minerva` service running.

### Step 6: Start the Watcher

In a separate terminal:

```bash
cd tools/minerva-watcher
node dist/index.js --config ../../configs/watcher/my-repo.json
```

You should see:
```
[2025-11-29T...] Watching /path/to/your/repo
```

### Step 7: Test the Workflow

Make a change to a file in your repository:

```bash
echo "# New Documentation" > /path/to/your/repo/test.md
```

Watch the watcher terminal for output:
```
[2025-11-29T...] change detected: test.md
[2025-11-29T...] Running pipeline for 1 file(s)
[2025-11-29T...] repository-doc-extractor started
[2025-11-29T...] repository-doc-extractor finished in 2.3s
[2025-11-29T...] minerva validate started
[2025-11-29T...] minerva validate finished in 0.5s
[2025-11-29T...] minerva index started
[2025-11-29T...] minerva index finished in 3.1s
[2025-11-29T...] Pipeline complete
```

## Verifying the Setup

### Check Extracted Data

```bash
docker compose exec minerva cat /data/extracted/local-repo.json | head -n 20
```

You should see extracted markdown content in JSON format.

### Check ChromaDB Collection

```bash
docker compose exec minerva minerva peek my_local_repo --chromadb /data/chromadb
```

You should see your indexed documents.

### Query via MCP Server

Configure Claude Desktop to connect to the MCP server (see main Minerva docs), then try:
- "What documentation is available in my_local_repo?"
- "Search for [topic] in my local repository"

## Dry-Run Mode

To test without actually executing commands:

```bash
cd tools/minerva-watcher
node dist/index.js --config ../../configs/watcher/my-repo.json --dry-run
```

This will show the exact commands that would be executed when files change.

## Troubleshooting

### Watcher Not Detecting Changes

**Issue:** Files change but watcher doesn't trigger

**Solutions:**
1. Check file extensions match `includeExtensions` in config
2. Verify file is not in `ignoreGlobs` patterns
3. Enable `logChangedFiles: true` to see all detected changes
4. Check file system permissions (watcher must be able to read the directory)

### Docker Permission Errors

**Issue:** `permission denied` when accessing `/workspace`

**Solutions:**
1. Verify bind mount path is correct in `docker-compose.yml`
2. Use `:ro` (read-only) mount to avoid permission issues
3. Check Docker Desktop settings → Resources → File Sharing (macOS/Windows)
4. On Linux, ensure your user has access to the mounted directory

### Extractor Can't Find Files

**Issue:** `repository-doc-extractor` reports no files found

**Solutions:**
1. Verify bind mount is working:
   ```bash
   docker compose exec minerva ls -la /workspace
   ```
   You should see your repository files.

2. Check that extractor command uses `/workspace` (container path), not host path

3. Verify file extensions - extractor looks for markdown by default

### Index Command Fails

**Issue:** `minerva index` command fails

**Solutions:**
1. Check that index config exists at `/data/config/index/local-repo.json`
2. Verify ChromaDB path is writable:
   ```bash
   docker compose exec minerva ls -la /data/chromadb
   ```
3. Check AI provider is accessible (Ollama, LM Studio, etc.)
4. Review index config for correct paths and settings

### Ollama Connection Refused

**Issue:** `Connection refused` when connecting to Ollama

**Solutions:**
1. Use `host.docker.internal` instead of `localhost` in index config:
   ```json
   "base_url": "http://host.docker.internal:11434"
   ```

2. Verify Ollama is running on host:
   ```bash
   ollama list
   ```

3. Ensure required models are pulled:
   ```bash
   ollama pull mxbai-embed-large:latest
   ollama pull llama3.1:8b
   ```

### Docker Desktop Not Seeing Bind Mount

**Issue:** Docker can't access the mounted directory

**Solutions:**
1. **macOS/Windows**: Add directory to Docker Desktop → Settings → Resources → File Sharing
2. Use absolute paths (not `~` or relative paths)
3. Restart Docker Desktop after changing settings

### Watcher Exits Immediately

**Issue:** Watcher starts but exits right away

**Solutions:**
1. Check for config file errors:
   ```bash
   node dist/index.js --config ../../configs/watcher/my-repo.json
   ```
   Look for JSON parsing errors or validation messages

2. Verify all paths in config are valid
3. Check that `composeDirectory` points to directory containing `docker-compose.yml`

### Pipeline Stuck After Error

**Issue:** After an error, pipeline doesn't retry

**Expected behavior:** This is intentional. The watcher waits for a new file change after errors to avoid repeated failures.

**Solution:** Fix the underlying issue, then make any file change to trigger a retry.

## Configuration Tips

### Performance Tuning

**Debounce time:**
- Lower (500-1000ms): Faster updates, more frequent indexing
- Higher (3000-5000ms): Fewer runs, batches more changes

**Include/exclude patterns:**
- Only watch files that need indexing (`.md`, `.mdx`)
- Exclude build artifacts, dependencies, large binary files

### Multiple Repositories

To watch multiple repositories:

1. Create separate watcher configs:
   - `configs/watcher/repo-1.json`
   - `configs/watcher/repo-2.json`

2. Add multiple bind mounts in `docker-compose.yml`:
   ```yaml
   volumes:
     - /path/to/repo1:/workspace/repo1:ro
     - /path/to/repo2:/workspace/repo2:ro
   ```

3. Run multiple watcher instances (separate terminals):
   ```bash
   node dist/index.js --config ../../configs/watcher/repo-1.json
   node dist/index.js --config ../../configs/watcher/repo-2.json
   ```

## Production Considerations

### Running as a Service

For production use, consider running the watcher as a system service:

**macOS (launchd):**
Create `~/Library/LaunchAgents/com.minerva.watcher.plist`

**Linux (systemd):**
Create `/etc/systemd/system/minerva-watcher.service`

**Windows (Task Scheduler):**
Create a scheduled task to run on startup

### Monitoring

- Use `logChangedFiles: true` to track activity
- Monitor Docker logs: `docker compose logs -f minerva`
- Set up alerts for indexing failures
- Track ChromaDB collection size and performance

### Security

- Use `:ro` (read-only) mounts to protect source files
- Don't expose Docker ports publicly without authentication
- Keep API keys in environment variables, not configs
- Regularly update Docker images and dependencies

## See Also

- [tools/minerva-watcher/README.md](../tools/minerva-watcher/README.md) - Watcher implementation details
- [configs/watcher/README.md](../configs/watcher/README.md) - Configuration examples
- [docs/CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) - Index configuration reference
