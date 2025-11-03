# Minerva Note Schema

This document defines the JSON schema that all extractors must produce for Minerva to process notes correctly.

## Table of Contents

- [Overview](#overview)
- [Schema Specification](#schema-specification)
- [Field Definitions](#field-definitions)
- [Validation Rules](#validation-rules)
- [Examples](#examples)
- [Common Errors](#common-errors)
- [Best Practices](#best-practices)

---

## Overview

The Minerva Note Schema is a standardized JSON format that serves as the universal interface between extractors and the Minerva indexing system. All notes, regardless of their original source (Bear, Zim, books, custom sources), must be converted to this format.

### Why a Standard Schema?

- **Extractor Independence**: Extractors can be written in any language as long as they output valid JSON
- **Validation**: Notes can be validated before expensive indexing operations
- **Consistency**: All notes have the same structure in the vector database
- **Extensibility**: Custom metadata fields are allowed for source-specific information

### Schema Format

Extractors must output a **JSON array** of note objects:

```json
[
  { note object 1 },
  { note object 2 },
  ...
]
```

---

## Schema Specification

### JSON Schema (Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "provider_type": "array",
  "items": {
    "provider_type": "object",
    "required": ["title", "markdown", "size", "modificationDate"],
    "properties": {
      "title": {
        "provider_type": "string",
        "description": "The title or name of the note",
        "minLength": 1
      },
      "markdown": {
        "provider_type": "string",
        "description": "The full markdown content of the note"
      },
      "size": {
        "provider_type": "integer",
        "description": "Size of the note content in bytes (UTF-8 encoded)",
        "minimum": 0
      },
      "modificationDate": {
        "provider_type": "string",
        "description": "ISO 8601 formatted modification date (UTC timezone preferred)",
        "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
      },
      "creationDate": {
        "provider_type": "string",
        "description": "ISO 8601 formatted creation date (UTC timezone preferred) - optional",
        "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
      }
    },
    "additionalProperties": true
  }
}
```

---

## Field Definitions

### Required Fields

All notes **must** include these four fields:

#### `title` (string, non-empty)

The human-readable title or name of the note.

- **Type**: string
- **Constraints**: Must have at least 1 character
- **Purpose**: Used for display, search results, and chunk metadata
- **Examples**:
  - `"Project Ideas"`
  - `"Meeting Notes - 2025-10-20"`
  - `"Introduction to Quantum Computing"`

**Recommendations**:

- Use descriptive, unique titles when possible
- For untitled notes, generate a title from the first heading or content
- Avoid overly long titles (> 200 characters)

#### `markdown` (string)

The full content of the note in markdown format.

- **Type**: string
- **Constraints**: Can be empty string for notes without content
- **Purpose**: The actual text that will be chunked and indexed
- **Format**: Standard markdown with CommonMark compatibility

**Supported Markdown Features**:

- Headings (`#`, `##`, etc.)
- Lists (ordered and unordered)
- Code blocks (fenced with triple backticks)
- Links and images
- Tables
- Blockquotes
- Emphasis (_italic_, **bold**)

**Example**:

````markdown
# Introduction

This is a note about **important concepts**.

## Key Points

1. First point
2. Second point

```python
def hello():
    print("Hello, world!")
```
````

````

#### `size` (integer, ≥ 0)

The size of the note content in bytes, calculated using UTF-8 encoding.

- **Type**: integer
- **Constraints**: Must be non-negative (≥ 0)
- **Purpose**: Used for statistics, filtering, and progress tracking
- **Calculation**: `len(markdown.encode('utf-8'))`

**Examples**:
- Empty note: `0`
- Small note (100 characters): ~`100`
- Large note (10KB): ~`10000`

**Why This Matters**:
- Helps users understand collection composition
- Useful for filtering very short or very long notes
- Enables progress bars during processing

#### `modificationDate` (string, ISO 8601)

The date and time when the note was last modified.

- **Type**: string
- **Format**: ISO 8601 datetime (`YYYY-MM-DDTHH:MM:SS` with optional timezone)
- **Constraints**: Must match pattern `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`
- **Purpose**: Chronological sorting, incremental updates, metadata preservation

**Recommended Format**: UTC with 'Z' suffix
- ✅ Good: `"2025-10-20T14:30:00Z"`
- ⚠️ Acceptable: `"2025-10-20T14:30:00"`
- ⚠️ Acceptable: `"2025-10-20T14:30:00-05:00"`
- ❌ Invalid: `"2025-10-20"` (missing time)
- ❌ Invalid: `"20/10/2025 14:30"` (wrong format)

**Python Example**:
```python
from datetime import datetime, timezone

# UTC timestamp
utc_now = datetime.now(timezone.utc).isoformat()
# Result: '2025-10-20T14:30:00+00:00'

# With 'Z' suffix (recommended)
utc_now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
# Result: '2025-10-20T14:30:00Z'
````

### Optional Fields

#### `creationDate` (string, ISO 8601)

The date and time when the note was originally created.

- **Type**: string
- **Format**: Same as `modificationDate` (ISO 8601)
- **Optional**: Yes
- **Purpose**: Track note age, sort by creation time

If the source system provides creation dates, include them. Otherwise, this field can be omitted.

### Custom Fields (Additional Properties)

Extractors may include **any additional fields** to preserve source-specific metadata.

**Allowed Custom Fields Examples**:

- `"tags": ["project", "important"]` - Note tags or categories
- `"author": "John Doe"` - Note author
- `"sourceId": "bear-uuid-12345"` - Original ID in source system
- `"url": "https://example.com/article"` - Original URL
- `"archived": false` - Archive status
- `"pinned": true` - Pin status
- `"folder": "/Projects/2025"` - Folder location

**Important**: Custom fields are preserved but not validated. Use consistent naming across your extractor.

---

## Validation Rules

Minerva validates notes using the following rules:

### Structural Validation

1. **Root must be array**: The top-level JSON must be an array `[...]`
2. **Items must be objects**: Each array element must be a JSON object `{...}`
3. **Empty arrays allowed**: `[]` is valid (0 notes)

### Field Validation

For each note in the array:

1. **Required fields present**: `title`, `markdown`, `size`, `modificationDate` must exist
2. **Type checking**: Fields must have correct types (string, integer, etc.)
3. **Non-empty title**: `title` must have at least 1 character
4. **Non-negative size**: `size` must be ≥ 0
5. **ISO 8601 dates**: Date fields must match the ISO pattern
6. **String dates**: Date fields must be strings, not numbers or dates

### Validation Modes

#### Strict Mode (default)

Stops at first error, reports one issue at a time.

```bash
minerva validate notes.json
```

#### Non-Strict Mode

Collects all errors and reports them together.

```bash
minerva validate notes.json --verbose
```

---

## Examples

### Minimal Valid Note

The absolute minimum required to pass validation:

```json
[
  {
    "title": "My Note",
    "markdown": "",
    "size": 0,
    "modificationDate": "2025-10-20T10:00:00Z"
  }
]
```

### Complete Note with All Standard Fields

```json
[
  {
    "title": "Introduction to RAG Systems",
    "markdown": "# Introduction to RAG Systems\n\nRetrieval-Augmented Generation (RAG) combines...",
    "size": 2847,
    "modificationDate": "2025-10-20T14:30:00Z",
    "creationDate": "2025-10-15T09:00:00Z"
  }
]
```

### Note with Custom Metadata

```json
[
  {
    "title": "Project Planning Q1 2025",
    "markdown": "# Q1 Planning\n\n## Goals\n- Launch new feature\n- Improve performance",
    "size": 1234,
    "modificationDate": "2025-10-20T14:30:00Z",
    "creationDate": "2025-01-05T08:00:00Z",
    "tags": ["planning", "2025", "Q1"],
    "author": "Michele Orsini",
    "pinned": true,
    "folder": "/Projects/2025",
    "sourceId": "bear-note-abcd-1234"
  }
]
```

### Multiple Notes (Typical Extractor Output)

```json
[
  {
    "title": "Meeting Notes - Oct 15",
    "markdown": "## Attendees\n- Alice\n- Bob\n\n## Discussion\n...",
    "size": 456,
    "modificationDate": "2025-10-15T16:00:00Z",
    "creationDate": "2025-10-15T14:00:00Z"
  },
  {
    "title": "Python Best Practices",
    "markdown": "# Python Best Practices\n\n## Code Style\nFollow PEP 8...",
    "size": 3201,
    "modificationDate": "2025-10-18T10:30:00Z",
    "creationDate": "2025-09-20T11:00:00Z",
    "tags": ["python", "coding", "best-practices"]
  },
  {
    "title": "TODO List",
    "markdown": "- [ ] Buy groceries\n- [x] Finish report\n- [ ] Call dentist",
    "size": 89,
    "modificationDate": "2025-10-20T08:15:00Z"
  }
]
```

### Edge Cases

#### Empty markdown (valid)

```json
[
  {
    "title": "Untitled Note",
    "markdown": "",
    "size": 0,
    "modificationDate": "2025-10-20T10:00:00Z"
  }
]
```

#### Very long title (valid but not recommended)

```json
[
  {
    "title": "This is an extremely long note title that goes on and on and probably should be shortened but technically is still valid according to the schema rules",
    "markdown": "Content...",
    "size": 100,
    "modificationDate": "2025-10-20T10:00:00Z"
  }
]
```

---

## Common Errors

### Error: Missing required field

```
✗ Note at index 0: Missing required fields: title, size
```

**Cause**: Note is missing one or more required fields.

**Fix**: Ensure all four required fields are present:

```json
{
  "title": "My Note",
  "markdown": "Content",
  "size": 123,
  "modificationDate": "2025-10-20T10:00:00Z"
}
```

### Error: Title cannot be empty

```
✗ Note at index 0: 'title' cannot be empty
```

**Cause**: Title field exists but is an empty string.

**Fix**: Provide a non-empty title:

```json
{
  "title": "Untitled Note" // Not ""
}
```

### Error: Invalid date format

```
✗ Note at index 0: 'modificationDate' must be ISO 8601 format (YYYY-MM-DDTHH:MM:SS...)
```

**Cause**: Date doesn't match ISO 8601 pattern.

**Fix**: Use correct format:

```json
{
  "modificationDate": "2025-10-20T14:30:00Z" // Not "10/20/2025"
}
```

### Error: Size must be non-negative

```
✗ Note at index 0: 'size' must be non-negative, got -100
```

**Cause**: Size field is negative.

**Fix**: Calculate size correctly:

```python
size = len(markdown.encode('utf-8'))  # Always >= 0
```

### Error: Expected array, got object

```
✗ Expected an array of notes, got dict
```

**Cause**: Root JSON is an object `{...}` instead of array `[...]`.

**Fix**: Wrap notes in an array:

```json
[
  { note 1 },
  { note 2 }
]
```

Not:

```json
{ note 1 }
```

---

## Best Practices

### For Extractor Developers

1. **Always output arrays**: Even for single notes, wrap in `[...]`
2. **Use UTF-8 encoding**: Calculate size with `len(text.encode('utf-8'))`
3. **Prefer UTC timestamps**: Add 'Z' suffix for clarity
4. **Generate titles**: If source has no title, generate from first heading or content
5. **Preserve rich metadata**: Use custom fields for source-specific data
6. **Test with validation**: Run `minerva validate` during development
7. **Handle encoding properly**: Ensure markdown is valid UTF-8
8. **Normalize timestamps**: Convert all dates to UTC for consistency

### For Users

1. **Validate before indexing**: Always run `minerva validate notes.json` first
2. **Check error messages**: Validation errors point to specific issues
3. **Use verbose mode**: `--verbose` shows all errors at once
4. **Keep backups**: Keep original source files before extraction
5. **Verify samples**: Inspect a few notes manually to ensure quality

### Python Extractor Template

```python
#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

def extract_notes(input_path):
    """Extract notes from source and convert to Minerva schema."""
    notes = []

    # Your extraction logic here...
    for item in your_source_data:
        markdown = item.get_content()

        note = {
            "title": item.title or "Untitled",
            "markdown": markdown,
            "size": len(markdown.encode('utf-8')),
            "modificationDate": item.modified.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        # Optional fields
        if item.created:
            note["creationDate"] = item.created.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Custom metadata
        if item.tags:
            note["tags"] = item.tags

        notes.append(note)

    return notes

if __name__ == "__main__":
    notes = extract_notes("input.source")
    print(json.dumps(notes, indent=2, ensure_ascii=False))
```

### Shell Script Extractor Example

```bash
#!/bin/bash
# Simple extractor that converts text files to Minerva format

echo "["
first=true

for file in *.txt; do
    [[ $first == false ]] && echo ","
    first=false

    title=$(basename "$file" .txt)
    content=$(cat "$file")
    size=$(wc -c < "$file")
    modified=$(stat -f "%Sm" -t "%Y-%m-%dT%H:%M:%SZ" "$file")

    jq -n \
        --arg title "$title" \
        --arg markdown "$content" \
        --argjson size "$size" \
        --arg modified "$modified" \
        '{
            title: $title,
            markdown: $markdown,
            size: $size,
            modificationDate: $modified
        }'
done

echo "]"
```

---

## Testing Your Extractor

### 1. Extract a small sample

```bash
your-extractor input.source -o sample.json
```

### 2. Validate the output

```bash
minerva validate sample.json --verbose
```

### 3. Inspect manually

```bash
jq '.[0]' sample.json  # Look at first note
jq 'length' sample.json  # Count notes
jq '.[].title' sample.json  # List all titles
```

### 4. Check encoding

```bash
file sample.json  # Should show "UTF-8 Unicode text"
```

### 5. Test with Minerva

```bash
# Create test config
cat > test-config.json << 'EOF'
{
  "collection_name": "test_collection",
  "description": "Test collection for validation",
  "chromadb_path": "./test_chromadb",
  "json_file": "sample.json"
}
EOF

# Dry run (validates without indexing)
minerva index --config test-config.json --dry-run
```

---

## Schema Versioning

**Current Version**: 1.0.0

The schema follows semantic versioning:

- **Major version**: Breaking changes (new required fields)
- **Minor version**: Backward-compatible additions (new optional fields)
- **Patch version**: Documentation updates, clarifications

Future versions will maintain backward compatibility whenever possible. Extractors should target specific schema versions in their documentation.

---

## Resources

- **Validation Tool**: `minerva validate notes.json`
- **Schema Implementation**: [`minerva/common/schemas.py`](../minerva/common/schemas.py)
- **Extractor Guide**: [EXTRACTOR_GUIDE.md](EXTRACTOR_GUIDE.md)
- **Example Extractors**: [`extractors/`](../extractors/)

---

## Questions or Issues?

If you encounter schema-related issues:

1. Check this documentation
2. Run `minerva validate` with `--verbose` for detailed errors
3. Review example extractors in `extractors/` directory
4. Open an issue on [GitHub](https://github.com/yourusername/minerva/issues)
