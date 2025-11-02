from argparse import Namespace

from minerva.common.logger import get_logger
from minerva.common.server_config import load_server_config
from minerva.server.mcp_server import main as mcp_main
from minerva.common.exceptions import ConfigError

logger = get_logger(__name__, simple=True, mode="cli")


def run_serve(args: Namespace) -> int:
    try:
        config_path = str(args.config)
        server_config = load_server_config(config_path)
        mcp_main(server_config)

        return 0

    except KeyboardInterrupt:
        logger.error("Server shutting down (keyboard interrupt)")
        return 130

    except ConfigError as error:
        logger.error(f"Configuration error: {error}")
        return 1

    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1
