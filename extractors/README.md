# Minerva Official Extractors

This directory contains official extractors for converting various data sources into the Minerva Note Schema.

## Overview

Extractors are independent tools that transform data from specific sources (apps, databases, file formats) into standardized JSON that Minerva can index. Each extractor is a standalone package that can be installed and used independently of Minerva core.

### Why Separate Extractors?

- **Independence**: No dependency on Minerva core - just output JSON
- **Language Freedom**: Write extractors in any language (all official extractors happen to be Python)
- **Focused Scope**: Each extractor handles one source type very well
- **Easy Testing**: Validate output with `minerva validate` before indexing
- **Distribution**: Install only the extractors you need

---

## Official Extractors

### 📝 Bear Notes Extractor

**Package**: `bear-notes-extractor`
**Command**: `bear-extractor`
**Source**: Bear app backup files (.bear2bk format)

Extract notes from Bear app backups into Minerva-compatible JSON.

**Features**:

- Extracts notes from Bear 2.x backup archives
- Preserves markdown formatting
- Filters out trashed notes automatically
- Maintains creation and modification dates
- Zero dependencies (uses only Python stdlib)

**Installation**:

```bash
cd extractors/bear-notes-extractor
pip install -e .
```

**Quick Start**:

```bash
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o notes.json
minerva validate notes.json
```

[📖 Full Documentation](bear-notes-extractor/README.md)

---

### 🌍 Zim Extractor

**Package**: `zim-extractor`
**Command**: `zim-extractor`
**Source**: ZIM archive files (Wikipedia dumps, offline content)

Extract articles from ZIM archives (offline Wikipedia, educational content, etc.) into searchable notes.

**Features**:

- Reads ZIM archives using libzim
- Converts HTML articles to clean markdown
- Extracts article metadata (title, last modified)
- Handles large archives efficiently
- Preserves article structure

**Dependencies**:

- `libzim>=3.0.0` (ZIM archive reader)
- `markdownify>=0.11.0` (HTML to Markdown conversion)

**Installation**:

```bash
cd extractors/zim-extractor
pip install -e .
```

**Quick Start**:

```bash
zim-extractor "wikipedia_en_history.zim" -o wiki.json
minerva validate wiki.json
```

[📖 Full Documentation](zim-extractor/README.md)

---

### 📚 Markdown Books Extractor

**Package**: `markdown-books-extractor`
**Command**: `markdown-books-extractor`
**Source**: Markdown book files and directories

Extract structured markdown books (like Project Gutenberg exports) into individual note entries.

**Features**:

- Processes directories of markdown files
- Extracts book metadata from frontmatter
- Generates titles from headings or filenames
- Handles multiple books in one directory
- Zero dependencies (uses only Python stdlib)

**Installation**:

```bash
cd extractors/markdown-books-extractor
pip install -e .
```

**Quick Start**:

```bash
markdown-books-extractor ~/books/alice-in-wonderland.md -o book.json
minerva validate book.json
```

[📖 Full Documentation](markdown-books-extractor/README.md)

---

## Quick Comparison

| Extractor                    | Source Type             | Dependencies        | Output Size    | Use Case                   |
| ---------------------------- | ----------------------- | ------------------- | -------------- | -------------------------- |
| **bear-extractor**           | Bear backups (.bear2bk) | None                | 100-10K notes  | Personal note-taking       |
| **zim-extractor**            | ZIM archives            | libzim, markdownify | 1K-1M articles | Wikipedia, offline content |
| **markdown-books-extractor** | Markdown files          | None                | 1-100 books    | Literature, documentation  |

---

## Installation

### Install All Extractors

```bash
# From the project root
cd extractors

# Install each extractor
for extractor in bear-notes-extractor zim-extractor markdown-books-extractor; do
    echo "Installing $extractor..."
    cd $extractor
    pip install -e .
    cd ..
done

# Verify installations
bear-extractor --help
zim-extractor --help
markdown-books-extractor --help
```

### Install Individual Extractor

```bash
# Navigate to specific extractor
cd extractors/bear-notes-extractor

# Install in development mode
pip install -e .

# Or install from source
pip install .

# Or use pipx for isolation
pipx install .
```

---

## Usage Workflow

All extractors follow the same general workflow:

### 1. Extract

Run the extractor to convert your source data:

```bash
# Example with Bear extractor
bear-extractor "backup.bear2bk" -o notes.json
```

### 2. Validate

Verify the output conforms to the Minerva schema:

```bash
minerva validate notes.json --verbose
# ✓ Validation successful: notes.json contains 1,234 valid note(s)
```

### 3. Index

Create a configuration and index the notes:

```bash
# Create index config
cat > config.json << 'EOF'
{
  "collection_name": "my_bear_notes",
  "description": "Personal notes from Bear app",
  "chromadb_path": "./chromadb_data",
  "json_file": "notes.json"
}
EOF

# Index into Minerva
minerva index --config config.json --verbose
```

### 4. Search

Start the MCP server and search through Claude Desktop:

```bash
minerva serve --config server-config.json
```

---

## Common Options

All official extractors support these standard options:

```bash
# Output to file
extractor-name input.source -o output.json

# Output to stdout (for piping)
extractor-name input.source

# Verbose mode (progress to stderr)
extractor-name input.source -v -o output.json

# Version information
extractor-name --version

# Help text
extractor-name --help
```

