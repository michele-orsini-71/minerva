import sys

from minerva_common.init import ensure_server_config
from minerva_common.paths import CHROMADB_DIR
from minerva_common.server_manager import start_server


def run_serve() -> int:
    """Start the Minerva MCP server using shared server config."""
    server_config_path, created = ensure_server_config()

    if created:
        print(f"✓ Created server config: {server_config_path}", file=sys.stderr)

    try:
        server_process = start_server(server_config_path, CHROMADB_DIR)
        server_process.wait()  # Wait for server to exit (keeps process alive)
        return 0
    except FileNotFoundError as e:
        print(f"❌ Server config not found: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"❌ Failed to start server: {e}", file=sys.stderr)
        return 1
