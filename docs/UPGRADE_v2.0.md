# Upgrading to Minerva v2.0

This guide helps you migrate from Minerva v1.0 to v2.0.

## What's New in v2.0

### Incremental Updates

- **Smart Change Detection**: Only processes added, modified, or deleted notes
- **Content Hash Tracking**: SHA256 hashes detect content changes efficiently
- **Faster Re-indexing**: Skip unchanged notes, dramatically reducing processing time
- **Automatic Timestamp Tracking**: Collections maintain `last_updated` metadata

### HTTP Server Mode

- **SSE Transport**: Serve MCP over HTTP using Server-Sent Events
- **New Command**: `minerva serve-http` with configurable host and port
- **Concurrent Operation**: Run HTTP and stdio servers simultaneously

### Version Migration System

- **Automatic Detection**: Identifies v1.0 collections that need upgrading
- **Configuration Validation**: Detects incompatible embedding/chunking changes
- **Clear Error Messages**: Guides you through the upgrade process

## Breaking Changes

### Collection Format

**v2.0 collections are incompatible with v1.0**

v1.0 collections lack:

- `version` metadata field
- `content_hash` tracking on chunks
- `last_updated` timestamp
- `note_hash_algorithm` metadata

**Impact**: Existing v1.0 collections must be recreated to use incremental updates.

### Default Indexing Behavior

**v1.0**: Collection existence always triggered recreation prompt
**v2.0**: Existing collections trigger **incremental update** by default

To force full recreation:

```json
{
  "force_recreate": true
}
```

### Configuration Changes Require Recreation

Changes to these settings require `forceRecreate: true`:

- `embedding_model`
- `embedding_provider`
- `chunk_size`

**Reason**: Embeddings are incompatible across different models/settings.

## Migration Steps

### Step 1: Backup Your Data

```bash
# Backup your ChromaDB directory
cp -r ./chromadb_data ./chromadb_data_v1_backup

# Backup your extraction files
cp my_notes.json my_notes_backup.json
```

### Step 2: Install Minerva v2.0

```bash
# Update to v2.0
pip install -e . --force-reinstall

# Verify version
minerva --version
# Should output: minerva 2.0.0
```

### Step 3: Migrate Collections

#### Option A: Recreate Collection (Recommended)

```json
{
  "collection_name": "my_notes",
  "description": "My personal notes",
  "chromadb_path": "./chromadb_data",
  "json_file": "./my_notes.json",
  "force_recreate": true
}
```

```bash
minerva index --config config.json --verbose
```

**Note**: This deletes the old collection and creates a new v2.0 collection.

#### Option B: Keep v1.0 Collection (Use Different Name)

```json
{
  "collection_name": "my_notes_v2",
  "description": "My personal notes (v2.0)",
  "chromadb_path": "./chromadb_data",
  "json_file": "./my_notes.json"
}
```

This creates a new collection alongside your v1.0 collection.

### Step 4: Update Server Configuration

No changes needed! Server configs are backward compatible.

```json
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
```

### Step 5: Test Incremental Updates

```bash
# Initial index
minerva index --config config.json --verbose

# Modify a note in your source
# Re-run index - only changes will be processed
minerva index --config config.json --verbose
```

You should see output like:

```
Change detection complete: 0 added, 1 updated, 0 deleted, 99 unchanged
```

## New Features Guide

### Using Incremental Updates

**Automatic**: Just re-run `minerva index` with the same config:

```bash
# First time: indexes all notes
minerva index --config config.json

# Later: only processes changes
minerva index --config config.json
```

**What gets updated**:

- Added notes: New notes in your JSON file
- Modified notes: Changed title or markdown content
- Deleted notes: Notes removed from JSON file
- Unchanged notes: Skipped entirely (fast!)

**Change detection uses**:

- Note ID (SHA1 of title + creation date)
- Content hash (SHA256 of title + markdown)

### Using HTTP Server Mode

**Start HTTP server**:

```bash
minerva serve-http --config server-config.json --host localhost --port 8000
```

**Default values**:

- Host: `localhost`
- Port: `8000`
- Transport: SSE (Server-Sent Events)

**Test it**:

```bash
curl http://localhost:8000/sse
```

**Run both modes concurrently**:

```bash
# Terminal 1: stdio mode
minerva serve --config server-config.json

# Terminal 2: HTTP mode
minerva serve-http --config server-config.json --port 9000
```

### Monitoring Collection Status

**Use peek command**:

```bash
minerva peek my_collection --chromadb ./chromadb_data --format json
```

**Check metadata**:

```json
{
  "version": "2.0",
  "description": "My notes",
  "last_updated": "2025-01-15T10:30:45Z",
  "note_hash_algorithm": "sha256",
  "embedding_model": "mxbai-embed-large:latest",
  "chunk_size": 1200
}
```

## Troubleshooting

### Error: "Collection is v1.0 (legacy)"

**Solution**: Add `forceRecreate: true` to recreate the collection:

```json
{
  "collection_name": "my_notes",
  "force_recreate": true,
  ...
}
```

**Warning**: This permanently deletes the old collection.

### Error: "Critical configuration change detected"

**Cause**: Changed embedding model, provider, or chunk size.

**Solution**: Use `forceRecreate: true` to rebuild with new settings:

```json
{
  "collection_name": "my_notes",
  "force_recreate": true,
  ...
}
```

### Error: "[Errno 48] Address already in use"

**Cause**: Port 8000 is already in use.

**Solutions**:

1. Use a different port:

   ```bash
   minerva serve-http --config config.json --port 9000
   ```

2. Find and stop the conflicting process:
   ```bash
   lsof -i :8000
   kill <PID>
   ```

### Incremental Update Not Working

**Check**:

1. Collection is v2.0: `minerva peek <name> --chromadb <path> --format json`
2. No config changes: embedding model, provider, chunk size unchanged
3. JSON file path correct in config

**Force full reindex** if needed:

```json
{
  "force_recreate": true
}
```

## Performance Comparison

### Full Reindex (v1.0 Behavior)

```
Processing 1000 notes...
Time: 180 seconds
```

### Incremental Update (v2.0)

```
Processing 1000 notes...
Change detection: 5 added, 10 updated, 2 deleted, 983 unchanged
Time: 8 seconds
```

**Speedup**: ~22x faster for typical changes (1-2% modification rate)

## Rollback to v1.0

If you need to rollback:

1. **Restore backup**:

   ```bash
   rm -rf ./chromadb_data
   mv ./chromadb_data_v1_backup ./chromadb_data
   ```

2. **Reinstall v1.0**:

   ```bash
   git checkout v1.0.0
   pip install -e . --force-reinstall
   ```

3. **Verify**:
   ```bash
   minerva --version
   # Should output: minerva 1.0.0
   ```

## Getting Help

- **Documentation**: See `README.md` and `CLAUDE.md`
- **Issues**: https://github.com/yourusername/minerva/issues
- **Questions**: Open a GitHub Discussion

## Summary Checklist

- [ ] Backup your ChromaDB directory
- [ ] Backup your extraction JSON files
- [ ] Install Minerva v2.0
- [ ] Update configurations with `forceRecreate: true`
- [ ] Recreate collections
- [ ] Test incremental updates
- [ ] Try HTTP server mode (optional)
- [ ] Update any automation scripts

**Welcome to Minerva v2.0!** 🎉
