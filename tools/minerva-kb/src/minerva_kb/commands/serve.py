import sys

from minerva_common.init import ensure_server_config
from minerva_common.paths import CHROMADB_DIR
from minerva_common.server_manager import start_server


def run_serve() -> int:
    """Start the Minerva MCP server using shared server config."""
    try:
        return execute_serve()
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
        return 0
    except FileNotFoundError as e:
        print(f"❌ Server config not found: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Failed to start server: {e}", file=sys.stderr)
        return 1


def execute_serve() -> int:
    # Ensure config exists, create if needed
    server_config_path, created = ensure_server_config()

    if created:
        print(f"✓ Created server config: {server_config_path}", file=sys.stderr)

    # Display informative header
    print(file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("Starting Minerva MCP Server", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(file=sys.stderr)
    print("This server exposes ALL collections in ChromaDB:", file=sys.stderr)
    print("  - Collections managed by minerva-doc", file=sys.stderr)
    print("  - Collections managed by minerva-kb", file=sys.stderr)
    print("  - Any other collections in ChromaDB", file=sys.stderr)
    print(file=sys.stderr)

    # Start server with correct parameters
    server_process = start_server(server_config_path, CHROMADB_DIR)
    server_process.wait()  # Keep process alive
    return 0
