# Minerva Watcher

A filesystem watcher that triggers Minerva indexing pipeline when files change. Designed to run Minerva extraction, validation, and indexing commands in a Docker Compose environment.

## Features

- **File watching** with debouncing to batch rapid changes
- **Docker Compose integration** for running Minerva commands in containers
- **Flexible filtering** by file extensions and glob patterns
- **Error recovery** that waits for file changes after pipeline failures
- **Dry-run mode** for testing configuration without executing commands
- **Fully testable** with dependency injection architecture

## Installation

```bash
npm install
npm run build
```

## Usage

### Basic Usage

```bash
# Production mode
minerva-watcher --config /path/to/config.json

# Dry-run mode (shows commands without executing)
minerva-watcher --config /path/to/config.json --dry-run
```

### Configuration

Create a JSON configuration file:

```json
{
  "workspacePath": "/path/to/watch",
  "composeDirectory": "/path/to/docker-compose",
  "composeCommand": ["docker", "compose"],
  "serviceName": "minerva",
  "extractorCommand": ["repository-doc-extractor"],
  "validateCommand": ["minerva", "validate", "normalized-notes.json"],
  "indexCommand": ["minerva", "index", "--config", "configs/index/my-collection.json"],
  "debounceMs": 2000,
  "includeExtensions": [".md", ".mdx"],
  "ignoreGlobs": ["**/.git/**", "**/node_modules/**"],
  "logChangedFiles": true
}
```

#### Configuration Options

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `workspacePath` | string | Yes | - | Directory to watch for changes |
| `composeDirectory` | string | No | `process.cwd()` | Working directory for docker-compose |
| `composeCommand` | string[] | No | `["docker", "compose"]` | Command to run docker-compose |
| `serviceName` | string | No | `"minerva"` | Docker service name to use |
| `extractorCommand` | string[] | Yes | - | Command for extraction step |
| `validateCommand` | string[] | No | - | Optional validation step (skipped if omitted) |
| `indexCommand` | string[] | Yes | - | Command for indexing step |
| `debounceMs` | number | No | `2000` | Milliseconds to wait after last change |
| `includeExtensions` | string[] | No | `[".md", ".mdx"]` | File extensions to watch (empty = all) |
| `ignoreGlobs` | string[] | No | See below | Glob patterns to ignore |
| `logChangedFiles` | boolean | No | `false` | Log individual file changes |

**Default ignore patterns:**
```json
["**/.git/**", "**/node_modules/**", "**/.venv/**", "**/__pycache__/**"]
```

### Dry-Run Mode

Use `--dry-run` to test your configuration without actually executing commands:

```bash
minerva-watcher --config config.json --dry-run
```

This will:
- Watch for real file changes
- Log the exact commands that would be executed
- Show the working directory for each command
- Skip actual command execution

Example output:
```
[2025-11-29T10:30:00.000Z] DRY-RUN MODE: Commands will be logged but not executed
[2025-11-29T10:30:00.000Z] Watching /path/to/workspace
[2025-11-29T10:30:05.000Z] change detected: README.md
[2025-11-29T10:30:07.000Z] Running pipeline for 1 file(s)
[DRY-RUN] repository-doc-extractor
  Command: docker compose run --rm minerva repository-doc-extractor
  Working directory: /path/to/compose
[DRY-RUN] minerva validate
  Command: docker compose run --rm minerva minerva validate normalized-notes.json
  Working directory: /path/to/compose
[DRY-RUN] minerva index
  Command: docker compose run --rm minerva minerva index --config configs/index/my-collection.json
  Working directory: /path/to/compose
```

## Architecture

The watcher is built with dependency injection for testability:

### Core Interfaces

#### FileWatcher
```typescript
interface FileWatcher {
  start(): void;
  close(): Promise<void>;
  onChange(callback: FileChangeCallback): void;
}
```

