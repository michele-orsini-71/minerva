# PRD: Multi-Collection Support for Markdown Notes Pipeline

## Introduction/Overview

This feature adds multi-collection support to the `markdown-notes-cag-data-creator` pipeline, enabling users to create and manage multiple ChromaDB collections from different knowledge sources (Bear notes, Zim wikis, documentation sites, etc.) within a single database instance. Each collection will have rich metadata to help AI agents understand its purpose and content.

**Problem Statement:**
Currently, the pipeline creates a single hardcoded collection (`bear_notes_chunks`). Users who want to maintain multiple knowledge bases (personal notes, wikis, project documentation) must either:
1. Manually modify the code to change collection names
2. Maintain separate ChromaDB instances
3. Mix all content into a single collection with no semantic separation

**Goal:**
Enable users to create named collections with descriptive metadata through CLI parameters, without modifying code.

## Goals

1. **Flexible Collection Naming:** Users can specify collection names via configuration file
2. **Rich Metadata:** Collections include AI-optimized descriptions to guide intelligent querying
3. **Zero Code Changes:** Adding new collections requires only running the pipeline with different configuration files
4. **Quality Enforcement:** Validation ensures collection descriptions are useful for AI agents

## User Stories

### As a User (Knowledge Base Owner)

1. **Story 1:** As a user, I want to create a JSON configuration file for my Bear notes collection with all metadata, so that I can easily manage complex, multi-line descriptions without command-line escaping issues.

2. **Story 2:** As a user, I want to run the pipeline with `python full_pipeline.py --config collections/bear_notes_config.json notes.json`, so that I can create collections with a simple, repeatable command.

3. **Story 3:** As a user, when my configuration file has invalid JSON or missing fields, I want clear error messages showing exactly what's wrong and how to fix it.

4. **Story 4:** As a user, I want to keep all my collection configurations in a `collections/` directory, so that I can version control them, reuse them, and understand what collections exist in my system.

### As a Developer

5. **Story 5:** As a developer, I want to understand how collection metadata is stored in ChromaDB, so that I can add new metadata fields in the future.

6. **Story 6:** As a developer, I want clear error messages when validation fails, so that I can quickly fix my command and retry.

## Functional Requirements

### Configuration File Approach (`full_pipeline.py`)

**FR1:** The `full_pipeline.py` CLI must accept a **required** `--config` parameter:
- Type: Path to JSON configuration file
- Contains collection metadata (name, description, optional forceRecreate)
- Validation: File must exist and be valid JSON
- Example: `--config collections/bear_notes_config.json`

**FR2:** The configuration file must have the following JSON schema:
```json
{
  "collection_name": "string (required)",
  "description": "string (required)",
  "forceRecreate": "boolean (optional, default: false)",
  "skipAiValidation": "boolean (optional, default: false)"
}
```

**FR3:** Example configuration file (`bear_notes_config.json`):
```json
{
  "collection_name": "bear_notes_chunks",
  "description": "Personal notes from Bear app covering software development, machine learning, and productivity systems. Use this to search the user's past work, recall their perspective on technical topics, or find code snippets they've saved. Contains notes from 2020-2024."
}
```

**FR4:** The pipeline must validate the configuration file:
- **File existence:** Config file must exist at specified path
- **Valid JSON:** File must parse as valid JSON
- **Required fields:** `collection_name` and `description` must be present
- **Field types:** `collection_name` and `description` must be strings, `forceRecreate` must be boolean (if present)
- **On validation failure:** Display clear error with field name and issue

**FR5:** The pipeline must handle existing collections with `forceRecreate` validation:
- **Default behavior (forceRecreate=false or omitted):** Fail if collection already exists with clear error message
- **Force recreation (forceRecreate=true):** Delete existing collection and recreate with new data
- **Error message:** Must explain how to enable forceRecreate and warn about data loss
- **Confirmation:** Display warning when forceRecreate=true showing which collection will be deleted

### Collection Metadata Storage (`storage.py`)

**FR6:** The `get_or_create_collection()` function in `storage.py` must accept and store metadata:
- Accept new parameters: `description` (string), `force_recreate` (boolean)
- Check if collection exists; fail if exists and force_recreate=False
- Delete and recreate if force_recreate=True
- Store in ChromaDB's collection-level metadata dictionary
- Metadata schema:
  ```python
  {
      "hnsw:space": "cosine",  # Existing
      "version": "1.0",  # Existing
      "description": description,  # NEW - AI-optimized collection description
      "created_at": datetime.now(timezone.utc).isoformat()  # NEW
  }
  ```
