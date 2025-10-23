import zipfile
import json
import tempfile
import os
import sys
from datetime import datetime
from typing import List, Dict


def parse_bear_backup(backup_path: str, progress_callback=None) -> List[Dict]:
    notes = []

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        except (zipfile.BadZipFile, zipfile.LargeZipFile, FileNotFoundError, PermissionError) as e:
            raise ValueError(f"Failed to extract backup file: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during extraction: {e}")

        # Get list of TextBundle folders for progress tracking (search recursively)
        textbundle_items = []
        for root, dirs, files in os.walk(temp_dir):
            for dir_name in dirs:
                if dir_name.endswith('.textbundle'):
                    textbundle_items.append(os.path.join(root, dir_name))
        total_notes = len(textbundle_items)

        # Iterate through TextBundle folders in extracted archive
        for i, item_path in enumerate(textbundle_items):
            try:
                note_data = extract_note_data(item_path)
                if note_data:  # Only add if extraction was successful
                    notes.append(note_data)

                # Report progress if callback provided
                if progress_callback:
                    progress_callback(i + 1, total_notes)

            except Exception:
                # Skip invalid files and continue processing
                if progress_callback:
                    progress_callback(i + 1, total_notes)
                continue

    return notes


def extract_note_data(textbundle_path: str) -> Dict:
    info_json_path = os.path.join(textbundle_path, 'info.json')
    text_markdown_path = os.path.join(textbundle_path, 'text.markdown')

    if not os.path.exists(info_json_path) or not os.path.exists(text_markdown_path):
        return None

    try:
        with open(info_json_path, 'r', encoding='utf-8') as f:
            info_data = json.load(f)

        bear_data = info_data.get('net.shinyfrog.bear', info_data)

        # Filter out trashed notes
        if bear_data.get('trashed') == 1:
            return None

        # Read markdown content and normalize line separators
        with open(text_markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Normalize Unicode line separators to standard newlines
        # U+2028 (Line Separator) and U+2029 (Paragraph Separator)
        markdown_content = markdown_content.replace('\u2028', '\n').replace('\u2029', '\n')

        content_size = len(markdown_content.encode('utf-8'))

        modification_date = bear_data.get('modificationDate')
        if modification_date:
            # Handle both timestamp formats (numeric and ISO string)
            if isinstance(modification_date, str):
                # Already in ISO format, ensure it ends with Z
                iso_date = modification_date if modification_date.endswith('Z') else modification_date + 'Z'
            else:
                # Convert timestamp to UTC ISO format
                dt = datetime.fromtimestamp(modification_date)
                iso_date = dt.isoformat() + 'Z'
        else:
            iso_date = None

        creation_date = bear_data.get('creationDate')
        if creation_date:
            # Handle both timestamp formats (numeric and ISO string)
            if isinstance(creation_date, str):
                # Already in ISO format, ensure it ends with Z
                iso_creation_date = creation_date if creation_date.endswith('Z') else creation_date + 'Z'
            else:
                # Convert timestamp to UTC ISO format
                dt = datetime.fromtimestamp(creation_date)
                iso_creation_date = dt.isoformat() + 'Z'
        else:
            iso_creation_date = None

        # Get title from Bear metadata, fallback to textbundle directory name
        title = bear_data.get('title', '')
        if not title:
            title = os.path.basename(textbundle_path).replace('.textbundle', '')

        return {
            'title': title,
            'markdown': markdown_content,
            'size': content_size,
            'modificationDate': iso_date,
            'creationDate': iso_creation_date
        }

    except Exception:
        # Return None for any parsing errors
        return None