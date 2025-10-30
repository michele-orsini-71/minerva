# Agent Operations Guide

## Overview
- Multi-source knowledge ingestion stack for Bear backups, ZIM archives, and markdown notes.
- Primary flow: extract → normalize JSON → chunk & embed via `minerva` → inspect/search with Chroma + MCP.
- Entire pipeline runs locally: Ollama supplies embeddings and validations; ChromaDB persists vectors under `chromadb_data/`.

## Key Directories
- `minerva/` – Core RAG pipeline package with CLI commands (`index`, `serve`, `validate`, `peek`), LangChain chunking, embedding, and storage modules.
- `extractors/bear-notes-extractor/` – CLI + library that converts `.bear2bk` backups to normalized JSON; fixtures live in `test-data/`.
- `extractors/zim-extractor/` – CLI (`zim-extractor`) for pulling markdown and catalogs from ZIM archives.
- `extractors/markdown-books-extractor/` – CLI for extracting markdown books into note format.
- `chroma-peek/` – Streamlit inspector pointed at local Chroma collections (keep `chromadb_data/` untracked).
- `prompts/`, `tasks/`, and `tools/` – Shared prompts, planning docs, automation/scripts (e.g., `tools/find_dead_code.py`).

## Environment & Installation
- Activate the shared virtualenv: `source .venv/bin/activate` (Python 3.13 expected).
- Editable installs after activation: `pip install -e .` for minerva core, then `pip install -e extractors/bear-notes-extractor -e extractors/zim-extractor -e extractors/markdown-books-extractor` for extractors.
- Ollama must be running (`ollama serve`) with `mxbai-embed-large:latest`; pull `llama3.1:8b` when enabling AI validation.
- Point configs at the absolute `chromadb_data/` path; keep the directory out of version control.

## Core Workflows
- **Bear extraction**: `bear-extractor "Bear Notes.bear2bk" -o notes.json` or use `python -m bear_extractor.cli`.
- **ZIM extraction**: `zim-extractor archive.zim -o articles.json --limit 1000` or use `python -m zim_extractor.cli`.
- **Validation**: `minerva validate notes.json --verbose` to check schema compliance.
- **RAG pipeline**: Create config JSON, then run `minerva index --config config.json --verbose` (`--dry-run` for validation-only run).
- **Data inspection**: `minerva peek COLLECTION_NAME --chromadb ./chromadb_data --format table` or launch `streamlit run chroma-peek/main.py -- --chromadb-path ./chromadb_data`.
- **MCP server**: `minerva serve --config server-config.json` validates connectivity and exposes tools to Claude Desktop (update Claude config with the absolute path).

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
