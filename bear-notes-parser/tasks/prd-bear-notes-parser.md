# Product Requirements Document: Bear Notes Parser

## Introduction/Overview

The Bear Notes Parser is a Python-based tool designed to extract note content and metadata from Bear Notes backup files (.bear2bk) for integration into AI-powered personal knowledge systems. The tool processes Bear's TextBundle format exports, filters out trashed notes, and outputs structured data suitable for vector database ingestion.

**Problem Statement**: Users building AI-based personal knowledge systems need a reliable way to extract clean, structured data from their Bear Notes backups to feed vector databases for intelligent note querying and retrieval.

**Goal**: Provide a simple, efficient tool that converts Bear Notes backups into structured JSON data ready for AI/ML processing pipelines.

## Goals

1. **Data Extraction**: Successfully parse Bear Notes backup files and extract note content with metadata
2. **Data Quality**: Filter out trashed notes and provide clean, structured output
3. **Performance**: Handle large note collections (1000+ notes) reliably within reasonable time limits (up to 5 minutes)
4. **Simplicity**: Provide a straightforward command-line interface requiring minimal setup
5. **Reliability**: Skip corrupted files gracefully while continuing to process valid notes

## User Stories

### Primary User Story

**As a** personal knowledge system builder
**I want to** extract my Bear Notes data in a structured format
**So that** I can feed it into a vector database for AI-powered note querying

### Supporting User Stories

**As a** Bear Notes user migrating to an AI system
**I want to** process my backup file with a single command
**So that** I can quickly convert my notes without manual data manipulation

**As a** developer building note processing pipelines
**I want to** get consistent JSON output from Bear backups
**So that** I can reliably integrate the data into my vector database workflow

**As a** user with large note collections
**I want to** process thousands of notes reliably
**So that** my entire knowledge base can be extracted in reasonable time (up to 5 minutes)

## Functional Requirements

### Core Parser Module

1. The system **must** accept a Bear Notes backup file (.bear2bk) as input
2. The system **must** extract and parse TextBundle folders from the zip archive
3. The system **must** read and parse info.json files for note metadata
4. The system **must** filter out notes where `trashed: 1` in the Bear metadata
5. The system **must** read text.markdown files and extract content
6. The system **must** calculate the byte size of markdown content using UTF-8 encoding
7. The system **must** return an array of note objects with exactly these fields:
   - `title`: TextBundle folder name
   - `markdown`: Original markdown content
   - `size`: Content size in bytes
   - `modificationDate`: ISO format timestamp normalized to UTC
8. The system **must** handle missing or corrupted files by skipping them and continuing processing

### Command Line Interface

9. The CLI **must** accept a single argument: the path to a .bear2bk file
10. The CLI **must** generate a JSON output file with the same base name as input + .json extension
11. The CLI **must** overwrite existing output files without prompting
12. The CLI **must** use UTF-8 encoding for all file operations
13. The CLI **must** provide progress feedback showing percentage of notes extracted

### Technical Requirements

14. The implementation **must** use pure Python (no external dependencies beyond standard library)
15. The system **must** use temporary directories for safe zip extraction
16. The system **must** properly clean up temporary files after processing
17. The system **must** normalize all dates to UTC timezone in ISO format
18. The implementation **must** follow Clean Code principles as defined by Robert Martin ("Uncle Bob")

## Non-Goals (Out of Scope)

1. **Asset Processing**: The tool will not extract, process, or include any assets (images, attachments, etc.)
2. **Complex Error Recovery**: No sophisticated error handling or recovery mechanisms for corrupted archives
3. **Configuration Options**: No command-line options for customizing output format or filtering criteria
4. **Incremental Processing**: No support for processing only new/changed notes since last run
5. **GUI Interface**: Command-line only, no graphical user interface
6. **Data Transformation**: No content modification, formatting, or preprocessing beyond basic extraction
7. **Multi-format Support**: Only Bear Notes .bear2bk format, no other note-taking app formats
8. **Unit Tests**: Testing infrastructure is explicitly out of scope per requirements

## Technical Considerations

### Dependencies

- **Standard Library Only**: zipfile, json, tempfile, os, sys, datetime modules
- **Python Version**: Compatible with Python 3.6+
- **Encoding**: UTF-8 for all text operations

### Performance

- **Memory Efficiency**: Process notes individually rather than loading entire archive into memory
- **Standard Extraction**: Use standard zip extraction (not streaming)
- **Temporary Storage**: Use system temp directory for zip extraction
- **File Cleanup**: Ensure proper cleanup of temporary files even on errors

### Data Format

- **Input**: .bear2bk zip files containing TextBundle folders
- **Output**: JSON array of objects with title, markdown, size, modificationDate fields
- **Character Encoding**: UTF-8 throughout the pipeline
- **Date Format**: All timestamps normalized to UTC timezone

### Error Handling

- **Graceful Degradation**: Skip corrupted or invalid TextBundle folders
- **Continue Processing**: Don't halt on individual file errors
- **Minimal Logging**: Basic error indication without verbose debugging

## Success Metrics

### Functional Success

1. **Data Extraction Rate**: Successfully extract >95% of valid, non-trashed notes from backup files
2. **Processing Performance**: Handle 1000+ notes within 5 minutes on standard hardware
3. **Output Quality**: Generate valid JSON with all required fields for every extracted note
4. **Error Resilience**: Continue processing even when 5-10% of TextBundle folders are corrupted

### User Experience Success

1. **Simplicity**: Single command execution with no configuration required
2. **Reliability**: Consistent output format suitable for automated processing
3. **Feedback**: Clear percentage-based progress indication during processing

## Open Questions

1. **Output Validation**: Should the tool validate that generated JSON is well-formed before writing to file?
2. **Memory Optimization**: For archives with 10,000+ notes, should we implement batch processing to manage memory usage?

## Implementation Notes

### File Structure

```text
bear-notes-parser/
├── bear_parser.py    # Core parsing logic
├── cli.py           # Command line interface
└── README.md        # Usage instructions
```

### Key Functions

- `parse_bear_backup(backup_path: str) -> List[Dict]`: Main parsing function
- `extract_note_data(textbundle_path: str) -> Dict`: Extract data from single TextBundle
- `main()`: CLI entry point

### Code Quality Guidelines

- **Clean Code**: Follow Robert Martin's Clean Code principles including meaningful names, small functions, and clear responsibilities
- **Pure Python**: Use only standard library modules (zipfile, json, tempfile, os, sys, datetime)
- **Date Handling**: All timestamps must be normalized to UTC timezone
- **Extraction Method**: Use standard zip extraction, not streaming
- **Progress Reporting**: Display percentage of notes processed

This PRD provides the foundation for implementing a focused, efficient Bear Notes parser tailored for AI knowledge system integration.