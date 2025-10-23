# Markdown Books Extractor

Extract structured markdown books into Minervium-compatible JSON format.

## Overview

The Markdown Books Extractor is a standalone CLI tool that converts markdown book files with structured metadata into searchable notes. It's designed for literary works, documentation, and educational content formatted as markdown files with standardized headers.

### Features

✅ **Structured parsing**: Extracts title, author, and year from markdown headers
✅ **Metadata preservation**: Keeps bibliographic information as custom fields
✅ **Simple format**: Requires minimal formatting from source files
✅ **Single-file input**: Each markdown file represents one book
✅ **Zero dependencies**: Uses only Python standard library
✅ **UTF-8 support**: Handles international characters correctly
✅ **Timestamping**: Uses book publication year for dates

## Installation

### Method 1: Install from Package Directory

```bash
# Navigate to the extractor directory
cd extractors/markdown-books-extractor

# Install in development mode
pip install -e .

# Verify installation
markdown-books-extractor --help
```

### Method 2: Install with pipx (Isolated)

```bash
cd extractors/markdown-books-extractor
pipx install .

# Now available globally
markdown-books-extractor --help
```

### Requirements

- Python 3.8 or higher
- No external dependencies (uses only stdlib)

## Quick Start

```bash
# Extract a book
markdown-books-extractor alice-in-wonderland.md -o alice.json

# Validate the output
minerva validate alice.json

# Index into Minervium
minerva index --config config.json --verbose
```

## Usage

### Basic Command

```bash
markdown-books-extractor SOURCE_FILE [OPTIONS]
```

### Options

- `SOURCE_FILE` (required): Path to the markdown book file
- `-o, --output FILE`: Output JSON file path (default: stdout)
- `-v, --verbose`: Show progress information on stderr
- `--help`: Show help message

### Examples

#### Extract to File

```bash
markdown-books-extractor "Alice's Adventures in Wonderland.md" -o alice.json
```

#### Extract to Stdout

```bash
markdown-books-extractor book.md | jq '.[0].title'
```

#### Verbose Mode

```bash
markdown-books-extractor book.md -v -o output.json
# Output on stderr:
# Parsing markdown book from book.md
# Exported 1 record(s)
```

## Supported Format

### Input Format: Structured Markdown

Book files must follow this format:

```markdown
# Title: Alice's Adventures in Wonderland

## Author: Lewis Carroll

## Year: 1865

---

# Chapter I: Down the Rabbit Hole

Alice was beginning to get very tired of sitting by her sister...

# Chapter II: The Pool of Tears

"Curiouser and curiouser!" cried Alice...
```

**Required elements**:

1. **Title line**: `# Title: [Book Title]`
2. **Author line**: `## Author: [Author Name]`
3. **Year line**: `## Year: [YYYY]`
4. **Delimiter**: `-------` (exactly 7 dashes)
5. **Body**: Book content in markdown format

### Header Format Rules

```markdown
# Title: The Great Gatsby

## Author: F. Scott Fitzgerald

## Year: 1925

---
```

- Title must start with `# Title:`
- Author must start with `## Author:`
- Year must start with `## Year:` and be a 4-digit number
- Delimiter must be exactly `-------` on its own line
- Everything after delimiter is treated as book content

### Output Format: Minervium JSON

Outputs a JSON array with one note per book:

```json
[
  {
    "title": "Alice's Adventures in Wonderland",
    "markdown": "# Alice's Adventures in Wonderland\n\n**Author:** Lewis Carroll | **Year:** 1865\n\nChapter I...",
    "size": 234567,
    "modificationDate": "1865-01-01T00:00:00Z",
    "creationDate": "1865-01-01T00:00:00Z",
    "author": "Lewis Carroll",
    "year": 1865
  }
]
```

#### Field Mapping

