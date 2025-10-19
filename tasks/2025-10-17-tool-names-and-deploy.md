# Minervium: Tool Names and Deployment Strategy

**Document Version:** 1.0
**Date:** 2025-10-16
**Status:** Draft - Iterative Design Phase

---

## Executive Summary

This document outlines the architectural refactoring of the "search-markdown-notes" project into **Minervium**, a personal knowledge management RAG (Retrieval-Augmented Generation) system that accepts standardized JSON notes from any source.

### Key Decisions
- **Brand Name:** Minervium
- **Architecture:** Core RAG/MCP tool + independent extractor examples
- **Core Components:** RAG pipeline (`index`) + MCP server (`serve`) + validation (`validate`)
- **Extractors:** Standalone tools (not plugins) that output Minervium-compatible JSON
- **Deployment:** Monorepo with core + example extractors

---

## Current State Analysis

### Current Project Structure

```
search-markdown-notes/
├── bear-notes-extractor/          # Bear backup parser
│   ├── cli.py                     # Entry point
│   ├── bear_parser.py             # Core logic
│   └── setup.py                   # Package: "bear-notes-extractor"
│
├── markdown-notes-cag-data-creator/  # RAG pipeline
│   ├── full_pipeline.py           # Entry point
│   ├── chunk_creator.py
│   ├── embedding.py
│   ├── storage.py
│   ├── json_loader.py             # Validates JSON contract
│   └── setup.py                   # Package: "markdown-notes-cag-data-creator"
│
├── markdown-notes-mcp-server/     # MCP server
│   ├── server.py                  # Entry point
│   ├── search_tools.py
│   ├── collection_discovery.py
│   ├── ai_provider.py
│   └── config.py
│
├── zim-articles-parser/           # Zim wiki extractor
│   └── zim_cli.py
│
├── markdown-books-extractor/      # Books extractor
│   └── book_parser.py
│
├── chromadb_data/                 # Vector database
├── configs/                       # JSON configs
└── test-data/
```

### Current Naming Inconsistencies

| Component | Directory Prefix | Entry Point | Console Command |
|-----------|------------------|-------------|-----------------|
| Bear extractor | `bear-notes-` | `cli.py` | `extract-bear-notes` |
| RAG pipeline | `markdown-notes-` | `full_pipeline.py` | `create-cag-from-markdown-notes` |
| MCP server | `markdown-notes-` | `server.py` | (none) |
| Zim extractor | `zim-articles-` | `zim_cli.py` | (none) |

**Problems:**
- Inconsistent prefixes (`bear-notes-`, `markdown-notes-`, `zim-articles-`)
- Entry points don't reflect functionality (`cli.py`, `full_pipeline.py`)
- Console commands are verbose and unmemorable
- No unified brand identity

---

## Target Architecture: Minervium

### Design Philosophy

**Core Principle:** Minervium is a RAG system that accepts standardized JSON notes. How you create those notes is up to you - use the example extractors, write your own, or generate them however you like.

**JSON Schema:** All notes ingested by Minervium must conform to this format:
```json
[
  {
    "title": "Note title",
    "markdown": "Full markdown content",
    "size": 1234,
    "modificationDate": "2025-10-16T10:30:00Z"
  }
]
```

This schema is the **contract** between any data source and Minervium - validated by `json_loader.py`.

**Extractors are Independent:** The example extractors in `extractors/` are standalone tools, not plugins. They're provided as reference implementations showing how to produce valid JSON. Users can build extractors in any language (Python, Go, Rust, JavaScript, etc.).

### Package Structure

#### **Core Package: `minervium`** (mandatory)

```
minervium/                           # Main package directory
├── minervium/                       # Python package
│   ├── __init__.py
│   ├── __main__.py                  # Enables: python -m minervium
│   ├── cli.py                       # Main CLI entry point
│   │
│   ├── commands/                    # CLI command implementations
│   │   ├── __init__.py
│   │   ├── index.py                 # Index command (was: full_pipeline.py)
│   │   ├── serve.py                 # Serve command (was: server.py)
│   │   ├── peek.py                  # Peek command (inspect collections)
│   │   └── validate.py              # Validate command (check JSON schema)
│   │
│   ├── indexing/                    # RAG pipeline (core functionality)
│   │   ├── __init__.py
│   │   ├── chunking.py              # Was: chunk_creator.py
│   │   ├── embeddings.py            # Was: embedding.py
│   │   ├── storage.py               # Was: storage.py
│   │   └── json_loader.py           # JSON schema validation
│   │
│   ├── server/                      # MCP server (core functionality)
│   │   ├── __init__.py
│   │   ├── mcp_server.py            # Was: server.py
│   │   ├── search_tools.py
│   │   ├── collection_discovery.py
│   │   ├── context_retrieval.py
│   │   └── startup_validation.py
│   │
│   └── common/                      # Shared utilities
│       ├── __init__.py
│       ├── ai_provider.py
│       ├── config.py
│       ├── logger.py
│       └── schemas.py               # NoteSchema definition
│
├── setup.py                         # Package configuration
├── README.md                        # Main documentation
├── CLAUDE.md                        # AI assistant guidance
└── pyproject.toml                   # Modern Python packaging (optional)
```

