"""
Bear Notes Parser - Core parsing logic module for extracting notes from Bear backup files.
"""

import zipfile
import json
import tempfile
import os
import sys
from datetime import datetime
from typing import List, Dict


def parse_bear_backup(backup_path: str) -> List[Dict]:
    """
    Parse a Bear backup file (.bear2bk) and extract all note data.

    Args:
        backup_path: Path to the .bear2bk file

    Returns:
        List of dictionaries containing note data with fields:
        - title: Note title
        - markdown: Note content in markdown format
        - size: UTF-8 byte size of markdown content
        - modificationDate: Last modification date in UTC ISO format
    """
    notes = []

    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract zip archive to temporary directory
        with zipfile.ZipFile(backup_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Iterate through TextBundle folders in extracted archive
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path) and item.endswith('.textbundle'):
                try:
                    note_data = extract_note_data(item_path)
                    if note_data:  # Only add if extraction was successful
                        notes.append(note_data)
                except Exception:
                    # Skip invalid files and continue processing
                    continue

    return notes


def extract_note_data(textbundle_path: str) -> Dict:
    """
    Extract note data from a single TextBundle folder.

    Args:
        textbundle_path: Path to the .textbundle folder

    Returns:
        Dictionary containing note data with fields:
        - title: Note title
        - markdown: Note content in markdown format
        - size: UTF-8 byte size of markdown content
        - modificationDate: Last modification date in UTC ISO format
        Returns None if note should be skipped (e.g., trashed notes)
    """
    info_json_path = os.path.join(textbundle_path, 'info.json')
    text_markdown_path = os.path.join(textbundle_path, 'text.markdown')

    # Check if required files exist
    if not os.path.exists(info_json_path) or not os.path.exists(text_markdown_path):
        return None

    try:
        # Parse info.json to extract Bear metadata
        with open(info_json_path, 'r', encoding='utf-8') as f:
            info_data = json.load(f)

        # Filter out trashed notes
        if info_data.get('trashed') == 1:
            return None

        # Read markdown content
        with open(text_markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # Calculate UTF-8 byte size
        content_size = len(markdown_content.encode('utf-8'))

        # Extract and normalize modification date to UTC ISO format
        modification_date = info_data.get('modificationDate')
        if modification_date:
            # Convert timestamp to UTC ISO format
            dt = datetime.fromtimestamp(modification_date)
            iso_date = dt.isoformat() + 'Z'
        else:
            iso_date = None

        return {
            'title': info_data.get('title', ''),
            'markdown': markdown_content,
            'size': content_size,
            'modificationDate': iso_date
        }

    except Exception:
        # Return None for any parsing errors
        return None