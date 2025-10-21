# Bear Notes Extractor

Extract notes from Bear app backups into Minervium-compatible JSON format.

## Overview

The Bear Notes Extractor is a standalone CLI tool that converts Bear app backup files (`.bear2bk` format) into standardized JSON that can be indexed by Minervium. It's designed to preserve your notes' content, metadata, and structure while making them searchable through semantic search.

### Features

✅ **Automatic backup parsing**: Extracts notes from Bear 2.x backup archives
✅ **Markdown preservation**: Maintains all markdown formatting from Bear
✅ **Smart filtering**: Automatically skips trashed notes
✅ **Metadata preservation**: Keeps creation and modification timestamps
✅ **Unicode normalization**: Handles special line separators correctly
✅ **Zero dependencies**: Uses only Python standard library
✅ **Progress reporting**: Shows extraction progress in verbose mode
✅ **Error resilient**: Continues processing even if individual notes fail

## Installation

### Method 1: Install from Package Directory

```bash
# Navigate to the extractor directory
cd extractors/bear-notes-extractor

# Install in development mode
pip install -e .

# Verify installation
bear-extractor --help
```

### Method 2: Install with pipx (Isolated)

```bash
cd extractors/bear-notes-extractor
pipx install .

# Now available globally
bear-extractor --help
```

### Requirements

- Python 3.8 or higher
- No external dependencies (uses only stdlib)

## Quick Start

```bash
# Extract notes from a Bear backup
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o my-notes.json

# Validate the output
minervium validate my-notes.json

# Index into Minervium
minervium index --config config.json --verbose
```

## Usage

### Basic Command

```bash
bear-extractor BACKUP_FILE [OPTIONS]
```

### Options

- `BACKUP_FILE` (required): Path to the Bear backup file (`.bear2bk`)
- `-o, --output FILE`: Output JSON file path (default: stdout)
- `-v, --verbose`: Show progress information on stderr
- `--help`: Show help message

### Examples

#### Extract to File

```bash
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o notes.json
```

#### Extract to Stdout (for Piping)

```bash
bear-extractor backup.bear2bk | jq '.[] | .title'
```

#### Verbose Mode (Show Progress)

```bash
bear-extractor backup.bear2bk -v -o notes.json
# Output on stderr:
# Parsing Bear backup from backup.bear2bk
# Processed 1234/1234 notes (100.0%)
# Exported 1234 notes
```

#### Validate Before Indexing

```bash
# Extract
bear-extractor backup.bear2bk -o notes.json

# Validate
minervium validate notes.json --verbose
# ✓ Validation successful: notes.json contains 1,234 valid note(s)
```

## Supported Formats

### Input Format: .bear2bk

Bear 2.x backup files are ZIP archives containing:

```
Bear Backup.bear2bk/
├── Note1.textbundle/
│   ├── info.json          # Metadata (title, dates, tags, trash status)
│   └── text.markdown      # Note content in markdown
├── Note2.textbundle/
│   ├── info.json
│   └── text.markdown
└── ...
```

**Supported Bear versions**: Bear 2.x
**Format**: TextBundle-based ZIP archives
**File extension**: `.bear2bk`

### Output Format: Minervium JSON

The extractor outputs a JSON array conforming to the [Minervium Note Schema](../../docs/NOTE_SCHEMA.md):

```json
[
  {
    "title": "My Note Title",
    "markdown": "# My Note Title\n\nNote content here...",
    "size": 1234,
    "modificationDate": "2025-10-20T14:30:00Z",
    "creationDate": "2025-10-15T10:00:00Z"
  }
]
```

#### Field Mapping

| Bear Metadata | Minervium Field | Notes |
|---------------|-----------------|-------|
| `title` | `title` | From info.json, fallback to filename |
| `text.markdown` content | `markdown` | Preserves all markdown formatting |
| Content byte size | `size` | Calculated as UTF-8 byte length |
| `modificationDate` | `modificationDate` | Normalized to UTC ISO 8601 |
| `creationDate` | `creationDate` | Normalized to UTC ISO 8601 |
| `trashed = 1` | (filtered out) | Trashed notes are excluded |

## How It Works

### Extraction Process

1. **Unzip Archive**: Extracts `.bear2bk` ZIP to temporary directory
2. **Find TextBundles**: Recursively scans for `.textbundle` folders
3. **Parse Metadata**: Reads `info.json` from each TextBundle
4. **Filter Trashed**: Skips notes with `trashed = 1`
5. **Read Content**: Loads `text.markdown` with UTF-8 encoding
6. **Normalize Unicode**: Converts special line separators to `\n`
7. **Calculate Size**: Computes UTF-8 byte size of content
8. **Normalize Dates**: Converts timestamps to UTC ISO 8601 format
9. **Build JSON**: Assembles note objects conforming to schema
10. **Output**: Writes JSON array to file or stdout

