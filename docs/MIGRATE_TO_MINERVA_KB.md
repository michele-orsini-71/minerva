# Migrating to minerva-kb

Guide for users transitioning from the old setup wizard or manual configuration to `minerva-kb`.

## Table of Contents

- [Overview](#overview)
- [What Changed](#what-changed)
- [Migration Scenarios](#migration-scenarios)
- [Step-by-Step Migration](#step-by-step-migration)
- [Adopting Existing Collections](#adopting-existing-collections)
- [Frequently Asked Questions](#frequently-asked-questions)

---

## Overview

### What is minerva-kb?

`minerva-kb` is a unified orchestrator tool that replaces the monolithic setup wizard (`apps/local-repo-kb/setup.py`) with a composable CLI for managing repository-based knowledge base collections.

### Who Should Migrate?

You should consider migrating if you:

- Used the old setup wizard (1,277 lines in `apps/local-repo-kb/setup.py`)
- Manually created collections with `minerva index`
- Used `local-repo-watcher-manager` (deprecated)
- Want to manage multiple repository collections easily

### Migration Status

**Phase 1 (Current)**: No existing users exist, so this guide is primarily for reference and future migrations.

---

## What Changed

### Old Approach: Setup Wizard

**File**: `apps/local-repo-kb/setup.py` (1,277 lines)

**Workflow**:
1. Run monolithic setup script
2. Answer ~20 interactive prompts
3. Wait 15+ minutes for installation and first collection setup
4. Manually edit configs for second collection
5. Use separate `local-repo-watcher-manager` for watchers
6. Repeat entire process for each new collection

**Limitations**:
- Single-collection focus (adding more requires manual config editing)
- No built-in status/list commands
- No provider validation before indexing
- Watcher management separate from collection management
- High barrier to entry (must understand all concepts upfront)

### New Approach: minerva-kb

**Tool**: `minerva-kb` CLI

**Workflow**:
1. Run `minerva-kb add <repo-path>`
2. Answer 2-3 prompts (provider, models)
3. Wait <2 minutes for second+ collections
4. Built-in commands for list, status, sync, watch, remove
5. Integrated watcher management
6. Add new collections in <2 minutes

**Benefits**:
- Multi-collection native
- Time to second collection: <2 minutes (vs 15+ minutes)
- Built-in observability (list, status commands)
- Integrated provider validation
- Lower barrier to entry
- Composable CLI design

---

## Migration Scenarios

### Scenario 1: Fresh Install (Recommended)

**If you haven't started using Minerva yet**, skip the old setup wizard entirely:

```bash
# Install core Minerva
pip install -e .

# Install minerva-kb and dependencies
pipx install tools/minerva-kb
pipx install extractors/repository-doc-extractor
pipx install tools/local-repo-watcher

# Add your first collection
minerva-kb add ~/code/my-project
```

**Why?** No migration needed. Start with the simplified workflow.

---

### Scenario 2: Migrating from Setup Wizard

**If you used the old setup wizard**, your existing collection should work with minerva-kb.

#### Check If Already Compatible

```bash
# Check if config files exist
ls ~/.minerva/apps/minerva-kb/

# Look for files matching: *-index.json, *-watcher.json
```

**If config files exist**: Your collection is already compatible! The setup wizard created configs that minerva-kb can use.

**If config files don't exist**: See [Scenario 3: Manual Collections](#scenario-3-manual-collections-unmanaged).

#### Using minerva-kb with Existing Collection

```bash
# List collections (should show your existing one)
minerva-kb list

# Check status
minerva-kb status <collection-name>

# Start watcher (if not already running)
minerva-kb watch <collection-name>

# Add more collections (now fast and easy!)
minerva-kb add ~/code/another-repo
```

**Migration complete!** Continue using minerva-kb for all future operations.

---

### Scenario 3: Manual Collections (Unmanaged)

**If you created collections manually** with `minerva index` (without minerva-kb or setup wizard):

#### Symptoms

```bash
$ minerva-kb list

Collections (1):

my-collection
  ⚠ Unmanaged (created outside minerva-kb)
  Chunks: 1,234
  (No config files found)
```

#### Migration Options

**Option A: Keep Unmanaged (No Action)**

Your collection still works for search via MCP. You just can't use minerva-kb commands (status, sync, watch, remove) for it.

**When to choose**: Collection is stable, rarely changes, no need for watcher.

**Option B: Recreate as Managed (Recommended)**

Delete the unmanaged collection and recreate with minerva-kb:

```bash
# 1. Note repository path for this collection
# (find it manually or from old configs)

# 2. Remove unmanaged collection from ChromaDB
minerva remove ~/.minerva/chromadb <collection-name>

# 3. Recreate with minerva-kb
minerva-kb add /path/to/repository

# Now fully managed with all minerva-kb features!
```

**When to choose**: You want to use watchers, status checking, and easy management.

**Trade-off**: Requires full re-indexing (takes a few minutes).

---

### Scenario 4: Migrating from local-repo-watcher-manager

**If you used `local-repo-watcher-manager`** (deprecated tool):

#### What Changed

`local-repo-watcher-manager` is replaced by `minerva-kb watch`.

| Old: watcher-manager | New: minerva-kb watch |
|---------------------|---------------------|
| Separate tool | Integrated command |
| Manual config creation | Auto-generated configs |
| No status visibility | Built-in status checking |

#### Migration Steps

```bash
# 1. Stop existing watchers
ps aux | grep local-repo-watcher
kill <PID1> <PID2> <PID3>

# 2. Uninstall watcher-manager (optional)
pipx uninstall local-repo-watcher-manager

# 3. Use minerva-kb watch instead
minerva-kb watch <collection-name>

# Or interactive mode
minerva-kb watch
```

**Note**: `local-repo-watcher` (the underlying watcher binary) is still required and used by minerva-kb. Only the *manager* layer is removed.

---

## Step-by-Step Migration

### For Setup Wizard Users

#### Before Migration

**Check existing setup**:

```bash
# 1. Check if collections exist
python -c "
import chromadb
client = chromadb.PersistentClient(path='/Users/$(whoami)/.minerva/chromadb')
for c in client.list_collections():
    print(c.name)
"

# 2. Check if config files exist
ls ~/.minerva/apps/minerva-kb/

# 3. Note repository paths (from old configs or memory)
```

#### Migration Process

```bash
# 1. Install minerva-kb
pipx install tools/minerva-kb

# 2. Verify existing collection is recognized
minerva-kb list

# 3. If collection shows as "managed" (has config files):
#    No migration needed! Continue with minerva-kb commands.

# 4. If collection shows as "unmanaged" (no config files):
#    Choose Option A (keep as-is) or Option B (recreate)
#    See Scenario 3 above for details.

# 5. Add new collections easily
minerva-kb add ~/code/second-repo
minerva-kb add ~/code/third-repo
```

#### After Migration

**Verify everything works**:

```bash
# List all collections
minerva-kb list

# Check detailed status
minerva-kb status <collection-name>

# Start watcher
minerva-kb watch <collection-name>

# Test search via Claude Desktop
# (ask Claude to search your collections)
```

---

### For Manual Setup Users

#### Before Migration

**Inventory existing collections**:

```bash
# List ChromaDB collections
python -c "
import chromadb
client = chromadb.PersistentClient(path='/Users/$(whoami)/.minerva/chromadb')
print('ChromaDB collections:')
for c in client.list_collections():
    print(f'  - {c.name} ({c.count()} chunks)')
"

# Check for any existing configs
ls ~/.minerva/apps/minerva-kb/ 2>/dev/null || echo "No minerva-kb configs found"
```

#### Migration Process

**For each unmanaged collection**:

```bash
# 1. Decide: Keep unmanaged OR Recreate as managed?

# 2. If recreating:

# a. Remove from ChromaDB
minerva remove ~/.minerva/chromadb <collection-name>

# b. Recreate with minerva-kb
minerva-kb add /path/to/repository

# c. Verify
minerva-kb status <new-collection-name>
```

#### After Migration

```bash
# All collections now managed
minerva-kb list

# Full lifecycle management available
minerva-kb status <collection>
minerva-kb sync <collection>
minerva-kb watch <collection>
minerva-kb remove <collection>
```

---

## Adopting Existing Collections

### Can minerva-kb Adopt Unmanaged Collections?

**Short answer**: Not automatically.

**Why?** minerva-kb requires specific configuration files (`*-index.json`, `*-watcher.json`) that unmanaged collections don't have. These files store:

- Repository path
- Provider configuration
- Chunk size settings
- Watcher patterns

Without these files, minerva-kb cannot manage the collection.

### Workaround: Manual Config Creation (Advanced)

**For advanced users only.** If you don't want to re-index:

#### Step 1: Identify Collection Details

You need to know:
- Repository path
- Provider type and models used
- Chunk size used during indexing
- Collection description

#### Step 2: Create Index Config

```bash
# Create config manually
cat > ~/.minerva/apps/minerva-kb/<collection-name>-index.json << 'EOF'
{
  "chromadb_path": "/Users/michele/.minerva/chromadb",
  "collection": {
    "name": "<collection-name>",
    "description": "<your description>",
    "json_file": "/Users/michele/.minerva/apps/minerva-kb/<collection-name>-extracted.json",
    "chunk_size": 1200,
    "force_recreate": false,
    "skip_ai_validation": false
  },
  "provider": {
    "provider_type": "openai",
    "base_url": "https://api.openai.com/v1",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini",
    "api_key": "${OPENAI_API_KEY}"
  }
}
EOF
```

#### Step 3: Create Watcher Config

```bash
cat > ~/.minerva/apps/minerva-kb/<collection-name>-watcher.json << 'EOF'
{
  "repository_path": "/path/to/repository",
  "collection_name": "<collection-name>",
  "extracted_json_path": "/Users/michele/.minerva/apps/minerva-kb/<collection-name>-extracted.json",
  "index_config_path": "/Users/michele/.minerva/apps/minerva-kb/<collection-name>-index.json",
  "debounce_seconds": 60.0,
  "include_extensions": [".md", ".mdx", ".markdown", ".rst", ".txt"],
  "ignore_patterns": [".git", "node_modules", ".venv", "__pycache__"]
}
EOF
```

#### Step 4: Create Extracted JSON

```bash
# Extract repository (required for sync/watch to work)
repository-doc-extractor /path/to/repository \
  -o ~/.minerva/apps/minerva-kb/<collection-name>-extracted.json
```

#### Step 5: Verify

```bash
minerva-kb list
minerva-kb status <collection-name>
```

**Recommendation**: Only do this if re-indexing is prohibitively expensive. Otherwise, recreating with `minerva-kb add` is simpler and safer.

---

## Frequently Asked Questions

### Do I need to delete the old setup wizard?

No, but it's now deprecated. The slimmed version (Phase 13 of implementation) will only install dependencies, not create collections.

### Will my existing collections stop working?

No. Existing collections in ChromaDB continue to work for search via MCP. You just can't manage them with minerva-kb unless you migrate.

### Can I use both old and new approaches?

Technically yes, but not recommended. Stick with minerva-kb for consistency.

### What happens to my API keys?

API keys stored in OS keychain (via `minerva keychain`) are preserved. minerva-kb uses the same keychain storage.

### Do I need to re-index when migrating?

- **Setup wizard users**: Usually no (configs are compatible)
- **Manual setup users**: Yes, if adopting as managed (or use advanced workaround)

### How do I uninstall the old tools?

```bash
# Uninstall deprecated watcher manager (if installed)
pipx uninstall local-repo-watcher-manager

# Note: Do NOT uninstall local-repo-watcher itself
# (still used by minerva-kb)
```

### Can I migrate without downtime?

Yes. Existing collections remain searchable during migration. Add new collections with minerva-kb while old ones continue working.

### What if I have multiple collections created manually?

Migrate them one at a time:

1. Note repository paths for all collections
2. For each collection: remove from ChromaDB and recreate with `minerva-kb add`
3. Or keep them as unmanaged (search still works)

### Where can I get help?

- **Documentation**: [MINERVA_KB_GUIDE.md](MINERVA_KB_GUIDE.md)
- **Examples**: [MINERVA_KB_EXAMPLES.md](MINERVA_KB_EXAMPLES.md)
- **Issues**: Check troubleshooting sections in docs above

---

## Summary

### Migration Checklist

- [ ] Install minerva-kb: `pipx install tools/minerva-kb`
- [ ] Check existing collections: `minerva-kb list`
- [ ] Verify collection status: `minerva-kb status <collection>`
- [ ] Stop old watchers (if using watcher-manager)
- [ ] Decide: Keep unmanaged OR Recreate as managed
- [ ] If recreating: Remove old, add with minerva-kb
- [ ] Start watchers: `minerva-kb watch <collection>`
- [ ] Add new collections: `minerva-kb add <repo-path>`
- [ ] Test search via Claude Desktop

### Key Takeaways

- **Existing collections**: Continue working for search
- **Setup wizard configs**: Compatible with minerva-kb
- **Manual collections**: Need recreation to become managed
- **Time savings**: <2 minutes for each additional collection
- **No downtime**: Migrate gradually, collections remain searchable

### Next Steps

1. **Install minerva-kb**: Follow [installation guide](../tools/minerva-kb/README.md)
2. **Try first command**: `minerva-kb list` (see what you have)
3. **Add new collection**: `minerva-kb add ~/code/repo` (experience the new workflow)
4. **Read comprehensive guide**: [MINERVA_KB_GUIDE.md](MINERVA_KB_GUIDE.md)

Welcome to the new minerva-kb workflow!
