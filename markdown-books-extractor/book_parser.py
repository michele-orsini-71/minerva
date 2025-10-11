import re
import sys
from pathlib import Path


def parse_book_file(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        print(f"Input file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    if not path.is_file():
        print(f"Path is not a file: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        content = path.read_text(encoding='utf-8')
    except PermissionError:
        print(f"Cannot read input file: {file_path}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"File encoding error in {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

    parts = content.split('-------', maxsplit=1)
    if len(parts) != 2:
        raise ValueError("File must contain '-------' delimiter separating header from body")

    header, body = parts

    title_pattern = r'^#\s+Title:\s*(.+)$'
    author_pattern = r'^##\s+Author:\s*(.+)$'
    year_pattern = r'^##\s+Year:\s*(\d{4})$'

    title_match = re.search(title_pattern, header, re.MULTILINE)
    author_match = re.search(author_pattern, header, re.MULTILINE)
    year_match = re.search(year_pattern, header, re.MULTILINE)

    if not title_match or not title_match.group(1).strip():
        raise ValueError("Missing required field: Title")

    if not author_match or not author_match.group(1).strip():
        raise ValueError("Missing required field: Author")

    if not year_match or not year_match.group(1).strip():
        raise ValueError("Missing required field: Year")

    title = title_match.group(1).strip()
    author = author_match.group(1).strip()
    year_str = year_match.group(1).strip()

    try:
        year = int(year_str)
        if len(year_str) != 4:
            raise ValueError(f"Invalid year format: {year_str}")
    except ValueError:
        raise ValueError(f"Invalid year format: {year_str}")

    return {
        "title": title,
        "author": author,
        "year": year,
        "content": body.strip()
    }
