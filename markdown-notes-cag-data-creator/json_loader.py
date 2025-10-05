import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_json_notes(json_path: str) -> List[Dict[str, Any]]:
    try:
        # Convert to Path object for better path handling
        file_path = Path(json_path)

        # Check if file exists
        if not file_path.exists():
            print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
            sys.exit(1)

        # Check if it's a file (not a directory)
        if not file_path.is_file():
            print(f"Error: Path is not a file: {json_path}", file=sys.stderr)
            sys.exit(1)

        # Load and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate that we got a list
        if not isinstance(data, list):
            print(f"Error: JSON file must contain an array of notes, got {type(data).__name__}", file=sys.stderr)
            sys.exit(1)

        # Validate note structure
        if data:  # Only validate if not empty
            required_fields = {'title', 'markdown', 'size', 'modificationDate'}
            first_note = data[0]

            if not isinstance(first_note, dict):
                print(f"Error: Notes must be objects, got {type(first_note).__name__}", file=sys.stderr)
                sys.exit(1)

            missing_fields = required_fields - set(first_note.keys())
            if missing_fields:
                print(f"Error: Notes missing required fields: {', '.join(missing_fields)}", file=sys.stderr)
                sys.exit(1)

        print(f"   Loaded {len(data)} notes from {json_path}")
        return data

    except json.JSONDecodeError as error:
        print(f"Error: Invalid JSON format in {json_path}: {error}", file=sys.stderr)
        sys.exit(1)

    except UnicodeDecodeError as error:
        print(f"Error: File encoding issue in {json_path}: {error}", file=sys.stderr)
        sys.exit(1)

    except PermissionError:
        print(f"Error: Permission denied reading {json_path}", file=sys.stderr)
        sys.exit(1)

    except Exception as error:
        print(f"Error: Unexpected error loading {json_path}: {error}", file=sys.stderr)
        sys.exit(1)