- Metadata persists in ChromaDB's internal storage (no external files)

**FR7:** The pipeline must validate collection descriptions with a two-tier system:

**Tier 1: Mandatory Regex Validation (always runs, cannot be skipped)**
- **Minimum length:** 50 characters
- **Required phrases:** Must contain at least one of: "Use this when", "Use this collection", "Search this for", "Use this to"
- **Vague description blacklist:** Reject patterns like "My notes", "Personal wiki", "Documentation" without context
- **Validation timing:** When loading configuration file, before creating/updating collection

**Tier 2: AI Validation (runs by default, can be skipped via config file)**
- **Uses:** Local Ollama model (llama3.1:8b) to evaluate description quality
- **Scoring:** 0-10 rating based on clarity, specificity, and actionability
- **Threshold:** Score of 7+ required to pass
- **Model availability check:** Fails execution if llama3.1:8b is not available (consistent with embedding model behavior)
- **Skip option:** Setting `"skipAiValidation": true` in config file allows users to bypass when AI is too strict or model unavailable

**On validation failure:**
- Display clear error message with specific issues identified
- Show description template and good examples
- If AI validation failed, suggest setting `"skipAiValidation": true` in config file as escape hatch
- When `skipAiValidation` is enabled, display warning about user responsibility for quality
- Show path to the config file with the issue

**FR8:** The pipeline must validate collection names:
- **Allowed characters:** `a-z`, `A-Z`, `0-9`, `_` (underscore), `-` (hyphen)
- **Disallowed:** Spaces, special characters, emoji, punctuation (except underscore/hyphen)
- **Maximum length:** 64 characters
- **Validation timing:** When loading configuration file
- **On validation failure:**
  - Display clear error with the invalid character(s) or length issue
  - Show valid examples: `bear_notes_chunks`, `wikipedia-history`, `python_docs_2024`
  - Show path to the config file with the issue

### Error Handling

**FR10:** When ChromaDB collection creation fails, the pipeline must:
- Display the full error from ChromaDB
- Suggest common fixes (check permissions, disk space, collection name validity)
- Exit with non-zero status code

**FR11:** When AI validation fails but user sets `"skipAiValidation": true` in config, the pipeline must:
- Log a prominent warning
- Explain the consequences (AI agents may not select this collection correctly)
- Note that regex validation still passed
- Proceed with collection creation

**FR12:** When configuration file is malformed or missing required fields, the pipeline must:
- Display clear error indicating which field is missing/invalid
- Show the expected JSON schema
- Provide a complete example configuration file
- Exit with non-zero status code

**FR13:** The pipeline must support a `--dry-run` parameter for validation without execution:
- Validates configuration file (JSON syntax, required fields, field types)
- Validates collection name (character restrictions, max length)
- Validates description (regex validation + optional AI validation)
- Loads and analyzes input notes file
- Displays preview of what would be created:
  - Collection name and description
  - Estimated chunk count
  - Estimated storage size
  - Whether collection exists (and forceRecreate setting)
- Does NOT create/modify ChromaDB collection
- Useful for testing configuration before committing to execution
- Exit code: 0 if validation passes, non-zero if validation fails

**FR14:** Configuration files must be validated using JSON Schema:
- Use `jsonschema` library for structural validation
- Enforce field types: `collection_name` (string), `description` (string), `forceRecreate` (boolean), `skipAiValidation` (boolean)
- Provide precise error messages for type mismatches
- Example error: "Field 'forceRecreate': expected boolean, got string"
- Schema validation runs before custom validation (name format, description quality)
- Clear error output shows field path and expected type

## Non-Goals (Out of Scope)

**NG1:** Migration of existing collections to add metadata (users must rebuild if needed)

**NG2:** GUI or interactive mode for collection creation (CLI only)

**NG3:** Collection renaming or deletion tools (use ChromaDB client directly if needed)

**NG4:** Automatic description generation based on content analysis (user must provide description)

**NG5:** Multi-language descriptions (English only for AI optimization)

**NG6:** Collection dependencies or relationships (each collection is independent)

## Collection Description Guidelines (CRITICAL for System Success)

