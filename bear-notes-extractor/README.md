# Bear Notes Parser

A Python tool for extracting notes from Bear backup files (.bear2bk format) and converting them to structured JSON data.

## Features

- Extract notes from Bear backup files (.bear2bk)
- Filter out trashed notes automatically
- Convert timestamps to UTC ISO format
- Calculate UTF-8 byte sizes for content
- Progress feedback during processing
- Pure Python implementation (no external dependencies)
- UTF-8 encoding support throughout

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## Installation

Clone or download the repository:

```bash
git clone <repository-url>
cd bear-notes-parser
```

## Usage

### Command Line Interface

```bash
python cli.py <path-to-bear-backup-file>
```

### Examples

Process a Bear backup file:

```bash
python cli.py "Bear Notes 2025-09-20 at 08.49.bear2bk"
```

This will:
1. Process the backup file
2. Show progress feedback: `Progress: 150/300 (50.0%)`
3. Create an output file: `Bear Notes 2025-09-20 at 08.49.json`

### Output Format

The tool generates a JSON file with the following structure:

```json
[
  {
    "title": "My First Note",
    "markdown": "# My First Note\n\nThis is the content of my note...",
    "size": 1234,
    "modificationDate": "2025-09-20T08:49:30Z"
  },
  {
    "title": "Another Note",
    "markdown": "Some more note content...",
    "size": 567,
    "modificationDate": "2025-09-19T15:30:45Z"
  }
]
```

#### Field Descriptions

- `title`: The note title as stored in Bear
- `markdown`: Full markdown content of the note
- `size`: UTF-8 byte size of the markdown content
- `modificationDate`: Last modification date in UTC ISO format (YYYY-MM-DDTHH:MM:SSZ)

### Programmatic Usage

You can also use the parser as a Python module:

```python
from bear_parser import parse_bear_backup

# Parse backup file with progress callback
def show_progress(current, total):
    print(f"Processing: {current}/{total}")

notes = parse_bear_backup("backup.bear2bk", progress_callback=show_progress)

# Process the extracted notes
for note in notes:
    print(f"Title: {note['title']}")
    print(f"Size: {note['size']} bytes")
    print(f"Modified: {note['modificationDate']}")
```

## Error Handling

The tool handles various error conditions gracefully:

- **Missing backup file**: Reports file not found error
- **Corrupted backup**: Reports zip extraction failure
- **Invalid TextBundle folders**: Skips corrupted entries and continues
- **Missing note files**: Skips incomplete notes
- **Trashed notes**: Automatically filters out trashed notes

## File Structure

- `bear_parser.py`: Core parsing logic module
- `cli.py`: Command line interface entry point
- `README.md`: This documentation file

## Technical Details

- **Input Format**: Bear backup files (.bear2bk) which are ZIP archives containing TextBundle folders
- **TextBundle Structure**: Each note is stored as a folder with `info.json` (metadata) and `text.markdown` (content)
- **Encoding**: UTF-8 encoding used throughout for proper international character support
- **Timezone**: All timestamps normalized to UTC in ISO format
- **Memory Usage**: Uses temporary directories for extraction, automatically cleaned up
- **Error Recovery**: Continues processing even if individual notes fail to extract

## Limitations

- Only processes non-trashed notes
- Requires valid Bear backup file format
- Does not preserve Bear-specific metadata beyond title and modification date
- Does not extract attached files or images from notes

## Troubleshooting

**"File not found" error**: Ensure the backup file path is correct and the file exists.

**"Failed to extract backup file" error**: The backup file may be corrupted or not a valid Bear backup.

**Empty output**: All notes in the backup may be trashed, or the backup may contain no valid notes.

**Permission errors**: Ensure you have read access to the backup file and write access to the output directory.