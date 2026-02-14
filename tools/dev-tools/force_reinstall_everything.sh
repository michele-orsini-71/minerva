#!/usr/bin/env bash
set -e

# Force reinstall all Minerva pipx packages from source.
# Run from anywhere — paths are resolved relative to the script location.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🔄 Force reinstalling everything from: $REPO_ROOT"
echo "============================================================"
echo ""

# --- pipx install --force ---------------------------------------------------

echo "📦 minerva (core)..."
pipx install --force "$REPO_ROOT"
echo ""

echo "📦 minerva-kb..."
pipx install --force "$REPO_ROOT/tools/minerva-kb"
echo ""

echo "📦 minerva-doc..."
pipx install --force "$REPO_ROOT/tools/minerva-doc"
echo ""

echo "📦 repository-doc-extractor..."
pipx install --force "$REPO_ROOT/extractors/repository-doc-extractor"
echo ""

echo "📦 local-repo-watcher..."
pipx install --force "$REPO_ROOT/tools/local-repo-watcher"
echo ""

# --- pipx inject --force -----------------------------------------------------

echo "💉 minerva-common → minerva-kb..."
pipx inject minerva-kb "$REPO_ROOT/tools/minerva-common" --force
echo ""

echo "💉 minerva-common → minerva-doc..."
pipx inject minerva-doc "$REPO_ROOT/tools/minerva-common" --force
echo ""

echo "============================================================"
echo "✅ All packages reinstalled."
