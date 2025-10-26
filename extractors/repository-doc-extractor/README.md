# Repository Documentation Extractor

Extract markdown documentation from repository directory hierarchies into Minerva-compatible JSON format.

## Overview

The Repository Documentation Extractor is a standalone CLI tool that recursively walks through directory trees, finds all markdown files, and converts them into searchable notes. It's designed for documentation repositories, project wikis, technical guides, and any collection of markdown files organized in folders.

### Features

✅ **Recursive directory walking**: Finds all `.md` files in nested folders
✅ **Smart title extraction**: Uses first H1 heading or filename as title
✅ **Automatic exclusions**: Skips `.git`, `node_modules`, and other common non-doc directories
✅ **Custom exclusions**: Exclude additional patterns via command-line flags
✅ **File metadata**: Preserves modification and creation dates from filesystem
✅ **Source tracking**: Includes relative file path for reference
✅ **Zero dependencies**: Uses only Python standard library
✅ **UTF-8 support**: Handles international characters correctly

## Installation

### Method 1: Install from Package Directory

```bash
# Navigate to the extractor directory
cd extractors/repository-doc-extractor

# Install in development mode
pip install -e .

# Verify installation
repository-doc-extractor --help
```

### Method 2: Install with pipx (Isolated)

```bash
cd extractors/repository-doc-extractor
pipx install .

# Now available globally
repository-doc-extractor --help
```

### Requirements

- Python 3.10 or higher
- No external dependencies (uses only stdlib)

## Quick Start

```bash
# Extract documentation from a repository
repository-doc-extractor /path/to/repo/docs -o docs.json

# Validate the output
minerva validate docs.json

# Index into Minerva
minerva index --config config.json --verbose
```

## Usage

### Basic Command

```bash
repository-doc-extractor DIRECTORY [OPTIONS]
```

### Options

- `DIRECTORY` (required): Root directory to scan for markdown files
- `-o, --output FILE`: Output JSON file path (default: stdout)
- `-v, --verbose`: Show progress information on stderr
- `--exclude PATTERN`: Exclude directories matching pattern (can be used multiple times)
- `--help`: Show help message

### Examples

#### Extract to File

```bash
repository-doc-extractor ./docs -o documentation.json
```

#### Extract with Verbose Output

```bash
repository-doc-extractor /path/to/project/docs -v -o docs.json
# Output on stderr:
# Scanning directory: /path/to/project/docs
# ✓ Exported 45 markdown file(s)
```

#### Exclude Additional Patterns

```bash
# Exclude 'drafts' and 'archive' directories
repository-doc-extractor ./docs --exclude drafts --exclude archive -o docs.json
```

#### Extract to Stdout and Pipe

```bash
repository-doc-extractor ./docs | jq '.[0].title'
```

## How It Works

### Extraction Process

1. **Walk Directory Tree**: Recursively traverse from root directory
2. **Find Markdown Files**: Identify all files with `.md` extension
3. **Filter Exclusions**: Skip files in excluded directories (`.git`, `node_modules`, etc.)
4. **Extract Title**:
   - Parse markdown content for first H1 heading (`# Title`)
   - Fall back to filename (without `.md`) if no H1 found
5. **Collect Metadata**: Read file modification time, creation time, size
6. **Build Notes**: Create note object for each markdown file
7. **Output JSON**: Write array of all notes

### Title Extraction Logic

The extractor uses this priority:

1. **First H1 heading**: If markdown contains `# Some Title`, uses "Some Title"
2. **Filename fallback**: If no H1 found, uses filename without `.md` extension

Examples:

| Markdown Content              | Filename      | Extracted Title                |
| ----------------------------- | ------------- | ------------------------------ |
| `# Getting Started`           | `intro.md`    | "Getting Started"              |
| `## Setup\nContent...`        | `setup.md`    | "setup" (no H1, uses filename) |
| `# API Reference\n## Methods` | `api-docs.md` | "API Reference"                |
| Plain text, no headers        | `README.md`   | "README"                       |

### Automatic Exclusions

These directories are always excluded:

- `.git` - Git repository metadata
- `node_modules` - Node.js dependencies
- `__pycache__` - Python bytecode cache
- `.venv` - Python virtual environment
- `venv` - Python virtual environment
- `.pytest_cache` - Pytest cache

Use `--exclude` to add more patterns.