#### **Extractor Examples** (optional, independent tools)

```
extractors/
├── bear-notes-extractor/            # Bear backup extractor
│   ├── bear_extractor/
│   │   ├── __init__.py
│   │   ├── cli.py                   # CLI entry point
│   │   └── parser.py                # Extraction logic
│   ├── setup.py                     # Package: bear-notes-extractor
│   ├── README.md                    # Usage instructions
│   └── tests/
│
├── zim-extractor/                   # ZIM articles extractor
│   ├── zim_extractor/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   └── parser.py
│   ├── setup.py                     # Package: zim-extractor
│   ├── README.md
│   └── tests/
│
├── markdown-books-extractor/        # Markdown books extractor
│   ├── markdown_books/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   └── parser.py
│   ├── setup.py                     # Package: markdown-books-extractor
│   ├── README.md
│   └── tests/
│
└── README.md                        # "How to build your own extractor"
```

---

## Command Line Interface Design

### Unified CLI: `minervium`

All functionality accessed through single `minervium` command with subcommands.

#### Command Structure

```bash
minervium [OPTIONS] COMMAND [ARGS]...

Commands:
  index       Create vector embeddings and ChromaDB index from JSON notes
  serve       Start MCP server for AI agent queries
  peek        Inspect ChromaDB collection metadata
  validate    Validate JSON notes against Minervium schema
```

### Command Reference

#### 1. `minervium index`

**Purpose:** Create vector embeddings and ChromaDB collection from JSON notes.

**Usage:**
```bash
minervium index [OPTIONS] NOTES_JSON

Arguments:
  NOTES_JSON              Path to JSON file with notes

Options:
  -c, --config PATH       Configuration file (required)
  -v, --verbose           Enable verbose output
  --dry-run               Validate config without processing
  --help                  Show this message and exit
```

**Examples:**
```bash
# Index notes with Ollama provider
minervium index notes.json --config configs/ollama.json

# Verbose mode shows embedding progress
minervium index notes.json --config configs/openai.json --verbose

# Dry run to validate config
minervium index notes.json --config configs/gemini.json --dry-run
```

**Implementation Notes:**
- Was: `full_pipeline.py`
- Validates JSON schema before processing
- Shows provider initialization, chunking, embedding, storage progress
- Supports multiple AI providers (Ollama, OpenAI, Gemini) via config

#### 2. `minervium serve`

**Purpose:** Start MCP server for AI agent queries (Claude Desktop integration).

**Usage:**
```bash
minervium serve [OPTIONS]

Options:
  -c, --config PATH       Server configuration file
  --chromadb PATH         ChromaDB database path (default: ./chromadb_data)
  --help                  Show this message and exit
```

**Examples:**
```bash
# Start server with default settings
minervium serve

# Custom ChromaDB path
minervium serve --chromadb /path/to/chromadb_data

# Custom config
minervium serve --config server-config.json
```

**Implementation Notes:**
- Was: `markdown-notes-mcp-server/server.py`
- Runs in stdio mode for MCP protocol
- Auto-discovers collections on startup
- Validates AI provider availability for each collection
- Logs collection status (available/unavailable)

#### 3. `minervium peek`

**Purpose:** Inspect ChromaDB collection metadata and statistics.

**Usage:**
```bash
minervium peek [OPTIONS] COLLECTION_NAME

Arguments:
  COLLECTION_NAME         Name of collection to inspect

Options:
  --chromadb PATH         ChromaDB database path (default: ./chromadb_data)
  --format [table|json]   Output format (default: table)
  --help                  Show this message and exit
```

**Examples:**
```bash
# Inspect collection
minervium peek bear_notes

# Custom ChromaDB path
minervium peek bear_notes --chromadb /path/to/chromadb_data

# JSON output for scripting
minervium peek bear_notes --format json
```

**Implementation Notes:**
- New utility (consolidates functionality from test-files/chroma-peek)
- Shows: collection name, document count, metadata, provider info, embedding dimensions
- Table output uses rich/tabulate for formatting

#### 4. `minervium validate`

**Purpose:** Validate JSON notes file against Minervium schema.

**Usage:**
```bash
minervium validate [OPTIONS] NOTES_JSON

Arguments:
  NOTES_JSON              Path to JSON file to validate

Options:
  -v, --verbose           Show detailed validation errors
  --help                  Show this message and exit
```

**Examples:**
```bash
# Validate notes file
minervium validate notes.json

# Verbose mode shows detailed schema errors
minervium validate notes.json --verbose
```

