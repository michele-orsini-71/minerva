
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import BookParseError, parse_book_file


def _write_output(records: list[dict[str, object]], output: Path | None) -> None:
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a structured markdown book file into Minervium-compatible JSON.",
        epilog="Example: markdown-books-extractor book.md -o notes.json",
    )
    parser.add_argument("source", help="Path to the markdown book file to parse")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path to write JSON output (defaults to stdout)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit progress information to stderr",
    )

    args = parser.parse_args()
    source_path = Path(args.source)

    if args.verbose:
        print(f"Parsing markdown book from {source_path}", file=sys.stderr)

    try:
        records = parse_book_file(str(source_path))
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except BookParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    _write_output(records, args.output)

    if args.verbose:
        print(f"Exported {len(records)} record(s)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