### Why This Matters

Collection descriptions are **prompts for AI agents**, not just documentation. Poor descriptions will cause AI agents to select wrong collections, making the multi-collection feature unusable.

### Inadequate Descriptions (DO NOT USE)

- ❌ **"Zim wiki"** - What content? When should AI use it?
- ❌ **"Personal notes"** - About what topics? Why would AI search here?
- ❌ **"Documentation"** - For what software/project?
- ❌ **"My stuff"** - Completely useless for AI selection

### Effective AI-Optimized Descriptions

- ✅ **"A selection of the best 50,000 Wikipedia articles covering general knowledge. Use this collection to search for factual information on topics after your knowledge cutoff date, or to supplement your existing knowledge when answering user questions. Don't use for the user's personal notes or opinions."**

- ✅ **"Wikipedia articles focused on world history from ancient civilizations to modern times. Use this when the user prompt requires historical context, dates, events, or historical figures. Don't use for current events or the user's personal recollections."**

- ✅ **"Personal notes from Bear app covering software development, machine learning, and productivity systems. Use this to search the user's past work, recall their perspective on technical topics, or find code snippets they've saved. Don't use for factual information about external topics."**

- ✅ **"Complete documentation for the GitHub b4 repository codebase including API references, architecture diagrams, and usage examples. Use this when the user asks about b4 commands, workflows, or integration patterns. Don't use for other tools or general Git questions."**

### Description Template

**Basic template:**
```
[Content summary: what's in this collection]. Use this collection when [specific user intent/query patterns]. [Optional: Additional context about scope, limitations, or special features].
```

**Enhanced template (with negative guidance):**
```
[Content summary: what's in this collection]. Use this when [specific user intent/query patterns]. [Optional: timeframe/scope]. Don't use for [common mismatches].
```

**Components:**
1. **Content summary:** 1-2 sentences describing what's in the collection
2. **Usage guidance:** Explicit instructions on when AI should query this collection
3. **Optional context:** Timeframes, special coverage areas, limitations
4. **Negative guidance (advanced):** Helps AI avoid incorrect selections when multiple collections could match

**Note on formatting:** Descriptions should be plain text strings (no markdown). AI agents parse semantic meaning, not visual formatting. Structured writing patterns (as shown above) are sufficient for clear communication.

### Examples by Source Type

**Personal Notes:**
```
Personal notes from [app name] covering [topic areas]. Use this to search the user's past work, their perspective on [topics], or when they ask about their own ideas/projects. Contains notes from [date range]. Don't use for factual information about external topics.
```

**Wikipedia/General Knowledge:**
```
Wikipedia articles on [topic area]. Use this when the user asks about [types of questions], needs factual information on [subjects], or wants [specific knowledge type]. Covers [scope/timeframe]. Don't use for the user's personal notes or opinions.
```

**Technical Documentation:**
```
Complete documentation for [project/tool name] including [what's covered]. Use this when the user asks about [tool usage patterns], needs [specific help], or wants to understand [concepts]. Version: [version info]. Don't use for other tools or general programming questions.
```

**Code Repository Docs:**
```
Documentation and markdown files from [repository name] repository. Use this when the user asks about [project name] architecture, APIs, usage examples, or [specific features]. Extracted on [date]. Don't use for other projects or general software development questions.
```

**Multiple Collections of Same Type (example: two wikis):**
```
# Personal wiki
Personal Zim wiki covering daily notes, project planning, and meeting logs from 2020-2024. Use this to search the user's personal organization and work history. Don't use for entertainment or hobby content.

# D&D campaign wiki
Zim wiki containing D&D campaign world-building notes, character backstories, and session summaries. Use this when the user asks about their D&D campaign, NPCs, or world lore. Don't use for personal work or planning topics.
```

**Note:** The negative guidance in the two wiki examples helps AI distinguish between collections that could both match queries about "my wiki" or "my notes".

## Technical Considerations

### CLI Argument Parsing

**Current implementation:** `full_pipeline.py` uses `argparse`

**New argument to add:**
```python
# Config file (required)
parser.add_argument(
    "--config",
    type=str,
    required=True,
    help="Path to JSON configuration file with collection metadata"
)
```

### Configuration File Loading

