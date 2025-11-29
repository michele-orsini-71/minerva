# Watcher Configuration Examples

This directory contains example configurations for `minerva-watcher`, a filesystem watcher that automatically triggers Minerva indexing when files change.

## Files

- **`local-repo-example.json`** - Template for watching a local repository with automatic reindexing

## Usage

1. Copy an example config and customize it for your use case:
   ```bash
   cp configs/watcher/local-repo-example.json configs/watcher/my-repo.json
   ```

2. Edit the configuration:
   - Set `workspacePath` to your local repository path
   - Adjust `extractorCommand`, `indexCommand` paths to match your setup
   - Customize `includeExtensions` and `ignoreGlobs` as needed

3. Update `deployment/docker-compose.yml` to mount your workspace:
   ```yaml
   volumes:
     - /path/to/your/local/repo:/workspace:ro
   ```

4. Start the watcher:
   ```bash
   cd tools/minerva-watcher
   node dist/index.js --config ../../configs/watcher/my-repo.json
   ```

## Configuration Fields

| Field | Description | Example |
|-------|-------------|---------|
| `workspacePath` | Local directory to watch | `"/Users/you/code/my-repo"` |
| `composeDirectory` | Where docker-compose.yml lives | `"../../deployment"` |
| `composeCommand` | Docker compose command | `["docker", "compose"]` |
| `serviceName` | Service name in docker-compose.yml | `"minerva"` |
| `extractorCommand` | Command to extract docs | `["repository-doc-extractor", "/workspace"]` |
| `validateCommand` | Optional validation step | `["minerva", "validate", "notes.json"]` |
| `indexCommand` | Command to index into ChromaDB | `["minerva", "index", "--config", "..."]` |
| `debounceMs` | Wait time after last change (ms) | `2000` |
| `includeExtensions` | File extensions to watch | `[".md", ".mdx"]` |
| `ignoreGlobs` | Patterns to ignore | `["**/node_modules/**"]` |
| `logChangedFiles` | Log each file change | `true` or `false` |

## See Also

- [docs/local-watcher.md](../../docs/local-watcher.md) - Complete setup guide
- [tools/minerva-watcher/README.md](../../tools/minerva-watcher/README.md) - Watcher implementation details
