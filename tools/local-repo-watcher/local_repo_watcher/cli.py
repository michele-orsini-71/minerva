#!/usr/bin/env python3
"""
Local Repository Watcher CLI
Watches a repository for changes and triggers Minerva indexing
"""

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict

from .watcher import RepositoryWatcher


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load watcher configuration from JSON file."""
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path) as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for the watcher CLI."""
    parser = argparse.ArgumentParser(
        description='Watch repository for changes and trigger Minerva indexing'
    )
    parser.add_argument(
        '--config',
        type=Path,
        required=True,
        help='Path to watcher configuration JSON file'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--no-initial-index',
        action='store_true',
        help='Skip initial indexing on startup'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without running commands'
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Load configuration
    config = load_config(args.config)

    if args.dry_run:
        logging.info("DRY-RUN MODE: Commands will be logged but not executed")

    # Create watcher
    watcher = RepositoryWatcher(
        config=config,
        run_initial_index=not args.no_initial_index,
        dry_run=args.dry_run
    )

    # Setup signal handlers for graceful shutdown
    def shutdown_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Start watching
    logging.info(f"Starting watcher for: {config['repository_path']}")
    logging.info(f"Collection: {config['collection_name']}")
    logging.info(f"Press Ctrl+C to stop")

    try:
        watcher.start()
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down...")
        watcher.stop()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        watcher.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
