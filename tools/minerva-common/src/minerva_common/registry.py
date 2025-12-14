import json
import os
from pathlib import Path


class Registry:
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path

    def load(self) -> dict:
        if not self.registry_path.exists():
            return {"collections": {}}

        with self.registry_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: dict) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = self.registry_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        temp_path.replace(self.registry_path)

        try:
            os.chmod(self.registry_path, 0o600)
        except PermissionError:
            pass

    def add_collection(self, name: str, metadata: dict) -> None:
        data = self.load()
        data["collections"][name] = metadata
        self.save(data)

    def get_collection(self, name: str) -> dict | None:
        data = self.load()
        return data["collections"].get(name)

    def update_collection(self, name: str, metadata: dict) -> None:
        data = self.load()
        if name in data["collections"]:
            data["collections"][name].update(metadata)
            self.save(data)

    def remove_collection(self, name: str) -> None:
        data = self.load()
        if name in data["collections"]:
            del data["collections"][name]
            self.save(data)

    def list_collections(self) -> list[dict]:
        data = self.load()
        collections = []
        for name, metadata in data["collections"].items():
            collection_info = {"name": name, **metadata}
            collections.append(collection_info)
        return collections

    def collection_exists(self, name: str) -> bool:
        data = self.load()
        return name in data["collections"]