**Load and validate configuration:**
```python
import json
from pathlib import Path
from typing import Dict, Any

def load_collection_config(config_path: str) -> Dict[str, Any]:
    """
    Load and validate collection configuration from JSON file.

    Returns:
        Dictionary with collection_name, description, forceRecreate, skipAiValidation

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
        ValueError: If required fields are missing
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Validate required fields
    required_fields = ['collection_name', 'description']
    missing = [field for field in required_fields if field not in config]
    if missing:
        raise ValueError(f"Missing required fields in {config_path}: {', '.join(missing)}")

    # Set defaults for optional fields
    if 'forceRecreate' not in config:
        config['forceRecreate'] = False
    if 'skipAiValidation' not in config:
        config['skipAiValidation'] = False

    return config
```

### Validation Implementation

**Collection name validation:**
```python
import re

def validate_collection_name(name: str) -> bool:
    """Validate collection name contains only safe characters."""
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name))
```

**Description validation (hybrid approach):**
```python
def validate_description_hybrid(
    description: str,
    config_path: str,
    skip_ai: bool = False
) -> tuple[bool, list[str]]:
    """
    Validate description with mandatory regex + optional AI validation.

    Args:
        description: The collection description to validate
        config_path: Path to config file (for error messages)
        skip_ai: Whether to skip AI validation (from config's skipAiValidation field)

    Returns:
        (is_valid, issues_list)
    """
    issues = []

    # TIER 1: Mandatory regex checks (always run)
    if len(description) < 50:
        issues.append(f"Description too short: {len(description)} chars (minimum: 50)")

    guidance_phrases = [
        "use this when",
        "use this collection",
        "search this for",
        "use this to"
    ]
    if not any(phrase in description.lower() for phrase in guidance_phrases):
        issues.append("Missing usage guidance. Include phrases like: 'Use this when...', 'Use this to...'")

    # Vague description blacklist
    vague_patterns = [
        r"^(my|personal)\s+(notes?|wiki|docs?)$",
        r"^(notes?|docs?|wiki|stuff|things)$"
    ]
    if any(re.match(pattern, description.lower().strip()) for pattern in vague_patterns):
        issues.append("Description is too vague (e.g., 'My notes', 'Wiki')")

    # If regex fails, stop here
    if issues:
        return False, issues

    # TIER 2: Optional AI validation
    if skip_ai:
        print("⚠️  AI validation skipped (skipAiValidation=true in config)")
        return True, []

    # Check if llama3.1:8b is available (fail if not, consistent with embedding model)
    if not check_model_availability("llama3.1:8b"):
        issues.append("Model 'llama3.1:8b' is not available")
        issues.append("Either: (1) Pull the model: ollama pull llama3.1:8b")
        issues.append("Or: (2) Skip AI validation by adding '\"skipAiValidation\": true' to your config file")
        return False, issues

    ai_result = validate_with_ai(description)
    if not ai_result["passed"]:
        issues.append(f"AI validation failed (score: {ai_result['score']}/10)")
        issues.append(f"Reason: {ai_result['reason']}")
        issues.append('Set "skipAiValidation": true in config if you believe this is incorrect')
        return False, issues

    print(f"✅ AI validation passed (score: {ai_result['score']}/10)")
    return True, []
```

### Storage.py Integration

**Current function signature:**
```python
def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    reset_collection: bool = False
) -> chromadb.Collection:
```

**New function signature:**
```python
def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    description: str = "No description provided",
    force_recreate: bool = False
) -> chromadb.Collection:
```

**Implementation changes:**
```python
from datetime import datetime, timezone

# Inside function:
# Check if collection exists
existing_collections = [c.name for c in client.list_collections()]
collection_exists = collection_name in existing_collections

if collection_exists and not force_recreate:
    raise StorageError(
        f"Collection '{collection_name}' already exists.\n"
        f"To recreate it, add '\"forceRecreate\": true' to your configuration file.\n"
        f"WARNING: This will delete all existing data in the collection."
    )

# Delete if force recreate
if collection_exists and force_recreate:
    client.delete_collection(collection_name)
    print(f"🗑️  Deleted existing collection '{collection_name}' (forceRecreate=true)")

# Create collection
collection = client.create_collection(
    name=collection_name,
    metadata={
        "hnsw:space": HNSW_SPACE,
        "version": "1.0",
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
)

# Warn if using defaults
if description == "No description provided":
    print(f"⚠️  Warning: Collection '{collection_name}' created with default metadata")
    print("    Consider providing --config with proper description for AI integration")
```

