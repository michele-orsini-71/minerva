
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import extract_zim


def _write_output(records: list[dict[str, object]], output: Path | None) -> None:
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract markdown and JSON notes from a ZIM archive in Minervium format.",
        epilog="Example: zim-extractor archive.zim -o notes.json --markdown-dir ./markdown --limit 1000",
    )
    parser.add_argument("zim_file", help="Path to the ZIM archive to extract")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSON catalog to the provided path; defaults to stdout",
    )
    parser.add_argument(
        "-m",
        "--markdown-dir",
        type=Path,
        help="Optional directory to write markdown files extracted from the archive",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        help="Maximum number of articles to extract (useful for sampling)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit progress information to stderr",
    )

    args = parser.parse_args()
    zim_path = Path(args.zim_file)

    if not zim_path.exists() or not zim_path.is_file():
        print(f"Error: ZIM file '{zim_path}' not found", file=sys.stderr)
        return 1

    if args.markdown_dir:
        try:
            args.markdown_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as exc:
            print(f"Error creating markdown directory: {exc}", file=sys.stderr)
            return 1

    if args.verbose:
        print(
            f"Extracting notes from {zim_path} (limit={args.limit or 'all'})",
            file=sys.stderr,
        )

    try:
        records = extract_zim(
            zim_path=str(zim_path),
            markdown_dir=str(args.markdown_dir) if args.markdown_dir else None,
            limit=args.limit,
            verbose=args.verbose,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    _write_output(records, args.output)

    if args.verbose:
        print(f"Exported {len(records)} records", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
