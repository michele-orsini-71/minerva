# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Parser
```bash
# Process a Bear backup file
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"

# Or with any .bear2bk file
python cli.py <path-to-bear-backup-file>
```

### Testing
```bash
# Manual testing with sample backup file
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"

# Test the core parsing function programmatically
python -c "from bear_parser import parse_bear_backup; notes = parse_bear_backup('Bear Notes 2025-09-20 at 08.49.bear2bk'); print(f'Extracted {len(notes)} notes')"
```

### Development
```bash
# Run with Python 3.6+ (project uses Python 3.12.0)
python --version  # Should show 3.6+

# Check code structure
python -c "import bear_parser; help(bear_parser.parse_bear_backup)"
```

## Architecture

This is a simple Python utility with a clean separation of concerns:

### Core Components
- **`bear_parser.py`**: Core parsing logic module containing `parse_bear_backup()` function
- **`cli.py`**: Command line interface entry point with argument parsing and progress display

### Data Flow
1. **Input**: Bear backup files (.bear2bk format) - ZIP archives containing TextBundle folders
2. **Processing**: Extract ZIP → Parse TextBundle folders → Extract note metadata and markdown content
3. **Output**: JSON file with structured note data (title, markdown, size, modificationDate)

### Key Design Patterns
- **No external dependencies**: Uses only Python standard library (zipfile, json, tempfile, os, datetime)
- **Error resilience**: Continues processing even if individual notes fail to extract
- **Progress feedback**: Optional callback system for progress reporting during long operations
- **UTF-8 throughout**: Proper international character support for input/output
- **Automatic cleanup**: Uses temporary directories that are automatically cleaned up

### Note Data Structure
Each extracted note contains:
- `title`: Note title from Bear
- `markdown`: Full markdown content
- `size`: UTF-8 byte size of content
- `modificationDate`: UTC ISO format timestamp (YYYY-MM-DDTHH:MM:SSZ)

### Error Handling Strategy
- **File-level errors**: Graceful failure with informative error messages
- **Note-level errors**: Skip corrupted notes and continue processing
- **Automatic filtering**: Trashed notes are filtered out during processing

## File Organization

- Main modules are at root level (bear_parser.py, cli.py)
- No complex package structure - straightforward single-purpose utility
- Sample backup files and generated JSON outputs are in root directory
- Task tracking and documentation in subdirectories (tasks/, various .md files)