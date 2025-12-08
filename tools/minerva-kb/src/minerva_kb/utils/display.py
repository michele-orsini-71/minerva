from datetime import datetime
from pathlib import Path


def format_file_size(value: int | float | None) -> str:
    if value is None or value <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def format_timestamp(value: Path | str | None) -> str:
    if not value:
        return "unknown"
    path = Path(value).expanduser()
    if not path.exists():
        return "unknown"
    timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def format_chunk_count(count: int | None) -> str:
    if count is None:
        return "unknown"
    return f"{count:,}"


def display_section_header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def display_error(message: str) -> None:
    print(f"❌ {message}")


def display_success(message: str) -> None:
    print(f"✓ {message}")


def display_warning(message: str) -> None:
    print(f"⚠️ {message}")
