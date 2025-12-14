import json
import subprocess
from pathlib import Path

import chromadb

from minerva_common.minerva_runner import run_serve


def start_server(server_config_path: str | Path, chromadb_path: str | Path) -> subprocess.Popen:
    server_config_path = Path(server_config_path)
    chromadb_path = Path(chromadb_path)

    if not server_config_path.exists():
        raise FileNotFoundError(f"Server config not found: {server_config_path}")

    with open(server_config_path, "r", encoding="utf-8") as f:
        server_config = json.load(f)

    collections = list_available_collections(chromadb_path)

    display_server_info(server_config, collections)

    server_process = run_serve(str(server_config_path))

    return server_process


def list_available_collections(chromadb_path: str | Path) -> list[dict]:
    chromadb_path = Path(chromadb_path)

    if not chromadb_path.exists():
        return []

    try:
        client = chromadb.PersistentClient(path=str(chromadb_path))
        collections = client.list_collections()

        result = []
        for collection in collections:
            result.append({"name": collection.name, "count": collection.count()})

        return result

    except Exception:
        return []


def display_server_info(config: dict, collections: list[dict]) -> None:
    print()
    print("=" * 60)
    print("🚀 Starting Minerva MCP Server")
    print("=" * 60)
    print()

    print(f"📁 ChromaDB Path: {config.get('chromadb_path', 'N/A')}")
    print(f"🔢 Default Max Results: {config.get('default_max_results', 'N/A')}")

    host = config.get("host")
    port = config.get("port")
    if host and port:
        print(f"🌐 Server URL: http://{host}:{port}")

    print()
    print(f"📚 Available Collections: {len(collections)}")

    if collections:
        print()
        for col in collections:
            print(f"  • {col['name']}: {col['count']:,} chunks")
    else:
        print("  (No collections found)")

    print()
    print("=" * 60)
    print("Server is running. Press Ctrl+C to stop.")
    print("=" * 60)
    print()
