import argparse
import sys

from minerva_kb.commands import run_add, run_list, run_status, run_sync, run_watch


def main():
    parser = argparse.ArgumentParser(
        prog='minerva-kb',
        description='Orchestrator tool for managing Minerva repository-based knowledge base collections',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )

    add_parser = subparsers.add_parser(
        'add',
        help='Create a new collection or update an existing collection\'s AI provider',
        description='Create a new collection or update an existing collection\'s AI provider'
    )
    add_parser.add_argument(
        'repo_path',
        help='Path to repository to index'
    )

    list_parser = subparsers.add_parser(
        'list',
        help='Display all managed collections with status information',
        description='Display all managed collections with status information'
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
        description='Display detailed status for a specific collection'
    )
    status_parser.add_argument(
        'collection_name',
        help='Name of the collection to check'
    )

    sync_parser = subparsers.add_parser(
        'sync',
        help='Manually trigger re-indexing for a collection',
        description='Manually trigger re-indexing for a collection'
    )
    sync_parser.add_argument(
        'collection_name',
        help='Name of the collection to sync'
    )

    watch_parser = subparsers.add_parser(
        'watch',
        help='Start file watcher for a collection',
        description='Start file watcher for a collection (or interactively select one)'
    )
    watch_parser.add_argument(
        'collection_name',
        nargs='?',
        help='Name of the collection to watch (optional, will prompt if not provided)'
    )

    remove_parser = subparsers.add_parser(
        'remove',
        help='Delete collection and all associated data',
        description='Delete collection and all associated data'
    )
    remove_parser.add_argument(
        'collection_name',
        help='Name of the collection to remove'
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
        print(f"remove command called for collection: {args.collection_name}")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
