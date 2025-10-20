#!/usr/bin/env python3
"""
Command-line interface for ZIM articles extractor.

This script extracts articles from ZIM files (Kiwix/Wikipedia offline format)
and outputs structured article data in JSON format, optionally extracting
markdown files to a directory.
"""

import argparse
import sys
from pathlib import Path
from .parser import extract_zim


def main():
    """Main entry point for the ZIM articles extractor CLI."""
    parser = argparse.ArgumentParser(
        description="Extract articles from ZIM files and convert to JSON/Markdown",
        epilog="Example: extract-zim-articles wikipedia.zim --json catalog.json --limit 1000"
    )

    parser.add_argument(
        "zim_file",
        help="Path to the ZIM file to extract articles from"
    )

    parser.add_argument(
        "--output-dir", "-o",
        help="Directory to write markdown files (optional, JSON-only if not specified)"
    )

    parser.add_argument(
        "--json", "-j",
        help="Path to write JSON catalog file (required for downstream RAG processing)"
    )

    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Maximum number of articles to extract (useful for testing)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose progress output"
    )

    args = parser.parse_args()

    # Validate input file
    zim_path = Path(args.zim_file)
    if not zim_path.exists():
        print(f"Error: ZIM file '{zim_path}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Ensure JSON output is specified (required for RAG pipeline compatibility)
    if not args.json:
        print("Error: --json output path is required", file=sys.stderr)
        sys.exit(1)

    # Validate output directory if specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            print(f"Error: Cannot create output directory '{output_dir}': {e}", file=sys.stderr)
            sys.exit(1)

    if args.verbose:
        print(f"Extracting articles from: {zim_path}")
        if args.output_dir:
            print(f"Markdown output directory: {args.output_dir}")
        print(f"JSON catalog output: {args.json}")
        if args.limit:
            print(f"Article limit: {args.limit}")
        print()

    try:
        extract_zim(
            zim_path=str(zim_path),
            out_dir=args.output_dir,
            limit=args.limit,
            json_path=args.json
        )

        if args.verbose:
            print(f"\n✓ Extraction completed successfully")
            print(f"JSON catalog written to: {args.json}")
            if args.output_dir:
                print(f"Markdown files written to: {args.output_dir}")

    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()