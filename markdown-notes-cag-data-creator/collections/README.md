# Collection Configuration Files

This directory contains JSON configuration files for different ChromaDB collections in the multi-collection RAG pipeline.

## File Format

Each configuration file must be a valid JSON file with the following structure:

```json
{
  "collection_name": "your_collection_name",
  "description": "Detailed description of when to use this collection...",
  "forceRecreate": false,
  "skipAiValidation": false
}
```

## Field Specifications

### Required Fields

- **`collection_name`** (string)
  - Must start with alphanumeric character
  - Can contain: letters, numbers, underscores, hyphens
  - Length: 1-63 characters
  - Pattern: `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`
  - Examples: `bear_notes`, `project-docs`, `team123`

- **`description`** (string)
  - Clear explanation of when to use this collection
  - Length: 10-1000 characters
  - Should describe the content type, use cases, and search scenarios
  - Best practice: Include "Use this collection when..." at the beginning

### Optional Fields

- **`forceRecreate`** (boolean, default: `false`)
  - `false`: Error if collection already exists (safe default)
  - `true`: Delete and recreate collection if it exists (destructive!)
  - Use with caution - destroys existing data

- **`skipAiValidation`** (boolean, default: `false`)
  - `false`: Validate description quality using AI (recommended)
  - `true`: Skip AI validation (escape hatch if AI is too strict)
  - AI validation ensures description is clear and actionable

## Usage

### Using a configuration file with the pipeline:

```bash
python full_pipeline.py --config collections/bear_notes_config.json notes.json
```

### Validating a configuration file:

```bash
python -c "from config_loader import load_collection_config; config = load_collection_config('collections/your_config.json'); print(f'✅ Valid: {config.collection_name}')"
```

## Example Configurations

### Personal Notes (Bear Notes)
See: [bear_notes_config.json](bear_notes_config.json)
- **Use case**: Personal knowledge management
- **Content**: Private notes, ideas, research
- **Search scenarios**: Finding specific information in personal notes

### Historical Articles (Wikipedia)
See: [wikipedia_history_config.json](wikipedia_history_config.json)
- **Use case**: Historical research and fact-checking
- **Content**: Wikipedia articles about history
- **Search scenarios**: Historical context, dates, biographies

## Creating Your Own Configuration

1. Copy an example configuration file
2. Update `collection_name` to match your use case
3. Write a clear `description` explaining when to use this collection
4. Set `forceRecreate` to `false` (unless you want to replace existing data)
5. Set `skipAiValidation` to `false` (recommended for quality)
6. Validate using the command above

## Validation Rules

The configuration loader will reject files that:
- Are not valid JSON
- Have missing required fields
- Have incorrect field types
- Have collection names with invalid characters
- Have descriptions that are too short or too long
- Have unknown/extra fields (prevents typos)

## Best Practices

1. **Descriptive names**: Use clear, descriptive collection names that indicate content type
2. **Detailed descriptions**: Explain what's in the collection and when to search it
3. **Start fresh**: Keep `forceRecreate: false` unless you're intentionally rebuilding
4. **Use AI validation**: Keep `skipAiValidation: false` to ensure quality descriptions
5. **Version control**: Commit configuration files to track changes
6. **One collection per source**: Create separate collections for different data sources

## Error Messages

If validation fails, you'll see helpful error messages with:
- The specific problem (missing field, invalid type, etc.)
- The location in the file
- Suggestions for fixing the issue
- Examples of correct values

For detailed validation logic, see: [../config_loader.py](../config_loader.py)
