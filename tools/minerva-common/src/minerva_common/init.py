import json
import os
from pathlib import Path

from minerva_common.paths import CHROMADB_DIR, MINERVA_DIR, SERVER_CONFIG_PATH


def ensure_shared_dirs() -> None:
    MINERVA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(MINERVA_DIR, 0o700)
    except PermissionError:
        pass

    CHROMADB_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CHROMADB_DIR, 0o700)
    except PermissionError:
        pass


def ensure_server_config() -> tuple[Path, bool]:
    ensure_shared_dirs()

    if SERVER_CONFIG_PATH.exists():
        return SERVER_CONFIG_PATH, False

    config = {
        "chromadb_path": str(CHROMADB_DIR),
        "default_max_results": 5,
        "host": "127.0.0.1",
        "port": 8337,
    }

    temp_path = SERVER_CONFIG_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")

    temp_path.replace(SERVER_CONFIG_PATH)

    try:
        os.chmod(SERVER_CONFIG_PATH, 0o600)
    except PermissionError:
        pass

    return SERVER_CONFIG_PATH, True
