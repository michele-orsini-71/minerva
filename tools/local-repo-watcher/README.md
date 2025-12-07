# Local Repository Watcher

A Python-based file system watcher for Minerva that automatically re-indexes your repository when files change.

## Features

- **Initial indexing on startup** - Ensures index is up-to-date when watcher starts
- **File system monitoring** - Watches for file changes using watchdog
- **Debouncing** - Batches rapid changes to avoid excessive indexing
- **Smart filtering** - Only tracks relevant files (documentation, code)
- **Error recovery** - Waits for file changes after pipeline failures
- **Graceful shutdown** - Handles SIGINT and SIGTERM signals

## Installation

```bash
# Install with pipx (recommended)
pipx install /path/to/minerva/tools/local-repo-watcher

# Or install in development mode
pip install -e /path/to/minerva/tools/local-repo-watcher
```

## Usage

```bash
# Basic usage
local-repo-watcher --config ~/.minerva/apps/local-repo-kb/my-project-watcher.json

# With verbose logging
local-repo-watcher --config watcher.json --verbose

# Dry-run mode (test without executing commands)
local-repo-watcher --config watcher.json --dry-run

# Skip initial indexing
local-repo-watcher --config watcher.json --no-initial-index

# Combine flags for testing
local-repo-watcher --config watcher.json --dry-run --no-initial-index --verbose
```

## Configuration

The watcher uses a JSON configuration file:

```json
{
  "repository_path": "/Users/you/code/my-project",
  "collection_name": "my-project",
  "extracted_json_path": "/Users/you/.minerva/apps/local-repo-kb/my-project-extracted.json",
  "index_config_path": "/Users/you/.minerva/apps/local-repo-kb/my-project-index.json",
  "debounce_seconds": 2.0,
  "include_extensions": [".md", ".py", ".js", ".ts"],
  "ignore_patterns": [".git", "node_modules", ".venv", "__pycache__"]
}
```

### Configuration Options

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repository_path` | string | Yes | - | Path to repository to watch |
| `collection_name` | string | Yes | - | Minerva collection name |
| `extracted_json_path` | string | Yes | - | Output path for extracted JSON |
| `index_config_path` | string | Yes | - | Path to Minerva index config |
| `debounce_seconds` | number | No | 2.0 | Seconds to wait after last change |
| `include_extensions` | string[] | No | See below | File extensions to track |
| `ignore_patterns` | string[] | No | See below | Directory patterns to ignore |

**Default extensions tracked:**
```python
['.md', '.mdx', '.markdown', '.rst', '.txt',
 '.py', '.js', '.ts', '.tsx', '.jsx',
 '.java', '.go', '.rs', '.c', '.cpp', '.h', '.hpp']
```

**Default ignore patterns:**
```python
['.git', 'node_modules', '.venv', '__pycache__',
 '.pytest_cache', 'dist', 'build', '.tox']
```

## How It Works

### Startup Behavior

1. **Initial indexing** - Runs extraction and indexing once on startup (unless `--no-initial-index` is used)
2. **Start watching** - Begins monitoring file system for changes
3. **Wait for changes** - Stays running until stopped with Ctrl+C

### Change Detection

1. File change detected → Add to pending queue
2. Reset debounce timer
3. Wait for debounce period (default: 2 seconds)
4. Execute pipeline: extract → index
5. Log completion or errors
6. Ready for next changes

### Error Handling

When the pipeline fails:
- Logs the error
- Clears pending file queue
- Enters "awaiting change" state
- Waits for next file change before retrying
- Prevents repeated failed executions

### Debouncing

The watcher batches rapid changes:
- File changes reset the debounce timer
- Pipeline runs only after changes stop for `debounce_seconds`
- Prevents excessive indexing during active editing

## Running as a Background Service

### macOS (launchd)

Create `~/Library/LaunchAgents/com.minerva.local-repo-watcher.my-project.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.minerva.local-repo-watcher.my-project</string>
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

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.minerva.local-repo-watcher.my-project.plist
```

### Linux (systemd)

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

Enable and start:

```bash
systemctl --user enable local-repo-watcher@my-project
systemctl --user start local-repo-watcher@my-project
```

## Development

### Running Tests

```bash
cd tools/local-repo-watcher
pytest
```

### Manual Testing with Dry-Run

**Step 1: Create a test configuration**

Copy and edit the sample config:

```bash
cd tools/local-repo-watcher
cp sample-config.json test-config.json
```

Edit `test-config.json` and update:
- `repository_path`: Path to a test repository (or the minerva repo itself)
- `extracted_json_path`: Where to write extracted data (e.g., `/tmp/test-extracted.json`)
- `index_config_path`: Path to a valid index config (can be dummy for dry-run)

**Step 2: Run in dry-run mode**

```bash
# Terminal 1: Run watcher in dry-run mode with verbose logging
local-repo-watcher --config test-config.json --dry-run