**Example Output:**
```bash
$ minervium validate notes.json

✓ Valid JSON format
✓ Array of notes
✓ All notes have required fields (title, markdown, size, modificationDate)
✓ Field types correct
✓ 142 notes validated successfully

Schema compliant! Ready for indexing.
```

**Implementation Notes:**
- New command to help extractor developers
- Uses same validation logic as `minervium index`
- Provides clear error messages with field/note location
- Exit code 0 for valid, 1 for invalid

---

## Extractor Architecture

### Design Philosophy

Extractors are **standalone tools**, not plugins integrated into Minervium core. They are independent programs that output JSON conforming to Minervium's schema.

**Key Principles:**
- **Language agnostic:** Build extractors in Python, Go, Rust, JavaScript, or any language
- **No coupling:** Extractors don't import Minervium code
- **Simple contract:** Just output valid JSON to stdout or file
- **Independent versioning:** Extractors evolve separately from Minervium core

### Extractor Interface (Conceptual)

There is NO base class or plugin system. Extractors simply need to:

1. **Accept input** (file path, directory, etc.)
2. **Process data** (parse, extract, transform)
3. **Output JSON** matching this schema:

```json
[
  {
    "title": "string",
    "markdown": "string",
    "size": integer,
    "modificationDate": "ISO 8601 UTC timestamp string"
  }
]
```

4. **Validate output** (optional but recommended - use `minervium validate`)

### Example Extractor Implementation (Python)

**File:** `extractors/bear-notes-extractor/bear_extractor/cli.py`

```python
#!/usr/bin/env python3
"""
Bear Notes Extractor - Standalone tool to extract notes from Bear backups.
Outputs JSON compatible with Minervium RAG system.
"""
import json
import argparse
from pathlib import Path
from .parser import parse_bear_backup  # Core extraction logic

def main():
    parser = argparse.ArgumentParser(
        description="Extract notes from Bear backup files to Minervium JSON format"
    )
    parser.add_argument("input", help="Path to .bear2bk file")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Extract notes using parser
    notes = parse_bear_backup(args.input, verbose=args.verbose)

    # Output JSON
    output_json = json.dumps(notes, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json, encoding='utf-8')
        if args.verbose:
            print(f"✓ Extracted {len(notes)} notes to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()
```

**File:** `extractors/bear-notes-extractor/setup.py`

```python
from setuptools import setup, find_packages

setup(
    name="bear-notes-extractor",
    version="1.0.0",
    author="Michele",
    description="Extract notes from Bear app backups to Minervium JSON format",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",

    packages=find_packages(),

    # No dependency on Minervium core!
    install_requires=[
        # Add any dependencies needed for Bear parsing only
    ],

    # Install CLI command
    entry_points={
        "console_scripts": [
            "bear-extractor=bear_extractor.cli:main",
        ],
    },

    python_requires=">=3.8",

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Text Processing",
    ],
)
```

**Usage:**
```bash
# Install extractor
pip install bear-notes-extractor

# Extract to file
bear-extractor "backup.bear2bk" -o notes.json

# Extract to stdout (pipe to other tools)
bear-extractor "backup.bear2bk" | jq '.[] | .title'

# Validate output with Minervium
bear-extractor "backup.bear2bk" -o notes.json
minervium validate notes.json
```

---

## User Experience Scenarios

### Scenario 1: Core-Only User (Custom JSON Source)

**User has:** Custom scripts that generate JSON in Minervium format.

```bash
# Install only core
pip install minervium

# User creates notes.json however they want
# (manual creation, custom script, export from another tool, etc.)

# Validate JSON (optional)
minervium validate my-notes.json

# Index notes
minervium index my-notes.json --config ollama.json

# Start MCP server
minervium serve
```

**No extractors needed!** User brings their own JSON that conforms to schema.

### Scenario 2: Bear Notes User

**User has:** Bear notes backup file.

```bash
# Install core + Bear extractor
pip install minervium bear-notes-extractor

# Extract notes from Bear (using standalone extractor)
bear-extractor "Bear Notes 2025-10-16.bear2bk" -o notes.json

# Validate (optional but recommended)
minervium validate notes.json

# Index extracted notes
minervium index notes.json --config ollama.json

# Start MCP server
minervium serve
```

**Two independent tools:** `bear-extractor` creates JSON, `minervium` processes it.

### Scenario 3: Multi-Source User

**User has:** Bear notes + Wikipedia Zim + Markdown books.

