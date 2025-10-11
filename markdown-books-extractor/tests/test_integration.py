import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from book_parser import parse_book_file
from chapter_detector import detect_chapters
from json_generator import create_chapter_entries, write_json_output


def test_basic_integration():
    test_content = """# Title: Test Book
## Author: Test Author
## Year: 2020

-------

## Chapter 1

This is the first chapter content.

## Chapter 2

This is the second chapter content.
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_input = f.name

    try:
        book_data = parse_book_file(temp_input)
        assert book_data['title'] == 'Test Book'
        assert book_data['author'] == 'Test Author'
        assert book_data['year'] == 2020
        assert 'content' in book_data

        chapters = detect_chapters(book_data['content'])
        assert len(chapters) == 2
        assert chapters[0]['title'] == 'Chapter 1'
        assert chapters[1]['title'] == 'Chapter 2'

        entries = create_chapter_entries(chapters, book_data)
        assert len(entries) == 2
        assert entries[0]['title'] == 'Test Book - Chapter 1'
        assert 'markdown' in entries[0]
        assert '**Author:** Test Author' in entries[0]['markdown']
        assert '**Year:** 2020' in entries[0]['markdown']
        assert entries[0]['size'] > 0
        assert 'modificationDate' in entries[0]
        assert 'creationDate' in entries[0]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_output = f.name

        write_json_output(entries, temp_output)

        with open(temp_output, 'r', encoding='utf-8') as f:
            loaded_entries = json.load(f)

        assert len(loaded_entries) == 2
        assert loaded_entries[0]['title'] == 'Test Book - Chapter 1'

        Path(temp_output).unlink()

        print("✓ All integration tests passed!")

    finally:
        Path(temp_input).unlink()


if __name__ == '__main__':
    test_basic_integration()