Implementations:
- `ChokidarFileWatcher` - Production implementation using chokidar
- `FakeFileWatcher` - Test implementation with `fireAdd()`, `fireChange()`, `fireUnlink()` methods

#### CommandRunner
```typescript
interface CommandRunner {
  runInCompose(command: string[], label: string): Promise<void>;
}
```

Implementations:
- `RealCommandRunner` - Production implementation that executes commands
- `DryRunCommandRunner` - Logs commands without executing
- `FakeCommandRunner` - Test implementation that records execution

### Pipeline Flow

```
File Change → Debounce → Queue → Execute Pipeline
                                      ↓
                                  Extractor
                                      ↓
                                  Validate (optional)
                                      ↓
                                  Index
                                      ↓
                                  Success/Failure
```

**On Success:** Ready for next change
**On Failure:** Wait for new file change before retrying

## Development

### Running Tests

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run tests in watch mode
npm run test:watch
```

### Test Coverage

The test suite covers:
- File extension filtering
- Debouncing behavior
- Pipeline execution order
- Error handling and recovery
- Concurrent execution prevention
- Multiple file batching

### Writing Tests

Use `FakeFileWatcher` and `FakeCommandRunner` for unit tests:

```typescript
import { FakeFileWatcher } from './fileWatcher';
import { FakeCommandRunner } from './commandRunner';

const fileWatcher = new FakeFileWatcher();
const commandRunner = new FakeCommandRunner();

// Simulate file changes
fileWatcher.fireChange('/path/to/file.md');

// Inspect executed commands
expect(commandRunner.executedCommands).toHaveLength(3);
```

## Behavior Details

### Debouncing

The watcher batches rapid file changes using a debounce timer:

1. File change detected → Start/reset timer
2. Timer expires → Execute pipeline with all queued files
3. New change during debounce → Reset timer

### Error Recovery

When the pipeline fails:

1. Stop execution immediately
2. Clear pending file queue
3. Enter "awaiting change" state
4. Wait for next file change
5. Resume normal operation

This prevents repeated failed executions and ensures fresh context after errors.

### Concurrent Execution

Only one pipeline run executes at a time:

- Changes during execution are queued
- Pipeline runs again after completion if files are queued
- Prevents resource conflicts and command interference

## Examples

### Basic Repository Watching

```json
{
  "workspacePath": "/Users/you/code/my-repo",
  "extractorCommand": ["repository-doc-extractor"],
  "indexCommand": ["minerva", "index", "--config", "configs/index/repo.json"],
  "includeExtensions": [".md"]
}
```

### Multiple File Types

```json
{
  "workspacePath": "/Users/you/docs",
  "extractorCommand": ["markdown-books-extractor"],
  "indexCommand": ["minerva", "index", "--config", "configs/index/docs.json"],
  "includeExtensions": [".md", ".mdx", ".markdown"],
  "debounceMs": 3000
}
```

### Custom Docker Setup

```json
{
  "workspacePath": "/data",
  "composeDirectory": "/app/deployment",
  "composeCommand": ["docker-compose", "-f", "production.yml"],
  "serviceName": "minerva-indexer",
  "extractorCommand": ["custom-extractor", "--format", "json"],
  "indexCommand": ["minerva", "index", "--verbose"],
  "logChangedFiles": true
}
```

## Troubleshooting

### Commands not executing

1. Check that docker-compose is running: `docker-compose ps`
2. Verify service name matches: `docker-compose config --services`
3. Test command manually: `docker compose run --rm minerva minerva --version`
4. Use `--dry-run` to see exact commands being generated

### Files not triggering changes

1. Check file extension matches `includeExtensions`
2. Verify file is not in `ignoreGlobs` patterns
3. Enable `logChangedFiles: true` to see detected changes
4. Check that `workspacePath` is correct and accessible

### Pipeline stuck after error

The watcher waits for a file change after errors. To recover:
1. Fix the underlying issue
2. Make any file change in the watched directory
3. Pipeline will resume automatically

## License

Part of the Minerva project.
