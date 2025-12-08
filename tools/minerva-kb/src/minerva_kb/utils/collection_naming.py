import re
from pathlib import Path

MIN_LENGTH = 3
MAX_LENGTH = 512
VALID_PATTERN = re.compile(r"^[a-z0-9-]+$")


def sanitize_collection_name(repo_path: str | Path) -> str:
    path = Path(repo_path)
    folder_name = path.name
    if not folder_name:
        raise ValueError("Repository path must include folder name")
    cleaned = folder_name.lower().replace(" ", "-").replace("_", "-")
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    if not cleaned:
        raise ValueError("Collection name cannot be empty after sanitization")
    if len(cleaned) < MIN_LENGTH:
        raise ValueError("Collection name must be at least 3 characters")
    if len(cleaned) > MAX_LENGTH:
        raise ValueError("Collection name cannot exceed 512 characters")
    return cleaned


def validate_collection_name_format(value: str) -> None:
    name = value.strip()
    if len(name) < MIN_LENGTH:
        raise ValueError("Collection name must be at least 3 characters")
    if len(name) > MAX_LENGTH:
        raise ValueError("Collection name cannot exceed 512 characters")
    if not VALID_PATTERN.fullmatch(name):
        raise ValueError("Collection name may use lowercase letters, numbers, and hyphens only")
