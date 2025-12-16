from minerva_common.server_manager import start_server


def run_serve() -> int:
    try:
        return execute_serve()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        return 0


def execute_serve() -> int:
    print()
    print("=" * 60)
    print("Starting Minerva MCP Server")
    print("=" * 60)
    print()
    print("Using shared server configuration:")
    print("  ~/.minerva/server.json")
    print()
    print("This server exposes ALL collections in ChromaDB:")
    print("  - Collections managed by minerva-doc")
    print("  - Collections managed by minerva-kb")
    print("  - Any other collections in ChromaDB")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    return start_server()
