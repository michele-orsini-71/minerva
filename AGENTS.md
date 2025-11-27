# Repository Guidelines

## Project Structure & Module Organization
The `minerva/` package is the core RAG pipeline, exposing CLI commands such as `index`, `serve`, `validate`, and `peek`. Extractor CLIs live under `extractors/` (`bear-notes-extractor`, `zim-extractor`, `markdown-books-extractor`) with fixtures under `test-data/`. Scripts and docs reside in `tools/`, `tasks/`, and `docs/`, while repo-wide tests sit in `tests/`. Keep `chromadb_data/` local and untracked, and store deployment configs under `configs/` or `deployment/`.

## Build, Test, and Development Commands
Activate the virtualenv (`source .venv/bin/activate`) before installing dependencies. Run `pip install -e .` for the core pipeline and `pip install -e extractors/...` for each extractor. Workflows: `minerva validate notes.json --verbose` to check extractor output, `minerva index --config path/to/config.json --verbose` (append `--dry-run` for validation-only), and `minerva peek COLLECTION --chromadb ./chromadb_data` to inspect embeddings. Execute `pytest` at the repo root or target `pytest extractors/zim-extractor/tests`, and finish with `black .`, `flake8`, and `mypy`.

## Coding Style & Naming Conventions
Follow Black-formatted Python with 4-space indentation, type hints for public APIs, and docstrings aligned with runtime behavior. Prefer snake_case for modules, functions, and variables; use UpperCamelCase only for classes and dataclasses. CLI entry points should mirror the Python module name (e.g., `bear-extractor` ↔ `bear_extractor`). Keep configuration JSON/YAML filenames lowercase with hyphens (e.g., `server-config.json`).

## Testing Guidelines
Write focused `pytest` tests that sit alongside the relevant module (`tests/` for core, extractor-specific `tests/` directories otherwise). Name test files `test_<feature>.py` and lean on deterministic fixtures in `test-data/`. Before opening a PR, run `pytest`, `black .`, `flake8`, and any extractor suite touched by your change. Note Ollama or Chroma manual validation steps in the PR.

## Commit & Pull Request Guidelines
Commits should be short, imperative statements (`fix chroma peek output`, `add indexing health endpoint`) and grouped logically by feature. Reference related issues or tasks in the body when applicable. Pull requests must include purpose summary, testing evidence (commands + results), configuration or data prerequisites, and screenshots/log snippets when altering CLI UX. Keep `chromadb_data/` and proprietary archives out of git, and rebase rather than merge when synchronizing long-lived work.

## Security & Configuration Tips
Never commit Bear backups, ZIM archives, or generated Chroma databases. Store secrets and absolute paths (e.g., Ollama sockets, `chromadb_data/`) outside version control and reference them via environment variables or local config files. When enabling AI validation or MCP serving, confirm `ollama serve` is running with `mxbai-embed-large:latest` pulled, and record any manual steps in `docs/` so other contributors can reproduce them.
