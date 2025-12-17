# minerva-common: Shared Library Documentation

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Shared Infrastructure](#shared-infrastructure)
- [Module Reference](#module-reference)
  - [paths.py](#pathspy)
  - [init.py](#initpy)
  - [registry.py](#registrypy)
  - [config_builder.py](#config_builderpy)
  - [minerva_runner.py](#minerva_runnerpy)
  - [provider_setup.py](#provider_setuppy)
  - [description_generator.py](#description_generatorpy)
  - [server_manager.py](#server_managerpy)
  - [collection_ops.py](#collection_opspy)
  - [collision.py](#collisionpy)
- [Integration Examples](#integration-examples)
- [Direct Usage Examples](#direct-usage-examples)

---

## Overview

`minerva-common` is a shared library that provides common infrastructure and utilities for Minerva orchestrator tools. It eliminates code duplication between `minerva-kb` and `minerva-doc` by centralizing:

- **Shared directory paths** (`~/.minerva/` structure)
- **Registry management** (collection metadata storage)
- **AI provider setup** (interactive provider selection)
- **Configuration builders** (index config generation)
- **Minerva CLI wrappers** (validate, index, serve commands)
- **Collision detection** (cross-tool collection name conflicts)
- **Server management** (MCP server startup)

### Design Principles

1. **Single Source of Truth**: All shared paths and infrastructure defined once
2. **Clean Code**: No docstrings, self-documenting function names, Uncle Bob principles
3. **Atomic Operations**: Safe file writes using temp files + replace pattern
4. **Permission Management**: Proper 0o700/0o600 permissions for sensitive data
5. **Tool Independence**: Both minerva-kb and minerva-doc consume the same library

### Tools Using minerva-common

- **minerva-kb**: Repository knowledge base orchestrator
- **minerva-doc**: Document collection orchestrator

Both tools are installed via `pipx` and have `minerva-common` injected as a dependency using `pipx inject`.

---

## Architecture

### Package Structure

```
tools/minerva-common/
├── src/minerva_common/
│   ├── __init__.py
│   ├── paths.py                    # Shared directory paths
│   ├── init.py                     # Directory initialization
│   ├── registry.py                 # Collection registry management
│   ├── config_builder.py           # Index config builder
│   ├── minerva_runner.py           # Minerva CLI wrappers
│   ├── provider_setup.py           # AI provider selection
│   ├── description_generator.py    # AI-powered descriptions
│   ├── server_manager.py           # MCP server management
│   ├── collection_ops.py           # ChromaDB operations
│   └── collision.py                # Collection name collision detection
├── tests/                          # Unit tests for all modules
├── pyproject.toml                  # Package configuration
└── README.md
```

### Dependency Flow

```
minerva-kb ──┐
             ├──▶ minerva-common ──▶ minerva (core CLI)
minerva-doc ─┘
```

Both orchestrator tools depend on `minerva-common`, which in turn uses the core `minerva` CLI for validation, indexing, and serving.

---

## Shared Infrastructure

### Directory Structure

minerva-common defines and manages the following shared directory structure:

```
~/.minerva/                         # Root directory (0o700)
├── chromadb/                       # Shared ChromaDB storage (0o700)
│   └── [collection data]
├── server.json                     # Shared MCP server config (0o600)
└── apps/                           # App-specific directories
    ├── minerva-kb/
    │   └── collections.json        # minerva-kb registry (0o600)
    └── minerva-doc/
        └── collections.json        # minerva-doc registry (0o600)
```

### Path Constants

All shared paths are defined in `paths.py`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `HOME_DIR` | `Path.home()` | User's home directory |
| `MINERVA_DIR` | `~/.minerva` | Root Minerva directory |
| `CHROMADB_DIR` | `~/.minerva/chromadb` | Shared ChromaDB storage |
| `SERVER_CONFIG_PATH` | `~/.minerva/server.json` | Shared MCP server config |
| `APPS_DIR` | `~/.minerva/apps` | App-specific directories |

### Permissions

- **Directories**: `0o700` (rwx------)
  - Only owner can read, write, and execute
  - Applied to: `~/.minerva/`, `~/.minerva/chromadb`, app directories

- **Files**: `0o600` (rw-------)
  - Only owner can read and write
  - Applied to: `server.json`, `collections.json` files

Permission errors are caught and ignored gracefully to support systems where chmod is restricted.

### Registry Format

Each app maintains a JSON registry at `~/.minerva/apps/<app-name>/collections.json`:

```json
{
  "collections": {
    "my-collection": {
      "json_file": "/path/to/source.json",
      "chromadb_path": "/Users/user/.minerva/chromadb",
      "provider": {
        "provider_type": "ollama",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "base_url": "http://localhost:11434"
      },
      "description": "Collection description",
      "created_at": "2025-12-15T10:00:00Z",
      "indexed_at": "2025-12-15T10:05:00Z"
    }
  }
}
```

---

## Module Reference

### paths.py

**Purpose**: Define all shared directory paths used across Minerva tools.

**Constants**:

```python
HOME_DIR: Path           # User's home directory
MINERVA_DIR: Path        # ~/.minerva
CHROMADB_DIR: Path       # ~/.minerva/chromadb
SERVER_CONFIG_PATH: Path # ~/.minerva/server.json
APPS_DIR: Path           # ~/.minerva/apps
```

**Usage**:

```python
from minerva_common.paths import MINERVA_DIR, CHROMADB_DIR

print(f"Minerva root: {MINERVA_DIR}")
print(f"ChromaDB: {CHROMADB_DIR}")
```

**Design Notes**:
- All paths are `Path` objects from `pathlib`
- No functions, just constants
- Single source of truth for all Minerva paths

---

### init.py

**Purpose**: Initialize shared infrastructure directories and files.

**Functions**:

#### `ensure_shared_dirs() -> None`

Creates `~/.minerva/` and `~/.minerva/chromadb` with proper permissions (0o700).

**Behavior**:
- Creates directories if they don't exist
- Sets permissions to 0o700 (owner-only)
- Ignores `PermissionError` gracefully

**Usage**:

```python
from minerva_common.init import ensure_shared_dirs

ensure_shared_dirs()
# Now ~/.minerva/ and ~/.minerva/chromadb exist
```

#### `ensure_server_config() -> tuple[Path, bool]`

Creates `~/.minerva/server.json` if it doesn't exist.

**Returns**:
- `(Path, bool)`: Tuple of (config_path, was_created)
  - `was_created=True` if config was just created
  - `was_created=False` if config already existed

**Default Config**:

```json
{
  "chromadb_path": "/Users/user/.minerva/chromadb",
  "default_max_results": 5,
  "host": "127.0.0.1",
  "port": 8337
}
```

**Usage**:

```python
from minerva_common.init import ensure_server_config

config_path, created = ensure_server_config()
if created:
    print(f"Created new server config: {config_path}")
else:
    print(f"Using existing config: {config_path}")
```

**Implementation Details**:
- Uses atomic write (temp file + replace)
- Sets permissions to 0o600
- chromadb_path is absolute path string

---

### registry.py

**Purpose**: Manage collection metadata registries for orchestrator tools.

**Class**: `Registry`

#### Constructor

```python
Registry(registry_path: Path)
```

**Parameters**:
- `registry_path`: Path to collections.json file (e.g., `~/.minerva/apps/minerva-kb/collections.json`)

#### Methods

##### `load() -> dict`

Loads the registry from disk.

**Returns**: Dictionary with "collections" key containing collection metadata

**Behavior**:
- Returns `{"collections": {}}` if file doesn't exist
- Parses JSON and returns data

**Usage**:

```python
from pathlib import Path
from minerva_common.registry import Registry

registry_path = Path("~/.minerva/apps/minerva-kb/collections.json").expanduser()
registry = Registry(registry_path)

data = registry.load()
print(f"Found {len(data['collections'])} collections")
```

##### `save(data: dict) -> None`

Saves registry data to disk atomically.

**Parameters**:
- `data`: Dictionary to save (must have "collections" key)

**Behavior**:
- Uses atomic write (temp file + replace)
- Sets permissions to 0o600
- Creates parent directories if needed

##### `add_collection(name: str, metadata: dict) -> None`

Adds a new collection to the registry.

**Parameters**:
- `name`: Collection name
- `metadata`: Dictionary of collection metadata

**Usage**:

```python
registry.add_collection("my-docs", {
    "json_file": "/path/to/docs.json",
    "provider": {...},
    "description": "My documentation",
    "created_at": "2025-12-15T10:00:00Z"
})
```

##### `get_collection(name: str) -> dict | None`

Gets metadata for a specific collection.

**Returns**: Metadata dictionary or `None` if not found

##### `update_collection(name: str, metadata: dict) -> None`

Updates existing collection metadata (merges with existing).

**Parameters**:
- `name`: Collection name
- `metadata`: Dictionary of fields to update

**Behavior**:
- Only updates if collection exists
- Merges metadata with existing data (uses `dict.update()`)

##### `remove_collection(name: str) -> None`

Removes a collection from the registry.

**Behavior**:
- Only removes if collection exists
- No error if collection not found

##### `list_collections() -> list[dict]`

Returns list of all collections with metadata.

**Returns**: List of dictionaries, each containing `{"name": ..., **metadata}`

**Usage**:

```python
collections = registry.list_collections()
for col in collections:
    print(f"{col['name']}: {col.get('description', 'No description')}")
```

##### `collection_exists(name: str) -> bool`

Checks if a collection exists in the registry.

**Returns**: `True` if collection exists, `False` otherwise

---

### config_builder.py

**Purpose**: Build minerva index configuration dictionaries.

**Functions**:

#### `build_index_config(...) -> dict`

Builds a complete index configuration dictionary for the `minerva index` command.

**Parameters**:

```python
collection_name: str           # Collection name
json_file: str | Path          # Path to JSON notes file
chromadb_path: str | Path      # Path to ChromaDB directory
provider: dict                 # AI provider configuration
description: str = ""          # Collection description
chunk_size: int = 1200         # Chunk size for splitting
force_recreate: bool = False   # Whether to recreate collection
skip_ai_validation: bool = False  # Skip AI validation step
```

**Returns**: Dictionary in minerva index config format

**Example Output**:

```python
{
    "chromadb_path": "/Users/user/.minerva/chromadb",
    "collection": {
        "name": "my-docs",
        "description": "My documentation collection",
        "json_file": "/path/to/docs.json",
        "chunk_size": 1200,
        "force_recreate": False,
        "skip_ai_validation": False
    },
    "provider": {
        "provider_type": "ollama",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "base_url": "http://localhost:11434"
    }
}
```

**Usage**:

```python
from minerva_common.config_builder import build_index_config
from minerva_common.paths import CHROMADB_DIR

provider = {
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
}

config = build_index_config(
    collection_name="my-docs",
    json_file="/path/to/docs.json",
    chromadb_path=CHROMADB_DIR,
    provider=provider,
    description="My documentation",
    chunk_size=1200
)
```

#### `save_index_config(config: dict, output_path: Path) -> None`

Saves index configuration to a JSON file atomically.

**Parameters**:
- `config`: Configuration dictionary from `build_index_config()`
- `output_path`: Where to save the config file

**Behavior**:
- Uses atomic write (temp file + replace)
- Sets permissions to 0o600
- Creates parent directories if needed

**Usage**:

```python
from pathlib import Path
from minerva_common.config_builder import save_index_config

temp_config = Path("/tmp/index-config.json")
save_index_config(config, temp_config)
```

---

### minerva_runner.py

**Purpose**: Wrap minerva CLI commands for programmatic use.

**Functions**:

#### `run_validate(json_file: str | Path) -> tuple[bool, str]`

Validates a JSON file against the note schema.

**Parameters**:
- `json_file`: Path to JSON file to validate

**Returns**: `(success: bool, output: str)`
- `success=True` if validation passed
- `output` contains stdout/stderr from validation

**Usage**:

```python
from minerva_common.minerva_runner import run_validate

success, output = run_validate("/path/to/notes.json")
if success:
    print("✓ Validation passed")
else:
    print(f"✗ Validation failed:\n{output}")
```

**Implementation Details**:
- Runs: `minerva validate <json_file>`
- Timeout: 30 seconds
- Captures both stdout and stderr
- Finds minerva command in PATH or common locations

#### `run_index(config_path: str | Path, timeout: int = 600, verbose: bool = True) -> tuple[bool, str]`

Indexes a collection using minerva.

**Parameters**:
- `config_path`: Path to index configuration JSON
- `timeout`: Maximum seconds to wait (default: 600)
- `verbose`: Show progress output (default: True)

**Returns**: `(success: bool, output: str)`
- `success=True` if indexing completed successfully
- `output` contains captured output (empty if verbose=True)

**Usage**:

```python
from minerva_common.minerva_runner import run_index

success, output = run_index("/tmp/index-config.json", verbose=True)
if success:
    print("✓ Indexing completed")
else:
    print(f"✗ Indexing failed:\n{output}")
```

**Implementation Details**:
- Runs: `minerva index --config <path> [--verbose]`
- Default timeout: 10 minutes
- If `verbose=True`, streams output to terminal in real-time
- If `verbose=False`, captures output and returns it

#### `run_serve(server_config_path: str | Path) -> subprocess.Popen`

Starts the minerva MCP server.

**Parameters**:
- `server_config_path`: Path to server configuration JSON

**Returns**: `subprocess.Popen` process object

**Usage**:

```python
from minerva_common.minerva_runner import run_serve
from minerva_common.paths import SERVER_CONFIG_PATH

process = run_serve(SERVER_CONFIG_PATH)

# Server runs in background
print(f"Server started with PID: {process.pid}")

# Wait for server to finish (Ctrl+C)
process.wait()
```

**Implementation Details**:
- Runs: `minerva serve --config <path>`
- Returns immediately (non-blocking)
- stdout/stderr stream to parent process
- Process continues until killed or Ctrl+C

#### `_get_minerva_command() -> str` (Internal)

Finds the minerva command executable.

**Search Order**:
1. PATH environment variable
2. `~/.local/bin/minerva` (pipx default)
3. `/usr/local/bin/minerva`
4. `/usr/bin/minerva`

**Returns**: Full path to minerva executable

**Raises**: `FileNotFoundError` if minerva not found

**Why This Matters**:
- Claude Desktop MCP servers run without full PATH
- Explicit search ensures minerva is found even without PATH

---

### provider_setup.py

**Purpose**: Interactive AI provider selection and configuration.

**Constants**:

```python
PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "ollama": "Ollama",
    "lmstudio": "LM Studio",
}

DEFAULT_PROVIDER_MODELS = {
    "openai": {
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY"
    },
    "gemini": {
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
        "api_key_env": "GEMINI_API_KEY"
    },
    "ollama": {
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "api_key_env": None
    },
    "lmstudio": {
        "embedding_model": None,
        "llm_model": None,
        "api_key_env": None
    }
}

LOCAL_PROVIDER_ENDPOINTS = {
    "ollama": {
        "url": "http://localhost:11434/api/tags",
        "instruction": "Run 'ollama serve' to start the Ollama API"
    },
    "lmstudio": {
        "url": "http://localhost:1234/v1/models",
        "instruction": "Open LM Studio and ensure the local server is running"
    }
}
```

**Functions**:

#### `select_provider_interactive() -> dict[str, Any]`

Interactively guides user through provider selection.

**Returns**: Complete provider configuration dictionary

**Flow**:
1. Prompts user to choose provider (OpenAI, Gemini, Ollama, LM Studio)
2. Prompts for model names (or uses defaults)
3. Validates configuration
4. Returns validated config

**Usage**:

```python
from minerva_common.provider_setup import select_provider_interactive

provider_config = select_provider_interactive()
# User is guided through selection process

print(f"Selected: {provider_config['provider_type']}")
```

**Example Output**:

```python
{
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
}
```

#### `prompt_provider_choice() -> str`

Prompts user to choose an AI provider.

**Returns**: Provider type string ("openai", "gemini", "ollama", "lmstudio")

**UI Output**:

```
🤖 AI Provider Selection
============================================================

Which AI provider do you want to use?

  1. OpenAI (cloud, requires API key)
     • Default embedding: text-embedding-3-small
     • Default LLM: gpt-4o-mini

  2. Google Gemini (cloud, requires API key)
     • Default embedding: text-embedding-004
     • Default LLM: gemini-1.5-flash

  3. Ollama (local, free, no API key)
     • Default embedding: mxbai-embed-large:latest
     • Default LLM: llama3.1:8b

  4. LM Studio (local, free, no API key)
     • Enter the model names you loaded in LM Studio

Choice [1-4, default 1]:
```

#### `prompt_for_models(provider_type: str) -> dict[str, str]`

Prompts user for embedding and LLM model names.

**Parameters**:
- `provider_type`: Provider type from `prompt_provider_choice()`

**Returns**: Dictionary with "embedding_model" and "llm_model" keys

**Behavior**:
- Shows defaults for provider
- Asks if user wants to use defaults
- If no, prompts for custom model names

#### `build_provider_config(provider_type: str, embedding_model: str, llm_model: str) -> dict[str, Any]`

Builds a complete provider configuration.

**Parameters**:
- `provider_type`: Provider type
- `embedding_model`: Embedding model name
- `llm_model`: LLM model name

**Returns**: Complete provider config with all required fields

**Behavior**:
- Adds `api_key` field for cloud providers (with `${ENV_VAR}` syntax)
- Adds `base_url` field for local providers
- Returns minimal config for each provider

#### `validate_provider_config(config: dict[str, Any]) -> tuple[bool, str | None]`

Validates a provider configuration.

**Parameters**:
- `config`: Provider configuration dictionary

**Returns**: `(is_valid: bool, error_message: str | None)`

**Validation Checks**:
1. Provider type is recognized
2. Embedding model is specified
3. LLM model is specified
4. API key environment variable is set (for cloud providers)
5. Local server is reachable (for Ollama/LM Studio)

**Usage**:

```python
from minerva_common.provider_setup import validate_provider_config

config = {
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
}

is_valid, error = validate_provider_config(config)
if not is_valid:
    print(f"Invalid config: {error}")
```

---

### description_generator.py

**Purpose**: Generate AI-powered collection descriptions.

**Functions**:

#### `generate_description_from_records(json_file: str | Path, provider_config: dict[str, Any], max_samples: int = 10) -> str`

Generates a description by analyzing sample records.

**Parameters**:
- `json_file`: Path to JSON file with records
- `provider_config`: AI provider configuration
- `max_samples`: Number of records to sample (default: 10)

**Returns**: Generated description string (1-2 sentences)

**Process**:
1. Loads JSON file
2. Samples first `max_samples` records
3. Extracts titles and content previews
4. Builds prompt asking AI to describe the collection
5. Calls AI provider's LLM
6. Returns generated description

**Example**:

```python
from minerva_common.description_generator import generate_description_from_records

provider = {
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
}

description = generate_description_from_records(
    "/path/to/notes.json",
    provider,
    max_samples=10
)

print(description)
# Output: "Personal notes covering AI, Python programming, and database design principles with examples and best practices."
```

#### `prompt_for_description(json_file: str | Path, provider_config: dict[str, Any], auto_generate: bool = True) -> str`

Interactively prompts user for a description with AI generation option.

**Parameters**:
- `json_file`: Path to JSON file
- `provider_config`: AI provider configuration
- `auto_generate`: Whether to offer AI generation (default: True)

**Returns**: Description string (user-provided or AI-generated)

**Flow**:
1. Prompts user to enter description (or press Enter for AI generation)
2. If user provides description, returns it
3. If user presses Enter, generates description with AI
4. Shows generated description
5. Asks user to confirm or provide custom description
6. Returns final description

**Usage**:

```python
from minerva_common.description_generator import prompt_for_description

description = prompt_for_description(
    "/path/to/notes.json",
    provider_config
)

print(f"Using description: {description}")
```

**UI Output**:

```
📝 Collection Description
========================================
Enter a description for this collection.
Press Enter to auto-generate using AI.

Description: [user presses Enter]

⏳ Generating description using AI...

Generated: Personal notes covering AI, Python programming, and database design.

Use this description? [Y/n]:
```

#### `build_description_prompt(titles: list[str], content_previews: list[str], total_count: int) -> str` (Internal)

Builds the prompt sent to the AI for description generation.

#### `extract_content_from_response(response: dict[str, Any]) -> str` (Internal)

Extracts text content from AI provider's response.

---

### server_manager.py

**Purpose**: Manage MCP server startup and display server information.

**Functions**:

#### `start_server(server_config_path: str | Path, chromadb_path: str | Path) -> subprocess.Popen`

Starts the MCP server with informational display.

**Parameters**:
- `server_config_path`: Path to server config JSON
- `chromadb_path`: Path to ChromaDB directory

**Returns**: `subprocess.Popen` process object

**Behavior**:
1. Validates server config exists
2. Lists available collections in ChromaDB
3. Displays server information banner
4. Starts minerva serve command
5. Returns process object

**Usage**:

```python
from minerva_common.server_manager import start_server
from minerva_common.paths import SERVER_CONFIG_PATH, CHROMADB_DIR

process = start_server(SERVER_CONFIG_PATH, CHROMADB_DIR)

# Server runs in background
try:
    process.wait()
except KeyboardInterrupt:
    print("\nServer stopped")
```

**Output**:

```
============================================================
🚀 Starting Minerva MCP Server
============================================================

📁 ChromaDB Path: /Users/user/.minerva/chromadb
🔢 Default Max Results: 5

📚 Available Collections: 3

  • my-docs: 245 chunks
  • project-kb: 1,123 chunks
  • bear-notes: 89 chunks

============================================================
Server is running. Press Ctrl+C to stop.
============================================================
```

#### `list_available_collections(chromadb_path: str | Path) -> list[dict]`

Lists all collections in ChromaDB.

**Parameters**:
- `chromadb_path`: Path to ChromaDB directory

**Returns**: List of dictionaries with "name" and "count" keys

**Usage**:

```python
from minerva_common.server_manager import list_available_collections
from minerva_common.paths import CHROMADB_DIR

collections = list_available_collections(CHROMADB_DIR)
for col in collections:
    print(f"{col['name']}: {col['count']} chunks")
```

#### `display_server_info(config: dict, collections: list[dict]) -> None`

Displays formatted server information to stderr.

**Parameters**:
- `config`: Server configuration dictionary
- `collections`: List of collection info from `list_available_collections()`

**Behavior**:
- Outputs to stderr (so it doesn't interfere with MCP stdio protocol)
- Shows ChromaDB path, max results, server URL (if HTTP), and collection list

---

### collection_ops.py

**Purpose**: ChromaDB collection operations.

**Functions**:

#### `list_chromadb_collections(chromadb_path: str | Path) -> list[dict]`

Lists all collections in ChromaDB.

**Parameters**:
- `chromadb_path`: Path to ChromaDB directory

**Returns**: List of dictionaries with "name" and "count" keys

**Behavior**:
- Returns empty list if ChromaDB directory doesn't exist
- Returns empty list on any error
- Never raises exceptions

**Usage**:

```python
from minerva_common.collection_ops import list_chromadb_collections
from minerva_common.paths import CHROMADB_DIR

collections = list_chromadb_collections(CHROMADB_DIR)
print(f"Found {len(collections)} collections")
```

#### `remove_chromadb_collection(chromadb_path: str | Path, collection_name: str) -> bool`

Removes a collection from ChromaDB.

**Parameters**:
- `chromadb_path`: Path to ChromaDB directory
- `collection_name`: Name of collection to remove

**Returns**: `True` if successfully removed, `False` otherwise

**Behavior**:
- Returns `False` if ChromaDB directory doesn't exist
- Returns `False` if collection doesn't exist
- Returns `False` on any error
- Never raises exceptions

**Usage**:

```python
from minerva_common.collection_ops import remove_chromadb_collection
from minerva_common.paths import CHROMADB_DIR

success = remove_chromadb_collection(CHROMADB_DIR, "my-docs")
if success:
    print("✓ Collection removed from ChromaDB")
else:
    print("✗ Failed to remove collection")
```

#### `get_collection_count(chromadb_path: str | Path, collection_name: str) -> int | None`

Gets the chunk count for a collection.

**Parameters**:
- `chromadb_path`: Path to ChromaDB directory
- `collection_name`: Name of collection

**Returns**: Chunk count (int) or `None` if collection doesn't exist

**Usage**:

```python
from minerva_common.collection_ops import get_collection_count
from minerva_common.paths import CHROMADB_DIR

count = get_collection_count(CHROMADB_DIR, "my-docs")
if count is not None:
    print(f"Collection has {count:,} chunks")
else:
    print("Collection not found")
```

---

### collision.py

**Purpose**: Detect collection name collisions across tools.

**Functions**:

#### `check_collection_exists(collection_name: str, chromadb_path: str | Path | None = None) -> tuple[bool, str | None]`

Checks if a collection exists in ChromaDB and identifies its owner.

**Parameters**:
- `collection_name`: Collection name to check
- `chromadb_path`: Path to ChromaDB (optional, defaults to `CHROMADB_DIR`)

**Returns**: `(exists: bool, owner: str | None)`
- `exists=True` if collection found in ChromaDB
- `owner` is app name ("minerva-kb", "minerva-doc") or `None` if unmanaged

**Usage**:

```python
from minerva_common.collision import check_collection_exists

exists, owner = check_collection_exists("my-docs")

if not exists:
    print("✓ Name available")
elif owner:
    print(f"✗ Collection already exists, owned by {owner}")
else:
    print("✗ Collection exists but is unmanaged")
```

**Example Flow**:

```python
# User tries to add collection named "my-docs" with minerva-doc

exists, owner = check_collection_exists("my-docs")

if exists and owner == "minerva-kb":
    print("Error: Collection 'my-docs' already exists, managed by minerva-kb")
    print("Use 'minerva-kb list' to see all minerva-kb collections")
    print("Use 'minerva-kb remove my-docs' to remove it")
    return 1
```

#### `find_collection_owner(collection_name: str) -> str | None`

Finds which app owns a collection.

**Parameters**:
- `collection_name`: Collection name to check

**Returns**: App name ("minerva-kb", "minerva-doc") or `None` if not found

**Behavior**:
- Checks `~/.minerva/apps/minerva-kb/collections.json`
- Checks `~/.minerva/apps/minerva-doc/collections.json`
- Returns first match
- Returns `None` if not found in any registry

#### `check_registry_owner(collection_name: str, app_name: str) -> str | None` (Internal)

Checks if a collection is in a specific app's registry.

**Parameters**:
- `collection_name`: Collection name
- `app_name`: App name ("minerva-kb", "minerva-doc")

**Returns**: `app_name` if found, `None` otherwise

---

## Integration Examples

### How minerva-kb Uses minerva-common

```python
# tools/minerva-kb/src/minerva_kb/commands/add.py

from minerva_common.collision import check_collection_exists
from minerva_common.config_builder import build_index_config, save_index_config
from minerva_common.description_generator import prompt_for_description
from minerva_common.init import ensure_shared_dirs
from minerva_common.minerva_runner import run_index
from minerva_common.paths import CHROMADB_DIR
from minerva_common.provider_setup import select_provider_interactive
from minerva_common.registry import Registry

def execute_add(repo_path: str) -> int:
    # 1. Collision detection
    collection_name = sanitize_name(repo_path)
    exists, owner = check_collection_exists(collection_name)
    if exists:
        display_collision_error(collection_name, owner)
        return 1

    # 2. Ensure shared infrastructure
    ensure_shared_dirs()

    # 3. Provider selection
    provider_config = select_provider_interactive()

    # 4. Description generation
    description = prompt_for_description(json_file, provider_config)

    # 5. Build index config
    config = build_index_config(
        collection_name=collection_name,
        json_file=str(json_file),
        chromadb_path=str(CHROMADB_DIR),
        provider=provider_config,
        description=description,
    )

    # 6. Index with minerva
    temp_config = Path(f"/tmp/minerva-kb-{collection_name}.json")
    save_index_config(config, temp_config)

    success, _ = run_index(temp_config, verbose=True)
    if not success:
        return 1

    # 7. Register collection
    registry = Registry(KB_REGISTRY_PATH)
    registry.add_collection(collection_name, {
        "repo_path": str(repo_path),
        "json_file": str(json_file),
        "provider": provider_config,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    })

    print(f"✓ Collection '{collection_name}' created successfully")
    return 0
```

### How minerva-doc Uses minerva-common

```python
# tools/minerva-doc/src/minerva_doc/commands/add.py

from minerva_common.collision import check_collection_exists
from minerva_common.config_builder import build_index_config, save_index_config
from minerva_common.description_generator import prompt_for_description
from minerva_common.init import ensure_shared_dirs
from minerva_common.minerva_runner import run_validate, run_index
from minerva_common.paths import CHROMADB_DIR
from minerva_common.provider_setup import select_provider_interactive
from minerva_common.registry import Registry

def execute_add(json_file: str, collection_name: str) -> int:
    # 1. Validate JSON
    success, output = run_validate(json_file)
    if not success:
        print(f"✗ Validation failed:\n{output}")
        return 1

    # 2. Collision detection
    exists, owner = check_collection_exists(collection_name)
    if exists:
        display_collision_error(collection_name, owner)
        return 1

    # 3. Ensure shared infrastructure
    ensure_shared_dirs()

    # 4. Provider selection
    provider_config = select_provider_interactive()

    # 5. Description generation
    description = prompt_for_description(json_file, provider_config)

    # 6. Build index config
    config = build_index_config(
        collection_name=collection_name,
        json_file=str(json_file),
        chromadb_path=str(CHROMADB_DIR),
        provider=provider_config,
        description=description,
    )

    # 7. Index with minerva
    temp_config = Path(f"/tmp/minerva-doc-{collection_name}.json")
    save_index_config(config, temp_config)

    success, _ = run_index(temp_config, verbose=True)
    if not success:
        return 1

    # 8. Register collection
    registry = Registry(DOC_REGISTRY_PATH)
    registry.add_collection(collection_name, {
        "json_file": str(json_file),
        "provider": provider_config,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    })

    print(f"✓ Collection '{collection_name}' created successfully")
    return 0
```

---

## Direct Usage Examples

### Example 1: Validate JSON File

```python
from minerva_common.minerva_runner import run_validate

json_file = "/path/to/notes.json"

print(f"Validating {json_file}...")
success, output = run_validate(json_file)

if success:
    print("✓ Validation passed")
else:
    print(f"✗ Validation failed:\n{output}")
```

### Example 2: Build and Save Index Config

```python
from pathlib import Path
from minerva_common.config_builder import build_index_config, save_index_config
from minerva_common.paths import CHROMADB_DIR

provider = {
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
}

config = build_index_config(
    collection_name="test-collection",
    json_file="/path/to/notes.json",
    chromadb_path=CHROMADB_DIR,
    provider=provider,
    description="Test collection",
    chunk_size=1200
)

config_path = Path("/tmp/test-config.json")
save_index_config(config, config_path)

print(f"✓ Config saved to {config_path}")
```

### Example 3: Index a Collection

```python
from pathlib import Path
from minerva_common.minerva_runner import run_index
from minerva_common.config_builder import build_index_config, save_index_config
from minerva_common.paths import CHROMADB_DIR

# Build config
config = build_index_config(
    collection_name="my-docs",
    json_file="/path/to/docs.json",
    chromadb_path=CHROMADB_DIR,
    provider={
        "provider_type": "ollama",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "base_url": "http://localhost:11434"
    },
    description="My documentation"
)

# Save config
config_path = Path("/tmp/index-config.json")
save_index_config(config, config_path)

# Run indexing
print("Starting indexing...")
success, output = run_index(config_path, verbose=True)

if success:
    print("✓ Indexing completed successfully")
else:
    print(f"✗ Indexing failed:\n{output}")
```

### Example 4: Manage Registry

```python
from pathlib import Path
from minerva_common.registry import Registry

registry_path = Path("~/.minerva/apps/my-app/collections.json").expanduser()
registry = Registry(registry_path)

# Add collection
registry.add_collection("my-docs", {
    "json_file": "/path/to/docs.json",
    "description": "My documentation",
    "created_at": "2025-12-15T10:00:00Z"
})

# List collections
collections = registry.list_collections()
for col in collections:
    print(f"{col['name']}: {col.get('description', 'No description')}")

# Get specific collection
metadata = registry.get_collection("my-docs")
if metadata:
    print(f"Found: {metadata}")

# Update collection
registry.update_collection("my-docs", {
    "indexed_at": "2025-12-15T10:05:00Z"
})

# Remove collection
registry.remove_collection("my-docs")
```

### Example 5: Interactive Provider Selection

```python
from minerva_common.provider_setup import select_provider_interactive

print("Select your AI provider:")
provider_config = select_provider_interactive()

print("\nYou selected:")
print(f"  Provider: {provider_config['provider_type']}")
print(f"  Embedding: {provider_config['embedding_model']}")
print(f"  LLM: {provider_config['llm_model']}")
if "base_url" in provider_config:
    print(f"  Base URL: {provider_config['base_url']}")
```

### Example 6: Check Collection Collisions

```python
from minerva_common.collision import check_collection_exists

collection_name = "my-docs"

exists, owner = check_collection_exists(collection_name)

if not exists:
    print(f"✓ '{collection_name}' is available")
elif owner:
    print(f"✗ '{collection_name}' already exists, owned by {owner}")
    if owner == "minerva-kb":
        print("  Use 'minerva-kb list' to see all collections")
        print(f"  Use 'minerva-kb remove {collection_name}' to remove it")
    elif owner == "minerva-doc":
        print("  Use 'minerva-doc list' to see all collections")
        print(f"  Use 'minerva-doc remove {collection_name}' to remove it")
else:
    print(f"✗ '{collection_name}' exists but is unmanaged")
    print("  The collection is in ChromaDB but not tracked by any tool")
```

### Example 7: Start MCP Server

```python
from minerva_common.server_manager import start_server
from minerva_common.paths import SERVER_CONFIG_PATH, CHROMADB_DIR
from minerva_common.init import ensure_server_config

# Ensure server config exists
config_path, created = ensure_server_config()
if created:
    print(f"✓ Created server config: {config_path}")

# Start server
print("Starting MCP server...")
process = start_server(SERVER_CONFIG_PATH, CHROMADB_DIR)

print(f"Server started with PID: {process.pid}")

try:
    process.wait()
except KeyboardInterrupt:
    print("\n✓ Server stopped")
```

### Example 8: Generate Collection Description

```python
from minerva_common.description_generator import generate_description_from_records

provider = {
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
}

print("Generating description...")
description = generate_description_from_records(
    "/path/to/notes.json",
    provider,
    max_samples=10
)

print(f"Generated: {description}")
```

---

## Testing

minerva-common includes comprehensive unit tests for all modules:

```bash
cd tools/minerva-common

# Run all tests
pytest

# Run with coverage
pytest --cov=minerva_common --cov-report=html

# Run specific test file
pytest tests/test_registry.py -v
```

Test files:
- `test_init.py` - Tests for directory initialization
- `test_registry.py` - Tests for registry operations
- `test_config_builder.py` - Tests for config building
- `test_minerva_runner.py` - Tests for CLI wrappers
- `test_provider_setup.py` - Tests for provider selection
- `test_description_generator.py` - Tests for AI description generation
- `test_server_manager.py` - Tests for server management
- `test_collection_ops.py` - Tests for ChromaDB operations
- `test_collision.py` - Tests for collision detection

---

## Installation

minerva-common is installed as a dependency of minerva-kb and minerva-doc using `pipx inject`:

```bash
# Install minerva-kb (which needs minerva-common)
pipx install tools/minerva-kb
pipx inject minerva-kb tools/minerva-common

# Install minerva-doc (which needs minerva-common)
pipx install tools/minerva-doc
pipx inject minerva-doc tools/minerva-common
```

For development:

```bash
cd tools/minerva-common
pip install -e .
```

---

## Design Rationale

### Why a Shared Library?

**Problem**: minerva-kb and minerva-doc had significant code duplication:
- Same directory structure (`~/.minerva/`)
- Same registry format
- Same provider selection flow
- Same config building logic
- Same minerva CLI wrappers

**Solution**: Extract shared code into `minerva-common` library:
- Single source of truth for paths and infrastructure
- Eliminates duplication
- Easier to maintain and test
- Both tools stay small and focused

### Why pipx inject?

**Requirement**: Both tools need minerva-common as a dependency, but it's not published to PyPI.

**Solution**: Use `pipx inject` to bundle minerva-common into each tool's isolated environment:

```bash
pipx install tools/minerva-kb
pipx inject minerva-kb tools/minerva-common
```

This approach:
- Keeps tools isolated (pipx principle)
- Allows local dependency (no PyPI publishing needed)
- Works with relative paths during installation
- Maintains clean separation between tools

### Why No Docstrings?

Following Uncle Bob's Clean Code principles:
- Function names should be self-documenting
- Types and signatures provide clarity
- External documentation (this file) provides comprehensive reference
- Code remains clean and readable without docstring clutter

Example:

```python
# Clear from signature what this does
def build_index_config(
    collection_name: str,
    json_file: str | Path,
    chromadb_path: str | Path,
    provider: dict,
    description: str = "",
    chunk_size: int = 1200,
    force_recreate: bool = False,
    skip_ai_validation: bool = False,
) -> dict:
    # Implementation
```

---

## Contributing

When adding new shared functionality:

1. **Add to minerva-common** if it's used by both minerva-kb and minerva-doc
2. **Keep it focused**: Only infrastructure and truly shared logic
3. **Write tests**: All modules should have unit tests
4. **Update this doc**: Add API reference and examples
5. **Follow conventions**: No docstrings, atomic writes, proper permissions

When modifying existing functions:

1. **Check both tools**: Ensure changes work for minerva-kb and minerva-doc
2. **Update tests**: Keep test coverage high
3. **Update docs**: Keep this file in sync with code

---

## Summary

minerva-common is the foundation of Minerva's orchestrator tools, providing:

- **Unified infrastructure** (`~/.minerva/` directory structure)
- **Registry management** (collection metadata tracking)
- **Provider setup** (interactive AI provider selection)
- **Config builders** (minerva index config generation)
- **CLI wrappers** (minerva validate/index/serve commands)
- **Collision detection** (cross-tool collection name conflicts)
- **Server management** (MCP server startup and info display)

By centralizing shared code, minerva-common enables both minerva-kb and minerva-doc to remain small, focused, and maintainable while providing consistent user experiences across tools.
