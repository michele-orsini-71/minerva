#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

from minerva.common.logger import get_logger
from minerva.common.exceptions import MinervaError, GracefulExit, resolve_exit_code

from minerva.commands.index import run_index
from minerva.commands.serve import run_serve
from minerva.commands.serve_http import run_serve_http
from minerva.commands.peek import run_peek
from minerva.commands.remove import run_remove
from minerva.commands.validate import run_validate
from minerva.commands.query import run_query

logger = get_logger(__name__, simple=True, mode="cli")


def create_parser():

    parser = argparse.ArgumentParser(
        prog='minerva',
        description='minerva - A unified RAG system for personal knowledge management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index markdown notes into ChromaDB
  minerva index --config configs/index/bear-notes-ollama.json

  # Validate JSON notes without indexing
  minerva validate notes.json

  # Start the MCP server
  minerva serve --config configs/server/local.json

  # Peek into a ChromaDB collection
  minerva peek bear_notes --chromadb ./chromadb_data

For more information, visit: https://github.com/yourusername/minerva
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 3.0.0'
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
  minerva index --config configs/index/bear-notes-ollama.json

  # Index with verbose output
  minerva index --config configs/index/bear-notes-ollama.json --verbose

  # Dry run to validate configuration
  minerva index --config configs/index/bear-notes-ollama.json --dry-run
        """
    )

    index_parser.add_argument(
        '--config',
        type=Path,
        required=True,
        metavar='FILE',
        help='Path to index configuration JSON file'
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
  minerva serve --config configs/server/local.json
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
    # SERVE-HTTP command
    # ========================================
    serve_http_parser = subparsers.add_parser(
        'serve-http',
        help='Start the MCP server in HTTP mode',
        description='Start the Model Context Protocol (MCP) server in HTTP mode for network access.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start HTTP server (host and port specified in config file)
  minerva serve-http --config configs/server/local.json

  # Use different config for different host/port settings
  minerva serve-http --config configs/server/production.json
        """
    )

    serve_http_parser.add_argument(
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
  # List all collections in a ChromaDB database
  minerva peek ./chromadb_data

  # Peek at a specific collection
  minerva peek ./chromadb_data bear_notes

  # Output as JSON
  minerva peek ./chromadb_data bear_notes --format json
        """
    )

    peek_parser.add_argument(
        'chromadb',
        type=Path,
        metavar='CHROMADB_PATH',
        help='Path to ChromaDB data directory (required)'
    )

    peek_parser.add_argument(
        'collection_name',
        type=str,
        nargs='?',
        metavar='COLLECTION_NAME',
        help='Name of the ChromaDB collection to inspect (optional, if omitted shows all collections)'
    )

    peek_parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    # ========================================
    # REMOVE command
    # ========================================
    remove_parser = subparsers.add_parser(
        'remove',
        help='Delete a ChromaDB collection after confirmation',
        description='Permanently delete a ChromaDB collection. Requires two confirmations.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete a collection (interactive confirmations)
  minerva remove ./chromadb_data bear_notes
        """
    )

    remove_parser.add_argument(
        'chromadb',
        type=Path,
        metavar='CHROMADB_PATH',
        help='Path to ChromaDB data directory'
    )

    remove_parser.add_argument(
        'collection_name',
        type=str,
        metavar='COLLECTION_NAME',
        help='Name of the collection to delete'
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

    # ========================================
    # QUERY command
    # ========================================
    query_parser = subparsers.add_parser(
        'query',
        help='Query ChromaDB collections with semantic search',
        description='Perform semantic search queries on indexed collections.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query a specific collection
  minerva query ~/.minerva/chromadb --collection my_docs "How does authentication work?"

  # Query all collections
  minerva query ~/.minerva/chromadb "How does authentication work?"

  # Limit results
  minerva query ~/.minerva/chromadb --collection my_docs --max-results 10 "API design"

  # JSON output for scripting
  minerva query ~/.minerva/chromadb --collection my_docs --format json "API design"
        """
    )

    query_parser.add_argument(
        'chromadb_path',
        type=Path,
        metavar='CHROMADB_PATH',
        help='Path to ChromaDB data directory'
    )

    query_parser.add_argument(
        'query',
        type=str,
        metavar='QUERY',
        help='Search query text'
    )

    query_parser.add_argument(
        '--collection',
        type=str,
        metavar='NAME',
        help='Collection name to search (if omitted, searches all collections)'
    )

    query_parser.add_argument(
        '--max-results',
        type=int,
        default=5,
        metavar='N',
        help='Maximum number of results to return (default: 5)'
    )

    query_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )

    query_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed search progress logs'
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
        elif args.command == 'serve-http':
            return run_serve_http(args)
        elif args.command == 'peek':
            return run_peek(args)
        elif args.command == 'remove':
            return run_remove(args)
        elif args.command == 'validate':
            return run_validate(args)
        elif args.command == 'query':
            return run_query(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logger.error("Interrupted by user")
        return 130  # Standard exit code for SIGINT

    except MinervaError as error:
        message = str(error).strip()
        if isinstance(error, GracefulExit):
            if message:
                logger.info(message)
        else:
            if message:
                logger.error(message)
        return resolve_exit_code(error)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if '--verbose' in sys.argv:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