### ChromaDB Metadata Persistence

- ChromaDB stores collection metadata in its internal SQLite database
- Metadata is retrieved via `collection.metadata`
- No additional storage mechanism needed
- Metadata survives ChromaDB restarts

## Success Metrics

**SM1:** Users can create a new collection with proper metadata in under 2 minutes (single command)

**SM2:** 100% of collection name validation errors provide actionable error messages with examples

**SM3:** 100% of description validation errors show examples of good vs. bad descriptions

**SM4:** Zero code changes required to add new collections (pure CLI usage)

**SM5:** Collection metadata correctly persists and can be retrieved by MCP server

## Resolved Questions (Converted to Requirements)

**RQ1 (was OQ1):** `--dry-run` flag → **Implemented as FR13**

**RQ2 (was OQ2):** Collection name max length → **Implemented as part of FR8** (64 characters)

**RQ3 (was OQ3):** Multilingual descriptions → **Rejected, added to NG5** (English only)

**RQ4 (was OQ5):** Auto-generate descriptions → **Rejected, already in NG4**

**RQ5 (was OQ6):** Block vs warn on validation errors → **Confirmed current approach** (block on errors, as per FR7, FR8, FR10-12)

**RQ6 (was OQ7):** JSON Schema validation → **Implemented as FR14**

**RQ7 (was OQ8):** Negative guidance requirement → **Decision: Optional but encouraged**
- Negative guidance ("Don't use for...") remains optional in descriptions
- Examples in PRD emphasize its value for collection disambiguation
- Future enhancement: AI validation could award bonus points for negative guidance

**RQ8 (was OQ4):** Metadata-only updates → **Rejected**
- **Question:** Should pipeline support updating collection metadata without rebuilding?
- **Decision:** No - not supported in v1
- **Rationale:**
  - ChromaDB collection metadata is immutable by design
  - Updating metadata requires delete + recreate (already handled by `forceRecreate=true`)
  - Only use case is fixing typos/wording in descriptions (edge case, low value)
  - If source notes change, full pipeline re-run is needed anyway
- **Current solution:** Use `forceRecreate=true` to update metadata by rebuilding collection
- **Future consideration:** Could optimize with `--skip-rechunking` if source unchanged, but out of scope

## Example Usage

### Step 1: Create Configuration Files

**`collections/bear_notes_config.json`:**
```json
{
  "collection_name": "bear_notes_chunks",
  "description": "Personal notes from Bear app covering software development, machine learning, and productivity systems. Use this to search the user's past work, recall their perspective on technical topics, or find code snippets they've saved. Contains notes from 2020-2024. Don't use for factual information about external topics or current events."
}
```

**`collections/wikipedia_history_config.json`:**
```json
{
  "collection_name": "wikipedia_history_chunks",
  "description": "Wikipedia articles focused on world history from ancient civilizations to modern times. Use this when the user prompt requires historical context, dates, events, or historical figures. Don't use for the user's personal notes or current events."
}
```

**`collections/personal_wiki_config.json`** (first Zim wiki example):
```json
{
  "collection_name": "personal_wiki_chunks",
  "description": "Personal Zim wiki covering daily notes, project planning, and meeting logs from 2020-2024. Use this to search the user's personal organization and work history. Don't use for entertainment or hobby content."
}
```

**`collections/dnd_wiki_config.json`** (second Zim wiki example):
```json
{
  "collection_name": "dnd_campaign_wiki_chunks",
  "description": "Zim wiki containing D&D campaign world-building notes, character backstories, and session summaries. Use this when the user asks about their D&D campaign, NPCs, or world lore. Don't use for personal work or planning topics."
}
```

### Step 2: Run Pipeline with Configuration

**Creating Bear Notes Collection:**
```bash
python full_pipeline.py \
  --config collections/bear_notes_config.json \
  ../test-data/bear_notes.json
```

**Creating Wikipedia History Collection:**
```bash
python full_pipeline.py \
  --config collections/wikipedia_history_config.json \
  ../test-data/wikipedia_history.json
```

**Creating Personal Wiki Collection:**
```bash
python full_pipeline.py \
  --config collections/personal_wiki_config.json \
  ../test-data/personal_wiki.json
```

