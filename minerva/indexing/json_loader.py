import json
from pathlib import Path
from typing import List, Dict, Any

from minerva.common.exceptions import JsonLoaderError
from minerva.common.logger import get_logger

logger = get_logger(__name__, mode="cli")


def load_json_notes(json_path: str) -> List[Dict[str, Any]]:
    try:
        # Convert to Path object for better path handling
        file_path = Path(json_path)

        if not file_path.exists():
            message = f"JSON file not found: {json_path}"
            logger.error(message)
            raise JsonLoaderError(message)

        if not file_path.is_file():
            message = f"Path is not a file: {json_path}"
            logger.error(message)
            raise JsonLoaderError(message)

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            message = "JSON file must contain an array of notes"
            logger.error(f"{message}, got {type(data).__name__}")
            raise JsonLoaderError(message)

        if data:  # Only validate if not empty
            required_fields = {'title', 'markdown', 'size', 'modificationDate'}
            first_note = data[0]

            if not isinstance(first_note, dict):
                message = "Notes must be objects"
                logger.error(f"{message}, got {type(first_note).__name__}")
                raise JsonLoaderError(message)

            missing_fields = required_fields - set(first_note.keys())
            if missing_fields:
                message = f"Notes missing required fields: {', '.join(sorted(missing_fields))}"
                logger.error(message)
                raise JsonLoaderError(message)

        logger.info(f"   Loaded {len(data)} notes from {json_path}")
        return data

    except json.JSONDecodeError as error:
        logger.error(f"Invalid JSON format in {json_path}: {error}")
        raise JsonLoaderError(f"Invalid JSON format: {error}") from error

    except UnicodeDecodeError as error:
        logger.error(f"File encoding issue in {json_path}: {error}")
        raise JsonLoaderError(f"File encoding issue: {error}") from error

    except PermissionError as error:
        logger.error(f"Permission denied reading {json_path}")
        raise JsonLoaderError("Permission denied reading JSON file") from error

    except Exception as error:
        logger.error(f"Unexpected error loading {json_path}: {error}")
        raise JsonLoaderError(f"Unexpected error loading {json_path}: {error}") from error
