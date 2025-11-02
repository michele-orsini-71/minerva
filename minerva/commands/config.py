from argparse import Namespace

from minerva.common.config_loader import load_unified_config
from minerva.common.exceptions import ConfigError
from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")


def run_config_command(args: Namespace) -> int:
    if args.config_command == 'validate':
        return run_config_validate(args)

    logger.error(f"Unknown config subcommand: {getattr(args, 'config_command', None)}")
    return 1


def run_config_validate(args: Namespace) -> int:
    config_path = str(args.config_file)

    logger.info("")
    logger.info("Minerva Configuration Validation")
    logger.info("=" * 60)
    logger.info(f"Validating configuration: {config_path}")

    try:
        unified_config = load_unified_config(config_path)
    except ConfigError as error:
        logger.error("Configuration validation failed")
        logger.error("=" * 60)
        logger.error(str(error))
        return 1

    providers_count = len(unified_config.providers)
    collections_count = len(unified_config.indexing.collections)

    logger.success("   ✓ Configuration is valid")
    logger.info("")
    logger.info("Summary:")
    logger.info(f"   Providers: {providers_count}")
    logger.info(f"   Index collections: {collections_count}")
    logger.info(f"   Chat provider: {unified_config.chat.chat_provider_id}")
    logger.info(f"   MCP server URL: {unified_config.chat.mcp_server_url}")
    logger.info(f"   ChromaDB path: {unified_config.server.chromadb_path}")

    return 0
