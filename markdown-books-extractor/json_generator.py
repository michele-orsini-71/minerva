import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def create_chapter_entries(chapters: list[dict], book_metadata: dict) -> list[dict]:
    entries = []

    for chapter in chapters:
        combined_title = f"{book_metadata['title']} - {chapter['title']}"

        markdown_content = (
            f"# {combined_title}\n"
            f"**Author:** {book_metadata['author']} | **Year:** {book_metadata['year']}\n\n"
            f"{chapter['content']}"
        )

        size = len(markdown_content.encode('utf-8'))

        year = book_metadata['year']
        creation_date = datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        modification_date = creation_date

        entry = {
            "title": combined_title,
            "markdown": markdown_content,
            "size": size,
            "modificationDate": modification_date,
            "creationDate": creation_date
        }

        entries.append(entry)

    return entries


def write_json_output(entries: list[dict], output_path: str) -> None:
    path = Path(output_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open('w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except PermissionError:
        print(f"Cannot write to output path: {output_path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)
