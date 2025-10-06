# Tasks for Bear Notes Parser Implementation

## Relevant Files

- `bear_parser.py` - Core parsing logic module containing the main parsing functions ✓ Created with required imports and progress callback support
- `cli.py` - Command line interface entry point for the tool ✓ Created with argument parsing, progress feedback, and JSON output
- `README.md` - Usage instructions and documentation for the tool

### Notes

- This project uses pure Python with no external dependencies beyond standard library
- No unit tests are required per PRD specifications
- UTF-8 encoding is used throughout for all file operations
- All timestamps must be normalized to UTC timezone in ISO format

## Tasks

- [x] 1.0 Core Parser Module Development
  - [x] 1.1 Create `bear_parser.py` with required imports (zipfile, json, tempfile, os, sys, datetime)
  - [x] 1.2 Implement `parse_bear_backup(backup_path: str) -> List[Dict]` main parsing function
  - [x] 1.3 Implement `extract_note_data(textbundle_path: str) -> Dict` for single TextBundle extraction
  - [x] 1.4 Add functionality to extract zip archive to temporary directory
  - [x] 1.5 Add logic to iterate through TextBundle folders in extracted archive
  - [x] 1.6 Implement proper temporary file cleanup mechanism

- [x] 2.0 Command Line Interface Implementation
  - [x] 2.1 Create `cli.py` with main() entry point function
  - [x] 2.2 Add command line argument parsing for .bear2bk file path
  - [x] 2.3 Implement progress feedback showing percentage of notes extracted
  - [x] 2.4 Add JSON output file generation with same base name as input + .json extension
  - [x] 2.5 Ensure UTF-8 encoding for all file operations
  - [x] 2.6 Add logic to overwrite existing output files without prompting

- [x] 3.0 Data Processing and Validation
  - [x] 3.1 Implement info.json parsing to extract Bear metadata
  - [x] 3.2 Add filtering logic to exclude trashed notes (trashed: 1)
  - [x] 3.3 Implement text.markdown file reading and content extraction
  - [x] 3.4 Add UTF-8 byte size calculation for markdown content
  - [x] 3.5 Implement date normalization to UTC timezone in ISO format
  - [x] 3.6 Structure output with required fields: title, markdown, size, modificationDate

- [x] 4.0 Error Handling and Resilience
  - [x] 4.1 Add graceful handling of missing or corrupted TextBundle folders
  - [x] 4.2 Implement logic to skip invalid files and continue processing
  - [x] 4.3 Add error handling for zip extraction failures
  - [x] 4.4 Ensure proper cleanup of temporary files even on errors
  - [x] 4.5 Add basic error indication without verbose debugging

- [x] 5.0 Documentation and Final Integration
  - [x] 5.1 Create README.md with usage instructions and examples
  - [x] 5.2 Add docstrings to all functions following Clean Code principles
  - [x] 5.3 Test the tool with the provided Bear backup file
  - [x] 5.4 Verify output JSON format and data quality
  - [x] 5.5 Ensure all functional requirements from PRD are met