## Output Format

### Minerva JSON Schema

Outputs a JSON array with one note per markdown file:

```json
[
  {
    "title": "Getting Started",
    "markdown": "# Getting Started\n\nWelcome to our documentation...",
    "size": 1234,
    "modificationDate": "2025-10-26T10:30:00Z",
    "creationDate": "2025-10-20T14:00:00Z",
    "sourcePath": "docs/getting-started.md"
  },
  {
    "title": "API Reference",
    "markdown": "# API Reference\n\n## Authentication\n...",
    "size": 5678,
    "modificationDate": "2025-10-25T16:45:00Z",
    "creationDate": "2025-10-18T09:00:00Z",
    "sourcePath": "docs/api/reference.md"
  }
]
```

### Field Mapping

| Source               | Minerva Field      | Notes                                          |
| -------------------- | ------------------ | ---------------------------------------------- |
| First H1 or filename | `title`            | Smart extraction with fallback                 |
| File content         | `markdown`         | Full markdown content as-is                    |
| File byte size       | `size`             | Calculated as UTF-8 length                     |
| File mtime           | `modificationDate` | ISO 8601 format with Z timezone                |
| File birthtime/ctime | `creationDate`     | ISO 8601 format (or mtime if unavailable)      |
| Relative path        | `sourcePath`       | Path relative to root directory (custom field) |

### Source Path Field

The `sourcePath` field helps you trace notes back to their original files:

```json
{
  "title": "Authentication",
  "sourcePath": "docs/api/authentication.md",
  ...
}
```

This is useful when:

- You want to edit the original file after finding issues via search
- You're debugging which files are being indexed
- You want to understand the documentation structure

## Examples

### Example 1: Extract Project Documentation

```bash
# Your repository structure
my-project/
├── docs/
│   ├── README.md
│   ├── getting-started.md
│   ├── api/
│   │   ├── authentication.md
│   │   └── endpoints.md
│   └── guides/
│       ├── deployment.md
│       └── troubleshooting.md
└── src/
    └── ...

# Extract documentation
repository-doc-extractor my-project/docs -v -o project-docs.json
# Scanning directory: my-project/docs
# ✓ Exported 6 markdown file(s)

# Validate
minerva validate project-docs.json
# ✓ Validation successful: project-docs.json contains 6 valid note(s)

# Index
cat > docs-config.json << 'EOF'
{
  "collection_name": "project_docs",
  "description": "My project documentation",
  "chromadb_path": "./chromadb_data",
  "json_file": "project-docs.json"
}
EOF

minerva index --config docs-config.json --verbose
```

### Example 2: Multiple Repositories

```bash
# Extract from multiple projects
repository-doc-extractor ~/projects/api-server/docs -o api-docs.json
repository-doc-extractor ~/projects/web-app/docs -o web-docs.json
repository-doc-extractor ~/projects/mobile-app/docs -o mobile-docs.json

# Combine all documentation
jq -s 'add' *-docs.json > all-docs.json

# Validate combined output
minerva validate all-docs.json

# Index as single collection
minerva index --config all-docs-config.json --verbose
```

### Example 3: Exclude Patterns

```bash
# Repository with drafts and templates to exclude
repository-doc-extractor ./wiki \
  --exclude drafts \
  --exclude templates \
  --exclude archived \
  -v -o wiki.json
```

### Example 4: Extract and Analyze

```bash
# Extract
repository-doc-extractor ./docs -o docs.json

# Count files by directory
jq '[.[].sourcePath | split("/")[0]] | group_by(.) | map({dir: .[0], count: length})' docs.json

# Find largest documents
jq 'sort_by(.size) | reverse | .[0:5] | map({title, size, path: .sourcePath})' docs.json

# List all titles
jq '.[].title' docs.json
```

### Example 5: Complete Workflow

```bash
# Step 1: Clone repository with documentation
git clone https://github.com/example/docs-repo.git
cd docs-repo

# Step 2: Extract all markdown files
repository-doc-extractor . -v -o docs.json
# Scanning directory: .
# ✓ Exported 127 markdown file(s)

# Step 3: Validate
minerva validate docs.json
# ✓ Validation successful: docs.json contains 127 valid note(s)

# Step 4: Create index configuration
cat > config.json << 'EOF'
{
  "collection_name": "external_docs",
  "description": "Documentation from external repository",
  "chromadb_path": "./chromadb_data",
  "json_file": "docs.json"
}
EOF

# Step 5: Index
minerva index --config config.json --verbose

# Step 6: Peek at results
minerva peek external_docs --chromadb ./chromadb_data --format table
```

