"""CLI for managing local-repo-watcher instances."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

CONFIG_DIR = Path.home() / '.minerva' / 'apps' / 'local-repo-kb'
DEFAULT_WATCHER_BINARY = 'local-repo-watcher'


def find_watcher_configs() -> List[Path]:
    if not CONFIG_DIR.exists():
        return []
    return sorted(CONFIG_DIR.glob('*-watcher.json'))


def load_collection_name(config_path: Path) -> str:
    try:
        data = json.loads(config_path.read_text())
        return data.get('collection_name') or config_path.stem.replace('-watcher', '')
    except Exception:
        return config_path.stem.replace('-watcher', '')


def choose_collection(configs: List[Path]) -> Optional[Path]:
    if not configs:
        print("❌ No watcher configs found. Run the setup wizard first.")
        return None

    print("Available collections:")
    for idx, path in enumerate(configs, start=1):
        print(f"  {idx}. {load_collection_name(path)}  ({path})")

    while True:
        choice = input("Select collection [1-{}] (or blank to cancel): ".format(len(configs))).strip()
        if not choice:
            return None
        if not choice.isdigit():
            print("❌ Invalid choice. Enter a number.")
            continue
        idx = int(choice)
        if 1 <= idx <= len(configs):
            return configs[idx - 1]
        print("❌ Choice out of range.")


def run_watcher(config_path: Path, watcher_bin: str, extra_args: List[str]) -> int:
    command = [watcher_bin, '--config', str(config_path), *extra_args]
    print()
    print(f"▶️  Starting watcher: {' '.join(command)}")
    print("   Press Ctrl+C to stop.")
    print()

    proc = subprocess.Popen(command)
    try:
        proc.wait()
        return proc.returncode or 0
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='minerva-local-watcher',
        description='Select and start a local-repo-watcher for Minerva collections.'
    )
    parser.add_argument(
        '--collection',
        type=str,
        help='Collection name to start immediately (skips interactive selection).'
    )
    parser.add_argument(
        '--config',
        type=Path,
        help='Explicit watcher config path (overrides --collection).'
    )
    parser.add_argument(
        '--watcher-bin',
        type=str,
        default=DEFAULT_WATCHER_BINARY,
        help='Watcher binary name (default: local-repo-watcher).'
    )
    parser.add_argument(
        'extra_args',
        nargs=argparse.REMAINDER,
        help='Additional args passed directly to local-repo-watcher after --.'
    )
    return parser.parse_args(argv)


def find_config_by_collection(name: str) -> Optional[Path]:
    configs = find_watcher_configs()
    target = name.strip().lower()
    for config_path in configs:
        coll_name = load_collection_name(config_path).lower()
        if coll_name == target:
            return config_path
    return None


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    config_path: Optional[Path] = None

    if args.config:
        config_path = args.config.expanduser().resolve()
        if not config_path.exists():
            print(f"❌ Config file not found: {config_path}")
            return 1
    elif args.collection:
        config_path = find_config_by_collection(args.collection)
        if not config_path:
            print(f"❌ No watcher config found for collection '{args.collection}'.")
            return 1
    else:
        config_path = choose_collection(find_watcher_configs())
        if not config_path:
            print("ℹ️  Watcher not started.")
            return 0

    extra_args = args.extra_args
    if extra_args and extra_args[0] == '--':
        extra_args = extra_args[1:]

    return run_watcher(config_path, args.watcher_bin, extra_args)


if __name__ == '__main__':
    raise SystemExit(main())
