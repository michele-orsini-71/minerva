import argparse
import sys
from pathlib import Path

from .server import main as server_main


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Webhook Orchestrator - Triggers automatic reindexing on GitHub push events"
    )

    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to configuration file'
    )

    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8338,
        help='Port to bind to (default: 8338)'
    )

    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        server_main(str(config_path), host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nShutting down webhook orchestrator...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting webhook orchestrator: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
