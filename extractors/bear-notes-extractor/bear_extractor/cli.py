"""
Command line interface for Bear Notes Parser.
"""

import argparse
import json
import os
import sys
from .parser import parse_bear_backup


def main():
    """
    Main entry point for the Bear Notes Parser CLI.
    """
    parser = argparse.ArgumentParser(
        description='Parse Bear backup files and extract notes to JSON format'
    )
    parser.add_argument(
        'backup_path',
        help='Path to the .bear2bk backup file'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.backup_path):
        print(f"Error: File '{args.backup_path}' not found", file=sys.stderr)
        sys.exit(1)

    # Generate output filename with same base name + .json extension
    base_name = os.path.splitext(args.backup_path)[0]
    output_path = f"{base_name}.json"

    def progress_callback(current, total):
        """Display progress percentage."""
        percentage = (current / total) * 100
        print(f"\rProgress: {current}/{total} ({percentage:.1f}%)", end='', flush=True)

    try:
        print(f"Processing Bear backup: {args.backup_path}")

        # Parse the backup file with progress feedback
        notes = parse_bear_backup(args.backup_path, progress_callback)

        print(f"\nExtracted {len(notes)} notes")

        # Write JSON output with UTF-8 encoding (overwrite existing files)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)

        print(f"Output written to: {output_path}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()