## Use Cases

### Documentation Repositories

Extract entire documentation sites:

```bash
# Docusaurus project
repository-doc-extractor ./docs -o docusaurus.json

# MkDocs project
repository-doc-extractor ./docs -o mkdocs.json

# VitePress project
repository-doc-extractor ./docs -o vitepress.json

# Sphinx project
repository-doc-extractor ./source -o sphinx.json
```

### Personal Wikis

```bash
# Obsidian vault
repository-doc-extractor ~/Documents/ObsidianVault --exclude .obsidian -o vault.json

# Foam workspace
repository-doc-extractor ~/foam-workspace -o foam.json

# Dendron notes
repository-doc-extractor ~/Dendron -o dendron.json
```

### Open Source Documentation

```bash
# Clone and index popular project docs
git clone https://github.com/kubernetes/website.git
repository-doc-extractor kubernetes/website/content/en/docs -o k8s-docs.json
minerva validate k8s-docs.json
minerva index --config k8s-config.json --verbose
```

### Research Notes

```bash
# Academic research directory
repository-doc-extractor ~/Research/Papers --exclude drafts -o research.json
minerva index --config research-config.json
```

## Troubleshooting

### Issue: "No markdown files found"

**Cause**: Directory doesn't contain any `.md` files, or all files are in excluded directories.

**Solution**:

```bash
# Check if markdown files exist
find /path/to/dir -name "*.md" -type f

# Try with verbose mode to see what's being scanned
repository-doc-extractor /path/to/dir -v -o output.json
```

### Issue: "Directory not found"

**Cause**: Path doesn't exist or is incorrect.

**Solution**:

```bash
# Verify path exists
ls -la /path/to/dir

# Use absolute path
repository-doc-extractor /absolute/path/to/dir -o output.json

# Check current directory
repository-doc-extractor $(pwd)/docs -o output.json
```

### Issue: "Path is not a directory"

**Cause**: You specified a file instead of a directory.

**Solution**:

```bash
# ✗ Wrong: passing a file
repository-doc-extractor README.md -o output.json

# ✓ Correct: passing parent directory
repository-doc-extractor . -o output.json
```

### Issue: "Permission denied" warnings

**Cause**: Some files can't be read due to permissions.

**Solution**:

```bash
# Check file permissions
ls -la /path/to/file.md

# Fix permissions if you own the files
chmod +r /path/to/dir/**/*.md

# Run with sudo if necessary (not recommended)
sudo repository-doc-extractor /restricted/path -o output.json
```

### Issue: "File encoding error"

**Cause**: Markdown file is not UTF-8 encoded.

**Solution**:

The extractor will skip files with encoding errors and continue. Check stderr output for warnings:

```bash
repository-doc-extractor ./docs -v -o output.json
# Warning: Skipping docs/old-file.md: File encoding error...
```

Convert problematic files to UTF-8:

```bash
# Convert file to UTF-8
iconv -f ISO-8859-1 -t UTF-8 old-file.md > new-file.md
```

### Issue: Validation fails after extraction

**Cause**: Extracted notes don't conform to schema.

**Solution**:

```bash
# Validate with verbose mode
minerva validate output.json --verbose

# Check first note manually
jq '.[0]' output.json

# Common issues:
# - Empty markdown files (size: 0) - these should be okay per schema
# - Invalid dates (shouldn't happen with filesystem dates)
```

## Performance

**Extraction speed**: Depends on number of files and directory depth.

| Files  | Time  | Rate    |
| ------ | ----- | ------- |
| 10     | < 1s  | instant |
| 100    | ~1s   | 100/sec |
| 1,000  | ~10s  | 100/sec |
| 10,000 | ~100s | 100/sec |

Performance is linear with file count. Most time is spent reading file contents and metadata.

**Memory usage**: Minimal (~20-50MB for typical documentation sets)

All notes are collected in memory before writing, so extremely large repositories (>100k files) may require more RAM.

## Limitations

### Not Supported

