import sys
from argparse import Namespace

from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")


def run_serve_http(args: Namespace) -> int:
    from minerva.server.mcp_server import main_http

    try:
        config_path = str(args.config)
        host = args.host
        port = args.port

        logger.info(f"Starting HTTP server on {host}:{port}...")

        main_http(config_path, host=host, port=port)

        return 0

    except OSError as e:
        if "Address already in use" in str(e) or "address already in use" in str(e).lower():
            logger.error(
                f"Error: Port {args.port} is already in use.\n\n"
                f"Troubleshooting:\n"
                f"1. Check if another server is running on port {args.port}\n"
                f"2. Use a different port with --port <port_number>\n"
                f"3. Stop any conflicting services using: lsof -ti:{args.port} | xargs kill\n"
            )
            return 1
        else:
            logger.error(f"Network error: {e}")
            return 1

    except KeyboardInterrupt:
        logger.info("\nServer shutting down (keyboard interrupt)")
        return 130

    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
