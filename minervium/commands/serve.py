"""
Serve command - Start the MCP server for AI integration.
"""

import sys
from argparse import Namespace
from minervium.server.mcp_server import main as mcp_main


def run_serve(args: Namespace) -> int:
    """
    Main entry point for the serve command.

    Args:
        args: Parsed command-line arguments containing:
            - config: Path to server configuration file (required)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Convert Path to string and start the MCP server
        config_path = str(args.config)

        # Start the MCP server (this blocks until shutdown)
        mcp_main(config_path)

        return 0

    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        print("\n\n✗ Server shutting down (keyboard interrupt)", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"\n✗ Server error: {e}", file=sys.stderr)
        return 1
