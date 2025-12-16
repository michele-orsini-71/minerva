import argparse
import sys


def get_version_info():
    return "minerva-doc 1.0.0"


def main():
    parser = argparse.ArgumentParser(
        prog='minerva-doc',
        description='Orchestrator tool for managing Minerva document-based knowledge base collections',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--version',
        action='version',
        version=get_version_info()
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )

    add_parser = subparsers.add_parser(
        'add',
        help='Create a new collection from pre-extracted JSON documents',
        description='''Create a new collection from pre-extracted JSON documents.

Accepts JSON files following Minerva's note schema (from extractors like
bear-extractor, zim-extractor, markdown-books-extractor, or custom tools).

Interactive workflow:
  - Validates JSON file format
  - Prompts for AI provider selection (OpenAI, Gemini, Ollama, LM Studio)
  - Prompts for collection description (with auto-generate option)
  - Creates embeddings and indexes them
  - Registers collection for management

Examples:
  minerva-doc add notes.json --name bear-notes
  minerva-doc add wiki.json --name wikipedia
  minerva-doc add alice.json --name alice-in-wonderland''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_parser.add_argument(
        'json_file',
        help='Path to JSON file containing extracted notes'
    )
    add_parser.add_argument(
        '--name',
        required=True,
        help='Collection name (must be unique)'
    )

    update_parser = subparsers.add_parser(
        'update',
        help='Re-index a collection with new data or different provider',
        description='''Re-index a collection with new data or different provider.

Use when:
  - You have updated document data (new JSON export)
  - You want to switch AI providers
  - You need to re-generate embeddings

Interactive workflow:
  - Validates new JSON file
  - Prompts to change AI provider (optional)
  - Re-indexes collection with new data
  - Updates registry metadata

Examples:
  minerva-doc update bear-notes updated-notes.json
  minerva-doc update wikipedia new-wiki-export.json''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    update_parser.add_argument(
        'collection_name',
        help='Name of the collection to update'
    )
    update_parser.add_argument(
        'json_file',
        help='Path to new JSON file'
    )

    list_parser = subparsers.add_parser(
        'list',
        help='Display all collections (managed and unmanaged)',
        description='''Display all collections in ChromaDB.

Shows two categories:
  - Managed by minerva-doc: Full details (provider, chunks, dates)
  - Unmanaged: Basic info with warning (use appropriate tool to manage)

Output formats:
  - table: Human-readable format (default)
  - json: Machine-readable format for scripting

Examples:
  minerva-doc list
  minerva-doc list --format json
  minerva-doc list --format json | jq '.managed[]' ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    list_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)'
    )

    status_parser = subparsers.add_parser(
        'status',
        help='Display detailed status for a specific collection',
        description='''Display detailed status for a specific collection.

Comprehensive diagnostics including:
  - Collection name and description
  - Source JSON file path
  - AI provider configuration (type, models)
  - ChromaDB status (chunk count, last modified)
  - Indexing dates (created, last updated)

Use for troubleshooting or verifying configuration.

Examples:
  minerva-doc status bear-notes
  minerva-doc status wikipedia''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    status_parser.add_argument(
        'collection_name',
        help='Name of the collection to check'
    )

    remove_parser = subparsers.add_parser(
        'remove',
        help='Delete collection and all associated data',
        description='''Delete collection and all associated data.

⚠️  WARNING: This operation cannot be undone.

Deletes:
  - ChromaDB collection and all embeddings
  - Registry entry and metadata

Does NOT delete:
  - Source JSON files (your documents are safe)
  - Shared server configuration
  - API keys (shared across collections)

Confirmation required: Must type "YES" exactly to proceed.

Examples:
  minerva-doc remove bear-notes
  minerva-doc remove old-collection''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    remove_parser.add_argument(
        'collection_name',
        help='Name of the collection to remove'
    )

    serve_parser = subparsers.add_parser(
        'serve',
        help='Start the Minerva MCP server',
        description='''Start the Minerva MCP server with shared configuration.

Uses the server config shared across all Minerva tools at:
  ~/.minerva/server.json

The server provides:
  - Semantic search across all collections (minerva-doc + minerva-kb)
  - MCP (Model Context Protocol) integration
  - Compatible with Claude Desktop and other MCP clients

Examples:
  minerva-doc serve                    # Start server (stdio mode)

Configuration for Claude Desktop:
  Add to ~/Library/Application Support/Claude/claude_desktop_config.json:
  {
    "mcpServers": {
      "minerva": {
        "command": "minerva-doc",
        "args": ["serve"]
      }
    }
  }''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    args = parser.parse_args()

    if args.command == 'add':
        from minerva_doc.commands.add import run_add
        return run_add(args.json_file, args.name)
    elif args.command == 'update':
        from minerva_doc.commands.update import run_update
        return run_update(args.collection_name, args.json_file)
    elif args.command == 'list':
        from minerva_doc.commands.list import run_list
        return run_list(args.format)
    elif args.command == 'status':
        from minerva_doc.commands.status import run_status
        return run_status(args.collection_name)
    elif args.command == 'remove':
        from minerva_doc.commands.remove import run_remove
        return run_remove(args.collection_name)
    elif args.command == 'serve':
        from minerva_doc.commands.serve import run_serve
        return run_serve()
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
