"""Command-line interface for the Bear notes extractor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

from .parser import parse_bear_backup


def _dump_notes(notes: List[Dict[str, object]], output_path: Path | None) -> None:
    payload = json.dumps(notes, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract notes from a Bear .bear2bk backup into Minervium JSON format.",
        epilog="Example: bear-extractor backup.bear2bk -o notes.json",
    )
    parser.add_argument("backup", help="Path to the Bear backup (.bear2bk) file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path for JSON output; defaults to stdout",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit progress information to stderr",
    )

    args = parser.parse_args()
    backup_path = Path(args.backup)

    if not backup_path.exists() or not backup_path.is_file():
        print(f"Error: backup file '{backup_path}' not found", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Parsing Bear backup from {backup_path}", file=sys.stderr)

    def progress_callback(current: int, total: int) -> None:
        if not args.verbose:
            return
        total_display = total or 1
        percentage = (current / total_display) * 100
        print(
            f"\rProcessed {current}/{total_display} notes ({percentage:.1f}%)",
            end="",
            file=sys.stderr,
            flush=True,
        )

    try:
        notes = parse_bear_backup(str(backup_path), progress_callback if args.verbose else None)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        if args.verbose:
            print("", file=sys.stderr)

    _dump_notes(notes, args.output)

    if args.verbose:
        print(f"Exported {len(notes)} notes", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
