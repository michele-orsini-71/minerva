# Repository Guidelines

## Project Structure & Module Organization
This workspace hosts Python tools for Bear exports and ChromaDB. `bear-notes-extractor/` converts `.bear2bk` backups to JSON. `markdown-notes-cag-data-creator/` runs the RAG pipeline (chunk → embed → store). `chroma-peek/` is a Streamlit inspector for persisted vectors, and `markdown-notes-mcp-server/` holds MCP design docs. Shared assets live in `prompts/`, `test-data/`, and `chromadb_data/` (keep untracked). Integration scripts and smoke checks sit in `test-files/`.

## Environment Setup
Activate `.venv` first: `source .venv/bin/activate`. For fresh setups install the editable packages: `pip install -e bear-notes-extractor -e markdown-notes-cag-data-creator`. The pipeline expects `ollama serve` with `mxbai-embed-large` available and writes to `chromadb_data/` by default.

## Build, Test, and Development Commands
- `python bear-notes-extractor/cli.py <backup.bear2bk>` converts a Bear backup; `extract-bear-notes` is the console alias.
- `python markdown-notes-cag-data-creator/full_pipeline.py notes.json --verbose` runs the full pipeline (tune with `--chunk-size`, `--chromadb-path`).
- `streamlit run chroma-peek/main.py` launches the database inspector; point it at your persistence directory.
- Use `pytest` (after `pip install -e markdown-notes-cag-data-creator[dev]`) for new tests; run existing benches as scripts, e.g. `python test-files/test-markdown-chunker.py --json-path test-data/...`.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation, `snake_case` for functions/modules, and PascalCase for classes. Keep type hints and docstrings aligned with existing modules. Run `black .` and `flake8` (provided by the `dev` extra) before opening a PR, and run `mypy` when touching typed modules such as `models.py`.

## Testing Guidelines
Aim for fast, deterministic coverage. Add automated tests alongside the code (e.g., `bear-notes-extractor/tests/`) so `pytest` finds them. Use the scripts in `test-files/` for integration checks around chunking, embeddings, and Chroma, updating defaults instead of hard-coding paths. Mock or document dependencies on Ollama and ChromaDB when tests require them.

## Commit & Pull Request Guidelines
Write short, present-tense subjects that mirror the existing history (`adds mcp implementation instructions`). Group related changes and add body context when behavior shifts. PRs should describe the change, list validation commands, link issues, and attach screenshots when UI output changes. Exclude generated databases and personal notes; rely on `test-data/` fixtures.

## Data & Security Notes
Never commit real notes or secrets. Scrub `chromadb_data/` before sharing. Document new external dependencies in the relevant `README.md` and update `requirements.txt` or `setup.py` to keep editable installs aligned.
