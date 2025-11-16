"""Parser for extracting markdown documentation from repository directories."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


class RepositoryParseError(ValueError):
    """Raised when repository parsing fails."""
    pass


def scan_directories_with_markdown(
    root_path: str,
    exclude_patterns: List[str] | None = None
) -> List[str]:
    """
    Scan directory tree and return all unique directory paths containing markdown files.

    Args:
        root_path: Root directory to start walking from
        exclude_patterns: Optional list of patterns to exclude (e.g., ['node_modules', '.git'])

    Returns:
        Sorted list of unique relative directory paths that contain .md or .mdx files

    Raises:
        FileNotFoundError: If root_path doesn't exist
        RepositoryParseError: If root_path is not a directory
    """
    root = Path(root_path)

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_path}")

    if not root.is_dir():
        raise RepositoryParseError(f"Path is not a directory: {root_path}")

    # Default exclude patterns
    if exclude_patterns is None:
        exclude_patterns = []

    # Always exclude common non-documentation directories
    default_excludes = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.pytest_cache'}
    exclude_set = set(exclude_patterns) | default_excludes

    md_files = _find_markdown_files(root, exclude_set)

    # Extract unique directory paths
    dir_paths = set()
    for md_file in md_files:
        # Get parent directory of the markdown file
        parent_dir = md_file.parent
        try:
            # Get relative path from root
            if parent_dir == root:
                # File is in root directory
                relative_path = "."
            else:
                relative_path = str(parent_dir.relative_to(root))
            dir_paths.add(relative_path)
        except ValueError:
            # Skip files not under root
            continue

    return sorted(dir_paths)


def extract_repository_docs(
    root_path: str,
    exclude_patterns: List[str] | None = None
) -> List[Dict[str, object]]:
    """
    Walk a directory tree and extract all markdown files as notes.

    Args:
        root_path: Root directory to start walking from
        exclude_patterns: Optional list of patterns to exclude (e.g., ['node_modules', '.git'])

    Returns:
        List of note dictionaries conforming to Minerva schema

    Raises:
        FileNotFoundError: If root_path doesn't exist
        RepositoryParseError: If root_path is not a directory
    """
    root = Path(root_path)

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_path}")

    if not root.is_dir():
        raise RepositoryParseError(f"Path is not a directory: {root_path}")

    # Default exclude patterns
    if exclude_patterns is None:
        exclude_patterns = []

    # Always exclude common non-documentation directories
    default_excludes = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.pytest_cache'}
    exclude_set = set(exclude_patterns) | default_excludes

    notes = []
    md_files = _find_markdown_files(root, exclude_set)

    for md_file in md_files:
        try:
            note = _parse_markdown_file(md_file, root)
            notes.append(note)
        except Exception as e:
            # Log warning but continue processing other files
            print(f"Warning: Skipping {md_file}: {e}", flush=True)
            continue

    if not notes:
        raise RepositoryParseError(f"No markdown files found in {root_path}")

    return notes


def _find_markdown_files(root: Path, exclude_patterns: set[str]) -> List[Path]:
    md_files = []

    for md_pattern in ["*.md", "*.mdx"]:
        for path in root.rglob(md_pattern):
            if any(excluded in path.parts for excluded in exclude_patterns):
                continue

            if path.is_file():
                md_files.append(path)

    # Sort for consistent ordering
    return sorted(md_files)


def _parse_markdown_file(file_path: Path, root: Path) -> Dict[str, object]:
    """
    Parse a single markdown file into a note dictionary.

    Args:
        file_path: Path to the markdown file
        root: Root directory (for calculating relative path)

    Returns:
        Note dictionary conforming to Minerva schema
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError(
            exc.encoding, exc.object, exc.start, exc.end,
            f"File encoding error in {file_path}: {exc.reason}"
        ) from exc
    except PermissionError as exc:
        raise PermissionError(f"Cannot read file: {file_path}") from exc

    # Extract title: first H1 heading or filename
    title = _extract_title(content, file_path)

    # Get file metadata
    stat = file_path.stat()

    # Modification time (required)
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    modification_date = mtime.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # Creation time (optional, best effort)
    try:
        # On Unix, st_birthtime may not be available
        ctime = datetime.fromtimestamp(stat.st_birthtime, tz=timezone.utc)
        creation_date = ctime.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except AttributeError:
        # Fallback to mtime if birthtime not available
        creation_date = modification_date

    # Calculate size
    size = len(content.encode("utf-8"))

    # Calculate relative path from root
    try:
        relative_path = file_path.relative_to(root)
        source_path = str(relative_path)
    except ValueError:
        # If file_path is not relative to root, use absolute path
        source_path = str(file_path)

    note = {
        "title": title,
        "markdown": content,
        "size": size,
        "modificationDate": modification_date,
        "creationDate": creation_date,
        "sourcePath": source_path,
    }

    return note


def _extract_title(content: str, file_path: Path) -> str:
    """
    Extract title from markdown content.

    First tries to find an H1 heading (# Title).
    Falls back to filename (without .md extension) if no H1 found.

    Args:
        content: Markdown content
        file_path: Path to the file (for fallback)

    Returns:
        Extracted or generated title
    """
    # Look for first H1 heading: # Title
    # Match: "# Title" at start of line, capture everything after #
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)

    if h1_match:
        title = h1_match.group(1).strip()
        if title:  # Ensure it's not just whitespace
            return title

    # Fallback to filename without extension
    return file_path.stem
