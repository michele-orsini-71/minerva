"""Command-line interface for the markdown books extractor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import parse_book_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a structured markdown book file into normalized JSON.",
        epilog="Example: markdown-books-extractor book.md -o output.json",
    )
    parser.add_argument("source", help="Path to the markdown book file to parse")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional path to write JSON output (defaults to stdout)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose progress information",
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    if args.verbose:
        print(f"Parsing markdown book from {source_path}")

    try:
        record = parse_book_file(str(source_path))
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_data = json.dumps(record, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.write_text(output_data + "
", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"Error writing to {output_path}: {exc}", file=sys.stderr)
            return 1
        if args.verbose:
            print(f"Wrote JSON output to {output_path}")
    else:
        print(output_data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