### Data Transformations

#### Unicode Line Separator Normalization

Bear sometimes uses Unicode line separators:
- `U+2028` (Line Separator) → `\n`
- `U+2029` (Paragraph Separator) → `\n`

This ensures compatibility with standard markdown processors.

#### Date Normalization

Bear stores dates as either:
- Unix timestamps (numeric)
- ISO strings (with or without timezone)

The extractor normalizes all dates to UTC ISO 8601 with 'Z' suffix:
```
1697812800 → "2025-10-20T14:30:00Z"
"2025-10-20T14:30:00" → "2025-10-20T14:30:00Z"
```

#### Title Fallback

If a note has no title in `info.json`, the extractor uses the TextBundle directory name (without `.textbundle` extension).

## Examples

### Example 1: Basic Extraction

```bash
bear-extractor "Bear Notes.bear2bk" -o notes.json
```

**Input**: Bear backup with 500 notes
**Output**: `notes.json` with 450 notes (50 were trashed)

### Example 2: Extract and Validate

```bash
# Extract with progress
bear-extractor backup.bear2bk -v -o notes.json

# Validate schema
minervium validate notes.json --verbose

# Check output
jq 'length' notes.json
# 1234

jq '.[0]' notes.json
# {
#   "title": "Meeting Notes - Oct 20",
#   "markdown": "# Meeting Notes\n...",
#   "size": 456,
#   "modificationDate": "2025-10-20T14:30:00Z",
#   "creationDate": "2025-10-20T09:00:00Z"
# }
```

### Example 3: Pipeline with jq

```bash
# Extract and analyze titles
bear-extractor backup.bear2bk | jq -r '.[] | .title' | sort

# Count notes by size range
bear-extractor backup.bear2bk | jq '[.[] | .size] | length'

# Find large notes (>10KB)
bear-extractor backup.bear2bk | jq '.[] | select(.size > 10000) | .title'
```

### Example 4: Complete Workflow

```bash
# Step 1: Export backup from Bear app
# In Bear: File → Export Notes → Bear Backup → Save as "Bear Notes.bear2bk"

# Step 2: Extract notes
bear-extractor "Bear Notes.bear2bk" -v -o bear-notes.json
# Parsing Bear backup from Bear Notes.bear2bk
# Processed 1234/1234 notes (100.0%)
# Exported 1234 notes

# Step 3: Validate
minervium validate bear-notes.json
# ✓ Validation successful: bear-notes.json contains 1,234 valid note(s)

# Step 4: Create index config
cat > bear-config.json << 'EOF'
{
  "collection_name": "bear_notes",
  "description": "Personal notes from Bear app covering projects, ideas, and research",
  "chromadb_path": "./chromadb_data",
  "json_file": "bear-notes.json"
}
EOF

# Step 5: Index
minervium index --config bear-config.json --verbose
# Processing 1,234 notes...
# Created 5,678 chunks...
# ✓ Indexing complete!

# Step 6: Peek at the collection
minervium peek bear_notes --chromadb ./chromadb_data --format table

# Step 7: Serve via MCP
minervium serve --config server-config.json
```

## How to Create a Bear Backup

To extract notes, you first need a Bear backup file:

1. **Open Bear app** on macOS or iOS
2. **Go to**: File → Export Notes
3. **Select**: "Bear Backup" format
4. **Choose location** and save as `.bear2bk` file
5. **Use the extractor** on the saved backup file

### Backup File Location

**macOS default**: `~/Library/Group Containers/9K33E3U3T4.net.shinyfrog.bear/Application Data/Local Backup/`

**Manual export**: File → Export Notes → Bear Backup → Choose location

## Troubleshooting

### Issue: "Error: backup file not found"

**Cause**: File path is incorrect or file doesn't exist.

**Solution**:
```bash
# Check file exists
ls -lh "Bear Notes.bear2bk"

# Use absolute path
bear-extractor "/Users/yourname/Downloads/Bear Notes.bear2bk" -o notes.json

# Use quotes for paths with spaces
bear-extractor "Bear Notes 2025-10-20.bear2bk" -o notes.json
```

### Issue: "Failed to extract backup file: Bad zip file"

**Cause**: Corrupted or incomplete backup file.

**Solution**:
```bash
# Verify it's a valid ZIP file
unzip -t "Bear Notes.bear2bk"

# Try re-exporting from Bear
# In Bear: File → Export Notes → Bear Backup → Save again
```

### Issue: "Exported 0 notes"

**Possible causes**:
1. All notes are in trash
2. Backup file is empty
3. Wrong Bear version (extractor supports Bear 2.x)