- ❌ **Non-markdown files**: Only `.md` files are processed (no `.txt`, `.rst`, `.adoc`, etc.)
- ❌ **Content transformation**: Markdown is extracted as-is, no preprocessing
- ❌ **Broken link detection**: Doesn't validate internal links
- ❌ **Frontmatter extraction**: YAML/TOML frontmatter is included in markdown content, not parsed separately
- ❌ **Git history**: Only current file state, no historical versions

### Known Issues

1. **Frontmatter handling**: If markdown files have YAML frontmatter, it's included in the content as-is
2. **Symlinks**: May follow symlinks and process same files twice
3. **Hidden files**: Files starting with `.` are processed (except in excluded directories)
4. **Large files**: Very large markdown files (>10MB) may be slow to process

### Workarounds

**For frontmatter-heavy markdown**:
The frontmatter will be included in search results. If this is undesirable, preprocess files to strip frontmatter:

```bash
# Strip frontmatter using sed (basic approach)
find docs -name "*.md" -exec sed -i '1{/^---$/!b};2,/^---$/d' {} \;
```

**For selective extraction**:
If you only want specific subdirectories:

```bash
# Extract only specific directories
repository-doc-extractor ./docs/guides -o guides.json
repository-doc-extractor ./docs/api -o api.json

# Combine
jq -s 'add' guides.json api.json > combined.json
```

## Advanced Usage

### Batch Processing Multiple Repositories

```bash
#!/bin/bash
# Process documentation from multiple repos

repos=(
  "~/projects/api-server/docs"
  "~/projects/web-frontend/docs"
  "~/projects/mobile-app/docs"
)

for repo in "${repos[@]}"; do
  name=$(basename $(dirname "$repo"))
  echo "Processing: $name"
  repository-doc-extractor "$repo" -o "${name}-docs.json"
done

# Combine all
jq -s 'add' *-docs.json > all-projects-docs.json

# Validate
minerva validate all-projects-docs.json

# Index
minerva index --config all-projects-config.json --verbose
```

### Filtering by Path

```bash
# Extract, then filter by source path
repository-doc-extractor ./docs -o all.json

# Only keep API documentation
jq '[.[] | select(.sourcePath | startswith("api/"))]' all.json > api-only.json

# Only keep guides
jq '[.[] | select(.sourcePath | contains("guides/"))]' all.json > guides-only.json
```

### Statistics and Analysis

```bash
# Get statistics about extracted documentation
jq '{
  total_files: length,
  total_size: (map(.size) | add),
  avg_size: (map(.size) | add / length | floor),
  directories: ([.[].sourcePath | split("/")[0]] | unique | length),
  oldest: (map(.creationDate) | min),
  newest: (map(.modificationDate) | max)
}' docs.json
```

### Directory Structure Analysis

```bash
# List all directories with file counts
jq -r '.[].sourcePath | split("/")[0]' docs.json | sort | uniq -c | sort -rn

# Create tree-like view of paths
jq -r '.[].sourcePath' docs.json | sort
```

## Development

### Code Structure

```
repository-doc-extractor/
├── repository_doc_extractor/
│   ├── __init__.py         # Package init with version
│   ├── cli.py              # Command-line interface
│   └── parser.py           # Directory walking and parsing logic
├── setup.py                # Package configuration
└── README.md              # This file
```

### Running Tests

```bash
cd extractors/repository-doc-extractor

# Create test directory structure
mkdir -p test-docs/subdir
echo "# Test Doc 1" > test-docs/doc1.md
echo "# Test Doc 2" > test-docs/subdir/doc2.md
echo "No H1 here" > test-docs/subdir/doc3.md

# Run extractor
repository-doc-extractor test-docs -v -o test.json

# Validate
minerva validate test.json

# Check output
jq '.' test.json
```

## Related Documentation

- **[Minerva Note Schema](../../docs/NOTE_SCHEMA.md)**: Complete JSON schema specification
- **[Extractor Development Guide](../../docs/EXTRACTOR_GUIDE.md)**: How to write custom extractors
- **[Extractors Overview](../README.md)**: All official extractors
- **[CLAUDE.md](../../CLAUDE.md)**: Complete Minerva development guide

## Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/minerva/issues)
- **Questions**: Ask in [GitHub Discussions](https://github.com/yourusername/minerva/discussions)

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

---

**Made for Minerva** - Index your documentation repositories with AI-powered semantic search.
