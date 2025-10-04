# Task List: Multi-Collection Support for Markdown Notes Pipeline

Generated from: [prd-multi-collection-pipeline.md](prd-multi-collection-pipeline.md)

## Relevant Files

### New Files to Create

- [markdown-notes-cag-data-creator/config_loader.py](../config_loader.py) - JSON configuration file loading and schema validation
- [markdown-notes-cag-data-creator/validation.py](../validation.py) - Collection name and description validation (regex + AI)
- [markdown-notes-cag-data-creator/collections/](../collections/) - Directory for storing collection configuration JSON files (create examples)
- [markdown-notes-cag-data-creator/collections/bear_notes_config.json](../collections/bear_notes_config.json) - Example configuration for Bear notes collection
- [markdown-notes-cag-data-creator/collections/wikipedia_history_config.json](../collections/wikipedia_history_config.json) - Example configuration for Wikipedia collection

### Files to Modify

- [markdown-notes-cag-data-creator/full_pipeline.py](../full_pipeline.py) - Add --config CLI argument, integrate configuration system, add --dry-run mode
- [markdown-notes-cag-data-creator/storage.py](../storage.py) - Update get_or_create_collection() to accept description and force_recreate parameters, add metadata storage
- [markdown-notes-cag-data-creator/embedding.py](../embedding.py) - May need check_model_availability() function for AI validation

### Notes

- This project uses Python 3.13 with virtual environment at `.venv/`
- Dependencies include: chromadb, ollama, langchain-text-splitters, jsonschema (add this)
- The codebase follows immutable data patterns with models defined in [models.py](../models.py)
- Ollama models required: `mxbai-embed-large:latest` (embeddings), `llama3.1:8b` (AI validation)
- Use `pip install jsonschema` to add JSON schema validation support

## Tasks

- [x] 1.0 Create JSON configuration file infrastructure and validation system
  - [x] 1.1 Create `config_loader.py` module with `load_collection_config()` function
  - [x] 1.2 Implement JSON schema validation using jsonschema library (validate field types: collection_name/description as strings, forceRecreate/skipAiValidation as booleans)
  - [x] 1.3 Add validation for required fields (collection_name, description) and set defaults for optional fields (forceRecreate=False, skipAiValidation=False)
  - [x] 1.4 Implement clear error messages for: file not found, invalid JSON syntax, missing required fields, type mismatches
  - [x] 1.5 Create `collections/` directory and example configuration files (bear_notes_config.json, wikipedia_history_config.json)
  - [x] 1.6 Add FileNotFoundError, json.JSONDecodeError, and ValueError exception handling with user-friendly error formatting

- [x] 2.0 Implement collection name and description validation (regex + AI)
  - [x] 2.1 Create `validation.py` module with `validate_collection_name()` function (regex: `^[a-zA-Z0-9_-]+$`, max 64 chars)
  - [x] 2.2 Implement `validate_description_regex()` for mandatory checks: minimum 50 chars, required phrases ("use this when", "use this collection", etc.), vague description blacklist
  - [x] 2.3 Create `check_model_availability()` function to verify llama3.1:8b model is available via Ollama
  - [x] 2.4 Implement `validate_with_ai()` function using Ollama llama3.1:8b model with scoring prompt (0-10 scale, threshold 7+)
  - [x] 2.5 Create `validate_description_hybrid()` that runs regex validation first (mandatory), then AI validation (optional based on skipAiValidation flag)
  - [x] 2.6 Add comprehensive error messages with examples, templates, and escape hatch instructions (suggest skipAiValidation when AI is too strict)

- [x] 3.0 Update storage.py to support collection metadata and force recreation
  - [x] 3.1 Update `get_or_create_collection()` function signature to accept `description: str` and `force_recreate: bool` parameters
  - [x] 3.2 Add collection existence check using `client.list_collections()` before creation
  - [x] 3.3 Implement force_recreate logic: raise StorageError if collection exists and force_recreate=False, delete and recreate if force_recreate=True
  - [x] 3.4 Update collection metadata to include: "description" field and "created_at" timestamp (ISO format with timezone.utc)
  - [x] 3.5 Add warning messages when using default metadata or when force recreating collections
  - [x] 3.6 Update StorageError messages to include instructions about forceRecreate configuration option

- [x] 4.0 Integrate configuration system into full_pipeline.py
  - [x] 4.1 Add `--config` argument to argparse (required parameter, type=str, help text explaining JSON configuration file)
  - [x] 4.2 Import and call `load_collection_config()` to load and validate configuration file early in pipeline
  - [x] 4.3 Import **validation** functions and validate collection name and description after loading config
  - [x] 4.4 Pass collection_name, description, and force_recreate from config to `get_or_create_collection()` in storage step
  - [x] 4.5 Update progress output to display collection name and description being used
  - [x] 4.6 Add try/except blocks for configuration and validation errors with clear error formatting (show config file path, issue details, suggestions)

- [ ] 5.0 Add dry-run mode and comprehensive error handling
  - [ ] 5.1 Add `--dry-run` argument to argparse (boolean flag, help text explaining validation-only mode)
  - [ ] 5.2 Implement dry-run logic: validate config file, validate collection name/description, load and analyze notes, check if collection exists
  - [ ] 5.3 Display dry-run preview output: collection name, description, estimated chunk count, estimated storage size, collection existence status, forceRecreate setting
  - [ ] 5.4 Make dry-run mode skip ChromaDB collection creation/modification and embedding generation
  - [ ] 5.5 Add exit code handling: 0 for successful validation, non-zero for validation failures
  - [ ] 5.6 Create comprehensive error message templates for all failure scenarios: config file errors, validation failures (name/description), ChromaDB errors, AI model unavailable
  - [ ] 5.7 Add `skipAiValidation` warning message when AI validation is skipped (display responsibility notice and consequences)
  - [ ] 5.8 Update all error messages to include actionable next steps (pull model, fix config file, add skipAiValidation, etc.)

- [ ] 6.0 Code Review
  - [ ] 6.1 Review all the project code using Robert C. Martin "Clean Code" principles, follow the tasklist in prompts/clean-code-review-tasks.md but to not alter the code: build a detailed, step-by-step task list of actions to execute reach a Clean Code status; wait for user input before executing it.
