#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from minerva.common.logger import get_logger

from minerva.commands.index import run_index
from minerva.commands.serve import run_serve
from minerva.commands.peek import run_peek
from minerva.commands.validate import run_validate

logger = get_logger(__name__, simple=True, mode="cli")


def create_parser():

    parser = argparse.ArgumentParser(
        prog='minerva',
        description='minerva - A unified RAG system for personal knowledge management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index markdown notes into ChromaDB
  minerva index --config configs/index-ollama.json

  # Validate JSON notes without indexing
  minerva validate notes.json

  # Start the MCP server
  minerva serve --config configs/server-config.json

  # Peek into a ChromaDB collection
  minerva peek bear_notes --chromadb ./chromadb_data

For more information, visit: https://github.com/yourusername/minerva
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title='commands',
        description='Available minerva commands',
        dest='command',
        required=True,
        help='Command to execute'
    )

    # ========================================
    # INDEX command
    # ========================================
    index_parser = subparsers.add_parser(
        'index',
        help='Index markdown notes into ChromaDB',
        description='Process markdown notes JSON, create chunks, generate embeddings, and store in ChromaDB.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index with Ollama provider
  minerva index --config configs/index-ollama.json

  # Index with verbose output
  minerva index --config configs/index-ollama.json --verbose

  # Dry run to validate configuration
  minerva index --config configs/index-ollama.json --dry-run
        """
    )

    index_parser.add_argument(
        '--config',
        type=Path,
        required=True,
        metavar='FILE',
        help='Path to configuration JSON file'
    )

    index_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output with detailed progress information'
    )

    index_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration and notes without indexing'
    )

    # ========================================
    # SERVE command
    # ========================================
    serve_parser = subparsers.add_parser(
        'serve',
        help='Start the MCP server',
        description='Start the Model Context Protocol (MCP) server for AI integration.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start MCP server with default config
  minerva serve

  # Start with custom config
  minerva serve --config configs/server-config.json
        """
    )

    serve_parser.add_argument(
        '--config',
        type=Path,
        required=True,
        metavar='FILE',
        help='Path to server configuration JSON file'
    )

    # ========================================
    # PEEK command
    # ========================================
    peek_parser = subparsers.add_parser(
        'peek',
        help='Inspect ChromaDB collections',
        description='View contents and metadata of ChromaDB collections.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Peek at a collection
  minerva peek bear_notes

  # Peek with custom ChromaDB path
  minerva peek bear_notes --chromadb ./chromadb_data

  # Output as JSON
  minerva peek bear_notes --format json
        """
    )

    peek_parser.add_argument(
        'collection_name',
        type=str,
        help='Name of the ChromaDB collection to inspect'
    )

    peek_parser.add_argument(
        '--chromadb',
        type=Path,
        default=Path('./chromadb_data'),
        metavar='PATH',
        help='Path to ChromaDB data directory (default: ./chromadb_data)'
    )

    peek_parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    # ========================================
    # VALIDATE command
    # ========================================
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate JSON notes against schema',
        description='Validate JSON notes file against minerva schema without indexing.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a JSON notes file
  minerva validate notes.json

  # Validate with verbose output
  minerva validate notes.json --verbose
        """
    )

    validate_parser.add_argument(
        'json_file',
        type=Path,
        help='Path to JSON notes file to validate'
    )

    validate_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output with validation details'
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.command == 'index':
            return run_index(args)
        elif args.command == 'serve':
            return run_serve(args)
        elif args.command == 'peek':
            return run_peek(args)
        elif args.command == 'validate':
            return run_validate(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logger.error("Interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if '--verbose' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
