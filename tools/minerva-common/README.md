# minerva-common

Shared library for Minerva orchestrator tools (`minerva-kb` and `minerva-doc`).

## Overview

`minerva-common` provides reusable infrastructure for building Minerva orchestrator tools. It handles:

- **Shared paths**: Standardized locations (`~/.minerva/`) for ChromaDB, configs, and app data
- **Initialization**: Creating directories, default configs, and managing permissions
- **Registry management**: Tracking collections and their metadata
- **Config building**: Generating index configurations for the core `minerva` CLI
- **Minerva runner**: Subprocess wrappers for `minerva validate`, `index`, and `serve`
- **Provider setup**: Interactive AI provider selection and validation
- **Description generation**: AI-powered collection description generation
- **Server management**: Starting and managing the MCP server
- **Collection operations**: ChromaDB query and management utilities
- **Collision detection**: Preventing name conflicts across tools

## Installation

**End users do not install this package directly.** It is automatically installed as a dependency when you install `minerva-kb` or `minerva-doc`:

```bash
# Installing minerva-kb automatically installs minerva-common
pipx install tools/minerva-kb

# Installing minerva-doc automatically installs minerva-common
pipx install tools/minerva-doc
```

**For development only:**

```bash
pipx install --editable tools/minerva-common
```

## Usage

This is an internal shared library consumed by `minerva-kb` and `minerva-doc`. It is not intended to be used directly by end users.

Example usage in a tool:

```python
from minerva_common import paths, init, registry

# Ensure shared infrastructure exists
init.ensure_shared_dirs()
config_path, created = init.ensure_server_config()

# Work with collection registry
reg = registry.Registry(paths.APPS_DIR / "my-app" / "collections.json")
reg.add_collection("my-collection", {"description": "..."})
```

## Modules

- `paths.py` - Shared path constants
- `init.py` - Infrastructure initialization
- `registry.py` - Collection registry management
- `config_builder.py` - Index config generation
- `minerva_runner.py` - Subprocess wrapper for minerva CLI
- `provider_setup.py` - AI provider selection
- `description_generator.py` - AI description generation
- `server_manager.py` - MCP server management
- `collection_ops.py` - ChromaDB operations
- `collision.py` - Collection name collision detection

## Testing

```bash
pytest tools/minerva-common/tests
```

## License

MIT
