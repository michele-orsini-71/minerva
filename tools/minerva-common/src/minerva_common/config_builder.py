import json
import os
from pathlib import Path


def build_index_config(
    collection_name: str,
    json_file: str | Path,
    chromadb_path: str | Path,
    provider: dict,
    description: str = "",
    chunk_size: int = 1200,
    force_recreate: bool = False,
    skip_ai_validation: bool = False,
) -> dict:
    config = {
        "chromadb_path": str(chromadb_path),
        "collection": {
            "name": collection_name,
            "description": description,
            "json_file": str(json_file),
            "chunk_size": chunk_size,
            "force_recreate": force_recreate,
            "skip_ai_validation": skip_ai_validation,
        },
        "provider": provider,
    }
    return config


def save_index_config(config: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    temp_path.replace(output_path)

    try:
        os.chmod(output_path, 0o600)
    except PermissionError:
        pass
