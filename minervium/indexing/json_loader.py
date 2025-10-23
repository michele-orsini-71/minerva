import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from minervium.common.logger import get_logger

logger = get_logger(__name__, mode="cli")


def load_json_notes(json_path: str) -> List[Dict[str, Any]]:
    try:
        # Convert to Path object for better path handling
        file_path = Path(json_path)

        if not file_path.exists():
            logger.error(f"JSON file not found: {json_path}")
            sys.exit(1)

        if not file_path.is_file():
            logger.error(f"Path is not a file: {json_path}")
            sys.exit(1)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error(f"JSON file must contain an array of notes, got {type(data).__name__}")
            sys.exit(1)

        if data:  # Only validate if not empty
            required_fields = {'title', 'markdown', 'size', 'modificationDate'}
            first_note = data[0]

            if not isinstance(first_note, dict):
                logger.error(f"Notes must be objects, got {type(first_note).__name__}")
                sys.exit(1)

            missing_fields = required_fields - set(first_note.keys())
            if missing_fields:
                logger.error(f"Notes missing required fields: {', '.join(missing_fields)}")
                sys.exit(1)

        logger.info(f"   Loaded {len(data)} notes from {json_path}")
        return data

    except json.JSONDecodeError as error:
        logger.error(f"Invalid JSON format in {json_path}: {error}")
        sys.exit(1)

    except UnicodeDecodeError as error:
        logger.error(f"File encoding issue in {json_path}: {error}")
        sys.exit(1)

    except PermissionError:
        logger.error(f"Permission denied reading {json_path}")
        sys.exit(1)

    except Exception as error:
        logger.error(f"Unexpected error loading {json_path}: {error}")
        sys.exit(1)
