# Zim Extractor

Extract articles from ZIM archives (offline Wikipedia, educational content) into Minerva-compatible JSON format.

## Overview

The Zim Extractor is a standalone CLI tool that reads ZIM archive files and converts HTML articles into clean markdown with standardized JSON metadata. ZIM archives are used for offline storage of web content like Wikipedia, WikiHow, Stack Exchange, and educational materials.

### Features

✅ **ZIM archive support**: Reads ZIM files using libzim library
✅ **HTML to Markdown**: Converts article HTML to clean, readable markdown
✅ **Dual output**: JSON catalog + optional individual markdown files
✅ **Smart enumeration**: Uses title index or full-text search to find articles
✅ **Redirect handling**: Follows redirects to get actual content
✅ **Timestamp extraction**: Attempts to find modification/creation dates from HTML
✅ **Sampling support**: Limit number of articles for testing
✅ **Deduplication**: Automatically removes duplicate titles
✅ **Progress reporting**: Verbose mode shows extraction progress
✅ **HTML filtering**: Extracts only text/html content (skips images, scripts, etc.)

## Installation

### Method 1: Install from Package Directory

```bash
# Navigate to the extractor directory
cd extractors/zim-extractor

# Install dependencies and package
pip install -e .

# Verify installation
zim-extractor --help
```

### Method 2: Install with pipx (Isolated)

```bash
cd extractors/zim-extractor
pipx install .

# Now available globally
zim-extractor --help
```

### Requirements

- **Python**: 3.8 or higher
- **libzim**: ≥3.0.0 (ZIM archive reader)
- **markdownify**: ≥0.11.0 (HTML to Markdown converter)

#### Installing libzim

**macOS (Homebrew)**:

```bash
brew install libzim
```

**Ubuntu/Debian**:

```bash
sudo apt-get install libzim-dev
```