---

## Multi-Source Example

Extract from multiple sources and index them separately:

```bash
# Extract from different sources
bear-extractor "Bear Backup.bear2bk" -o bear.json
zim-extractor "wikipedia_history.zim" -o wiki.json
markdown-books-extractor ~/books/ -o books.json

# Validate all outputs
minerva validate bear.json
minerva validate wiki.json
minerva validate books.json

# Index each as separate collection
minerva index --config bear-config.json
minerva index --config wiki-config.json
minerva index --config books-config.json

# All collections available through one MCP server
minerva serve --config server-config.json
```

Now you can search across your personal notes, Wikipedia articles, and book content from Claude Desktop!

---

## Writing Custom Extractors

Want to extract from a source not covered by the official extractors?

**Learn How**: See the [Extractor Development Guide](../docs/EXTRACTOR_GUIDE.md)

### What You Need

1. **Input**: Your data source (database, API, files, etc.)
2. **Output**: JSON array conforming to [Note Schema](../docs/NOTE_SCHEMA.md)
3. **Language**: Any! (Python, JavaScript, Go, Rust, Bash, etc.)

### Quick Template

Here's a minimal Python extractor:

```python
#!/usr/bin/env python3
import json
from datetime import datetime, timezone

def extract_notes(source_path):
    notes = []
    # Your extraction logic here
    for item in your_source:
        note = {
            "title": item.title,
            "markdown": item.content,
            "size": len(item.content.encode('utf-8')),
            "modificationDate": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        notes.append(note)
    return notes

if __name__ == "__main__":
    import sys
    notes = extract_notes(sys.argv[1])
    print(json.dumps(notes, indent=2))
```

Test it:

```bash
python my_extractor.py input.source > notes.json
minerva validate notes.json
```

### Resources

- **[Extractor Guide](../docs/EXTRACTOR_GUIDE.md)**: Step-by-step tutorial with examples in multiple languages
- **[Note Schema](../docs/NOTE_SCHEMA.md)**: Complete schema specification and validation rules
- **Official Extractors**: Study the source code in this directory for real-world examples

---

## Extractor Development

### Repository Structure

Each extractor follows this structure:

```
extractor-name/
├── README.md                    # Usage documentation
├── setup.py                     # Package configuration
├── extractor_package/           # Source code
│   ├── __init__.py
│   ├── cli.py                   # Command-line interface
│   └── parser.py                # Extraction logic
└── tests/                       # Tests (optional)
    └── test_parser.py
```

### Testing Your Extractor

```bash
# Unit tests (if available)
cd extractors/your-extractor
pytest tests/

# Integration test: extract and validate
./your-extractor test-data/sample.source -o /tmp/test.json
minerva validate /tmp/test.json

# End-to-end test: extract, validate, index (dry run)
./your-extractor test-data/sample.source -o /tmp/test.json
minerva validate /tmp/test.json
minerva index --config test-config.json --dry-run
```

### Best Practices

1. ✅ **Zero Minerva dependencies**: Extractors should not import from `minerva.*`
2. ✅ **Standard I/O**: Accept input as arguments, output JSON to stdout or file
3. ✅ **UTF-8 encoding**: Always use UTF-8 for reading and writing
4. ✅ **Error handling**: Handle missing files, corrupt data gracefully
5. ✅ **Progress reporting**: Print progress to stderr (not stdout)
6. ✅ **Validation**: Test output with `minerva validate` during development

---

## Troubleshooting

### Extractor Not Found After Installation

```bash
# Check if installed correctly
pip list | grep extractor

# Reinstall with -e flag
cd extractors/bear-notes-extractor
pip install -e .

# Check if command is in PATH
which bear-extractor
```

### Validation Fails

```bash
# Check what the error is
minerva validate notes.json --verbose

# Common issues:
# - Missing required fields (title, markdown, size, modificationDate)
# - Invalid date format (use ISO 8601: YYYY-MM-DDTHH:MM:SSZ)
# - Wrong root type (should be array [...], not object {...})
```

### Extraction Fails

```bash
# Run with verbose flag to see details
bear-extractor backup.bear2bk -v -o notes.json

# Check input file exists and is readable
ls -lh backup.bear2bk
file backup.bear2bk
```

---

## Contributing

### Adding a New Official Extractor

1. Create directory: `extractors/your-extractor/`
2. Follow the structure: `setup.py`, `your_package/`, `README.md`
3. Ensure zero Minerva dependencies
4. Add comprehensive README with examples
5. Test thoroughly with `minerva validate`
6. Submit pull request

### Guidelines

- **No Minerva imports**: Extractors must be independent
- **Standard schema**: Output must conform to Note Schema
- **Good documentation**: Users should understand what sources are supported
- **Error handling**: Handle edge cases gracefully
- **Testing**: Include test data and validation checks

---

## Support

- **Documentation**: [Extractor Guide](../docs/EXTRACTOR_GUIDE.md), [Note Schema](../docs/NOTE_SCHEMA.md)
- **Issues**: Report problems on [GitHub Issues](https://github.com/yourusername/minerva/issues)
- **Examples**: Study the official extractors in this directory

---

## License

All official extractors are licensed under the MIT License. See individual extractor directories for details.
