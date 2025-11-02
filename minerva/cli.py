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
from minerva.commands.validate import run_validate
from minerva.commands.chat import run_chat

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
  # Start HTTP server on default port (8000)
  minerva serve-http --config configs/server/local.json

  # Start on custom host and port
  minerva serve-http --config configs/server/local.json --host 0.0.0.0 --port 9000

  # Start on localhost only
  minerva serve-http --config configs/server/local.json --host 127.0.0.1 --port 8000
        """
    )

    serve_http_parser.add_argument(
        '--config',
        type=Path,
        required=True,
        metavar='FILE',
        help='Path to server configuration JSON file'
    )

    serve_http_parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        metavar='HOST',
        help='Host to bind to (default: localhost). Use 0.0.0.0 for all interfaces'
    )

    serve_http_parser.add_argument(
        '--port',
        type=int,
        default=8000,
        metavar='PORT',
        help='Port to bind to (default: 8000)'
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
    # CHAT command
    # ========================================
    chat_parser = subparsers.add_parser(
        'chat',
        help='Interactive chat with AI using your knowledge bases',
        description='Chat with an AI assistant that can search through your indexed knowledge bases.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start interactive chat session
  minerva chat --config configs/chat/ollama.json

  # Ask a single question and exit
  minerva chat --config configs/chat/ollama.json -q "What are my notes about Python?"

  # List past conversations
  minerva chat --config configs/chat/ollama.json --list

  # Resume a previous conversation
  minerva chat --config configs/chat/ollama.json --resume 20251030-143022-abc123

  # Start chat with custom system prompt
  minerva chat --config configs/chat/ollama.json --system "You are a code review assistant"
        """
    )

    chat_parser.add_argument(
        '--config',
        type=Path,
        required=True,
        metavar='FILE',
        help='Path to chat configuration JSON file'
    )

    chat_parser.add_argument(
        '-q', '--question',
        type=str,
        metavar='QUESTION',
        help='Ask a single question and exit (non-interactive mode)'
    )

    chat_parser.add_argument(
        '--system',
        type=str,
        metavar='PROMPT',
        help='Custom system prompt for the AI assistant'
    )

    chat_parser.add_argument(
        '--list',
        action='store_true',
        help='List all past conversations and exit'
    )

    chat_parser.add_argument(
        '--resume',
        type=str,
        metavar='CONVERSATION_ID',
        help='Resume a previous conversation by its ID'
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
        elif args.command == 'validate':
            return run_validate(args)
        elif args.command == 'chat':
            return run_chat(args)
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
