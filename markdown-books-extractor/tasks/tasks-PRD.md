# Task List: Markdown Books to CAG Format Converter

Generated from: `PRD.md`

## Relevant Files

- `markdown-books-extractor/markdown_to_cag.py` - Main CLI script and orchestration logic [COMPLETED]
- `markdown-books-extractor/book_parser.py` - Book file parsing and metadata extraction module
- `markdown-books-extractor/chapter_detector.py` - Chapter boundary detection and splitting logic
- `markdown-books-extractor/json_generator.py` - Bear Notes JSON format output generator [COMPLETED]
- `markdown-books-extractor/models.py` - Data models for Book, Chapter, and ChapterEntry (optional, for type safety)
- `markdown-books-extractor/tests/test_integration.py` - Integration test suite [COMPLETED]
- `markdown-books-extractor/tests/test_castle_of_otranto.py` - Manual test script for primary test file
- `markdown-books-extractor/tests/test_edge_cases.py` - Manual test script for edge cases

### Notes

- Follow existing codebase patterns from `markdown-notes-cag-data-creator/json_loader.py`:
  - Use `pathlib.Path` for file operations
  - Use `sys.stderr` for error messages, `sys.stdout` for progress
  - Use `sys.exit(1)` for fail-fast error handling
  - Explicit UTF-8 encoding for all file operations
- Python version: 3.13 (matches project environment in `.venv/`)
- Standard library only - no external dependencies for V1
- Target test file: `/Users/michele/my-code/classic-books-markdown/Horace Walpole/The Castle of Otranto.md`

## Tasks

- [ ] 1.0 Create core book parser module with metadata extraction
  - [x] 1.1 Create `book_parser.py` module with function `parse_book_file(file_path: str) -> dict`
  - [x] 1.2 Implement file existence and readability validation using `pathlib.Path`
  - [x] 1.3 Read entire file content with UTF-8 encoding (fail on encoding errors)
  - [x] 1.4 Split content into header section and body using `-------` delimiter (use `str.split()` with maxsplit=1)
  - [x] 1.5 Extract metadata from header using regex patterns:
    - Pattern for title: `r'^#\s+Title:\s*(.+)$'` (multiline mode)
    - Pattern for author: `r'^##\s+Author:\s*(.+)$'` (multiline mode)
    - Pattern for year: `r'^##\s+Year:\s*(\d{4})$'` (multiline mode)
  - [x] 1.6 Validate required fields (title, author, year) are present and non-empty after stripping whitespace
  - [x] 1.7 Validate year is a 4-digit number and convert to integer
  - [x] 1.8 Return dictionary: `{"title": str, "author": str, "year": int, "content": str}` where content is the body after `-------`
  - [x] 1.9 Add docstring with example usage and error behavior

- [ ] 2.0 Implement chapter detection and splitting logic
  - [x] 2.1 Create `chapter_detector.py` module with function `detect_chapters(content: str, book_metadata: dict) -> list[dict]`
  - [x] 2.2 Define regex pattern to match level 2-4 headers: `r'^(#{2,4})\s+(.+)$'` (multiline mode)
  - [x] 2.3 Use `re.finditer()` to find all chapter boundaries, storing match position and chapter title
  - [x] 2.4 Validate at least one chapter was detected (if zero, raise ValueError with clear message)
  - [x] 2.5 Extract content between chapter boundaries:
    - For each chapter, start position is after the header line (use `match.end()` to skip past newline)
    - End position is the start of the next chapter (or end of content for last chapter)
    - Strip leading/trailing whitespace from chapter content
  - [x] 2.6 Build list of chapter dictionaries: `[{"title": str, "content": str, "index": int}, ...]`
  - [x] 2.7 Handle edge case: empty chapter content (skip chapters with no content after stripping)
  - [x] 2.8 Add docstring explaining the detection algorithm and expected input format

