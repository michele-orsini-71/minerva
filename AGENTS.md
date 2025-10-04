# Repository Guidelines

## Project Structure & Module Organization
- `bear-notes-extractor/` exposes the Bear backup CLI and unit tests; keep fixtures in `test-data/`.
- `markdown-notes-cag-data-creator/` houses the RAG pipeline; `full_pipeline.py` is the orchestration entrypoint.
- `chroma-peek/` ships the Streamlit inspector; point configs at `chromadb_data/` (leave untracked).
- `markdown-notes-mcp-server/` contains MCP notes and design docs for reference.
- Shared prompts, smoke scripts (`test-files/`), and temporary embedding stores live alongside module directories.

## Build, Test, and Development Commands
- `source .venv/bin/activate` to enter the pinned virtualenv.
- `pip install -e bear-notes-extractor -e markdown-notes-cag-data-creator[dev]` bootstraps editable installs with dev extras.
- `python bear-notes-extractor/cli.py <backup.bear2bk>` (alias `extract-bear-notes`) converts Bear backups to JSON.
- `python markdown-notes-cag-data-creator/full_pipeline.py notes.json --verbose` executes chunk → embed → persist; pass `--chromadb-path` to override storage.
- `streamlit run chroma-peek/main.py` inspects persisted embeddings; ensure `ollama serve` with `mxbai-embed-large` is running.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, `snake_case` for functions/modules, and PascalCase for classes.
- Keep docstrings and type hints current; run `black .`, `flake8`, and `mypy` (for typed modules) before publishing changes.
- Prefer concise helper comments for complex logic; avoid commentary on obvious assignments.

## Testing Guidelines
- Use `pytest` from the repo root after activating the env; add tests under each package’s `tests/` directory.
- Lean on fixtures in `test-data/`; mock Ollama/Chroma dependencies or document manual steps.
- Name tests after behavior (`test_markdown_chunker_handles_html`), and ensure they execute quickly and deterministically.

## Commit & Pull Request Guidelines
- Commit subjects follow short, present-tense phrases (e.g., `adds mcp implementation instructions`).
- Group related changes, include context in the body when behavior shifts, and note validation commands.
- PRs should summarize intent, list verification (tests, scripts), link issues, and attach screenshots for UI diffs.

## Security & Data Handling
- Never commit personal notes, secrets, or generated Chroma stores; scrub `chromadb_data/` before sharing.
- Document new dependencies in the relevant `README.md` and sync `requirements.txt` or `setup.py` when they change.
