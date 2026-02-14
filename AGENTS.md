# Repository Guidelines

## Project Structure & Module Organization
Core RAG commands live in `minerva/` (`index`, `serve`, `validate`, `peek`). Extractor CLIs live under `extractors/` (e.g., `bear-notes-extractor`); matching fixtures live in `test-data/`. Shared docs, scripts, and automation sit in `docs/`, `tools/`, and `tasks/`. Keep local Chroma artifacts in `./chromadb_data/` (untracked) and place deployment configs under `configs/` or `deployment/`.

## Build, Test, and Development Commands
Activate the virtualenv with `source .venv/bin/activate`, then install the core with `pip install -e .` and individual extractors via `pip install -e extractors/<name>`. Validate extractor output using `minerva validate notes.json --verbose`. Index data through `minerva index --config path/to/config.json --verbose` (add `--dry-run` to inspect without writing). Inspect collections with `minerva peek COLLECTION --chromadb ./chromadb_data`. Run unit suites via `pytest`; target extractor suites with `pytest extractors/zim-extractor/tests`. Finish iterations with `black .`, `flake8`, and `mypy`.

## Coding Style & Naming Conventions
Use Black-formatted Python (4-space indents) and type hints on public APIs. Stick to snake_case for modules, functions, and variables; reserve UpperCamelCase for classes/dataclasses. CLI entry points mirror their modules (e.g., `bear-extractor` ↔ `bear_extractor`). Config files stay lowercase with hyphenated names such as `server-config.json`.

## Testing Guidelines
Author focused `pytest` cases alongside the code: core tests in `tests/`, extractor suites under each extractor's `tests/` directory. Name files `test_<feature>.py` and rely on deterministic fixtures from `test-data/`. Before a PR, run `pytest`, then `black .`, `flake8`, and `mypy`; document any manual Ollama or Chroma validation steps.

## Commit & Pull Request Guidelines
Keep commits short, imperative (e.g., `add indexing health endpoint`) and grouped by feature. PRs should explain purpose, reference related issues, record commands and results (`pytest`, `black`, etc.), and attach screenshots or logs if CLI UX changes. Never commit Bear backups, ZIM archives, or Chroma databases; store secrets via environment variables or local config files.

## Security & Configuration Tips
Confirm `ollama serve` is running with `mxbai-embed-large:latest` pulled before enabling AI validation or MCP serving. Keep `chromadb_data/` local, out of git. Place deployment-ready configs in `configs/` or `deployment/`, and ensure paths and secrets are externalized.