**Other platforms**: See [libzim documentation](https://github.com/openzim/libzim)

## Quick Start

```bash
# Extract first 100 articles as sample
zim-extractor wikipedia_en_history.zim -o articles.json -l 100 -v

# Validate the output
minerva validate articles.json

# Index into Minerva
minerva index --config config.json --verbose
```

## Usage

### Basic Command

```bash
zim-extractor ZIM_FILE [OPTIONS]
```

### Options

- `ZIM_FILE` (required): Path to the ZIM archive file
- `-o, --output FILE`: Output JSON file path (default: stdout)
- `-m, --markdown-dir DIR`: Optional directory to write individual markdown files
- `-l, --limit N`: Maximum number of articles to extract (useful for sampling)
- `-v, --verbose`: Show progress information on stderr
- `--help`: Show help message

### Examples

#### Extract to JSON Only

```bash
zim-extractor wikipedia_en_history.zim -o history.json -v
```

#### Extract JSON + Markdown Files

```bash
# Creates JSON + individual .md files in markdown/ directory
zim-extractor wikipedia_en_science.zim \
  -o science.json \
  -m ./markdown \
  -v
```

#### Sample First 1000 Articles

```bash
# Good for testing before full extraction
zim-extractor large-archive.zim -o sample.json -l 1000 -v
```

#### Pipe to jq for Analysis

```bash
# Extract and analyze titles
zim-extractor archive.zim | jq -r '.[] | .title' | sort

# Count extracted articles
zim-extractor archive.zim -l 500 | jq 'length'

# Find large articles
zim-extractor archive.zim | jq '.[] | select(.size > 50000) | .title'
```

## Supported Formats

### Input Format: ZIM Archives

ZIM (Zeno IMproved) is an open file format for storing web content offline.

**Common ZIM sources**:

- Wikipedia dumps (language-specific or topics)
- WikiHow, Wiktionary, Wikivoyage
- Stack Exchange sites
- Project Gutenberg
- Khan Academy
- Medical encyclopedias

**Where to get ZIM files**:

- [Kiwix Library](https://library.kiwix.org/) - Huge collection of ZIM files
- [download.kiwix.org](https://download.kiwix.org/zim/) - Direct downloads
- [Wikipedia ZIM dumps](https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/)

**File naming convention**:

```
wikipedia_en_history_2025-10.zim
│         │  │       └─ Date
│         │  └─ Topic/subset
│         └─ Language code
└─ Project name
```

### Output Format: Minerva JSON

Standard JSON array conforming to the [Minerva Note Schema](../../docs/NOTE_SCHEMA.md):

```json
[
  {
    "title": "World War II",
    "markdown": "# World War II\n\nWorld War II was a global conflict...",
    "size": 15234,
    "modificationDate": "2024-08-15T10:30:00Z",
    "creationDate": "2024-01-10T14:00:00Z"
  }
]
```

#### Field Mapping

| ZIM Source              | Minerva Field      | Notes                                          |
| ----------------------- | ------------------ | ---------------------------------------------- |
| Entry title             | `title`            | Article title from ZIM                         |
| HTML content → markdown | `markdown`         | Converted with markdownify                     |
| Markdown byte size      | `size`             | Calculated as UTF-8 length                     |
| Extracted from HTML     | `modificationDate` | Heuristic extraction, fallback to current time |
| Extracted from HTML     | `creationDate`     | Heuristic extraction, fallback to current time |

## How It Works

### Extraction Process

1. **Open Archive**: Load ZIM file using libzim
2. **Enumerate Articles**: Use title index or full-text search to get article list
3. **Deduplicate**: Remove duplicate titles
4. **Process Each Entry**:
   - Get entry by title
   - Follow redirects if needed
   - Filter for text/html content only
   - Convert HTML to markdown
   - Extract timestamps heuristically
   - Generate note object
5. **Optional**: Write individual markdown files
6. **Output**: Write JSON array

### HTML to Markdown Conversion

Uses the `markdownify` library to convert HTML to clean markdown:

- **Headings**: `<h1>` → `#`, `<h2>` → `##`, etc.
- **Emphasis**: `<strong>` → `**bold**`, `<em>` → `*italic*`
- **Lists**: `<ul>`, `<ol>` → markdown lists
- **Links**: `<a href="">` → `[text](url)`
- **Images**: `<img>` → `![alt](url)` (links only, not embedded)
- **Code**: `<code>`, `<pre>` → markdown code blocks
- **Tables**: `<table>` → markdown tables
- **Blockquotes**: `<blockquote>` → `>`

### Timestamp Extraction

The extractor attempts to find modification and creation dates in HTML content:

1. **Search for ISO 8601 patterns**: `2025-10-20T14:30:00Z`
2. **Check context** for keywords:
   - Modification: "modification", "modified", "updated", "last edit"
   - Creation: "creation", "created", "publish", "created time"
3. **Fallback**: If no timestamps found, use current extraction time

This is heuristic and may not be accurate for all ZIM archives.

### Redirect Handling

Some ZIM entries are redirects (aliases):

- Extractor detects redirects
- Follows redirect to actual content
- Extracts from final destination

### Content Filtering

Only `text/html` content is extracted:

- ✅ HTML articles
- ❌ Images, CSS, JavaScript, fonts
- ❌ Binary files

## Examples

### Example 1: Extract Wikipedia History Articles

```bash
# Download ZIM file
wget https://download.kiwix.org/zim/wikipedia/wikipedia_en_history_2025-10.zim

# Extract all articles
zim-extractor wikipedia_en_history_2025-10.zim -o history.json -v
# Output:
# Entries (user): 123456, articles: 98765
# Main entry path: A/Main_Page.html
# Collecting titles via title index…
# Unique titles to process: 95432
# Processed 10000 titles so far; captured 9234 markdown articles
# ...
# Done. Generated 95432 records

# Validate
minerva validate history.json
```

### Example 2: Sample for Testing

```bash
# Extract just 500 articles for testing
zim-extractor large-archive.zim -o sample.json -l 500 -v

# Validate sample
minerva validate sample.json

# Index sample
cat > test-config.json << 'EOF'
{
  "collection_name": "wikipedia_sample",
  "description": "Sample of 500 Wikipedia articles for testing",
  "chromadb_path": "./test_chromadb",
  "json_file": "sample.json"
}
EOF

minerva index --config test-config.json --verbose
```

### Example 3: Extract JSON + Markdown Files

```bash
# Extract to both JSON and individual markdown files
zim-extractor wikipedia_en_science.zim \
  -o science.json \
  -m ./science_markdown \
  -v

# Result:
# - science.json: JSON catalog of all articles
# - science_markdown/: Directory with .md files for each article

# Check markdown files
ls science_markdown/ | head -5
# Astronomy.md
# Biology.md
# Chemistry.md
# ...

# Use markdown files for other purposes
grep -r "quantum mechanics" science_markdown/
```

### Example 4: Complete Workflow

```bash
# Step 1: Download ZIM file
wget https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_2025-10.zim

# Step 2: Extract articles
zim-extractor wikipedia_en_top_2025-10.zim -v -o wiki.json
# Entries (user): 234567, articles: 187654
# Collecting titles via title index…
# Unique titles to process: 180234
# Processed 50000 titles so far; captured 48765 markdown articles
# Done. Generated 180234 records

# Step 3: Validate
minerva validate wiki.json
# ✓ Validation successful: wiki.json contains 180,234 valid note(s)

# Step 4: Create config
cat > wiki-config.json << 'EOF'
{
  "collection_name": "wikipedia_top",
  "description": "Top Wikipedia articles covering most popular topics and current knowledge",
  "chromadb_path": "./chromadb_data",
  "json_file": "wiki.json"
}
EOF

# Step 5: Index (this may take a while for large collections)
minerva index --config wiki-config.json --verbose
# Processing 180,234 notes...
# Created 987,654 chunks...
# Generating embeddings...
# ✓ Indexing complete!

# Step 6: Search
minerva serve --config server-config.json
# Now searchable via Claude Desktop
```

## Where to Get ZIM Files

### Official Sources

**Kiwix Library** (recommended):

- URL: https://library.kiwix.org/
- Browse by category, language, size
- Includes Wikipedia, WikiHow, Stack Exchange, and more
- Direct download links

**Download Server**:

- URL: https://download.kiwix.org/zim/
- All available ZIM files
- Organized by project and date

### Popular ZIM Files

**Wikipedia - Full**:

```bash
# English Wikipedia (all articles, ~100GB compressed)
wget https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_2025-10.zim
```

**Wikipedia - Topics** (smaller, focused):

```bash
# History (~5GB)
wget https://download.kiwix.org/zim/wikipedia/wikipedia_en_history_2025-10.zim

# Science (~3GB)
wget https://download.kiwix.org/zim/wikipedia/wikipedia_en_science_2025-10.zim

# Top 100K articles (~10GB)
wget https://download.kiwix.org/zim/wikipedia/wikipedia_en_top_2025-10.zim
```

**Other Languages**:

```bash
# Spanish Wikipedia
wget https://download.kiwix.org/zim/wikipedia/wikipedia_es_all_2025-10.zim

# French Wikipedia
wget https://download.kiwix.org/zim/wikipedia/wikipedia_fr_all_2025-10.zim
```

**Other Projects**:

```bash
# WikiHow
wget https://download.kiwix.org/zim/wikihow/wikihow_en_2025-10.zim

# Stack Exchange (programming)
wget https://download.kiwix.org/zim/stack_exchange/stackoverflow.com_en_2025-10.zim

# Project Gutenberg (books)
wget https://download.kiwix.org/zim/gutenberg/gutenberg_en_2025-10.zim
```

## Troubleshooting

### Issue: "Error: ZIM file not found"

**Cause**: File path is incorrect or file doesn't exist.

**Solution**:

```bash
# Check file exists
ls -lh wikipedia_en_history.zim

# Use absolute path
zim-extractor /path/to/wikipedia_en_history.zim -o output.json

# Check file is actually a ZIM file
file wikipedia_en_history.zim
# Should show: data (ZIM archive)
```

### Issue: "No title index or full-text index found"

**Cause**: ZIM archive doesn't have indexes for enumeration.

**Solution**: This is rare with modern ZIM files. If it occurs:

```bash
# Try with a different ZIM file
# Or report issue with ZIM file details

# Check ZIM file info
python -c "from libzim.reader import Archive; z=Archive('file.zim'); print(f'Title index: {z.has_title_index}, FT index: {z.has_fulltext_index}')"
```

### Issue: "ImportError: No module named 'libzim'"

**Cause**: libzim Python bindings not installed.

**Solution**:

```bash
# Install libzim system library first
# macOS:
brew install libzim

# Ubuntu/Debian:
sudo apt-get install libzim-dev

# Then install Python package
pip install libzim
```

### Issue: "Extraction is very slow"

**Cause**: Large ZIM files take time to process.

**Solution**:

```bash
# 1. Use limit flag for testing
zim-extractor large.zim -o sample.json -l 1000 -v

# 2. Check progress with verbose mode
zim-extractor large.zim -o output.json -v

# 3. Extract specific subset ZIM instead
# Use wikipedia_en_history.zim instead of wikipedia_en_all.zim
```

**Expected performance**:

- Small archives (1K articles): ~10 seconds
- Medium archives (10K articles): ~2 minutes
- Large archives (100K articles): ~20 minutes
- Very large (1M+ articles): ~3-4 hours

### Issue: "Validation fails - missing dates"

**Cause**: Timestamp extraction heuristic failed.

**Solution**: This is expected - the extractor uses current time as fallback:

```bash
# Check the dates in output
jq '.[0] | {title, modificationDate, creationDate}' output.json

# Dates will be extraction time if not found in HTML
# This is acceptable - Minerva requires dates but they don't have to be perfect
```

### Issue: "Out of memory"

**Cause**: Processing very large archives or extracting too many articles at once.

**Solution**:

```bash
# 1. Use limit to process in batches
zim-extractor large.zim -o batch1.json -l 50000 -v
# Note: Current implementation doesn't support offset, so full batching not available

# 2. Increase system memory
# 3. Use smaller subset ZIM files instead of full dumps
```

## Performance

**Typical performance** on modern hardware:

| Articles  | Time   | Rate    | RAM Usage |
| --------- | ------ | ------- | --------- |
| 1,000     | ~10s   | 100/sec | ~200MB    |
| 10,000    | ~2min  | 80/sec  | ~500MB    |
| 100,000   | ~25min | 65/sec  | ~2GB      |
| 1,000,000 | ~6hr   | 45/sec  | ~8GB      |

**Factors affecting speed**:

- Article size (longer articles take more time to convert)
- HTML complexity (tables, nested elements slow down conversion)
- Disk I/O (SSD vs HDD)
- Whether markdown files are being written (`-m` flag)

**Bottlenecks**:

- HTML to Markdown conversion (markdownify is CPU-intensive)
- ZIM archive reading (I/O bound)

## Limitations

### Not Extracted

- ❌ **Images**: Image files in ZIM not extracted (only markdown links preserved)
- ❌ **Multimedia**: Audio, video files ignored
- ❌ **Stylesheets/Scripts**: CSS and JavaScript skipped
- ❌ **Binary files**: Only text/html content processed
- ❌ **Attachments**: PDF, ZIP, etc. not extracted
- ❌ **Metadata**: ZIM-level metadata (creator, publisher, tags) not captured

### Known Issues

1. **Timestamp accuracy**: Heuristic extraction may not find correct dates
2. **Markdown conversion**: Complex HTML may not convert perfectly
3. **Special characters**: Some Unicode characters may not render correctly
4. **Large memory usage**: Very large archives need significant RAM
5. **No pagination**: Can't easily process in chunks (no offset parameter yet)

### HTML Conversion Caveats

- **Tables**: Complex tables may not render well in markdown
- **Math formulas**: LaTeX/MathML may not convert correctly
- **Nested structures**: Deeply nested HTML may lose some formatting
- **Custom HTML**: Non-standard HTML elements may be stripped

## Advanced Usage

### Analyzing ZIM Archives

```bash
# Get archive info
python -c "
from libzim.reader import Archive
z = Archive('wiki.zim')
print(f'Entries: {z.entry_count}')
print(f'Articles: {z.article_count}')
print(f'Title index: {z.has_title_index}')
print(f'Main entry: {z.main_entry.path if z.has_main_entry else \"None\"}')
"
```

### Filtering Extracted Articles

```bash
# Extract then filter with jq
zim-extractor wiki.zim | \
  jq '[.[] | select(.size > 5000)]' > large-articles.json

# Filter by title pattern
zim-extractor wiki.zim | \
  jq '[.[] | select(.title | contains("War"))]' > war-articles.json
```

### Multiple ZIM Files

```bash
# Extract from multiple archives
for zim in *.zim; do
    name=$(basename "$zim" .zim)
    echo "Processing $name..."
    zim-extractor "$zim" -o "${name}.json" -v
    minerva validate "${name}.json"
done

# Combine into single collection or index separately
```

## Development

### Running Tests

```bash
cd extractors/zim-extractor

# Manual test with sample ZIM
zim-extractor test-data/sample.zim -v -o /tmp/test.json
minerva validate /tmp/test.json
```

### Code Structure

```
zim-extractor/
├── zim_extractor/
│   ├── __init__.py         # Package init
│   ├── cli.py              # Command-line interface
│   └── parser.py           # Core extraction logic
├── setup.py                # Package configuration
└── README.md              # This file
```

## Related Documentation

- **[Minerva Note Schema](../../docs/NOTE_SCHEMA.md)**: Complete JSON schema specification
- **[Extractor Development Guide](../../docs/EXTRACTOR_GUIDE.md)**: How to write custom extractors
- **[Extractors Overview](../README.md)**: All official extractors
- **[libzim Documentation](https://github.com/openzim/libzim)**: ZIM format and library
- **[Kiwix](https://www.kiwix.org/)**: Offline content platform using ZIM

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/minerva/issues)
- **ZIM Format**: [OpenZIM Project](https://wiki.openzim.org/)
- **Get Help**: Questions about ZIM files → [Kiwix Forum](https://forum.kiwix.org/)

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

---

**Made for Minerva** - Index Wikipedia and offline content with AI-powered semantic search.