| Source             | Minervium Field    | Notes                                           |
| ------------------ | ------------------ | ----------------------------------------------- |
| `# Title:` value   | `title`            | Book title from header                          |
| Header + body      | `markdown`         | Formatted with title, author, year, and content |
| Markdown byte size | `size`             | Calculated as UTF-8 length                      |
| Year-01-01         | `modificationDate` | January 1st of publication year                 |
| Year-01-01         | `creationDate`     | January 1st of publication year                 |
| `## Author:` value | `author`           | Custom field                                    |
| `## Year:` value   | `year`             | Custom field (integer)                          |

### Markdown Output Format

The extractor reformats the book content as:

```markdown
# [Title]

**Author:** [Author] | **Year:** [Year]

[Body content from file]
```

This provides context when viewing extracted notes.

## How It Works

### Extraction Process

1. **Read File**: Load markdown file with UTF-8 encoding
2. **Split Header/Body**: Find `-------` delimiter
3. **Extract Metadata**: Parse title, author, year from header using regex
4. **Validate Year**: Ensure year is 4-digit integer
5. **Format Markdown**: Combine title, metadata, and body
6. **Calculate Size**: Get UTF-8 byte length
7. **Generate Timestamp**: Create ISO 8601 date from year (January 1st)
8. **Build Note Object**: Assemble all fields
9. **Output JSON**: Write array with single note

### Date Handling

Since books don't have modification dates, the extractor uses the publication year:

- `modificationDate`: `{year}-01-01T00:00:00Z`
- `creationDate`: `{year}-01-01T00:00:00Z`

Example: A book from 1925 gets `1925-01-01T00:00:00Z`

This allows sorting books chronologically by publication year.

## Examples

### Example 1: Extract Alice in Wonderland

**Input file** (`alice.md`):

```markdown
# Title: Alice's Adventures in Wonderland

## Author: Lewis Carroll

## Year: 1865

---

# Chapter I: Down the Rabbit Hole

Alice was beginning to get very tired of sitting by her sister on the
bank, and of having nothing to do: once or twice she had peeped into the
book her sister was reading, but it had no pictures or conversations in
it, "and what is the use of a book," thought Alice "without pictures or
conversations?"
```

**Extract**:

```bash
markdown-books-extractor alice.md -v -o alice.json
# Parsing markdown book from alice.md
# Exported 1 record(s)
```

**Output** (`alice.json`):

```json
[
  {
    "title": "Alice's Adventures in Wonderland",
    "markdown": "# Alice's Adventures in Wonderland\n\n**Author:** Lewis Carroll | **Year:** 1865\n\n# Chapter I...",
    "size": 12345,
    "modificationDate": "1865-01-01T00:00:00Z",
    "creationDate": "1865-01-01T00:00:00Z",
    "author": "Lewis Carroll",
    "year": 1865
  }
]
```

### Example 2: Extract Multiple Books

```bash
# Extract several books
for book in books/*.md; do
    name=$(basename "$book" .md)
    echo "Extracting: $name"
    markdown-books-extractor "$book" -o "json/${name}.json"
done

# Combine into single JSON array
jq -s 'add' json/*.json > all-books.json

# Validate
minerva validate all-books.json
# ✓ Validation successful: all-books.json contains 25 valid note(s)
```

### Example 3: Complete Workflow

```bash
# Step 1: Prepare markdown book file
cat > moby-dick.md << 'EOF'
# Title: Moby-Dick
## Author: Herman Melville
## Year: 1851
-------

# Chapter 1: Loomings

Call me Ishmael. Some years ago—never mind how long precisely—having
little or no money in my purse, and nothing particular to interest me
on shore, I thought I would sail about a little and see the watery part
of the world.
EOF

# Step 2: Extract
markdown-books-extractor moby-dick.md -v -o moby-dick.json
# Parsing markdown book from moby-dick.md
# Exported 1 record(s)

# Step 3: Validate
minerva validate moby-dick.json
# ✓ Validation successful: moby-dick.json contains 1 valid note(s)

# Step 4: Check output
jq '.[0] | {title, author, year, size}' moby-dick.json
# {
#   "title": "Moby-Dick",
#   "author": "Herman Melville",
#   "year": 1851,
#   "size": 456
# }

# Step 5: Index
cat > books-config.json << 'EOF'
{
  "collection_name": "classic_literature",
  "description": "Classic literature and novels from Project Gutenberg",
  "chromadb_path": "./chromadb_data",
  "json_file": "moby-dick.json"
}
EOF

minerva index --config books-config.json --verbose
```

