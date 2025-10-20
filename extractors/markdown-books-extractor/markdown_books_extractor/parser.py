"""Parsing helpers for markdown book source files."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

HEADER_DELIMITER = "-------"


class BookParseError(ValueError):
    """Raised when the markdown book file cannot be parsed."""


def parse_book_file(file_path: str) -> List[Dict[str, object]]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if not path.is_file():
        raise BookParseError(f"Path is not a file: {file_path}")

    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError as exc:
        raise PermissionError(f"Cannot read input file: {file_path}") from exc
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError(exc.encoding, exc.object, exc.start, exc.end, f"File encoding error in {file_path}: {exc.reason}") from exc

    parts = content.split(HEADER_DELIMITER, maxsplit=1)
    if len(parts) != 2:
        raise BookParseError("File must contain '-------' delimiter separating header from body")

    header, body = parts

    title = _extract_header_value(header, r"^#\s+Title:\s*(.+)$", "Title")
    author = _extract_header_value(header, r"^##\s+Author:\s*(.+)$", "Author")
    year_str = _extract_header_value(header, r"^##\s+Year:\s*(\d{4})$", "Year")

    try:
        year = int(year_str)
    except ValueError as exc:
        raise BookParseError(f"Invalid year format: {year_str}") from exc

    markdown_content = (
        f"# {title}\n\n"
        f"**Author:** {author} | **Year:** {year}\n\n"
        f"{body.strip()}"
    )
    size = len(markdown_content.encode("utf-8"))

    timestamp = datetime(year, 1, 1, tzinfo=timezone.utc).replace(microsecond=0)
    iso_timestamp = timestamp.isoformat().replace("+00:00", "Z")

    note = {
        "title": title,
        "markdown": markdown_content,
        "size": size,
        "modificationDate": iso_timestamp,
        "creationDate": iso_timestamp,
        "author": author,
        "year": year,
    }

    return [note]


def _extract_header_value(header: str, pattern: str, field_name: str) -> str:
    match = re.search(pattern, header, re.MULTILINE)
    if not match or not match.group(1).strip():
        raise BookParseError(f"Missing required field: {field_name}")
    return match.group(1).strip()
