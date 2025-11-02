from argparse import Namespace

from minerva.common.logger import get_logger
from minerva.common.server_config import load_server_config
from minerva.common.exceptions import ConfigError

logger = get_logger(__name__, simple=True, mode="cli")


def run_serve_http(args: Namespace) -> int:
    from minerva.server.mcp_server import main_http

    try:
        config_path = str(args.config)
        server_config = load_server_config(config_path)

        host = args.host if args.host else server_config.host or "localhost"
        port = args.port if args.port else server_config.port or 8000

        logger.info(f"Starting HTTP server on {host}:{port}...")

        main_http(server_config, host=host, port=port)

        return 0

    except OSError as e:
        if "Address already in use" in str(e) or "address already in use" in str(e).lower():
            logger.error(
                f"Error: Port {port} is already in use.\n\n"
                f"Troubleshooting:\n"
                f"1. Check if another server is running on port {port}\n"
                f"2. Use a different port with --port <port_number>\n"
                f"3. Stop any conflicting services using: lsof -ti:{port} | xargs kill\n"
            )
            return 1
        else:
            logger.error(f"Network error: {e}")
            return 1

    except KeyboardInterrupt:
        logger.info("\nServer shutting down (keyboard interrupt)")
        return 130

    except ConfigError as error:
        logger.error(f"Configuration error: {error}")
        return 1

    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
