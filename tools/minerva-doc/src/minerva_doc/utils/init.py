import json
import os
from pathlib import Path

from minerva_common.init import ensure_shared_dirs
from minerva_doc.constants import MINERVA_DOC_APP_DIR, COLLECTIONS_REGISTRY_PATH


def ensure_app_dir() -> Path:
    ensure_shared_dirs()

    MINERVA_DOC_APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(MINERVA_DOC_APP_DIR, 0o700)
    except PermissionError:
        pass

    return MINERVA_DOC_APP_DIR


def ensure_registry() -> Path:
    ensure_app_dir()

    if COLLECTIONS_REGISTRY_PATH.exists():
        return COLLECTIONS_REGISTRY_PATH

    empty_registry = {"collections": {}}

    temp_path = COLLECTIONS_REGISTRY_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(empty_registry, handle, indent=2)
        handle.write("\n")

    temp_path.replace(COLLECTIONS_REGISTRY_PATH)

    try:
        os.chmod(COLLECTIONS_REGISTRY_PATH, 0o600)
    except PermissionError:
        pass

    return COLLECTIONS_REGISTRY_PATH
