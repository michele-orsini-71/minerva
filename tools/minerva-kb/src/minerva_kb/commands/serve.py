import os
import shutil
import sys
from pathlib import Path

from minerva_kb.constants import MINERVA_KB_APP_DIR


def run_serve() -> int:
    """Start the Minerva MCP server using minerva-kb's managed server config."""
    server_config_path = MINERVA_KB_APP_DIR / "server.json"

    if not server_config_path.exists():
        print(f"❌ Server config not found: {server_config_path}", file=sys.stderr)
        print("Run 'minerva-kb add <repository>' first to create collections and server config.", file=sys.stderr)
        return 1

    # Find minerva command
    # Strategy 1: Look in same directory as minerva-kb (both installed via pipx)
    # Use sys.argv[0] without .resolve() to keep the symlink path from ~/.local/bin
    minerva_kb_path = Path(sys.argv[0])
    minerva_cmd = minerva_kb_path.parent / "minerva"

    if not minerva_cmd.exists():
        # Strategy 2: Check PATH (for non-pipx installations)
        minerva_cmd_str = shutil.which("minerva")
        if minerva_cmd_str:
            minerva_cmd = Path(minerva_cmd_str)
        else:
            print("❌ 'minerva' command not found", file=sys.stderr)
            print(f"Expected location: {minerva_cmd}", file=sys.stderr)
            print("Make sure Minerva is installed:", file=sys.stderr)
            print("  Run: tools/minerva-kb/install.sh", file=sys.stderr)
            return 1

    # Log to stderr (MCP protocol requires stdout for JSON-RPC only)
    print(f"Starting Minerva MCP server with config: {server_config_path}", file=sys.stderr)
    print(f"Using minerva at: {minerva_cmd}", file=sys.stderr)
    print(file=sys.stderr)

    try:
        # Run minerva serve with the managed config
        # Use execvp to replace the current process, so stdio is preserved
        os.execvp(minerva_cmd, ["minerva", "serve", "--config", str(server_config_path)])
    except FileNotFoundError as e:
        print(f"❌ Failed to execute: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nServer stopped", file=sys.stderr)
        return 0
