#!/usr/bin/env bash
#
# Set a single shared version across every Minerva package.
#
# Each package declares its version once, as __version__ in its package
# __init__.py. The package's setup.py / pyproject.toml reads that value at
# build time, so the __init__.py is the single source of truth per package.
# This script keeps all of those declarations in lockstep, so the whole repo
# moves to one version with a single command.
#
# Usage:
#   scripts/bump-version.sh 3.1.0
#
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>   (e.g. $0 3.1.0)" >&2
    exit 1
fi

new_version="$1"

# Accept a semantic version, optionally with a pre-release/build suffix
# (e.g. 3.1.0, 3.1.0rc1, 3.1.0.dev1).
if ! printf '%s' "$new_version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+([.-]?[0-9A-Za-z.]+)?$'; then
    echo "Error: '$new_version' does not look like a version (expected X.Y.Z)" >&2
    exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# Discover every tracked package __init__.py that declares __version__.
# git ls-files keeps build/, dist/, *.egg-info/ and .venv out automatically,
# since those are git-ignored. Test scaffolding __init__.py files have no
# __version__ line and are skipped.
count=0
while IFS= read -r f; do
    [ -z "$f" ] && continue
    perl -i -pe 'BEGIN{$v=shift} s/^(__version__\s*=\s*")[^"]*(")/${1}${v}${2}/' \
        "$new_version" "$f"
    printf '  updated %s\n' "$f"
    count=$((count + 1))
done < <(git ls-files '*__init__.py' | while IFS= read -r f; do
    grep -qE '^__version__[[:space:]]*=' "$f" && printf '%s\n' "$f"
done)

if [ "$count" -eq 0 ]; then
    echo "Error: no versioned __init__.py files found" >&2
    exit 1
fi

echo "Set version to $new_version across $count package(s)."
echo "Verify with: pytest tests/test_version_consistency.py"