**Recreating Collection (with forceRecreate):**
```bash
# First, update config to add forceRecreate: true
# Then run:
python full_pipeline.py \
  --config collections/bear_notes_config.json \
  ../test-data/bear_notes_updated.json
```

**Skipping AI Validation (when needed):**
```bash
# First, update config file to add "skipAiValidation": true
# Example: collections/bear_notes_config.json
# {
#   "collection_name": "bear_notes_chunks",
#   "description": "...",
#   "skipAiValidation": true
# }
# Then run:
python full_pipeline.py \
  --config collections/bear_notes_config.json \
  ../test-data/bear_notes.json
```

### Error Examples

**Missing configuration file:**
```bash
$ python full_pipeline.py --config collections/missing.json notes.json
❌ Error: Configuration file not found: collections/missing.json

Please create the configuration file with the following format:
{
  "collection_name": "your_collection_name",
  "description": "AI-optimized description (min 50 chars, include usage guidance)",
  "forceRecreate": false
}
```

**Invalid JSON in configuration:**
```bash
$ python full_pipeline.py --config collections/bad_config.json notes.json
❌ Error: Invalid JSON in configuration file: collections/bad_config.json
   JSONDecodeError: Expecting ',' delimiter: line 3 column 5

Please validate your JSON syntax.
```

**Missing required fields:**
```bash
$ python full_pipeline.py --config collections/incomplete.json notes.json
❌ Error: Missing required fields in collections/incomplete.json: description

Required fields:
  - collection_name (string)
  - description (string)

Optional fields:
  - forceRecreate (boolean, default: false)
```

**Invalid collection name in config:**
```bash
$ python full_pipeline.py --config collections/bad_name.json notes.json
❌ Error: Invalid collection name 'my notes!' in collections/bad_name.json
   Collection names can only contain: a-z, A-Z, 0-9, _ (underscore), - (hyphen)

   Valid examples:
     - bear_notes_chunks
     - wikipedia-history
     - python_docs_2024

Please update the "collection_name" field in your configuration file.
```

**Inadequate description in config:**
```bash
$ python full_pipeline.py --config collections/short_desc.json notes.json
❌ Error: Description validation failed in collections/short_desc.json
  - Description too short: 9 chars (minimum: 50)
  - Missing usage guidance. Include phrases like: 'Use this when...', 'Use this to...'

  💡 Description template:
  [Content summary]. Use this when [user intent]. [Optional: scope/limitations]

  ✅ Good example:
  "Wikipedia articles on world history. Use this when the user asks about
  historical events, dates, or needs historical context."

  Please update the "description" field in your configuration file.
```

**AI validation model unavailable:**
```bash
$ python full_pipeline.py --config collections/my_notes.json notes.json
🤖 Checking AI validation model availability...
❌ Description validation failed in collections/my_notes.json:
  - Model 'llama3.1:8b' is not available
  - Either: (1) Pull the model: ollama pull llama3.1:8b
  - Or: (2) Skip AI validation by adding "skipAiValidation": true to your config file

# User chooses to skip AI validation, updates config file:
# { ..., "skipAiValidation": true }
$ python full_pipeline.py --config collections/my_notes.json notes.json
⚠️  AI validation skipped (skipAiValidation=true in config)
   You are responsible for ensuring description quality
✅ Created new collection 'my_notes_chunks'
[proceeds with pipeline]
```

**AI validation failure (quality issues with escape hatch):**
```bash
$ python full_pipeline.py --config collections/maybe_ok.json notes.json
🤖 Running AI validation on description...
❌ Description validation failed in collections/maybe_ok.json:
  - AI validation failed (score: 6/10)
  - Reason: Description lacks specific usage guidance for AI selection
  - Set "skipAiValidation": true in config if you believe this is incorrect

# User updates config file to add "skipAiValidation": true, then retries
$ python full_pipeline.py --config collections/maybe_ok.json notes.json
⚠️  AI validation skipped (skipAiValidation=true in config)
   You are responsible for ensuring description quality
✅ Created new collection 'maybe_ok_chunks'
[proceeds with pipeline]
```

**Collection already exists:**
```bash
$ python full_pipeline.py --config collections/bear_notes.json notes.json
❌ Error: Collection 'bear_notes_chunks' already exists.
   To recreate it, add "forceRecreate": true to your configuration file.
   WARNING: This will delete all existing data in the collection.
```
