"""Command-line interface for repository documentation extractor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import RepositoryParseError, extract_repository_docs


def _write_output(records: list[dict[str, object]], output: Path | None) -> None:
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract markdown documentation from a repository into Minerva-compatible JSON.",
        epilog="Example: repository-doc-extractor /path/to/repo -o notes.json",
    )
    parser.add_argument(
        "directory",
        help="Path to the repository/directory to scan for markdown files"
    )
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
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_patterns",
        metavar="PATTERN",
        help="Exclude directories matching pattern (can be used multiple times). "
             "Note: .git, node_modules, __pycache__, .venv are always excluded.",
    )

    args = parser.parse_args()
    directory_path = Path(args.directory)

    if args.verbose:
        print(f"Scanning directory: {directory_path}", file=sys.stderr)
        if args.exclude_patterns:
            print(f"Excluding patterns: {', '.join(args.exclude_patterns)}", file=sys.stderr)

    try:
        records = extract_repository_docs(
            str(directory_path),
            exclude_patterns=args.exclude_patterns
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RepositoryParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    _write_output(records, args.output)

    if args.verbose:
        print(f"✓ Exported {len(records)} markdown file(s)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
