import sys
from argparse import Namespace

from minervium.common.logger import get_logger
from minervium.server.mcp_server import main as mcp_main

logger = get_logger(__name__, simple=True, mode="cli")


def run_serve(args: Namespace) -> int:
    try:
        # Convert Path to string and start the MCP server
        config_path = str(args.config)

        # Start the MCP server (this blocks until shutdown)
        mcp_main(config_path)

        return 0

    except KeyboardInterrupt:
        logger.error("Server shutting down (keyboard interrupt)")
        return 130

    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
