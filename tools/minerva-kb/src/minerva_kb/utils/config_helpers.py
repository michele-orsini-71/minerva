import os
from pathlib import Path

from minerva_kb.constants import MINERVA_KB_APP_DIR


def ensure_config_dir() -> Path:
    MINERVA_KB_APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(MINERVA_KB_APP_DIR, 0o700)
    except PermissionError:
        pass
    return MINERVA_KB_APP_DIR


def get_config_paths(collection_name: str) -> dict[str, Path]:
    base = ensure_config_dir()
    return {
        "watcher": base / f"{collection_name}-watcher.json",
        "index": base / f"{collection_name}-index.json",
        "extracted": base / f"{collection_name}-extracted.json",
        "server": base / "server.json",
    }


def config_files_exist(collection_name: str) -> tuple[bool, bool]:
    paths = get_config_paths(collection_name)
    return paths["index"].exists(), paths["watcher"].exists()


def delete_config_files(collection_name: str) -> list[Path]:
    deleted: list[Path] = []
    paths = get_config_paths(collection_name)
    for key in ("watcher", "index", "extracted"):
        path = paths[key]
        if path.exists():
            try:
                path.unlink()
                deleted.append(path)
            except OSError:
                continue
    return deleted


def list_managed_collections() -> list[str]:
    if not MINERVA_KB_APP_DIR.exists():
        return []
    names: list[str] = []
    for watcher_path in sorted(MINERVA_KB_APP_DIR.glob("*-watcher.json")):
        names.append(watcher_path.stem.replace("-watcher", ""))
    return names