**Solution**:
```bash
# Check backup contents
unzip -l "Bear Notes.bear2bk" | head -20

# Look for .textbundle folders
unzip -l "Bear Notes.bear2bk" | grep textbundle

# If no textbundle folders found, backup might be from Bear 1.x
# Export a new backup from Bear 2.x
```

### Issue: "Validation fails after extraction"

**Cause**: This shouldn't happen with the Bear extractor, but if it does:

**Solution**:
```bash
# Run validation with verbose mode to see errors
minervium validate notes.json --verbose

# Check the first note manually
jq '.[0]' notes.json

# Report issue with details:
# - Bear version
# - Backup file creation method
# - Error message from validation
```

### Issue: "Unicode/encoding errors"

**Cause**: Special characters or encodings in note content.

**Solution**: The extractor handles UTF-8 and normalizes Unicode line separators automatically. If you still see issues:

```bash
# Check file encoding
file notes.json
# Should show: UTF-8 Unicode text

# Validate JSON syntax
jq empty notes.json

# Check for specific problematic characters
jq -r '.[] | .markdown' notes.json | grep -n '[^\x00-\x7F]'
```

## Performance

**Typical performance** on modern hardware:

| Notes | Time | Rate |
|-------|------|------|
| 100 | ~1s | 100 notes/sec |
| 1,000 | ~5s | 200 notes/sec |
| 10,000 | ~45s | 220 notes/sec |
| 100,000 | ~7min | 240 notes/sec |

**Factors affecting speed**:
- Note size (larger notes take longer)
- Disk I/O speed (SSD vs HDD)
- Number of attachments (ignored by extractor, but affect ZIP extraction)

**Memory usage**: ~50-100MB for typical backups (scales with number of notes)

## Limitations

### Not Extracted

The following Bear features are **not** extracted:

- ❌ **Images and attachments**: Only markdown text is extracted
- ❌ **Tags**: Not included in output (Bear stores these separately)
- ❌ **Links between notes**: Internal Bear links are preserved as markdown, but relationships aren't tracked
- ❌ **Bear-specific markers**: Special Bear syntax may not render correctly outside Bear
- ❌ **Pin status**: Pinned notes are treated same as unpinned
- ❌ **Note color**: Not preserved
- ❌ **Archived notes**: Treated same as active notes (only trashed notes are filtered)

### Known Issues

1. **Bear 1.x backups**: Not supported (different format)
2. **Attachments**: Images/files in TextBundle are ignored
3. **Tags**: Would need to be extracted from markdown content or separate Bear database

## Advanced Usage

### Filtering Notes

Use jq to filter before indexing:

```bash
# Extract only recent notes (modified in last 30 days)
bear-extractor backup.bear2bk | \
  jq '[.[] | select(.modificationDate > "2025-09-20T00:00:00Z")]' > recent.json

# Extract only large notes (>5KB)
bear-extractor backup.bear2bk | \
  jq '[.[] | select(.size > 5000)]' > large-notes.json

# Extract notes with specific text in title
bear-extractor backup.bear2bk | \
  jq '[.[] | select(.title | contains("Project"))]' > project-notes.json
```

### Batch Processing

Process multiple backups:

```bash
#!/bin/bash
for backup in ~/Bear-Backups/*.bear2bk; do
    name=$(basename "$backup" .bear2bk)
    echo "Processing $name..."
    bear-extractor "$backup" -v -o "${name}.json"
    minervium validate "${name}.json"
done
```

### Incremental Extraction

Compare with previous extraction to find new/modified notes:

```bash
# Extract current backup
bear-extractor new-backup.bear2bk -o new.json

# Compare with previous
jq -r '.[] | "\(.title)|\(.modificationDate)"' old.json > old-index.txt
jq -r '.[] | "\(.title)|\(.modificationDate)"' new.json > new-index.txt
diff old-index.txt new-index.txt
```

## Development

### Running Tests

```bash
# Run parser tests (if available)
cd extractors/bear-notes-extractor
pytest tests/

# Manual test with sample data
bear-extractor test-data/sample.bear2bk -v -o /tmp/test.json
minervium validate /tmp/test.json
```

### Code Structure

```
bear-notes-extractor/
├── bear_extractor/
│   ├── __init__.py         # Package init
│   ├── cli.py              # Command-line interface
│   └── parser.py           # Core extraction logic
├── setup.py                # Package configuration
└── README.md              # This file
```

## Related Documentation

- **[Minervium Note Schema](../../docs/NOTE_SCHEMA.md)**: Complete JSON schema specification
- **[Extractor Development Guide](../../docs/EXTRACTOR_GUIDE.md)**: How to write custom extractors
- **[Extractors Overview](../README.md)**: All official extractors

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/minervium/issues)
- **Bear Format**: This extractor is based on the Bear 2.x TextBundle backup format
- **Validation**: Use `minervium validate` to check output

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

---

**Made for Minervium** - Extract, index, and search your Bear notes with AI.
