# PRD: Markdown Books to CAG Format Converter

## Introduction/Overview

This tool converts classic book markdown files into the JSON format expected by the CAG (Content Augmented Generation) data creator pipeline. Each book is split into chapters, with each chapter becoming a separate entry in the output JSON, enabling granular search and retrieval through the RAG system.

**Problem**: Classic books in markdown format (located at `/Users/michele/my-code/classic-books-markdown`) need to be processed into the same JSON format that the CAG data creator expects from Bear Notes backups, so they can be ingested into the RAG (Retrieval-Augmented Generation) system.

**Solution**: A command-line tool that parses book metadata, automatically detects chapter boundaries, and generates properly formatted JSON entries that can be consumed by the existing CAG pipeline.

## Goals

1. **Enable book ingestion into RAG system**: Convert markdown books to Bear Notes-compatible JSON format
2. **Preserve chapter granularity**: Split books by chapters so searches can identify specific chapter locations
3. **Maintain metadata provenance**: Extract and embed book metadata (title, author, year) into each chapter
4. **Ensure pipeline compatibility**: Generate output that `full_pipeline.py` can process without modification
5. **Provide clear feedback**: Include progress indicators for long-running operations

## User Stories

1. **As a knowledge base curator**, I want to convert a single book markdown file to JSON format, so that I can ingest it into the RAG system for semantic search.

2. **As a researcher**, I want each chapter to be a separate searchable unit with book context, so that search results can point me to specific chapters rather than entire books.

3. **As a developer**, I want clear error messages when conversion fails, so that I can quickly identify and fix issues with source files.

4. **As a user processing large books**, I want to see progress indicators, so that I know the tool is working and can estimate completion time.

## Functional Requirements

### 1. Input/Output Specification

- **FR-1.1**: The tool MUST accept a single markdown file path as a required command-line argument
- **FR-1.2**: The tool MUST support an optional `--output` flag to specify custom output path
- **FR-1.3**: The tool MUST derive output filename from input filename with `.json` extension when no custom output is specified
- **FR-1.4**: The tool MUST create output in the same directory as input when no custom path is specified

### 2. Source Format Parsing

- **FR-2.1**: The tool MUST parse markdown files with the following header structure:
  ```markdown
  # Title: [Book Title]
  ## Author: [Author Name]
  ## Year: [Publication Year]
  -------
  ```
- **FR-2.2**: The tool MUST recognize `-------` as the separator between header metadata and book content
- **FR-2.3**: The tool MUST extract title from `# Title:` lines
- **FR-2.4**: The tool MUST extract author from `## Author:` lines
- **FR-2.5**: The tool MUST extract publication year from `## Year:` lines

### 3. Chapter Detection

- **FR-3.1**: The tool MUST automatically detect chapter boundaries using markdown headers at levels 2, 3, or 4 (`##`, `###`, `####`)
- **FR-3.2**: The tool MUST treat any level 2-4 header occurring after the `-------` separator as a potential chapter boundary
- **FR-3.3**: The tool MUST extract chapter titles from the header text (e.g., `## CHAPTER I` → `"CHAPTER I"`)
- **FR-3.4**: When no chapters are detected, the tool MUST log a warning and skip the file entirely
- **FR-3.5**: The tool MUST handle various chapter naming conventions (CHAPTER, Chapter, PART, Book, Section, etc.) without explicit configuration

### 4. JSON Output Format

- **FR-4.1**: The tool MUST generate JSON matching the Bear Notes backup format exactly:
  ```json
  [
    {
      "title": "string",
      "markdown": "string",
      "size": number,
      "modificationDate": "ISO 8601 timestamp",
      "creationDate": "ISO 8601 timestamp"
    }
  ]
  ```
- **FR-4.2**: Each chapter entry's `title` field MUST follow the pattern: `"[Book Title] - [Chapter Title]"`
- **FR-4.3**: Each chapter entry's `markdown` field MUST contain:
  - Chapter heading with book metadata: `# [Book Title] - [Chapter Title]\n**Author:** [Author Name] | **Year:** [Publication Year]\n\n`
  - Original chapter content
