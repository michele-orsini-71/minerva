# Minerva Extractor Development Guide

Learn how to build custom extractors to bring any data source into Minerva.

## Table of Contents

- [Overview](#overview)
- [What is an Extractor?](#what-is-an-extractor)
- [Quick Start Tutorial](#quick-start-tutorial)
- [Language-Specific Examples](#language-specific-examples)
- [Testing Your Extractor](#testing-your-extractor)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Packaging and Distribution](#packaging-and-distribution)
- [Troubleshooting](#troubleshooting)

---

## Overview

Extractors are independent programs that convert data from specific sources (apps, databases, APIs, files) into the [Minerva Note Schema](NOTE_SCHEMA.md). They act as adapters between the Minerva indexing system and your data.

### Key Principles

1. **Language Agnostic**: Write extractors in any language (Python, JavaScript, Go, Rust, Bash, etc.)
2. **Single Responsibility**: Each extractor handles one source type
3. **Standard Output**: All extractors output JSON conforming to the note schema
4. **Independent**: Extractors have no dependencies on Minerva core
5. **Testable**: Use `minerva validate` to verify output

### The Extractor Pipeline

```
┌─────────────────┐
│  Data Source    │  ← Your specific format
│ (Bear, Notion,  │
│  Obsidian, DB)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   EXTRACTOR     │  ← Your code (any language)
│  (Your Code)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Standard JSON   │  ← Minerva Note Schema
│   (stdout)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  minerva      │  ← Validation & Indexing
│   validate      │
│   & index       │
└─────────────────┘
```

---

## What is an Extractor?

An extractor is any program that:

1. **Reads** data from a specific source
2. **Converts** that data to the Minerva Note Schema
3. **Outputs** valid JSON (to stdout or file)

### Minimal Extractor Requirements

✅ Outputs a JSON array of note objects
✅ Each note has required fields: `title`, `markdown`, `size`, `modificationDate`
✅ Dates are in ISO 8601 format
✅ JSON is valid UTF-8

### Optional Features

- Command-line arguments for input/output
- Progress reporting (to stderr)
- Error handling and logging
- Filtering and transformation options
- Packaging as installable tool

---

## Quick Start Tutorial

Let's build a simple extractor that converts plain text files into Minerva notes.

### Step 1: Understand Your Source Data

First, examine what you're extracting from:

```bash
# Example: Directory of text files
ls ~/my-notes/
  meeting-2025-10-15.txt
  project-ideas.txt
  todo.txt
```

Each file contains plain text that should become a note.

### Step 2: Design the Mapping

Decide how source data maps to the note schema:

| Source                  | Note Schema Field  |
| ----------------------- | ------------------ |
| Filename (without .txt) | `title`            |
| File contents           | `markdown`         |
| File size in bytes      | `size`             |
| File modification time  | `modificationDate` |
| File creation time      | `creationDate`     |

### Step 3: Write the Extractor

Here's a complete Python extractor:

```python
#!/usr/bin/env python3
"""
text-extractor: Convert text files to Minerva notes
Usage: text-extractor <directory> [-o output.json]
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def extract_text_files(directory):
    """Extract all .txt files from directory."""
    notes = []
    text_files = sorted(Path(directory).glob("*.txt"))

    for filepath in text_files:
        # Read file content
        content = filepath.read_text(encoding='utf-8')

        # Get file stats
        stat = filepath.stat()

        # Create note object
        note = {
            "title": filepath.stem,  # filename without extension
            "markdown": content,
            "size": len(content.encode('utf-8')),
            "modificationDate": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "creationDate": datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }

        notes.append(note)

    return notes

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: text-extractor <directory> [-o output.json]", file=sys.stderr)
        sys.exit(1)

    directory = sys.argv[1]
    notes = extract_text_files(directory)

    # Output JSON
    output = json.dumps(notes, indent=2, ensure_ascii=False)

    # Check if output file specified
    if len(sys.argv) > 2 and sys.argv[2] == "-o":
        Path(sys.argv[3]).write_text(output, encoding='utf-8')
        print(f"Extracted {len(notes)} notes to {sys.argv[3]}", file=sys.stderr)
    else:
        print(output)

```

### Step 4: Test the Extractor

```bash
# Make it executable
chmod +x text-extractor

# Run it
./text-extractor ~/my-notes -o notes.json

# Validate the output
minerva validate notes.json
# ✓ Validation successful: notes.json contains 3 valid note(s)
```

### Step 5: Index the Notes

```bash
# Create config
cat > config.json << 'EOF'
{
  "collection_name": "my_text_notes",
  "description": "Personal notes from text files",
  "chromadb_path": "./chromadb_data",
  "json_file": "notes.json"
}
EOF

# Index
minerva index --config config.json --verbose
```

That's it! You've built your first extractor. 🎉

---

## Language-Specific Examples

### Python Extractor

**Advantages**: Rich ecosystem, easy JSON handling, great for complex parsing

```python
#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

def extract_notes(source_path):
    """Extract notes from your source."""
    notes = []

    # Your extraction logic here
    # Example: CSV file
    import csv
    with open(source_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            markdown = f"# {row['title']}\n\n{row['content']}"

            note = {
                "title": row['title'],
                "markdown": markdown,
                "size": len(markdown.encode('utf-8')),
                "modificationDate": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            }

            # Optional: custom metadata
            if 'tags' in row:
                note['tags'] = row['tags'].split(',')

            notes.append(note)

    return notes

def main():
    if len(sys.argv) < 2:
        print("Usage: extractor <input> [-o output.json]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    notes = extract_notes(input_path)

    # Handle output
    json_output = json.dumps(notes, indent=2, ensure_ascii=False)

    if len(sys.argv) > 2 and sys.argv[2] == '-o':
        output_file = sys.argv[3]
        Path(output_file).write_text(json_output, encoding='utf-8')
        print(f"✓ Extracted {len(notes)} notes to {output_file}", file=sys.stderr)
    else:
        print(json_output)

if __name__ == "__main__":
    main()
```

**Dependencies**: None (uses only stdlib)

### JavaScript/Node.js Extractor

**Advantages**: Great for web APIs, JSON native, async/await support

```javascript
#!/usr/bin/env node
/**
 * markdown-extractor: Convert markdown files to Minerva notes
 * Usage: markdown-extractor <directory> [-o output.json]
 */

const fs = require("fs").promises;
const path = require("path");

async function extractMarkdownFiles(directory) {
  const notes = [];
  const files = await fs.readdir(directory);

  for (const filename of files) {
    if (!filename.endsWith(".md")) continue;

    const filepath = path.join(directory, filename);
    const content = await fs.readFile(filepath, "utf-8");
    const stats = await fs.stat(filepath);

    // Extract title from first heading or use filename
    const titleMatch = content.match(/^#\s+(.+)$/m);
    const title = titleMatch ? titleMatch[1] : path.basename(filename, ".md");

    const note = {
      title: title,
      markdown: content,
      size: Buffer.byteLength(content, "utf-8"),
      modificationDate: stats.mtime.toISOString(),
      creationDate: stats.birthtime.toISOString(),
    };

    notes.push(note);
  }

  return notes;
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length < 1) {
    console.error("Usage: markdown-extractor <directory> [-o output.json]");
    process.exit(1);
  }

  const directory = args[0];
  const notes = await extractMarkdownFiles(directory);
  const jsonOutput = JSON.stringify(notes, null, 2);

  // Check for output file
  const outputIndex = args.indexOf("-o");
  if (outputIndex !== -1 && args[outputIndex + 1]) {
    const outputFile = args[outputIndex + 1];
    await fs.writeFile(outputFile, jsonOutput, "utf-8");
    console.error(`✓ Extracted ${notes.length} notes to ${outputFile}`);
  } else {
    console.log(jsonOutput);
  }
}

main().catch((err) => {
  console.error("Error:", err.message);
  process.exit(1);
});
```

**Run**: `node markdown-extractor.js ~/docs -o notes.json`

### Bash Extractor

**Advantages**: No dependencies, works anywhere, great for simple sources

```bash
#!/bin/bash
# json-extractor: Convert JSON entries to Minerva notes
# Usage: json-extractor <input.json> [-o output.json]

set -e

if [ $# -lt 1 ]; then
    echo "Usage: json-extractor <input.json> [-o output.json]" >&2
    exit 1
fi

input_file="$1"
output_file=""

# Check for -o flag
if [ "$2" = "-o" ] && [ -n "$3" ]; then
    output_file="$3"
fi

# Process JSON using jq
result=$(jq '[.[] | {
    title: .name,
    markdown: ("# " + .name + "\n\n" + .description),
    size: (("# " + .name + "\n\n" + .description) | length),
    modificationDate: (.updated // now | strftime("%Y-%m-%dT%H:%M:%SZ")),
    creationDate: (.created // now | strftime("%Y-%m-%dT%H:%M:%SZ"))
}]' "$input_file")

# Output
if [ -n "$output_file" ]; then
    echo "$result" > "$output_file"
    count=$(echo "$result" | jq 'length')
    echo "✓ Extracted $count notes to $output_file" >&2
else
    echo "$result"
fi
```

**Dependencies**: `jq` (JSON processor)

### Go Extractor

**Advantages**: Fast, compiled binary, excellent error handling

```go
package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"time"
)

type Note struct {
	Title            string `json:"title"`
	Markdown         string `json:"markdown"`
	Size             int    `json:"size"`
	ModificationDate string `json:"modificationDate"`
	CreationDate     string `json:"creationDate,omitempty"`
}

func extractTextFiles(directory string) ([]Note, error) {
	var notes []Note

	files, err := filepath.Glob(filepath.Join(directory, "*.txt"))
	if err != nil {
		return nil, err
	}

	for _, filepath := range files {
		content, err := ioutil.ReadFile(filepath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Warning: Could not read %s: %v\n", filepath, err)
			continue
		}

		info, err := os.Stat(filepath)
		if err != nil {
			continue
		}

		title := filepath[:len(filepath)-4] // Remove .txt
		markdown := string(content)

		note := Note{
			Title:            filepath.Base(title),
			Markdown:         markdown,
			Size:             len(content),
			ModificationDate: info.ModTime().UTC().Format(time.RFC3339),
		}

		notes = append(notes, note)
	}

	return notes, nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "Usage: text-extractor <directory> [-o output.json]")
		os.Exit(1)
	}

	directory := os.Args[1]
	notes, err := extractTextFiles(directory)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	jsonData, err := json.MarshalIndent(notes, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error encoding JSON: %v\n", err)
		os.Exit(1)
	}

	// Check for output file
	if len(os.Args) > 2 && os.Args[2] == "-o" && len(os.Args) > 3 {
		outputFile := os.Args[3]
		err = ioutil.WriteFile(outputFile, jsonData, 0644)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error writing file: %v\n", err)
			os.Exit(1)
		}
		fmt.Fprintf(os.Stderr, "✓ Extracted %d notes to %s\n", len(notes), outputFile)
	} else {
		fmt.Println(string(jsonData))
	}
}
```

**Build**: `go build -o text-extractor extractor.go`

---

## Testing Your Extractor

### 1. Unit Testing (During Development)

Test individual functions before integration:

```python
# test_extractor.py
import json
from your_extractor import extract_notes

def test_basic_extraction():
    """Test that extraction produces valid structure."""
    notes = extract_notes("test-data/sample.source")

    assert isinstance(notes, list)
    assert len(notes) > 0

    # Check first note has required fields
    note = notes[0]
    assert "title" in note
    assert "markdown" in note
    assert "size" in note
    assert "modificationDate" in note

    # Check types
    assert isinstance(note["title"], str)
    assert isinstance(note["markdown"], str)
    assert isinstance(note["size"], int)
    assert len(note["title"]) > 0

def test_json_output():
    """Test that output is valid JSON."""
    notes = extract_notes("test-data/sample.source")
    json_str = json.dumps(notes)

    # Should parse without errors
    parsed = json.loads(json_str)
    assert isinstance(parsed, list)
```

### 2. Schema Validation (Integration Test)

Use Minerva's validator:

```bash
# Extract to temp file
./your-extractor test-data/sample.source -o /tmp/test-output.json

# Validate with Minerva
minerva validate /tmp/test-output.json --verbose

# Check exit code
if [ $? -eq 0 ]; then
    echo "✓ Schema validation passed"
else
    echo "✗ Schema validation failed"
    exit 1
fi
```

### 3. End-to-End Testing

Test the complete workflow:

```bash
#!/bin/bash
# test-e2e.sh - End-to-end extractor test

set -e

echo "Running end-to-end extractor test..."

# 1. Extract
echo "1. Extracting notes..."
./your-extractor test-data/sample.source -o /tmp/e2e-test.json

# 2. Validate
echo "2. Validating schema..."
minerva validate /tmp/e2e-test.json

# 3. Test indexing (dry run)
echo "3. Testing indexing (dry run)..."
cat > /tmp/e2e-config.json << 'EOF'
{
  "collection_name": "e2e_test",
  "description": "End-to-end test collection",
  "chromadb_path": "/tmp/e2e-chromadb",
  "json_file": "/tmp/e2e-test.json"
}
EOF

minerva index --config /tmp/e2e-config.json --dry-run

# 4. Cleanup
rm -rf /tmp/e2e-test.json /tmp/e2e-config.json /tmp/e2e-chromadb

echo "✓ All tests passed!"
```

### 4. Sample Data Testing

Create representative test files:

```
test-data/
  ├── empty.source          # Edge case: empty file
  ├── single.source         # Minimal: 1 note
  ├── multiple.source       # Normal: multiple notes
  ├── unicode.source        # Unicode characters
  ├── large.source          # Large file (stress test)
  └── malformed.source      # Invalid source (should handle gracefully)
```

Test all cases:

```bash
for test_file in test-data/*.source; do
    echo "Testing: $test_file"
    ./your-extractor "$test_file" -o /tmp/test.json
    minerva validate /tmp/test.json || echo "Failed: $test_file"
done
```

### 5. Continuous Testing

Add to CI/CD pipeline:

```yaml
# .github/workflows/test-extractor.yml
name: Test Extractor

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install Minerva
        run: pip install minerva

      - name: Run extractor tests
        run: |
          chmod +x your-extractor
          ./test-e2e.sh
```

---

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
def extract_with_error_handling(source_path):
    notes = []
    errors = []

    try:
        items = parse_source(source_path)
    except Exception as e:
        print(f"Error parsing source: {e}", file=sys.stderr)
        sys.exit(1)

    for i, item in enumerate(items):
        try:
            note = convert_to_note(item)
            notes.append(note)
        except Exception as e:
            errors.append(f"Item {i}: {e}")
            print(f"Warning: Skipping item {i}: {e}", file=sys.stderr)

    if errors:
        print(f"\nEncountered {len(errors)} errors during extraction", file=sys.stderr)

    return notes
```

### 2. Progress Reporting

Show progress for long operations (to stderr):

```python
import sys

def extract_with_progress(items):
    notes = []
    total = len(items)

    for i, item in enumerate(items, 1):
        note = convert_to_note(item)
        notes.append(note)

        # Progress to stderr (doesn't interfere with JSON stdout)
        if i % 100 == 0 or i == total:
            print(f"\rProcessed {i}/{total} items...", end='', file=sys.stderr)

    print(file=sys.stderr)  # Newline
    return notes
```

### 3. UTF-8 Encoding

Always use UTF-8:

```python
# Reading files
content = Path(filepath).read_text(encoding='utf-8')

# Writing JSON
with open(output, 'w', encoding='utf-8') as f:
    json.dump(notes, f, ensure_ascii=False, indent=2)

# Calculating size
size = len(markdown.encode('utf-8'))
```

### 4. Date Normalization

Convert all dates to UTC:

```python
from datetime import datetime, timezone

def to_utc_iso(timestamp):
    """Convert any timestamp to UTC ISO format."""
    if isinstance(timestamp, str):
        # Parse string timestamp
        dt = datetime.fromisoformat(timestamp)
    elif isinstance(timestamp, (int, float)):
        # Unix timestamp
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    else:
        dt = timestamp

    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
```

### 5. Title Generation

Generate meaningful titles for untitled content:

```python
def generate_title(markdown, max_length=100):
    """Generate title from markdown content."""
    # Try first heading
    heading_match = re.match(r'^#+\s+(.+)$', markdown, re.MULTILINE)
    if heading_match:
        return heading_match.group(1)[:max_length]

    # Try first sentence
    first_line = markdown.strip().split('\n')[0]
    if first_line:
        return first_line[:max_length].rstrip('.')

    # Fallback
    return "Untitled Note"
```

### 6. Command-Line Interface

Follow Unix conventions:

```python
import argparse

def create_parser():
    parser = argparse.ArgumentParser(
        description='Extract notes from SOURCE',
        epilog='Example: %(prog)s input.source -o notes.json'
    )

    parser.add_argument('input', help='Input source file or directory')
    parser.add_argument('-o', '--output', help='Output JSON file (default: stdout)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    return parser
```

### 7. Metadata Preservation

Keep source-specific metadata:

```python
note = {
    # Required fields
    "title": title,
    "markdown": markdown,
    "size": size,
    "modificationDate": mod_date,

    # Optional standard field
    "creationDate": create_date,

    # Custom metadata (preserved by Minerva)
    "source": "my-app",
    "sourceId": original_id,
    "tags": tags,
    "author": author,
    "url": original_url,
}
```

---

## Common Patterns

### Pattern 1: Database Extractor

Extract from SQL database:

```python
import sqlite3
import json

def extract_from_database(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, content, created_at, updated_at, tags
        FROM notes
        WHERE deleted = 0
        ORDER BY updated_at DESC
    """)

    notes = []
    for row in cursor:
        note = {
            "title": row['title'] or f"Note {row['id']}",
            "markdown": row['content'] or "",
            "size": len((row['content'] or "").encode('utf-8')),
            "modificationDate": row['updated_at'],
            "creationDate": row['created_at'],
            "tags": json.loads(row['tags']) if row['tags'] else [],
            "sourceId": f"db-{row['id']}"
        }
        notes.append(note)

    conn.close()
    return notes
```

### Pattern 2: API Extractor

Fetch from REST API:

```python
import requests

def extract_from_api(api_url, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    notes = []
    page = 1

    while True:
        response = requests.get(
            f"{api_url}/notes",
            headers=headers,
            params={"page": page, "per_page": 100}
        )
        response.raise_for_status()

        data = response.json()
        if not data['notes']:
            break

        for item in data['notes']:
            note = {
                "title": item['title'],
                "markdown": item['body'],
                "size": len(item['body'].encode('utf-8')),
                "modificationDate": item['updated_at'],
                "creationDate": item['created_at'],
                "sourceId": item['id'],
                "url": item['url']
            }
            notes.append(note)

        page += 1

    return notes
```

### Pattern 3: Archive Extractor

Extract from ZIP/TAR archives:

```python
import zipfile
from pathlib import Path

def extract_from_zip(archive_path):
    notes = []

    with zipfile.ZipFile(archive_path, 'r') as zf:
        for info in zf.infolist():
            if not info.filename.endswith('.md'):
                continue

            content = zf.read(info.filename).decode('utf-8')

            note = {
                "title": Path(info.filename).stem,
                "markdown": content,
                "size": len(content.encode('utf-8')),
                "modificationDate": datetime(*info.date_time).strftime('%Y-%m-%dT%H:%M:%SZ'),
            }
            notes.append(note)

    return notes
```

### Pattern 4: Incremental Extractor

Only extract new/modified notes:

```python
import json
from pathlib import Path

def load_previous_extraction(cache_file):
    """Load IDs and timestamps from previous extraction."""
    if not Path(cache_file).exists():
        return {}

    with open(cache_file) as f:
        data = json.load(f)
        return {note['sourceId']: note['modificationDate'] for note in data}

def extract_incremental(source, cache_file='extractor-cache.json'):
    previous = load_previous_extraction(cache_file)
    notes = []

    for item in get_source_items(source):
        item_id = item['id']
        item_modified = item['modified']

        # Skip if not modified since last extraction
        if item_id in previous and previous[item_id] == item_modified:
            continue

        note = convert_to_note(item)
        notes.append(note)

    print(f"Found {len(notes)} new/modified notes", file=sys.stderr)
    return notes
```

---

## Packaging and Distribution

### Python Package Structure

```
my-extractor/
├── setup.py
├── README.md
├── LICENSE
├── my_extractor/
│   ├── __init__.py
│   ├── cli.py
│   └── parser.py
└── tests/
    └── test_parser.py
```

**setup.py**:

```python
from setuptools import setup, find_packages

setup(
    name="my-extractor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        # Your dependencies here
    ],
    entry_points={
        "console_scripts": [
            "my-extractor=my_extractor.cli:main",
        ],
    },
    python_requires=">=3.8",
)
```

### Installation

```bash
# Install locally for development
pip install -e .

# Install from PyPI (after publishing)
pip install my-extractor

# Use with pipx (isolated)
pipx install my-extractor
```

---

## Troubleshooting

### Issue: "Expected an array, got dict"

**Cause**: Outputting single object instead of array.

**Fix**:

```python
# Wrong
print(json.dumps(note))

# Right
print(json.dumps([note]))  # Wrap in array
```

### Issue: "Invalid ISO date format"

**Cause**: Date format doesn't match ISO 8601.

**Fix**:

```python
# Use strftime with correct format
date_str = dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# Or use isoformat
date_str = dt.isoformat()
```

### Issue: "Unicode encoding error"

**Cause**: Non-UTF-8 encoding.

**Fix**:

```python
# Specify encoding when reading
content = open(file, encoding='utf-8').read()

# Handle errors gracefully
content = open(file, encoding='utf-8', errors='replace').read()
```

### Issue: Extractor is slow

**Optimization strategies**:

1. **Batch processing**: Process multiple items before I/O
2. **Parallel processing**: Use multiprocessing for CPU-bound work
3. **Streaming**: Don't load entire dataset into memory
4. **Caching**: Cache parsed results

```python
from multiprocessing import Pool

def extract_parallel(items):
    with Pool() as pool:
        notes = pool.map(convert_to_note, items)
    return notes
```

---

## Next Steps

- Review the [Note Schema](NOTE_SCHEMA.md) specification
- Study [official extractors](../extractors/) for real-world examples
- Join the community to share your extractors
- Submit your extractor to the official registry

**Questions?** Open an issue on [GitHub](https://github.com/yourusername/minerva/issues)

Happy extracting! 🚀
