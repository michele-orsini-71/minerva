#!/usr/bin/env python3
"""
JSON Loader module for Bear Notes data.

Handles loading and parsing Bear notes JSON files with proper error handling.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_json_notes(json_path: str) -> List[Dict[str, Any]]:
    """
    Load Bear notes from a JSON file.

    Args:
        json_path: Path to the Bear notes JSON file

    Returns:
        List of note dictionaries with keys: title, markdown, size, modificationDate, creationDate

    Raises:
        SystemExit: If file cannot be loaded or parsed
    """
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

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    except UnicodeDecodeError as e:
        print(f"Error: File encoding issue in {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    except PermissionError:
        print(f"Error: Permission denied reading {json_path}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Error: Unexpected error loading {json_path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Simple test when run directly
    if len(sys.argv) != 2:
        print("Usage: python json_loader.py <path_to_json>")
        sys.exit(1)

    notes = load_json_notes(sys.argv[1])
    print(f"Successfully loaded {len(notes)} notes")

    if notes:
        print(f"First note: '{notes[0]['title']}'")
        print(f"Content length: {len(notes[0]['markdown'])} characters")