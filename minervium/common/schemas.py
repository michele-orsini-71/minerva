"""
JSON schema definitions and validation functions for Minervium.

This module defines the standard note format that all extractors must produce
and provides validation utilities to ensure data integrity.
"""

from typing import List, Dict, Any, Tuple
import sys

from minervium.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")


# JSON Schema definition for a single note
NOTE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["title", "markdown", "size", "modificationDate"],
    "properties": {
        "title": {
            "type": "string",
            "description": "The title or name of the note",
            "minLength": 1
        },
        "markdown": {
            "type": "string",
            "description": "The full markdown content of the note"
        },
        "size": {
            "type": "integer",
            "description": "Size of the note content in bytes (UTF-8 encoded)",
            "minimum": 0
        },
        "modificationDate": {
            "type": "string",
            "description": "ISO 8601 formatted modification date (UTC timezone preferred)",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
        },
        "creationDate": {
            "type": "string",
            "description": "ISO 8601 formatted creation date (UTC timezone preferred) - optional",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"
        }
    },
    "additionalProperties": True  # Allow custom metadata fields from extractors
}


# JSON Schema for an array of notes (the complete extractor output)
NOTES_ARRAY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": NOTE_SCHEMA,
    "minItems": 0
}


def validate_note(note: Dict[str, Any], note_index: int = 0) -> Tuple[bool, List[str]]:
    """
    Validate a single note against the NOTE_SCHEMA.

    Args:
        note: Dictionary representing a note
        note_index: Index of the note in the array (for error reporting)

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check if note is a dictionary
    if not isinstance(note, dict):
        errors.append(f"Note at index {note_index}: Expected object, got {type(note).__name__}")
        return False, errors

    # Check required fields
    required_fields = {"title", "markdown", "size", "modificationDate"}
    missing_fields = required_fields - set(note.keys())
    if missing_fields:
        errors.append(f"Note at index {note_index}: Missing required fields: {', '.join(sorted(missing_fields))}")

    # Validate field types and constraints
    if "title" in note:
        if not isinstance(note["title"], str):
            errors.append(f"Note at index {note_index}: 'title' must be a string, got {type(note['title']).__name__}")
        elif len(note["title"]) == 0:
            errors.append(f"Note at index {note_index}: 'title' cannot be empty")

    if "markdown" in note:
        if not isinstance(note["markdown"], str):
            errors.append(f"Note at index {note_index}: 'markdown' must be a string, got {type(note['markdown']).__name__}")

    if "size" in note:
        if not isinstance(note["size"], int):
            errors.append(f"Note at index {note_index}: 'size' must be an integer, got {type(note['size']).__name__}")
        elif note["size"] < 0:
            errors.append(f"Note at index {note_index}: 'size' must be non-negative, got {note['size']}")

    if "modificationDate" in note:
        if not isinstance(note["modificationDate"], str):
            errors.append(f"Note at index {note_index}: 'modificationDate' must be a string, got {type(note['modificationDate']).__name__}")
        elif not _is_valid_iso_date(note["modificationDate"]):
            errors.append(f"Note at index {note_index}: 'modificationDate' must be ISO 8601 format (YYYY-MM-DDTHH:MM:SS...)")

    if "creationDate" in note:
        if not isinstance(note["creationDate"], str):
            errors.append(f"Note at index {note_index}: 'creationDate' must be a string, got {type(note['creationDate']).__name__}")
        elif not _is_valid_iso_date(note["creationDate"]):
            errors.append(f"Note at index {note_index}: 'creationDate' must be ISO 8601 format (YYYY-MM-DDTHH:MM:SS...)")

    return len(errors) == 0, errors


def validate_notes_array(data: Any, strict: bool = True) -> Tuple[bool, List[str]]:
    """
    Validate an array of notes against the NOTES_ARRAY_SCHEMA.

    Args:
        data: Data to validate (should be a list of note dictionaries)
        strict: If True, fail on first error. If False, collect all errors.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check if data is a list
    if not isinstance(data, list):
        errors.append(f"Expected an array of notes, got {type(data).__name__}")
        return False, errors

    # Validate each note
    for index, note in enumerate(data):
        is_valid, note_errors = validate_note(note, index)
        if not is_valid:
            errors.extend(note_errors)
            if strict:
                break

    return len(errors) == 0, errors


def validate_notes_file(data: Any, filepath: str = "input") -> bool:
    """
    Validate notes data and print user-friendly error messages.

    Args:
        data: Data to validate
        filepath: Path to the file being validated (for error messages)

    Returns:
        True if valid, False otherwise (with errors printed to stderr)
    """
    is_valid, errors = validate_notes_array(data, strict=False)

    if not is_valid:
        logger.error(f"Validation failed for {filepath}")
        for error in errors:
            logger.error(f"   • {error}", print_to_stderr=False)
        logger.error("", print_to_stderr=False)
        logger.error(
            f"Found {len(errors)} error(s). Please fix them and try again.",
            print_to_stderr=False
        )
        return False

    logger.success(f"✅ Validation successful: {filepath} contains {len(data)} valid note(s)")
    return True


def _is_valid_iso_date(date_string: str) -> bool:
    """
    Check if a string matches ISO 8601 date format (basic validation).

    Args:
        date_string: String to validate

    Returns:
        True if format looks like ISO 8601, False otherwise
    """
    # Basic pattern check: YYYY-MM-DDTHH:MM:SS (with optional timezone)
    import re
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    return bool(re.match(pattern, date_string))


def get_schema_summary() -> str:
    """
    Get a human-readable summary of the note schema.

    Returns:
        Multi-line string describing the schema requirements
    """
    return """
Minervium Note Schema
=====================

Required fields:
  • title (string, non-empty): The title or name of the note
  • markdown (string): The full markdown content of the note
  • size (integer, ≥0): Size of the note content in bytes (UTF-8)
  • modificationDate (string, ISO 8601): Last modification timestamp

Optional fields:
  • creationDate (string, ISO 8601): Creation timestamp
  • [any custom fields]: Extractors may include additional metadata

Example:
{
  "title": "My Note",
  "markdown": "# My Note\\n\\nContent here...",
  "size": 1234,
  "modificationDate": "2025-01-15T10:30:00Z",
  "creationDate": "2025-01-10T08:00:00Z"
}

Date format: ISO 8601 (YYYY-MM-DDTHH:MM:SS with optional timezone)
Recommended timezone: UTC (suffix with 'Z')
"""


if __name__ == "__main__":
    # Print schema information when run directly
    logger.info(get_schema_summary())
