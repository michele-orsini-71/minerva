#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from book_parser import parse_book_file
from chapter_detector import detect_chapters
from json_generator import create_chapter_entries, write_json_output


def main():
    parser = argparse.ArgumentParser(
        description="Convert classic book markdown files to CAG-compatible JSON format",
        epilog="""
Examples:
  %(prog)s "The Castle of Otranto.md"
  %(prog)s "The Castle of Otranto.md" --output /path/to/output.json
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'input_file',
        help='Path to input markdown file'
    )

    parser.add_argument(
        '--output',
        help='Path to output JSON file (default: same directory as input with .json extension)'
    )

    args = parser.parse_args()

    if args.output:
        output_path = args.output
    else:
        output_path = str(Path(args.input_file).with_suffix('.json'))

    try:
        filename = Path(args.input_file).name
        print(f"Parsing {filename}...")

        book_metadata = parse_book_file(args.input_file)

        print(f'Extracted metadata: Title="{book_metadata["title"]}", '
              f'Author="{book_metadata["author"]}", Year={book_metadata["year"]}')

        chapters = detect_chapters(book_metadata['content'])

        print(f"Detected {len(chapters)} chapters")

        entries = []
        for idx, chapter in enumerate(chapters, start=1):
            print(f"Processing chapter {idx}/{len(chapters)}: {chapter['title']}")
            chapter_entry = create_chapter_entries([chapter], book_metadata)
            entries.extend(chapter_entry)

        write_json_output(entries, output_path)

        output_filename = Path(output_path).name
        print(f"Successfully created {output_filename} with {len(entries)} chapters")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