```bash
# Install core + all extractors
pip install minervium
pip install bear-notes-extractor zim-extractor markdown-books-extractor

# Extract from multiple sources (each extractor is independent)
bear-extractor bear-backup.bear2bk -o bear-notes.json
zim-extractor wikipedia.zim -o wiki-articles.json
markdown-books-extractor books/ -o books.json

# Validate all (optional)
minervium validate bear-notes.json
minervium validate wiki-articles.json
minervium validate books.json

# Index each source into separate collections
minervium index bear-notes.json --config configs/bear-ollama.json
minervium index wiki-articles.json --config configs/wiki-openai.json
minervium index books.json --config configs/books-gemini.json

# Serve all collections
minervium serve
# MCP server discovers all 3 collections automatically
```

**Fully decoupled:** Extractors don't know about Minervium, Minervium doesn't know about extractors.

### Scenario 4: Custom Extractor Developer

**User wants:** Extract Notion workspace exports.

**Step 1: Copy an example extractor as template**

```bash
# Clone Minervium repo to access examples
git clone https://github.com/user/minervium
cd minervium/extractors

# Copy bear extractor as template
cp -r bear-notes-extractor notion-extractor
cd notion-extractor
```

**Step 2: Modify for your data source**

```python
# notion_extractor/cli.py
#!/usr/bin/env python3
import json
import argparse
from pathlib import Path
from .parser import parse_notion_export  # Your custom parsing logic

def main():
    parser = argparse.ArgumentParser(
        description="Extract notes from Notion exports to Minervium JSON format"
    )
    parser.add_argument("input", help="Path to Notion export (.zip)")
    parser.add_argument("-o", "--output", help="Output JSON file")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    # Extract notes (implement this in parser.py)
    notes = parse_notion_export(args.input, verbose=args.verbose)

    # Output JSON in Minervium format
    output_json = json.dumps(notes, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json, encoding='utf-8')
        if args.verbose:
            print(f"✓ Extracted {len(notes)} notes to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()
```

```python
# notion_extractor/parser.py
def parse_notion_export(zip_path: str, verbose: bool = False) -> list:
    """
    Parse Notion workspace export and return Minervium-compatible JSON.

    Returns:
        List of dicts with keys: title, markdown, size, modificationDate
    """
    notes = []

    # Your custom extraction logic here
    # Parse Notion's markdown files from the ZIP
    # Convert to Minervium schema

    return notes
```

**Step 3: Update package config**

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="notion-extractor",
    version="1.0.0",
    packages=find_packages(),

    # No Minervium dependency!
    install_requires=[
        # Only dependencies needed for Notion parsing
    ],

    entry_points={
        "console_scripts": [
            "notion-extractor=notion_extractor.cli:main",
        ],
    },
)
```

**Step 4: Test and use**

```bash
# Install locally
pip install -e .

# Test extraction
notion-extractor workspace-export.zip -o notes.json

# Validate output with Minervium
minervium validate notes.json