- **FR-4.4**: The `size` field MUST contain the byte length of the markdown content (UTF-8 encoding)
- **FR-4.5**: The `creationDate` field MUST use publication year as `YYYY-01-01T00:00:00Z`
- **FR-4.6**: The `modificationDate` field MUST be identical to `creationDate` (books don't change after publication)

### 5. Metadata Handling

- **FR-5.1**: When title is missing, the tool MUST fail with error message: "Missing required field: Title"
- **FR-5.2**: When author is missing, the tool MUST fail with error message: "Missing required field: Author"
- **FR-5.3**: When year is missing, the tool MUST fail with error message: "Missing required field: Year"
- **FR-5.4**: When year is not a valid 4-digit number, the tool MUST fail with error message: "Invalid year format: [value]"

### 6. Error Handling

- **FR-6.1**: The tool MUST use fail-fast error handling (exit immediately on first error)
- **FR-6.2**: The tool MUST display clear, actionable error messages including file path and issue description
- **FR-6.3**: When input file is not found, the tool MUST exit with message: "Input file not found: [path]"
- **FR-6.4**: When input file is not readable, the tool MUST exit with message: "Cannot read input file: [path]"
- **FR-6.5**: When output path is not writable, the tool MUST exit with message: "Cannot write to output path: [path]"
- **FR-6.6**: All error messages MUST be written to stderr
- **FR-6.7**: The tool MUST exit with non-zero status code on any error

### 7. Progress Feedback

- **FR-7.1**: The tool MUST display progress indicators for long-running operations
- **FR-7.2**: The tool MUST show: "Parsing [filename]..." when starting to process a file
- **FR-7.3**: The tool MUST show: "Detected [N] chapters" after chapter detection
- **FR-7.4**: The tool MUST show: "Processing chapter [N]/[Total]: [Chapter Title]" for each chapter
- **FR-7.5**: The tool MUST show: "Successfully created [output_path] with [N] chapters" upon completion
- **FR-7.6**: Progress messages MUST be written to stdout

### 8. Command-Line Interface

- **FR-8.1**: The tool MUST implement this interface:
  ```bash
  python markdown_to_cag.py <input_markdown_file> [--output <output_json_file>]
  ```
- **FR-8.2**: The tool MUST display usage help when run without arguments
- **FR-8.3**: The tool MUST support `-h` and `--help` flags to display detailed usage information
- **FR-8.4**: Help text MUST include examples of common usage patterns

## Non-Goals (Out of Scope)

The following features are explicitly **not included** in Version 1 to maintain focused scope:

1. **Batch processing**: Processing multiple books in a single command (single file only in V1)
2. **Custom chapter patterns**: Regex-based configuration for chapter detection (auto-detection only)
3. **Metadata file generation**: Separate book-level metadata files (JSON output only)
4. **Output validation**: Schema validation or pipeline integration testing (manual verification only)
5. **Interactive mode**: Prompting user for decisions or corrections
6. **Lenient parsing**: Continue-on-error or default value substitution
7. **Auto-chunking**: Splitting books without chapters into fixed-size chunks
8. **Additional metadata**: Extracting genre, language, publisher, ISBN, etc.
9. **Format conversion**: Supporting other input formats (EPUB, PDF, HTML)
10. **Collection metadata**: Creating CAG pipeline configuration files

## Design Considerations

### Code Structure

The implementation should follow a modular design:

```
markdown_to_cag.py
├── main()                    # CLI entry point and argument parsing
├── parse_book_file()         # Read and validate markdown file
├── extract_metadata()        # Parse header section (title, author, year)
├── detect_chapters()         # Split content by headers (levels 2-4)
├── create_chapter_entry()    # Generate JSON entry for single chapter
└── write_output_json()       # Write final JSON array to file
```

### Dependencies

- **Python version**: 3.13 (matches project environment)
- **Standard library only**: No external dependencies for V1
- **Modules needed**: `argparse`, `json`, `re`, `sys`, `os`, `pathlib`

### File Processing

1. Read entire markdown file into memory (books are typically < 2MB)
2. Split into header and content sections using `-------` delimiter
3. Parse metadata using regex patterns
4. Split content by level 2-4 markdown headers
5. Build JSON entries in memory
6. Write complete JSON array to file

### Chapter Detection Algorithm

```python
# Pseudo-code for chapter detection
chapters = []
pattern = r'^(#{2,4})\s+(.+)$'  # Match ## ### #### headers

for match in re.finditer(pattern, content, re.MULTILINE):
    chapter_title = match.group(2).strip()
    chapter_start = match.end()
    chapters.append({
        'title': chapter_title,
        'start_pos': chapter_start
    })

# Extract content between chapter boundaries
for i, chapter in enumerate(chapters):
    start = chapter['start_pos']
    end = chapters[i+1]['start_pos'] if i+1 < len(chapters) else len(content)
    chapter['content'] = content[start:end].strip()
```

## Technical Considerations

### Date Formatting

- Use `datetime` module to ensure consistent ISO 8601 formatting
- Publication year becomes January 1st of that year at midnight UTC
- Example: `1764` → `"1764-01-01T00:00:00Z"`

### UTF-8 Encoding

- All file operations must explicitly use UTF-8 encoding
- Size calculation must use UTF-8 byte length: `len(content.encode('utf-8'))`
- Handle Unicode characters properly (e.g., em dashes, quotes, accented characters)

### Performance Expectations

- Target: Process typical book (~200 chapters, ~500KB) in < 5 seconds
- This is a guideline, not a hard requirement for V1
- No optimization needed for V1 unless obviously slow

### Integration with CAG Pipeline

The output JSON must be usable with the existing pipeline:

```bash
# Step 1: Convert book to JSON
cd markdown-books-extractor
python markdown_to_cag.py "/Users/michele/my-code/classic-books-markdown/Horace Walpole/The Castle of Otranto.md"

# Step 2: Process with CAG pipeline
cd ../markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-ollama.json
# (config points to: "json_file": "../markdown-books-extractor/The Castle of Otranto.json")
```

## Success Metrics

The feature will be considered successful when:

1. **Parsing accuracy**: Successfully extracts metadata from all well-formed book markdown files (100% accuracy on test corpus)
2. **Chapter detection**: Correctly identifies and splits chapters across various naming conventions (verified manually on sample books)
3. **Format compliance**: Output JSON is identical in structure to Bear Notes format (validated by CAG pipeline acceptance)
4. **Pipeline integration**: Generated JSON files are successfully processed by `full_pipeline.py` without errors (end-to-end test passes)
5. **User feedback**: Progress indicators provide clear visibility into processing status (subjective evaluation)
6. **Error clarity**: Error messages enable users to quickly identify and fix issues (no confusion during testing)

## Example Output

### Input File
`/Users/michele/my-code/classic-books-markdown/Horace Walpole/The Castle of Otranto.md`

### Expected Console Output
```
Parsing The Castle of Otranto.md...
Extracted metadata: Title="The Castle of Otranto", Author="Horace Walpole", Year=1764
Detected 5 chapters
Processing chapter 1/5: CHAPTER I
Processing chapter 2/5: CHAPTER II
Processing chapter 3/5: CHAPTER III
Processing chapter 4/5: CHAPTER IV
Processing chapter 5/5: CHAPTER V
Successfully created The Castle of Otranto.json with 5 chapters
```

### Output File Content
`The Castle of Otranto.json`:

```json
[
  {
    "title": "The Castle of Otranto - CHAPTER I",
    "markdown": "# The Castle of Otranto - CHAPTER I\n**Author:** Horace Walpole | **Year:** 1764\n\nManfred, Prince of Otranto, had one son and one daughter...",
    "size": 15234,
    "modificationDate": "1764-01-01T00:00:00Z",
    "creationDate": "1764-01-01T00:00:00Z"
  },
  {
    "title": "The Castle of Otranto - CHAPTER II",
    "markdown": "# The Castle of Otranto - CHAPTER II\n**Author:** Horace Walpole | **Year:** 1764\n\nThe door of the chamber...",
    "size": 18456,
    "modificationDate": "1764-01-01T00:00:00Z",
    "creationDate": "1764-01-01T00:00:00Z"
  }
]
```

## Testing Strategy

### Manual Testing Approach (V1 Requirement)

1. **Happy path test**:
   - Input: `The Castle of Otranto.md` (known good file)
   - Verify: All 5 chapters extracted correctly
   - Verify: JSON structure matches Bear Notes format exactly
   - Verify: Metadata appears correctly in each chapter

2. **Edge case testing**:
   - Book with single chapter
   - Book with 100+ chapters (test progress indicators)
   - Book with mixed header levels (##, ###, ####)
   - Book with Unicode characters in title/content

3. **Error condition testing**:
   - Missing title field → should fail with clear error
   - Missing author field → should fail with clear error
   - Missing year field → should fail with clear error
   - Invalid year (non-numeric) → should fail with clear error
   - File not found → should fail with clear error
   - No chapters detected → should fail with clear error

4. **Integration testing**:
   - Process book with script
   - Feed output to `full_pipeline.py`
   - Verify ChromaDB ingestion succeeds
   - Perform sample search to verify chapter granularity

### Test Data

**Primary test file**: `/Users/michele/my-code/classic-books-markdown/Horace Walpole/The Castle of Otranto.md`

**Additional test candidates**:
- Books with different chapter styles
- Books from different authors/eras
- Books with varying lengths

### Success Criteria

- [ ] Script accepts markdown file path as input
- [ ] Script generates valid JSON output
- [ ] Output format matches Bear Notes backup structure exactly
- [ ] Chapter titles include book name prefix
- [ ] Each chapter markdown includes book metadata header
- [ ] Dates are formatted correctly (ISO 8601 with publication year)
- [ ] Size field accurately reflects content byte length (UTF-8)
- [ ] Error messages are clear and actionable
- [ ] Progress indicators display during processing
- [ ] Output file can be successfully processed by `full_pipeline.py` in the CAG data creator
- [ ] All manual tests pass without errors

## Open Questions

1. **Header level precedence**: If a book has both `##` and `###` headers, should we:
   - Treat both as chapters (flatten hierarchy)?
   - Only use the highest level detected (e.g., prefer `##` over `###`)?
   - **Recommendation**: Flatten hierarchy (treat all detected levels as chapters) for simplicity in V1

2. **Very large chapters**: Should we warn or handle chapters exceeding a certain size?
   - **Context**: CAG chunking happens later in pipeline, but very large chapters might indicate detection issues
   - **Recommendation**: No size limits in V1, trust pipeline chunking

3. **Chapter numbering**: Should we add numeric IDs to chapters beyond their titles?
   - **Context**: Could help with ordering/navigation
   - **Recommendation**: Not needed for V1, titles provide sufficient context

4. **Partial success handling**: If one chapter fails to process, should we:
   - Skip it and continue (return partial results)?
   - Fail entire file (current fail-fast approach)?
   - **Decision**: Stick with fail-fast for V1 (simpler, more predictable)

## Appendix: Reference Files

- **Target format example**: `/Users/michele/my-code/search-markdown-notes/test-data/Bear Notes 2025-10-11 at 10.17.json`
- **Source markdown example**: `/Users/michele/my-code/classic-books-markdown/Horace Walpole/The Castle of Otranto.md`
- **CAG pipeline config**: `/Users/michele/my-code/search-markdown-notes/configs/example-ollama.json`
- **CAG pipeline script**: `/Users/michele/my-code/search-markdown-notes/markdown-notes-cag-data-creator/full_pipeline.py`

## Version History

- **v1.0** (Current): Initial PRD with single-file processing, auto-detection of chapter headers (levels 2-4), fail-fast error handling, and progress indicators
