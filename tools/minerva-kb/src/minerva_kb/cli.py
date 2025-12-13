import argparse
import sys
import subprocess

from minerva_kb.commands import run_add, run_list, run_remove, run_serve, run_status, run_sync, run_watch


def get_version_info():
    lines = ["minerva-kb 1.0.0", ""]
    lines.append("Dependencies:")

    packages = [
        ("minerva", "Minerva core"),
        ("repository-doc-extractor", "Repository extractor"),
        ("local-repo-watcher", "File watcher"),
    ]

    for pkg_name, description in packages:
        try:
            result = subprocess.run(
                ["pipx", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if f"package {pkg_name}" in line.lower():
                        version = line.split()[-1] if line.split() else "unknown"
                        lines.append(f"  {description}: {version}")
                        break
                else:
                    lines.append(f"  {description}: not installed")
            else:
                lines.append(f"  {description}: unknown")
        except Exception:
            lines.append(f"  {description}: unknown")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog='minerva-kb',
        description='Orchestrator tool for managing Minerva repository-based knowledge base collections',
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
        help='Create a new collection or update an existing collection\'s AI provider',
        description='''Create a new collection or update an existing collection's AI provider.

For new collections:
  - Generates optimized description from README
  - Prompts for AI provider selection (OpenAI, Gemini, Ollama, LM Studio)
  - Extracts documentation files
  - Creates embeddings and indexes them
  - Auto-creates configuration files

For existing collections:
  - Detects collection exists
  - Prompts to change AI provider
  - Re-indexes with new provider if confirmed

Examples:
  minerva-kb add ~/code/my-project
  minerva-kb add /path/to/repository''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_parser.add_argument(
        'repo_path',
        help='Path to repository to index'
    )

    list_parser = subparsers.add_parser(
        'list',
        help='Display all managed collections with status information',
        description='''Display all managed collections with status information.

Shows for each collection:
  - Collection name
  - Repository path
  - AI provider and models
  - Chunk count
  - Watcher status (running/stopped with PID)
  - Last indexed timestamp

Output formats:
  - table: Human-readable format (default)
  - json: Machine-readable format for scripting

Examples:
  minerva-kb list
  minerva-kb list --format json
  minerva-kb list --format json | jq '.[] | select(.watcher.running)'  ''',
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
  - Collection name and repository path
  - AI provider configuration (type, models, API key status)
  - ChromaDB status (exists, chunk count, last modified)
  - Configuration files (paths and sizes)
  - Watcher status (running/stopped, PID, patterns, debounce)

Use for troubleshooting issues or verifying configuration.

Examples:
  minerva-kb status my-project
  minerva-kb status internal-docs''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    status_parser.add_argument(
        'collection_name',
        help='Name of the collection to check'
    )

    sync_parser = subparsers.add_parser(
        'sync',
        help='Manually trigger re-indexing for a collection',
        description='''Manually trigger re-indexing for a collection.

Re-extracts documentation from repository and updates embeddings.

Use when:
  - Made bulk changes outside watcher scope
  - Watcher was stopped during significant updates
  - Want to verify indexing after provider change
  - Debugging indexing issues

The watcher (if running) is unaffected by manual sync.

Examples:
  minerva-kb sync my-project
  minerva-kb sync internal-docs''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sync_parser.add_argument(
        'collection_name',
        help='Name of the collection to sync'
    )

    watch_parser = subparsers.add_parser(
        'watch',
        help='Start file watcher for a collection',
        description='''Start file watcher for automatic re-indexing on file changes.

Interactive mode (no collection name):
  - Shows numbered menu of all collections
  - Displays current watcher status for each
  - Prompts for selection

Direct mode (with collection name):
  - Starts watcher immediately for specified collection

Behavior:
  - Runs in foreground (use Ctrl+C to stop)
  - 60-second debounce prevents thrashing
  - Watches: .md, .mdx, .markdown, .rst, .txt
  - Ignores: .git, node_modules, .venv, __pycache__

For persistent watchers, use tmux or screen.

Examples:
  minerva-kb watch                    # Interactive selection
  minerva-kb watch my-project         # Direct start''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    watch_parser.add_argument(
        'collection_name',
        nargs='?',
        help='Name of the collection to watch (optional, will prompt if not provided)'
    )

    remove_parser = subparsers.add_parser(
        'remove',
        help='Delete collection and all associated data',
        description='''Delete collection and all associated data.

⚠️  WARNING: This operation cannot be undone (except from backups).

Deletes:
  - ChromaDB collection and all embeddings
  - Configuration files (index, watcher)
  - Extracted repository data

Does NOT delete:
  - Repository files (your source code is safe)
  - API keys (shared across collections)

Confirmation required: Must type "YES" exactly to proceed.

Examples:
  minerva-kb remove my-project
  minerva-kb remove old-collection''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    remove_parser.add_argument(
        'collection_name',
        help='Name of the collection to remove'
    )

    serve_parser = subparsers.add_parser(
        'serve',
        help='Start the Minerva MCP server',
        description='''Start the Minerva MCP server with auto-managed configuration.

Uses the server config automatically created by minerva-kb at:
  ~/.minerva/apps/minerva-kb/server.json

This config is automatically updated as you add/remove collections.

The server provides:
  - Semantic search across all managed collections
  - MCP (Model Context Protocol) integration
  - Compatible with Claude Desktop and other MCP clients

Examples:
  minerva-kb serve                    # Start server (stdio mode)

Configuration for Claude Desktop:
  Add to ~/Library/Application Support/Claude/claude_desktop_config.json:
  {
    "mcpServers": {
      "minerva": {
        "command": "minerva-kb",
        "args": ["serve"]
      }
    }
  }''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    args = parser.parse_args()

    if args.command == 'add':
        return run_add(args.repo_path)
    elif args.command == 'list':
        return run_list(args.format)
    elif args.command == 'status':
        return run_status(args.collection_name)
    elif args.command == 'sync':
        return run_sync(args.collection_name)
    elif args.command == 'watch':
        return run_watch(args.collection_name)
    elif args.command == 'remove':
        return run_remove(args.collection_name)
    elif args.command == 'serve':
        return run_serve()
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
