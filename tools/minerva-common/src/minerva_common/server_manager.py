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
    import sys

    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("🚀 Starting Minerva MCP Server", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)

    print(f"📁 ChromaDB Path: {config.get('chromadb_path', 'N/A')}", file=sys.stderr)
    print(f"🔢 Default Max Results: {config.get('default_max_results', 'N/A')}", file=sys.stderr)

    host = config.get("host")
    port = config.get("port")
    if host and port:
        print(f"🌐 Server URL: http://{host}:{port}", file=sys.stderr)

    print(file=sys.stderr)
    print(f"📚 Available Collections: {len(collections)}", file=sys.stderr)

    if collections:
        print(file=sys.stderr)
        for col in collections:
            print(f"  • {col['name']}: {col['count']:,} chunks", file=sys.stderr)
    else:
        print("  (No collections found)", file=sys.stderr)

    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Server is running. Press Ctrl+C to stop.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)
