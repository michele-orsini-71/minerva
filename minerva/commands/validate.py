import json
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any

from minerva.common.logger import get_logger
from minerva.common.schemas import validate_notes_array, get_schema_summary

logger = get_logger(__name__, simple=True, mode="cli")


def print_banner() -> None:
    logger.info("")
    logger.info("Minerva Validate Command")
    logger.info("=" * 60)


def load_json_file(json_path: Path) -> Any:
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Error: File not found: {json_path}")
        logger.error("   Please check the file path and try again.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error: Invalid JSON in file: {json_path}")
        logger.error(f"   {e}")
        logger.error("   Suggestion: Validate your JSON using a JSON linter")
        sys.exit(1)
    except PermissionError:
        logger.error(f"Error: Permission denied reading file: {json_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: Failed to read file: {json_path}")
        logger.error(f"   {e}")
        sys.exit(1)


def print_validation_statistics(data: list, verbose: bool) -> None:
    if not isinstance(data, list):
        return

    logger.info("")
    logger.info("Validation Statistics:")
    logger.info(f"  Total notes: {len(data)}")

    if verbose and len(data) > 0:
        total_size = sum(note.get('size', 0) for note in data if isinstance(note, dict))
        total_chars = sum(len(note.get('markdown', '')) for note in data if isinstance(note, dict))
        avg_size = total_size / len(data) if len(data) > 0 else 0
        avg_chars = total_chars / len(data) if len(data) > 0 else 0

        logger.info(f"  Total content size: {total_size:,} bytes")
        logger.info(f"  Total characters: {total_chars:,}")
        logger.info(f"  Average note size: {avg_size:.0f} bytes")
        logger.info(f"  Average characters: {avg_chars:.0f}")

        # Count notes with optional fields
        with_creation_date = sum(1 for note in data if isinstance(note, dict) and 'creationDate' in note)
        logger.info(f"  Notes with creationDate: {with_creation_date}")

        # Show sample titles
        logger.info("")
        logger.info("  Sample note titles:")
        for i, note in enumerate(data[:5], 1):
            if isinstance(note, dict) and 'title' in note:
                title = note['title']
                if len(title) > 60:
                    title = title[:57] + "..."
                logger.info(f"    {i}. {title}")


def print_validation_errors(errors: list, json_path: Path, verbose: bool) -> None:
    logger.error(f"Validation failed for: {json_path}")
    logger.error("=" * 60)

    if verbose:
        # Show all errors in verbose mode
        logger.error("")
        logger.error(f"Found {len(errors)} error(s):")
        for i, error in enumerate(errors, 1):
            logger.error(f"  {i}. {error}")
    else:
        # Show first 5 errors in normal mode
        max_errors = min(5, len(errors))
        logger.error("")
        logger.error(f"Showing first {max_errors} of {len(errors)} error(s):")
        for i, error in enumerate(errors[:max_errors], 1):
            logger.error(f"  {i}. {error}")

        if len(errors) > 5:
            logger.error("")
            logger.error(f"  ... and {len(errors) - 5} more error(s)")
            logger.error("  (Use --verbose to see all errors)")

    logger.error("")
    logger.error("=" * 60)
    logger.error("")
    logger.error("Suggestions:")
    logger.error("  • Check that all required fields are present: title, markdown, size, modificationDate")
    logger.error("  • Verify date fields are in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)")
    logger.error("  • Ensure size field is a non-negative integer")
    logger.error("  • Run 'minerva validate --help' for schema information")


def run_validate(args: Namespace) -> int:
    try:
        # Print banner
        print_banner()

        json_path = args.json_file
        verbose = args.verbose

        # Show what we're validating
        logger.info("")
        logger.info(f"Validating: {json_path}")

        if verbose:
            logger.info("")
            logger.info("Schema requirements:")
            logger.info("-" * 60)
            logger.info(get_schema_summary())
            logger.info("-" * 60)

        logger.info("")
        logger.info("Loading JSON file...")
        data = load_json_file(json_path)
        logger.success("   ✓ File loaded successfully")

        logger.info("")
        logger.info("Validating note structure...")
        is_valid, errors = validate_notes_array(data, strict=False)

        if not is_valid:
            print_validation_errors(errors, json_path, verbose)
            return 1

        # Success!
        logger.success("   ✓ All notes are valid")

        # Print statistics
        if isinstance(data, list):
            print_validation_statistics(data, verbose)

        # Final success message
        logger.info("")
        logger.info("=" * 60)
        logger.success("✓ Validation successful!")
        logger.info("=" * 60)
        logger.info("")
        logger.info(f"The file '{json_path.name}' contains valid notes and is ready for indexing.")
        logger.info("")
        logger.info("Next step:")
        logger.info("  minerva index --config <config-file>")
        logger.info("")

        return 0

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return 130

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