# If valid, index it!
minervium index notes.json --config ollama.json
```

**You can build extractors in ANY language:**
- **Python**: Use example extractors as templates
- **Go**: Output JSON to stdout, pipe to file
- **Rust**: Blazing fast extraction, JSON serialization
- **JavaScript/Node**: Perfect for parsing web exports
- **Bash script**: Simple text processing with jq

---

## Migration Roadmap

### Phase 1: Core Reorganization

**Goal:** Create unified Minervium core package structure.

**Tasks:**

1. **Create directory structure:**
   ```bash
   mkdir -p minervium/{commands,indexing,server,common,plugins}
   touch minervium/{__init__.py,__main__.py,cli.py}
   touch minervium/{commands,indexing,server,common,plugins}/__init__.py
   ```

2. **Migrate indexing components:**
   - `markdown-notes-cag-data-creator/chunk_creator.py` → `minervium/indexing/chunking.py`
   - `markdown-notes-cag-data-creator/embedding.py` → `minervium/indexing/embeddings.py`
   - `markdown-notes-cag-data-creator/storage.py` → `minervium/indexing/storage.py`
   - `markdown-notes-cag-data-creator/json_loader.py` → `minervium/indexing/json_loader.py`

3. **Migrate server components:**
   - `markdown-notes-mcp-server/server.py` → `minervium/server/mcp_server.py`
   - `markdown-notes-mcp-server/search_tools.py` → `minervium/server/search_tools.py`
   - `markdown-notes-mcp-server/collection_discovery.py` → `minervium/server/collection_discovery.py`
   - `markdown-notes-mcp-server/context_retrieval.py` → `minervium/server/context_retrieval.py`
   - `markdown-notes-mcp-server/startup_validation.py` → `minervium/server/startup_validation.py`

4. **Migrate common components:**
   - `markdown-notes-mcp-server/ai_provider.py` → `minervium/common/ai_provider.py`
   - `markdown-notes-mcp-server/config.py` → `minervium/common/config.py`
   - `markdown-notes-mcp-server/console_logger.py` → `minervium/common/logger.py`
   - Create: `minervium/common/schemas.py` (define NoteSchema)

5. **Create CLI:**
   - Create: `minervium/cli.py` (main CLI with Click/Typer)
   - Create: `minervium/commands/index.py` (wrapper for full_pipeline logic)
   - Create: `minervium/commands/serve.py` (wrapper for mcp_server logic)
   - Create: `minervium/commands/peek.py` (ChromaDB inspector)
   - Create: `minervium/commands/validate.py` (JSON schema validator)

6. **Update imports:**
   - Fix all import paths to use new `minervium.*` structure
   - Update cross-module references
   - Test import tree for circular dependencies

7. **Create unified setup.py:**
   - Consolidate dependencies from all old setup.py files
   - Define single entry point: `minervium = minervium.cli:main`
   - Configure package metadata

### Phase 2: Extractor Reorganization

**Goal:** Move extractors to standalone packages in `extractors/` directory.

**Tasks:**

1. **Create extractor directories:**
   ```bash
   mkdir -p extractors/{bear-notes-extractor,zim-extractor,markdown-books-extractor}
   ```

2. **Bear extractor:**
   - Create: `extractors/bear-notes-extractor/bear_extractor/{__init__.py,cli.py,parser.py}`
   - Copy: `bear-notes-extractor/bear_parser.py` → `parser.py`
   - Create: `cli.py` with standalone CLI (no Minervium imports)
   - Create: `setup.py` with console_scripts entry point: `bear-extractor`
   - Create: `README.md` with usage instructions

3. **Zim extractor:**
   - Create: `extractors/zim-extractor/zim_extractor/{__init__.py,cli.py,parser.py}`
   - Copy: `zim-articles-parser/zim_parser.py` → `parser.py`
   - Create: `cli.py` with standalone CLI
   - Create: `setup.py` with console_scripts entry point: `zim-extractor`
   - Create: `README.md` with usage instructions

4. **Books extractor:**
   - Create: `extractors/markdown-books-extractor/markdown_books/{__init__.py,cli.py,parser.py}`
   - Copy: `markdown-books-extractor/book_parser.py` → `parser.py`
   - Create: `cli.py` with standalone CLI
   - Create: `setup.py` with console_scripts entry point: `markdown-books-extractor`
   - Create: `README.md` with usage instructions

5. **Create extractor documentation:**
   - Create: `extractors/README.md` (overview of extractors, how to build your own)
   - Create: `docs/NOTE_SCHEMA.md` (JSON schema specification)
   - Create: `docs/EXTRACTOR_GUIDE.md` (step-by-step guide for building extractors)

6. **Test extractors independently:**
   - Install extractors: `pip install -e ./extractors/bear-notes-extractor`
   - Test CLI: `bear-extractor test.bear2bk -o test.json`
   - Validate: `minervium validate test.json`
   - Index: `minervium index test.json --config ollama.json`

### Phase 3: Documentation

**Goal:** Comprehensive documentation for core + extractor ecosystem.

**Tasks:**

1. **Main README:**
   - Overview of Minervium
   - Quick start guide
   - Installation instructions (core + extractors)
   - Basic usage examples
   - Architecture diagram showing separation of concerns
   - Link to extractor development guide

2. **Extractor Development Guide:**
   - `docs/EXTRACTOR_GUIDE.md`
   - Step-by-step extractor creation tutorial
   - JSON schema specification reference
   - Example extractors walkthrough
   - Multi-language examples (Python, Go, Rust, JavaScript)
   - Testing guidelines with `minervium validate`

3. **Schema Documentation:**
   - `docs/NOTE_SCHEMA.md`
   - Complete JSON schema specification
   - Field requirements and constraints
   - Validation rules
   - Example valid/invalid JSON

4. **CLAUDE.md update:**
   - Update with new directory structure
   - Update command examples (`minervium` commands only, extractors separate)
   - Add extractor development section
   - Update troubleshooting
   - Remove plugin system references

5. **CONFIGURATION_GUIDE.md update:**
   - Update paths to config files
   - Update command examples
   - Add multi-collection setup guide

6. **Individual extractor READMEs:**
   - Usage instructions
   - Supported file formats
   - Installation
   - Examples
   - No references to Minervium except output format

7. **Extractors overview:**
   - `extractors/README.md`
   - Overview of all official extractors
   - How to build your own
   - Link to extractor guide
   - Emphasize language-agnostic approach

### Phase 4: Testing & Validation

**Goal:** Ensure all functionality works after refactoring.

**Tasks:**

1. **Unit tests:**
   - JSON schema validation tests
   - CLI command tests
   - Import path validation
   - Schema enforcement

2. **Integration tests:**
   - End-to-end: extractor → validate → index → serve
   - Multi-source indexing
   - Extractor independence (no cross-dependencies)
   - Error handling

3. **Manual testing:**
   - Install from local packages
   - Test all CLI commands
   - Test with real data sources
   - Test MCP server integration with Claude Desktop

4. **Documentation validation:**
   - Verify all code examples work
   - Test installation instructions
   - Check links

### Phase 5: Deployment

**Goal:** Publish packages and make available to users.

**Tasks:**

1. **Repository structure:**
   - Decide: monorepo vs. multi-repo
   - **Recommendation:** Start with monorepo (easier to sync versions)
   - Structure:
     ```
     minervium/
     ├── core/              # Core package
     ├── plugins/
     │   ├── bear/
     │   ├── zim/
     │   └── books/
     ├── configs/           # Example configs
     ├── chromadb_data/     # Development DB
     └── docs/              # Documentation
     ```

2. **Version management:**
   - Core version: `1.0.0`
   - Plugin versions: `1.0.0` (sync with core initially)
   - Future: plugins can version independently

3. **PyPI publishing (optional):**
   - Register packages: `minervium`, `minervium-bear`, etc.
   - Create PyPI accounts / API tokens
   - Build distributions: `python setup.py sdist bdist_wheel`
   - Upload: `twine upload dist/*`
   - **Note:** Can defer PyPI publishing initially, use local installs

4. **GitHub releases:**
   - Tag version: `v1.0.0`
   - Create release notes
   - Attach source distributions

5. **Installation methods:**
   - **Development:** `pip install -e ./minervium`
   - **GitHub:** `pip install git+https://github.com/user/minervium.git`
   - **PyPI (future):** `pip install minervium`

---

## Repository Structure Options

### Option A: Monorepo (Recommended for Initial Release)

**Structure:**
```
minervium/
├── minervium/                       # Core Minervium package
│   ├── minervium/
│   ├── setup.py
│   ├── README.md
│   └── tests/
│
├── extractors/                      # Example extractors (standalone tools)
│   ├── bear-notes-extractor/
│   │   ├── bear_extractor/
│   │   ├── setup.py
│   │   ├── README.md
│   │   └── tests/
│   ├── zim-extractor/
│   │   ├── zim_extractor/
│   │   ├── setup.py
│   │   ├── README.md
│   │   └── tests/
│   ├── markdown-books-extractor/
│   │   ├── markdown_books/
│   │   ├── setup.py
│   │   ├── README.md
│   │   └── tests/
│   └── README.md                    # How to build extractors
│
├── configs/                         # Example configurations
│   ├── example-ollama.json
│   ├── example-openai.json
│   └── example-gemini.json
│
├── chromadb_data/                   # Development database
├── docs/                            # Comprehensive documentation
│   ├── architecture.md
│   ├── NOTE_SCHEMA.md               # JSON schema spec
│   ├── EXTRACTOR_GUIDE.md           # How to build extractors
│   └── api-reference.md
│
├── scripts/                         # Development scripts
│   ├── install-all.sh
│   └── test-all.sh
│
├── README.md                        # Main repository README
├── CLAUDE.md                        # AI assistant guidance
├── CONFIGURATION_GUIDE.md           # Config documentation
└── .gitignore
```

**Advantages:**
- Single repository to clone
- Easier to keep core + extractors in sync during development
- Simpler version management initially
- Example extractors easily accessible for users
- Easier to update schema across all extractors

**Disadvantages:**
- Larger repository size
- All extractors bundled together in one repo

### Option B: Multi-Repo

**Structure:**
```
minervium/                           # Core repository
bear-notes-extractor/                # Separate repo
zim-extractor/                       # Separate repo
markdown-books-extractor/            # Separate repo
```

**Advantages:**
- Cleaner separation of concerns
- Extractors can have independent release cycles
- Easier to grant per-extractor contributor access
- Smaller individual repos
- **Emphasizes independence** - extractors truly standalone

**Disadvantages:**
- Need to coordinate schema changes across repos
- Harder to update all extractors simultaneously
- More repositories to manage
- Users need to discover extractors separately

**Recommendation:** Start with **Option A (Monorepo)** for ease of development and providing examples. Extractors can be split later if community contributions grow.

---

## Package Publishing Strategy

### Option 1: Core Only (Recommended)

**Package:** `minervium` (core RAG/MCP system only)

**Installation:**
```bash
# Install core
pip install minervium

# Install extractors separately as needed
pip install bear-notes-extractor
pip install zim-extractor
pip install markdown-books-extractor
```

**Advantages:**
- Small, focused core package
- Users only install extractors they need
- Clear separation: core vs extractors
- Extractors evolve independently
- No coupling between core and extractors
- Aligns with "tool doesn't care how JSON was created" philosophy

**Disadvantages:**
- Requires separate installation steps
- Users need to know which extractors exist

### Option 2: Bundle with Official Extractors

**Packages:**
- `minervium` (core only)
- `minervium-all` (meta-package: core + all official extractors)

**Installation:**
```bash
# Core only
pip install minervium

# Everything (core + all official extractors)
pip install minervium-all
```

**Advantages:**
- Option for one-command install
- Still maintains package separation
- Users can choose minimal or full install

**Disadvantages:**
- Need to maintain meta-package
- Larger install size for `-all` variant

**Recommendation:** **Option 1** - Keeps core lightweight and emphasizes extractor independence. Users who want all extractors can install them explicitly.

---

## Brand Name Rationale

### Why "Minervium"?

**Etymology:**
- Derived from Minerva (Roman goddess of wisdom, strategic warfare, and crafts)
- Minerva is the Roman equivalent of Greek Athena
- "-ium" suffix suggests a substance/material (like titanium, chromium, uranium)

**Conceptual Fit:**
- **Wisdom personified:** Minerva is the goddess of wisdom and strategic knowledge → Minervium embodies organized knowledge management
- **Memory and intellect:** Minerva represents rational thought and accumulated learning
- **Strategic retrieval:** Like Minerva's tactical mind, the RAG system strategically retrieves relevant knowledge
- **Personal connection:** Strong connection to the creator's personal history with Minerva mythology

**Practical Benefits:**
- **Unique:** Not a real word → better for branding, domain availability, PyPI name
- **Memorable:** Single word, easy to spell, distinctive sound
- **CLI-friendly:** `minervium` is pronounceable (9 characters, same as "chromadb")
- **Expandable:** Can use "Minervian" as adjective (e.g., "Minervian search")
- **Mythological weight:** Carries the gravitas of ancient wisdom and knowledge

**Alternative Names Considered:**

| Name | Pros | Cons |
|------|------|------|
| Athenaeum | Library, wisdom (Athena), real word with historical meaning | Already considered and rejected for being too formal |
| Prometheum | Fire/enlightenment metaphor, unique | Less directly connected to wisdom and organized knowledge |
| Memoria | Latin for memory, elegant | Less distinctive, many "memoria" apps exist |
| Anamnesis | Greek for recollection, philosophical | Hard to spell/pronounce, too academic |
| Codex | Ancient book, knowledge | Generic, many "codex" projects |

**Decision:** **Minervium** wins for its strong mythological connection to wisdom, personal significance, and the elegant "-ium" suffix that suggests an essential substance of knowledge.

---

## Technical Specifications

### Python Version Support

**Minimum:** Python 3.8 (ChromaDB requirement)
**Recommended:** Python 3.10+ (better entry points API)
**Tested:** Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13

### Dependencies

**Core Package:**
```
chromadb>=0.4.0        # Vector database
litellm>=1.0.0         # Multi-provider AI abstraction
numpy>=1.21.0          # Vector operations
langchain>=0.1.0       # Text splitting
langchain-text-splitters>=0.0.1
tiktoken>=0.4.0        # Token counting
nltk>=3.8              # NLP utilities
click>=8.0             # CLI framework
rich>=10.0             # Terminal formatting
```

**Plugin Dependencies:**
```
minervium-bear:  (no external dependencies - stdlib only)
minervium-zim:   libzim>=3.0.0
minervium-books: (no external dependencies)
```

### Configuration Format

**Index Configuration (JSON):**
```json
{
  "collection_name": "my_notes",
  "description": "Personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "chunk_size": 1200,
  "forceRecreate": false,
  "skipAiValidation": false,
  "provider": {
    "type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
  }
}
```

**Server Configuration (JSON):**
```json
{
  "chromadb_path": "./chromadb_data",
  "log_level": "INFO"
}
```

---

## Open Questions & Decisions Needed

### 1. CLI Framework Choice

**Options:**
- **Click:** Most popular, mature, good docs
- **Typer:** Modern, type hints, Click-based, better auto-completion
- **argparse:** Stdlib, no dependencies, less ergonomic

**Recommendation:** **Typer** - Modern, type-safe, great UX.

### 2. Testing Framework

**Current:** Some pytest usage in markdown-notes-cag-data-creator

**Recommendation:** Standardize on pytest for all packages.

### 3. Async Support

**Question:** Should extractors support async operations for large files?

**Recommendation:** Start with sync, add async in v2 if needed (YAGNI principle).

### 4. Configuration Format

**Current:** JSON files

**Alternatives:** TOML, YAML

**Recommendation:** Keep JSON - already established, widely supported.

### 5. Logging

**Current:** Mix of print() and console_logger

**Recommendation:** Standardize on `logging` module with `rich` handlers for pretty output.

### 6. Error Handling

**Question:** How strict should plugin validation be?

**Recommendation:**
- Extractors MUST validate output before returning
- CLI shows helpful error messages with suggestions
- Server marks collections as unavailable but continues (don't crash)

---

## Success Metrics

### Developer Experience
- [ ] Single `pip install minervium` command
- [ ] `minervium --help` shows all capabilities
- [ ] Plugins install with no configuration
- [ ] Auto-detection works 90%+ of time
- [ ] Error messages suggest fixes

### User Workflows
- [ ] Extract → Index → Serve completes in <5 commands
- [ ] Multi-source indexing straightforward
- [ ] Custom plugins possible with <100 lines of code

### Technical Quality
- [ ] All commands have --help documentation
- [ ] Test coverage >70% for core
- [ ] No circular imports
- [ ] Clean separation: core ↔ plugins
- [ ] Backward compatible (JSON contract unchanged)

### Documentation
- [ ] README covers 80% of use cases
- [ ] Plugin development guide with working example
- [ ] Migration guide for existing users
- [ ] API reference for all public classes

---

## Timeline Estimate

**Phase 1 - Core Reorganization:** 2-3 days
- Directory restructuring
- Import path updates
- CLI creation
- Plugin system implementation

**Phase 2 - Plugin Extraction:** 1-2 days
- Create plugin packages
- Implement extractors
- Entry point registration

**Phase 3 - Documentation:** 1-2 days
- README
- Plugin guide
- CLAUDE.md update
- Migration guide

**Phase 4 - Testing:** 1-2 days
- Unit tests
- Integration tests
- Manual validation

**Phase 5 - Deployment:** 1 day
- Repository structure finalization
- Package building
- Installation testing

**Total:** ~1-2 weeks of focused work

---

## Next Steps

1. **Review this document:** Iterate on decisions, clarify open questions
2. **Finalize technical choices:** CLI framework, logging, testing
3. **Create migration checklist:** Detailed task breakdown for Phase 1
4. **Begin Phase 1:** Start with directory structure creation
5. **Iterate rapidly:** Small commits, test frequently

---

## Appendix: File Mapping

### Core Package File Mapping

| Old Path | New Path | Notes |
|----------|----------|-------|
| `markdown-notes-cag-data-creator/full_pipeline.py` | `minervium/commands/index.py` | Entry point wrapper |
| `markdown-notes-cag-data-creator/chunk_creator.py` | `minervium/indexing/chunking.py` | Rename |
| `markdown-notes-cag-data-creator/embedding.py` | `minervium/indexing/embeddings.py` | Rename |
| `markdown-notes-cag-data-creator/storage.py` | `minervium/indexing/storage.py` | Keep as-is |
| `markdown-notes-cag-data-creator/json_loader.py` | `minervium/indexing/json_loader.py` | Keep as-is |
| `markdown-notes-mcp-server/server.py` | `minervium/server/mcp_server.py` | Rename |
| `markdown-notes-mcp-server/search_tools.py` | `minervium/server/search_tools.py` | Keep as-is |
| `markdown-notes-mcp-server/collection_discovery.py` | `minervium/server/collection_discovery.py` | Keep as-is |
| `markdown-notes-mcp-server/context_retrieval.py` | `minervium/server/context_retrieval.py` | Keep as-is |
| `markdown-notes-mcp-server/startup_validation.py` | `minervium/server/startup_validation.py` | Keep as-is |
| `markdown-notes-mcp-server/ai_provider.py` | `minervium/common/ai_provider.py` | Move to common |
| `markdown-notes-mcp-server/config.py` | `minervium/common/config.py` | Move to common |
| `markdown-notes-mcp-server/console_logger.py` | `minervium/common/logger.py` | Rename |
| (new) | `minervium/common/schemas.py` | Create (NoteSchema) |
| (new) | `minervium/cli.py` | Create (main CLI) |
| (new) | `minervium/commands/index.py` | Create (index command wrapper) |
| (new) | `minervium/commands/serve.py` | Create (serve wrapper) |
| (new) | `minervium/commands/peek.py` | Create (peek command) |
| (new) | `minervium/commands/validate.py` | Create (validate command) |

### Extractor Package File Mapping

| Old Path | New Path | Notes |
|----------|----------|-------|
| `bear-notes-extractor/bear_parser.py` | `extractors/bear-notes-extractor/bear_extractor/parser.py` | Move |
| `bear-notes-extractor/cli.py` | `extractors/bear-notes-extractor/bear_extractor/cli.py` | Move & modify (standalone CLI) |
| `zim-articles-parser/zim_parser.py` | `extractors/zim-extractor/zim_extractor/parser.py` | Move |
| `zim-articles-parser/zim_cli.py` | `extractors/zim-extractor/zim_extractor/cli.py` | Move & modify (standalone CLI) |
| `markdown-books-extractor/book_parser.py` | `extractors/markdown-books-extractor/markdown_books/parser.py` | Move |
| (new) | `extractors/markdown-books-extractor/markdown_books/cli.py` | Create (standalone CLI) |
| (new) | `extractors/README.md` | Create (extractor overview) |
| (new) | `docs/NOTE_SCHEMA.md` | Create (JSON schema spec) |
| (new) | `docs/EXTRACTOR_GUIDE.md` | Create (how to build extractors) |

---

**End of Document**