# You'll see:
# [2025-12-06 10:30:00] DRY-RUN MODE: Commands will be logged but not executed
# [2025-12-06 10:30:00] Starting watcher for: /path/to/repo
# [2025-12-06 10:30:00] Collection: test-collection
# [2025-12-06 10:30:00] Running initial indexing
# [2025-12-06 10:30:00] Extracting repository contents...
# [2025-12-06 10:30:00] [DRY-RUN] Would execute: repository-doc-extractor /path/to/repo -o /tmp/test-extracted.json
# [2025-12-06 10:30:00] Indexing collection...
# [2025-12-06 10:30:00] [DRY-RUN] Would execute: minerva index --config /tmp/test-index-config.json
# [2025-12-06 10:30:00] ✓ Pipeline complete
# [2025-12-06 10:30:00] Watching: /path/to/repo
```

**Step 3: Test file change detection**

```bash
# Terminal 2: Make changes to tracked files
cd /path/to/repo
echo "# Test change" >> README.md
sleep 1
echo "# Another change" >> docs/guide.md

# Terminal 1 will show:
# [2025-12-06 10:31:00] File change detected: README.md
# [2025-12-06 10:31:01] File change detected: docs/guide.md
# [2025-12-06 10:31:03] Running pipeline for 2 changed file(s)
#   • README.md
#   • docs/guide.md
# [2025-12-06 10:31:03] Extracting repository contents...
# [2025-12-06 10:31:03] [DRY-RUN] Would execute: repository-doc-extractor ...
# [2025-12-06 10:31:03] ✓ Pipeline complete
```

**Step 4: Test debouncing**

```bash
# Terminal 2: Make rapid changes
for i in {1..5}; do
  echo "Change $i" >> README.md
  sleep 0.3
done

# Terminal 1 will show:
# [2025-12-06 10:32:00] File change detected: README.md
# [2025-12-06 10:32:00] File change detected: README.md
# [2025-12-06 10:32:01] File change detected: README.md
# [2025-12-06 10:32:01] File change detected: README.md
# [2025-12-06 10:32:01] File change detected: README.md
# [2025-12-06 10:32:03] Running pipeline for 1 changed file(s)
#   • README.md
# (Only one pipeline run after debounce period)
```

**Step 5: Test with real execution**

Once dry-run looks good, test without `--dry-run`:

```bash
# Make sure you have valid paths in test-config.json
local-repo-watcher --config test-config.json --verbose

# Make a change and verify real extraction/indexing happens
echo "# Real test" >> README.md
```

## Troubleshooting

### Watcher not detecting changes

1. Check file extension is in `include_extensions`
2. Verify file is not in `ignore_patterns`
3. Ensure repository path is correct
4. Run with `--verbose` to see debug logs

### Initial indexing fails

- Check that `repository-doc-extractor` is installed
- Verify `minerva` is installed and in PATH
- Check index config file exists and is valid
- Review error messages for specific issues

### Pipeline stuck after error

The watcher waits for new changes after errors:
1. Fix the underlying issue
2. Make any file change in the repository
3. Pipeline will automatically retry

## Integration with Setup Wizard

This watcher is automatically installed and configured by the `apps/local-repo-kb/setup.py` wizard. The wizard:

1. Installs the watcher via pipx
2. Generates the watcher configuration file
3. Provides instructions for running the watcher
4. Shows how to set up as a background service

## License

Part of the Minerva project.