### Example 4: Batch Processing Project Gutenberg

```bash
# Download books from Project Gutenberg (markdown format)
# Note: You'll need to convert from text/HTML to markdown first

# Process all books
for book in gutenberg-books/*.md; do
    name=$(basename "$book" .md)
    markdown-books-extractor "$book" -o "extracted/${name}.json"
done

# Combine all extractions
jq -s 'add' extracted/*.json > all-gutenberg.json

# Index as single collection
cat > gutenberg-config.json << 'EOF'
{
  "collection_name": "project_gutenberg",
  "description": "Classic books from Project Gutenberg",
  "chromadb_path": "./chromadb_data",
  "json_file": "all-gutenberg.json"
}
EOF

minerva index --config gutenberg-config.json --verbose
```

## Creating Markdown Book Files

### From Plain Text Books

If you have plain text books, add the structured header:

```bash
# Original book.txt
cat book.txt

# Add header
cat > book-formatted.md << 'EOF'
# Title: The Great Gatsby
## Author: F. Scott Fitzgerald
## Year: 1925
-------
EOF

# Append content
cat book.txt >> book-formatted.md

# Extract
markdown-books-extractor book-formatted.md -o book.json
```

### From Project Gutenberg

Project Gutenberg books need formatting:

1. Download book from https://www.gutenberg.org/
2. Remove Project Gutenberg header/footer
3. Add structured header with Title, Author, Year
4. Save as .md file
5. Extract with markdown-books-extractor

### Manual Template

```markdown
# Title: [Your Book Title]

## Author: [Author Name]

## Year: [Publication Year]

---

# Chapter 1

[Your content here...]

# Chapter 2

[More content...]
```

## Troubleshooting

### Issue: "Missing required field: Title"

**Cause**: Header doesn't have proper title line.

**Solution**: Ensure format is exactly:

```markdown
# Title: Your Book Title
```

Not:

```markdown
Title: Your Book Title (missing #)
#Title: Your Book Title (missing space)

# Title: (missing actual title)
```

### Issue: "File must contain '-------' delimiter"

**Cause**: Missing or incorrect delimiter.

**Solution**: Add exactly 7 dashes on a line by itself:

```markdown
# Title: Book

## Author: Author

## Year: 2025

---

Content starts here...
```

Not:

```markdown
------ (6 dashes)
-------- (8 dashes)

- - - - - - - (spaces between)
```

### Issue: "Invalid year format"

**Cause**: Year is not a 4-digit number.

**Solution**:

```markdown
## Year: 1925 ✅ Correct

## Year: 25 ✗ Wrong (2 digits)

## Year: 1925 CE ✗ Wrong (extra text)

## Year: nineteen twenty-five ✗ Wrong (words)
```

### Issue: "File encoding error"

**Cause**: File is not UTF-8 encoded.

**Solution**:

```bash
# Check file encoding
file book.md

# Convert to UTF-8 if needed
iconv -f ISO-8859-1 -t UTF-8 book.md > book-utf8.md

# Or use your text editor to save as UTF-8
```

### Issue: "Validation fails - title cannot be empty"

**Cause**: Title line exists but has no value.

**Solution**:

```markdown
# Title: Alice in Wonderland ✅ Has value

# Title: ✗ Empty after colon
```

## Performance

**Extraction time**: Nearly instantaneous (< 1 second per book)