- [x] 3.0 Build JSON output generator with Bear Notes format compliance
  - [x] 3.1 Create `json_generator.py` module with function `create_chapter_entries(chapters: list[dict], book_metadata: dict) -> list[dict]`
  - [x] 3.2 For each chapter, construct the combined title: `f"{book_metadata['title']} - {chapter['title']}"`
  - [x] 3.3 Build markdown content with metadata header:
    - Line 1: `f"# {combined_title}\n"`
    - Line 2: `f"**Author:** {book_metadata['author']} | **Year:** {book_metadata['year']}\n\n"`
    - Lines 3+: Original chapter content
  - [x] 3.4 Calculate UTF-8 byte size: `len(markdown_content.encode('utf-8'))`
  - [x] 3.5 Generate ISO 8601 timestamps using `datetime` module:
    - Import: `from datetime import datetime, timezone`
    - Creation date: `datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')`
    - Modification date: same as creation date (books don't change)
  - [x] 3.6 Build chapter entry dictionary matching Bear Notes format (title, markdown, size, modificationDate, creationDate)
  - [x] 3.7 Return list of all chapter entries
  - [x] 3.8 Add function `write_json_output(entries: list[dict], output_path: str) -> None` to write JSON file
  - [x] 3.9 In write function: validate output path is writable, write with UTF-8 encoding, use `json.dump()` with `indent=2` and `ensure_ascii=False`

- [x] 4.0 Develop command-line interface with argument parsing
  - [x] 4.1 Create main script `markdown_to_cag.py` with `if __name__ == "__main__":` entry point
  - [x] 4.2 Set up `argparse.ArgumentParser` with description: "Convert classic book markdown files to CAG-compatible JSON format"
  - [x] 4.3 Add positional argument `input_file` with help text: "Path to input markdown file"
  - [x] 4.4 Add optional argument `--output` with help text: "Path to output JSON file (default: same directory as input with .json extension)"
  - [x] 4.5 Add `-h/--help` flag support (automatic with argparse)
  - [x] 4.6 Implement output path derivation logic:
    - If `--output` provided, use it as-is
    - Otherwise: `Path(input_file).with_suffix('.json')`
  - [x] 4.7 Create `main()` function that orchestrates the pipeline:
    - Call `parse_book_file()` → get book metadata and content
    - Call `detect_chapters()` → get chapter list
    - Call `create_chapter_entries()` → get JSON entries
    - Call `write_json_output()` → write to file
  - [x] 4.8 Add example usage in help text (use `epilog` parameter): Show basic usage and usage with custom output path
  - [x] 4.9 Ensure all functions are imported at top of script

- [ ] 5.0 Add comprehensive error handling and validation
  - [ ] 5.1 In `parse_book_file()`: Handle `FileNotFoundError` → print "Input file not found: {path}" to stderr and exit(1)
  - [ ] 5.2 In `parse_book_file()`: Handle `PermissionError` → print "Cannot read input file: {path}" to stderr and exit(1)
  - [ ] 5.3 In `parse_book_file()`: Handle `UnicodeDecodeError` → print "File encoding error in {path}: {error}" to stderr and exit(1)
  - [ ] 5.4 In `parse_book_file()`: Validate title present → raise ValueError("Missing required field: Title")
  - [ ] 5.5 In `parse_book_file()`: Validate author present → raise ValueError("Missing required field: Author")
  - [ ] 5.6 In `parse_book_file()`: Validate year present → raise ValueError("Missing required field: Year")
  - [ ] 5.7 In `parse_book_file()`: Validate year is 4-digit number → raise ValueError(f"Invalid year format: {year_value}")
  - [ ] 5.8 In `detect_chapters()`: Validate at least one chapter found → raise ValueError(f"No chapters detected in file. Expected headers (##, ###, or ####)")
  - [ ] 5.9 In `write_json_output()`: Handle `PermissionError` → print "Cannot write to output path: {path}" to stderr and exit(1)
  - [ ] 5.10 In `write_json_output()`: Handle `OSError` (disk full, etc.) → print "Error writing output file: {error}" to stderr and exit(1)
  - [ ] 5.11 In `main()`: Wrap entire pipeline in try-except to catch ValueError and print error to stderr, then exit(1)
  - [ ] 5.12 Test all error paths manually by creating test files with: missing fields, invalid year, no chapters, unreadable files

- [ ] 6.0 Implement progress feedback system
  - [ ] 6.1 In `main()` after parsing: Print to stdout: "Parsing {filename}..." (use `Path(input_file).name` for filename only)
  - [ ] 6.2 In `main()` after metadata extraction: Print to stdout: 'Extracted metadata: Title="{title}", Author="{author}", Year={year}'
  - [ ] 6.3 In `main()` after chapter detection: Print to stdout: "Detected {count} chapters"
  - [ ] 6.4 In `main()` during chapter processing: For each chapter, print to stdout: "Processing chapter {current}/{total}: {chapter_title}"
  - [ ] 6.5 In `main()` after successful write: Print to stdout: "Successfully created {output_filename} with {count} chapters" (use `Path(output_path).name`)
  - [ ] 6.6 Ensure all progress messages go to stdout (use `print()` without `file=` parameter)
  - [ ] 6.7 Ensure all error messages go to stderr (use `print(..., file=sys.stderr)`)
  - [ ] 6.8 Test progress output by running with real book file and observing console output

- [ ] 7.0 Create manual test suite and validate with real book files
  - [ ] 7.1 **Happy path test**: Run script on "The Castle of Otranto.md"
    - Verify: Script completes without errors
    - Verify: Output JSON file created in same directory
    - Verify: JSON contains exactly 5 chapter entries (manually count chapters in source file)
    - Verify: Each entry has all required fields (title, markdown, size, modificationDate, creationDate)
    - Verify: First chapter title is "The Castle of Otranto - CHAPTER I."
    - Verify: Markdown content includes metadata header: "**Author:** Horace Walpole | **Year:** 1764"
    - Verify: Dates are "1764-01-01T00:00:00Z"
  - [ ] 7.2 **Custom output path test**: Run script with `--output /tmp/test_output.json`
    - Verify: Output created at specified path, not in source directory
  - [ ] 7.3 **Error test - missing title**: Create test file without "# Title:" line
    - Verify: Script exits with error "Missing required field: Title"
    - Verify: Error goes to stderr (redirect stderr to file and check contents)
  - [ ] 7.4 **Error test - missing author**: Create test file without "## Author:" line
    - Verify: Script exits with error "Missing required field: Author"
  - [ ] 7.5 **Error test - missing year**: Create test file without "## Year:" line
    - Verify: Script exits with error "Missing required field: Year"
  - [ ] 7.6 **Error test - invalid year**: Create test file with "## Year: ABC"
    - Verify: Script exits with error "Invalid year format: ABC"
  - [ ] 7.7 **Error test - no chapters**: Create test file with valid header but no ## headers in content
    - Verify: Script exits with error "No chapters detected in file"
  - [ ] 7.8 **Error test - file not found**: Run script with non-existent file path
    - Verify: Script exits with error "Input file not found: {path}"
  - [ ] 7.9 **Edge case test - single chapter**: Create test file with valid header and only one ## chapter
    - Verify: Output JSON contains 1 entry
    - Verify: All fields are correct
  - [ ] 7.10 **Edge case test - mixed header levels**: Create test file with ##, ###, and #### headers
    - Verify: All header levels are detected as chapters (flattened hierarchy)
    - Verify: Chapter count matches total number of level 2-4 headers
  - [ ] 7.11 **Edge case test - Unicode characters**: Create test file with accented characters, em dashes, quotes in title/content
    - Verify: All Unicode characters preserved in output JSON
    - Verify: Size calculation is correct (UTF-8 byte length)
  - [ ] 7.12 **Integration test - CAG pipeline**:
    - Run markdown_to_cag.py on "The Castle of Otranto.md"
    - Create/update config file in `configs/` to point to output JSON
    - Run `cd ../markdown-notes-cag-data-creator && python full_pipeline.py --config ../configs/test-books.json`
    - Verify: Pipeline completes without errors
    - Verify: ChromaDB collection created with chunks from book chapters
    - Optional: Use chroma-peek to visually inspect collection

---

## Implementation Notes

### Recommended Development Order

1. Start with task 1.0 (parser) - this is the foundation
2. Implement task 2.0 (chapter detection) - depends on parser output
3. Build task 3.0 (JSON generator) - depends on chapter detection
4. Create task 4.0 (CLI) to tie everything together
5. Add task 5.0 (error handling) throughout all modules
6. Implement task 6.0 (progress feedback) in the main orchestration
7. Execute task 7.0 (testing) to validate the complete implementation

### Code Organization Tips

- Keep functions small and focused (each sub-task could be one function)
- Use type hints for better IDE support: `def parse_book_file(file_path: str) -> dict:`
- Add docstrings with examples to every public function
- Consider creating a `models.py` file with dataclasses for Book/Chapter if you want stronger typing (optional for V1)

### Testing Tips

- Create a `tests/` subdirectory for test files and scripts
- Keep original "The Castle of Otranto.md" unchanged for reference
- Create small synthetic test files for error cases (faster to iterate)
- Use `pytest` command if you want to add unit tests later (not required for V1)
