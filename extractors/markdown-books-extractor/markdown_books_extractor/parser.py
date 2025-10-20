"""Parsing helpers for markdown book source files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

HEADER_DELIMITER = "-------"


def parse_book_file(file_path: str) -> Dict[str, object]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError as exc:
        raise PermissionError(f"Cannot read input file: {file_path}") from exc
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError(exc.encoding, exc.object, exc.start, exc.end, f"File encoding error in {file_path}: {exc.reason}") from exc

    parts = content.split(HEADER_DELIMITER, maxsplit=1)
    if len(parts) != 2:
        raise ValueError("File must contain '-------' delimiter separating header from body")

    header, body = parts

    title = _extract_header_value(header, r"^#\s+Title:\s*(.+)$", "Title")
    author = _extract_header_value(header, r"^##\s+Author:\s*(.+)$", "Author")
    year_str = _extract_header_value(header, r"^##\s+Year:\s*(\d{4})$", "Year")

    try:
        year = int(year_str)
    except ValueError as exc:
        raise ValueError(f"Invalid year format: {year_str}") from exc

    return {
        "title": title,
        "author": author,
        "year": year,
        "content": body.strip(),
    }


def _extract_header_value(header: str, pattern: str, field_name: str) -> str:
    match = re.search(pattern, header, re.MULTILINE)
    if not match or not match.group(1).strip():
        raise ValueError(f"Missing required field: {field_name}")
    return match.group(1).strip()