| Books | Time | Rate    |
| ----- | ---- | ------- |
| 1     | < 1s | instant |
| 10    | < 1s | instant |
| 100   | ~2s  | 50/sec  |
| 1,000 | ~20s | 50/sec  |

Books are extracted individually, so performance is linear with file count.

**Memory usage**: Minimal (~10-20MB regardless of book size)

## Limitations

### Not Supported

- ❌ **Multiple books per file**: Each file must contain exactly one book
- ❌ **Auto-detection of metadata**: Title, Author, Year must be explicitly specified
- ❌ **HTML input**: Only markdown files supported
- ❌ **Binary formats**: No PDF, EPUB, or Word document support
- ❌ **Complex metadata**: Only Title, Author, Year extracted (no ISBN, publisher, etc.)

### Known Issues

1. **Simplistic date handling**: All books get January 1st as date
2. **No content validation**: Doesn't verify book content quality
3. **Single note per book**: Large books create large notes (not split into chapters)
4. **Regex-based parsing**: Strict format requirements

### Workarounds

**For multi-chapter books**:
If you want each chapter as a separate note, split the file manually:

```bash
# Split book into chapter files
csplit -f chapter- book.md '/^# Chapter /' '{*}'

# Process each chapter (you'll need to add headers to each)
```

**For books without year**:
Use approximate or unknown year:

```markdown
## Year: 1900 # Approximate for older works

## Year: 2000 # For modern works
```

## Advanced Usage

### Combining Multiple Books

```bash
# Extract each book
markdown-books-extractor book1.md -o book1.json
markdown-books-extractor book2.md -o book2.json
markdown-books-extractor book3.md -o book3.json

# Combine using jq
jq -s 'add' book*.json > library.json

# Or use jq to merge and sort by year
jq -s 'add | sort_by(.year)' book*.json > library-sorted.json
```

### Filtering by Metadata

```bash
# Extract all books, then filter by year
markdown-books-extractor book.md | \
  jq '.[] | select(.year >= 1900 and .year < 2000)'

# Filter by author
markdown-books-extractor book.md | \
  jq '.[] | select(.author == "Lewis Carroll")'
```

### Batch Validation

```bash
#!/bin/bash
# Validate all book extractions

for json in books/*.json; do
    echo "Validating $json..."
    minerva validate "$json" || echo "FAILED: $json"
done
```

### Statistics

```bash
# Get total books, earliest/latest year
jq '{
  count: length,
  earliest: (map(.year) | min),
  latest: (map(.year) | max),
  authors: (map(.author) | unique | length)
}' library.json
```

## Development

### Running Tests

```bash
cd extractors/markdown-books-extractor

# Manual test
cat > test-book.md << 'EOF'
# Title: Test Book
## Author: Test Author
## Year: 2025
-------
This is test content.
EOF

markdown-books-extractor test-book.md -v -o test.json
minerva validate test.json
```

### Code Structure

```
markdown-books-extractor/
├── markdown_books_extractor/
│   ├── __init__.py         # Package init
│   ├── cli.py              # Command-line interface
│   └── parser.py           # Core parsing logic
├── setup.py                # Package configuration
└── README.md              # This file
```

## Related Documentation

- **[Minervium Note Schema](../../docs/NOTE_SCHEMA.md)**: Complete JSON schema specification
- **[Extractor Development Guide](../../docs/EXTRACTOR_GUIDE.md)**: How to write custom extractors
- **[Extractors Overview](../README.md)**: All official extractors

## Resources

- **Project Gutenberg**: https://www.gutenberg.org/ (free public domain books)
- **Standard Ebooks**: https://standardebooks.org/ (high-quality public domain ebooks)
- **Markdown Guide**: https://www.markdownguide.org/ (markdown syntax reference)

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/minerva/issues)
- **Questions**: Ask in [GitHub Discussions](https://github.com/yourusername/minerva/discussions)

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

---

**Made for Minervium** - Index classic literature and books with AI-powered semantic search.
