# Agent Operations Guide

## Overview
- Multi-source knowledge ingestion stack for Bear backups, ZIM archives, and markdown notes.
- Primary flow: extract → normalize JSON → chunk & embed via `markdown-notes-cag-data-creator` → inspect/search with Chroma + MCP.
- Entire pipeline runs locally: Ollama supplies embeddings and validations; ChromaDB persists vectors under `chromadb_data/`.

## Key Directories
- `bear-notes-extractor/` – CLI + library that converts `.bear2bk` backups to normalized JSON; fixtures live in `test-data/`.
- `zim-articles-parser/` – CLI (`extract-zim-articles`) for pulling markdown and catalogs from ZIM archives.
- `markdown-notes-cag-data-creator/` – Config-driven multi-collection RAG pipeline (`full_pipeline.py`) with LangChain chunking, embedding, and storage modules.
- `chroma-peek/` – Streamlit inspector pointed at local Chroma collections (keep `chromadb_data/` untracked).
- `markdown-notes-mcp-server/` – FastMCP server exposing list/search tools over generated collections; reads `config.json`.
- `prompts/`, `tasks/`, and `tools/` – Shared prompts, planning docs, automation/scripts (e.g., `tools/find_dead_code.py`).

## Environment & Installation
- Activate the shared virtualenv: `source .venv/bin/activate` (Python 3.13 expected).
- Editable installs after activation: `pip install -e bear-notes-extractor -e markdown-notes-cag-data-creator[dev] -e zim-articles-parser[dev]`.
- Ollama must be running (`ollama serve`) with `mxbai-embed-large:latest`; pull `llama3.1:8b` when enabling AI validation.
- Point configs at the absolute `chromadb_data/` path; keep the directory out of version control.

## Core Workflows
- **Bear extraction**: `python bear-notes-extractor/cli.py path/to/backup.bear2bk` → emits `{backup}.json`; console script alias `extract-bear-notes`.
- **ZIM extraction**: `python zim-articles-parser/zim_cli.py archive.zim --json catalog.json --output-dir markdown/ --limit 1000`; supports installed `extract-zim-articles` entrypoint.
- **RAG pipeline**: Create config in `markdown-notes-cag-data-creator/collections/*.json`, then run `python markdown-notes-cag-data-creator/full_pipeline.py --config collections/name.json --verbose` (`--dry-run` for validation-only run).
- **Data inspection**: Launch `streamlit run chroma-peek/main.py -- --chromadb-path ./chromadb_data` to browse stored chunks.
- **MCP server**: `python markdown-notes-mcp-server/server.py` loads `config.json`, validates Ollama + Chroma connectivity, and exposes tools to Claude Desktop (update Claude config with the absolute path).

## Testing & Quality
- Run `pytest` from the repo root; package-specific suites live under each module’s `tests/` directory.
- Enforce formatting and linting: `black .`, `flake8`, `mypy` (where types are declared).
- Lean on deterministic fixtures in `test-data/`; document manual steps when tests rely on Ollama or Chroma instances.
- Keep docstrings, type hints, and READMEs in sync with behavior; record new dependencies in package `setup.py` files.

## Data & Security
- Do not commit Bear backups, ZIM archives, or generated Chroma databases (`chromadb_data/` stays local and untracked).
- Redact personal content from fixtures and examples before sharing.
- Note any manual validation or external service requirements in PR descriptions.

## Agent Notes
- Review active plans under `tasks/` before large refactors or feature work.
- Align LLM prompt changes with `prompts/` so downstream tools stay consistent.
- If unexpected files change during your run, pause and ask for direction before reverting.
