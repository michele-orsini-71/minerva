# Minerva KB Example Workflows

Real-world examples showing how to use `minerva-kb` for common tasks.

## Table of Contents

- [Workflow 1: Adding Your First Collection](#workflow-1-adding-your-first-collection)
- [Workflow 2: Adding a Second Collection](#workflow-2-adding-a-second-collection)
- [Workflow 3: Changing AI Provider](#workflow-3-changing-ai-provider)
- [Workflow 4: Listing All Collections](#workflow-4-listing-all-collections)
- [Workflow 5: Checking Collection Status](#workflow-5-checking-collection-status)
- [Workflow 6: Manual Sync](#workflow-6-manual-sync)
- [Workflow 7: Starting a Watcher](#workflow-7-starting-a-watcher)
- [Workflow 8: Removing a Collection](#workflow-8-removing-a-collection)
- [Workflow 9: Handling Collection Name Conflicts](#workflow-9-handling-collection-name-conflicts)
- [Error Examples](#error-examples)

---

## Workflow 1: Adding Your First Collection

**Scenario**: You have a repository at `~/code/my-project` and want to create a searchable knowledge base from its documentation.

```bash
$ minerva-kb add ~/code/my-project

📚 Collection Name
==================
Derived from repository folder name: my-project

💬 Collection Description
==========================
📄 Found README.md in repository
🤖 Generating optimized description from README...

✨ Generated description:
   Python web framework with REST API, GraphQL support, and comprehensive
   documentation. Best for questions about API design, code architecture,
   testing strategies, component interactions, and deployment workflows.

✓ Description ready

🤖 AI Provider Selection
=========================
Which AI provider do you want to use?

  1. OpenAI (cloud, requires API key)
     • Default embedding: text-embedding-3-small
     • Default LLM: gpt-4o-mini

  2. Google Gemini (cloud, requires API key)
     • Default embedding: text-embedding-004
     • Default LLM: gemini-1.5-flash

  3. Ollama (local, free, no API key)

  4. LM Studio (local, free, no API key)

Choice [1-4]: 1

🔑 API Key Configuration
=========================
Your OpenAI API key will be stored securely in OS keychain.
The key will be stored as: 'OPENAI_API_KEY'

Enter your OpenAI API key: sk-proj-xxxxx...

🔍 Validating API key...
✓ OpenAI API key is valid and working

🎯 Model Selection
==================
Use default models? [Y/n]: Y

✓ Selected: OpenAI
  • Embedding: text-embedding-3-small
  • LLM: gpt-4o-mini

📂 Creating configuration files...
✓ Created: ~/.minerva/apps/minerva-kb/my-project-index.json
✓ Created: ~/.minerva/apps/minerva-kb/my-project-watcher.json

🔍 Extracting and Indexing
============================
📚 Extracting repository contents...
✓ Extraction complete: 245 files processed

🔍 Indexing collection...
⏳ Generating embeddings... (this may take a few minutes)
✓ Indexed 1,234 chunks

✅ Collection 'my-project' created successfully!

📝 Next Steps
==============
1. Start the file watcher (optional but recommended):
   minerva-kb watch my-project

2. Test by asking Claude:
   "Search the my-project collection for API documentation"
```

**Key points**:
- Collection name automatically derived from folder name
- README used to generate optimized description
- API key stored securely in OS keychain
- Configuration files auto-created

---

## Workflow 2: Adding a Second Collection

**Scenario**: You already have one collection and want to add another. This is much faster because API keys are already configured.

```bash
$ minerva-kb add ~/code/internal-docs

📚 Collection Name
==================
Derived from repository folder name: internal-docs

💬 Collection Description
==========================
ℹ️  No README.md found in repository
Please describe what's in this repository.

Brief description: Company internal documentation for infrastructure and deployment

🤖 Generating optimized description...

✨ Generated description:
   Company internal documentation covering infrastructure setup, deployment
   procedures, and system administration. Best for questions about setup
   procedures, configuration, troubleshooting, deployment workflows, and
   infrastructure architecture.

🤖 AI Provider Selection
=========================
✓ Using existing OpenAI API key from keychain

Which AI provider do you want to use?

  1. OpenAI (current: gpt-4o-mini)
  2. Google Gemini
  3. Ollama
  4. LM Studio

Choice [1-4]: 3

✓ Selected: Ollama (local)

📝 Ollama Model Configuration
-------------------------------
Embedding model [mxbai-embed-large:latest]:
LLM model [llama3.1:8b]:

🔍 Validating AI provider availability...
✓ Ollama is running and accessible

📂 Creating configuration files...
✓ Created: ~/.minerva/apps/minerva-kb/internal-docs-index.json
✓ Created: ~/.minerva/apps/minerva-kb/internal-docs-watcher.json

🔍 Extracting and Indexing
============================
📚 Extracting repository contents...
✓ Extraction complete: 87 files processed

🔍 Indexing collection...
✓ Indexed 456 chunks

✅ Collection 'internal-docs' created successfully!

📝 Next Steps
==============
Start the file watcher:
  minerva-kb watch internal-docs

View all collections:
  minerva-kb list
```

**Key points**:
- Much faster than first collection (API keys already configured)
- No README, so manual description provided
- Mixed providers (OpenAI for first, Ollama for second)
- Total time: <2 minutes

---

## Workflow 3: Changing AI Provider

**Scenario**: You want to switch from OpenAI to Gemini to reduce costs or try a different model.

```bash
$ minerva-kb add ~/code/my-project

⚠️  Collection 'my-project' already exists for this repository

Current provider: OpenAI (gpt-4o-mini + text-embedding-3-small)
Change AI provider? [y/N]: y

🤖 AI Provider Selection
=========================
Which AI provider do you want to use?

  1. OpenAI (current)
  2. Google Gemini
  3. Ollama
  4. LM Studio

Choice [1-4]: 2

🔑 API Key Configuration
=========================
Your Gemini API key will be stored securely in OS keychain.
The key will be stored as: 'GEMINI_API_KEY'

Enter your Gemini API key: xxxxx...

🔍 Validating API key...
✓ Gemini API key is valid and working

🎯 Model Selection
==================
Use default models? [Y/n]: n

Embedding model [text-embedding-004]: text-embedding-004
LLM model [gemini-1.5-flash]: gemini-1.5-pro

✓ Selected: Gemini
  • Embedding: text-embedding-004
  • LLM: gemini-1.5-pro

📝 Updating configuration...
✓ Updated index config with new provider

⏸️  Stopping watcher (PID 12345)...
✓ Watcher stopped

🔍 Re-indexing with new provider...
📚 Extracting repository contents...
✓ Extraction complete

🔍 Indexing collection...
✓ Indexed 1,234 chunks

✅ Collection 'my-project' reindexed with Gemini

⚠️  Watcher stopped during re-indexing
Restart with: minerva-kb watch my-project
```

**Key points**:
- Detects existing collection automatically
- Stops running watcher before re-indexing
- Full re-indexing required (embeddings incompatible across providers)
- Watcher must be manually restarted

---

## Workflow 4: Listing All Collections

**Scenario**: You want to see all managed collections and their status at a glance.

### Table Format (Default)

```bash
$ minerva-kb list

Collections (3):

my-project
  Repository: /Users/michele/code/my-project
  Provider: gemini (gemini-1.5-pro + text-embedding-004)
  Chunks: 1,234
  Watcher: ✓ Running (PID 45678)
  Last indexed: 2025-12-08 18:30:15

internal-docs
  Repository: /Users/michele/code/internal-docs
  Provider: ollama (llama3.1:8b + mxbai-embed-large:latest)
  Chunks: 456
  Watcher: ⚠ Not running
  Last indexed: 2025-12-07 17:22:45

company-kb
  Repository: /Users/michele/Documents/company-kb
  Provider: openai (gpt-4o-mini + text-embedding-3-small)
  Chunks: 789
  Watcher: ✓ Running (PID 45690)
  Last indexed: 2025-12-06 09:15:30
```

### JSON Format

```bash
$ minerva-kb list --format json

[
  {
    "name": "my-project",
    "repository_path": "/Users/michele/code/my-project",
    "provider": {
      "type": "gemini",
      "embedding_model": "text-embedding-004",
      "llm_model": "gemini-1.5-pro"
    },
    "chunks": 1234,
    "watcher": {
      "running": true,
      "pid": 45678
    },
    "last_indexed": "2025-12-08T18:30:15Z"
  },
  {
    "name": "internal-docs",
    "repository_path": "/Users/michele/code/internal-docs",
    "provider": {
      "type": "ollama",
      "embedding_model": "mxbai-embed-large:latest",
      "llm_model": "llama3.1:8b"
    },
    "chunks": 456,
    "watcher": {
      "running": false,
      "pid": null
    },
    "last_indexed": "2025-12-07T17:22:45Z"
  },
  {
    "name": "company-kb",
    "repository_path": "/Users/michele/Documents/company-kb",
    "provider": {
      "type": "openai",
      "embedding_model": "text-embedding-3-small",
      "llm_model": "gpt-4o-mini"
    },
    "chunks": 789,
    "watcher": {
      "running": true,
      "pid": 45690
    },
    "last_indexed": "2025-12-06T09:15:30Z"
  }
]
```

**Key points**:
- Table format for human readability
- JSON format for scripting/automation
- Shows watcher status with PID
- Chunk counts with thousands separator
- Last indexed timestamp

---

## Workflow 5: Checking Collection Status

**Scenario**: You want detailed diagnostics for a specific collection.

```bash
$ minerva-kb status my-project

Collection: my-project
Repository: /Users/michele/code/my-project

AI Provider:
  Type: gemini
  Embedding model: text-embedding-004
  LLM model: gemini-1.5-pro
  API key: ✓ Stored in keychain (GEMINI_API_KEY)

ChromaDB:
  Status: ✓ Collection exists
  Chunks: 1,234
  Last modified: 2025-12-08 18:30:15

Configuration Files:
  Index config: ~/.minerva/apps/minerva-kb/my-project-index.json
  Watcher config: ~/.minerva/apps/minerva-kb/my-project-watcher.json
  Extracted data: ~/.minerva/apps/minerva-kb/my-project-extracted.json (1.8 MB)

Watcher:
  Status: ✓ Running (PID 45678)
  Watch patterns: .md, .mdx, .markdown, .rst, .txt
  Ignore patterns: .git, node_modules, .venv, __pycache__
  Debounce: 60 seconds
```

**Key points**:
- Comprehensive health check
- Provider configuration details
- API key status verification
- File paths for all configs
- Watcher configuration and status

---

## Workflow 6: Manual Sync

**Scenario**: You made bulk changes to documentation files and want to re-index immediately without waiting for the watcher.

```bash
$ minerva-kb sync my-project

Syncing collection 'my-project'...

✓ Extracting repository documentation...
  Processed 248 files (3 new, 2 modified, 0 deleted)

✓ Indexing collection...
  Updated 1,240 chunks (1,234 existing, 6 new, 0 removed)

✓ Collection 'my-project' synced successfully!
```

**Key points**:
- Immediate re-indexing
- Shows file change summary
- Shows chunk change summary
- Watcher state unaffected

---

## Workflow 7: Starting a Watcher

**Scenario**: You want automatic re-indexing when documentation files change.

### With Collection Name

```bash
$ minerva-kb watch my-project

▶️ Starting watcher for 'my-project'... Press Ctrl+C to stop.

Watching: /Users/michele/code/my-project
Patterns: .md, .mdx, .markdown, .rst, .txt
Debounce: 60 seconds

[2025-12-08 14:45:23] Watcher started (PID 45678)
[2025-12-08 14:47:15] Change detected: docs/api.md
[2025-12-08 14:48:15] Re-indexing collection...
[2025-12-08 14:48:32] ✓ Re-indexed (1,235 chunks)
[2025-12-08 14:52:10] Change detected: README.md
[2025-12-08 14:53:10] Re-indexing collection...
[2025-12-08 14:53:25] ✓ Re-indexed (1,236 chunks)

^C
[2025-12-08 14:55:01] Watcher stopped
```

### Interactive Mode (No Collection Name)

```bash
$ minerva-kb watch

Select collection to watch:

  1. my-project (watcher: not running)
  2. internal-docs (watcher: not running)
  3. company-kb (watcher: running, PID 45690)

Choice [1-3]: 1

▶️ Starting watcher for 'my-project'... Press Ctrl+C to stop.
[continues as above...]
```

**Key points**:
- Runs in foreground (use tmux/screen for persistence)
- 60-second debounce prevents thrashing
- Shows detected changes and re-indexing progress
- Ctrl+C for clean shutdown

---

## Workflow 8: Removing a Collection

**Scenario**: You no longer need a collection and want to clean up all associated data.

```bash
$ minerva-kb remove my-project

Collection: my-project
Repository: /Users/michele/code/my-project
Provider: gemini (gemini-1.5-pro + text-embedding-004)
Chunks: 1,234

⚠️ WARNING: This will delete:
  - ChromaDB collection and all embeddings
  - Configuration files (~/.minerva/apps/minerva-kb/)
  - Extracted data (~/.minerva/apps/minerva-kb/my-project-extracted.json)

Your repository files will NOT be affected.

Type YES to confirm deletion: YES

✓ Stopping watcher (PID 45678)...
✓ Deleting configuration files...
  - my-project-index.json
  - my-project-watcher.json
  - my-project-extracted.json
✓ Deleting ChromaDB collection...

✓ Collection 'my-project' removed successfully!

Note: API keys remain in keychain
To remove: minerva keychain delete GEMINI_API_KEY
```

**Key points**:
- Confirmation required (type "YES" exactly)
- Repository files untouched
- Watcher stopped automatically
- API keys preserved (may be used by other collections)

---

## Workflow 9: Handling Collection Name Conflicts

**Scenario**: You try to add a repository but a collection with that name already exists in ChromaDB (created manually outside minerva-kb).

### Option 1: Abort

```bash
$ minerva-kb add ~/code/minerva

📚 Collection Name
==================
Derived from repository folder name: minerva

❌ Collection 'minerva' already exists in ChromaDB

This collection was not created by minerva-kb (no config files found).
It may have been created manually via 'minerva index'.

Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]: 1

❌ Collection creation aborted

Existing collections in ChromaDB:
  • minerva (unmanaged - created outside minerva-kb)
  • my-project (managed)
  • docs (managed)

To use a different name, rename the repository folder or manually:
  1. Remove existing collection: minerva remove ~/.minerva/chromadb minerva
  2. Try again: minerva-kb add ~/code/minerva
```

### Option 2: Wipe and Recreate

```bash
Options:
  1. Abort (keep existing collection)
  2. Wipe and recreate (DELETES existing embeddings)

Choice [1-2]: 2

⚠️  Deleting existing collection 'minerva' from ChromaDB...
✓ Collection deleted

💬 Collection Description
==========================
[continues with normal add flow...]
```

**Key points**:
- Detects unmanaged collections
- Offers safe abort option
- Allows wipe-and-recreate if intentional
- Clear explanation of consequences

---

## Error Examples

### Repository Path Invalid

```bash
$ minerva-kb add /nonexistent/path

❌ Repository path does not exist: /nonexistent/path

Please provide a valid directory path.
```

### API Key Validation Failed

```bash
$ minerva-kb add ~/code/project

[... provider selection ...]
Choice [1-4]: 1

Enter your OpenAI API key: sk-invalid-key

🔍 Validating API key...
❌ Failed to connect to OpenAI: Invalid API key

Possible issues:
  • API key is invalid or expired
  • No internet connection
  • API service is down

Try again with a different API key? [y/N]: n

⚠️  Setup cancelled
```

### Ollama Not Running

```bash
$ minerva-kb add ~/code/project

[... provider selection ...]
Choice [1-4]: 3

🔍 Validating AI provider availability...
❌ Cannot connect to Ollama at http://localhost:11434

Please start Ollama before continuing:
  ollama serve

Retry connection? [y/N]: n

⚠️  Setup cancelled
```

### Collection Not Found

```bash
$ minerva-kb status nonexistent

❌ Collection 'nonexistent' not found

Available collections:
  • my-project
  • internal-docs

Run 'minerva-kb list' to see all collections.
```

### Watcher Already Running

```bash
$ minerva-kb watch my-project

⚠️  Watcher already running for 'my-project' (PID 45678)

To stop the watcher:
  kill 45678
```

### Trying to Remove Unmanaged Collection

```bash
$ minerva-kb remove orphan-collection

❌ Collection 'orphan-collection' is not managed by minerva-kb

This collection exists in ChromaDB but has no config files in:
  ~/.minerva/apps/minerva-kb/

To remove it manually:
  minerva remove ~/.minerva/chromadb orphan-collection
```

---

## Summary

These workflows demonstrate:

- **First collection**: ~5 minutes (including API key setup)
- **Second collection**: <2 minutes (API keys already configured)
- **Provider change**: Re-indexes with new embeddings
- **Status commands**: Quick health checks and diagnostics
- **Watcher**: Automatic re-indexing on file changes
- **Removal**: Clean deletion with confirmations
- **Error handling**: Clear messages with actionable next steps

For comprehensive documentation, see [MINERVA_KB_GUIDE.md](MINERVA_KB_GUIDE.md).
