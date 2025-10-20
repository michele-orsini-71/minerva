"""
Validate command - Validate JSON notes against Minervium schema without indexing.
"""

import json
import sys
from argparse import Namespace
from pathlib import Path

from minervium.common.schemas import validate_notes_array, get_schema_summary


def print_banner() -> None:
    """Print command banner."""
    print("\nMinervium Validate Command")
    print("=" * 60)


def load_json_file(json_path: Path) -> any:
    """Load and parse JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"\n✗ Error: File not found: {json_path}", file=sys.stderr)
        print(f"   Please check the file path and try again.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"\n✗ Error: Invalid JSON in file: {json_path}", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        print(f"\n   Suggestion: Validate your JSON using a JSON linter", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"\n✗ Error: Permission denied reading file: {json_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: Failed to read file: {json_path}", file=sys.stderr)
        print(f"   {e}", file=sys.stderr)
        sys.exit(1)


def print_validation_statistics(data: list, verbose: bool) -> None:
    """Print statistics about the notes."""
    if not isinstance(data, list):
        return

    print(f"\nValidation Statistics:")
    print(f"  Total notes: {len(data)}")

    if verbose and len(data) > 0:
        # Calculate content statistics
        total_size = sum(note.get('size', 0) for note in data if isinstance(note, dict))
        total_chars = sum(len(note.get('markdown', '')) for note in data if isinstance(note, dict))
        avg_size = total_size / len(data) if len(data) > 0 else 0
        avg_chars = total_chars / len(data) if len(data) > 0 else 0

        print(f"  Total content size: {total_size:,} bytes")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Average note size: {avg_size:.0f} bytes")
        print(f"  Average characters: {avg_chars:.0f}")

        # Count notes with optional fields
        with_creation_date = sum(1 for note in data if isinstance(note, dict) and 'creationDate' in note)
        print(f"  Notes with creationDate: {with_creation_date}")

        # Show sample titles
        print(f"\n  Sample note titles:")
        for i, note in enumerate(data[:5], 1):
            if isinstance(note, dict) and 'title' in note:
                title = note['title']
                if len(title) > 60:
                    title = title[:57] + "..."
                print(f"    {i}. {title}")


def print_validation_errors(errors: list, json_path: Path, verbose: bool) -> None:
    """Print validation errors in a user-friendly format."""
    print(f"\n✗ Validation failed for: {json_path}", file=sys.stderr)
    print(f"=" * 60, file=sys.stderr)

    if verbose:
        # Show all errors in verbose mode
        print(f"\nFound {len(errors)} error(s):\n", file=sys.stderr)
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}", file=sys.stderr)
    else:
        # Show first 5 errors in normal mode
        max_errors = min(5, len(errors))
        print(f"\nShowing first {max_errors} of {len(errors)} error(s):\n", file=sys.stderr)
        for i, error in enumerate(errors[:max_errors], 1):
            print(f"  {i}. {error}", file=sys.stderr)

        if len(errors) > 5:
            print(f"\n  ... and {len(errors) - 5} more error(s)", file=sys.stderr)
            print(f"  (Use --verbose to see all errors)", file=sys.stderr)

    print(f"\n" + "=" * 60, file=sys.stderr)
    print(f"\nSuggestions:", file=sys.stderr)
    print(f"  • Check that all required fields are present: title, markdown, size, modificationDate", file=sys.stderr)
    print(f"  • Verify date fields are in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)", file=sys.stderr)
    print(f"  • Ensure size field is a non-negative integer", file=sys.stderr)
    print(f"  • Run 'minervium validate --help' for schema information", file=sys.stderr)


def run_validate(args: Namespace) -> int:
    """
    Main entry point for the validate command.

    Args:
        args: Parsed command-line arguments containing:
            - json_file: Path to JSON notes file to validate
            - verbose: Enable verbose output

    Returns:
        Exit code (0 for success, 1 for validation failure)
    """

    try:
        # Print banner
        print_banner()

        json_path = args.json_file
        verbose = args.verbose

        # Show what we're validating
        print(f"\nValidating: {json_path}")

        if verbose:
            print("\nSchema requirements:")
            print("-" * 60)
            print(get_schema_summary())
            print("-" * 60)

        # Load JSON file
        print(f"\nLoading JSON file...")
        data = load_json_file(json_path)
        print(f"   ✓ File loaded successfully")

        # Validate structure
        print(f"\nValidating note structure...")
        is_valid, errors = validate_notes_array(data, strict=False)

        if not is_valid:
            print_validation_errors(errors, json_path, verbose)
            return 1

        # Success!
        print(f"   ✓ All notes are valid")

        # Print statistics
        if isinstance(data, list):
            print_validation_statistics(data, verbose)

        # Final success message
        print(f"\n" + "=" * 60)
        print(f"✓ Validation successful!")
        print(f"=" * 60)
        print(f"\nThe file '{json_path.name}' contains valid notes and is ready for indexing.")
        print(f"\nNext step:")
        print(f"  minervium index --config <config-file>")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\n✗ Operation cancelled by user", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
