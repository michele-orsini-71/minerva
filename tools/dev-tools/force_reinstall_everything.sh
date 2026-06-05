#!/usr/bin/env bash
set -e

# Force reinstall all Minerva pipx packages from source.
# Run from anywhere — paths are resolved relative to the script location.
#
# Usage:
#   force_reinstall_everything.sh            # frozen copies (pipx default)
#   force_reinstall_everything.sh -e         # editable (live from source)
#   force_reinstall_everything.sh --editable # same as -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

EDITABLE=""
case "${1:-}" in
    -e|--editable) EDITABLE="--editable" ;;
    "") ;;
    *) echo "Unknown option: $1 (use -e/--editable)" >&2; exit 1 ;;
esac

mode="frozen copies"
[ -n "$EDITABLE" ] && mode="editable"

echo "🔄 Force reinstalling everything ($mode) from: $REPO_ROOT"
echo "============================================================"
echo ""

# --- pipx install --force ---------------------------------------------------

echo "📦 minerva (core)..."
pipx install --force $EDITABLE "$REPO_ROOT"
echo ""

echo "📦 minerva-kb..."
pipx install --force $EDITABLE "$REPO_ROOT/tools/minerva-kb"
echo ""

echo "📦 minerva-doc..."
pipx install --force $EDITABLE "$REPO_ROOT/tools/minerva-doc"
echo ""

echo "📦 local-repo-watcher..."
pipx install --force $EDITABLE "$REPO_ROOT/tools/local-repo-watcher"
echo ""

# --- extractors --------------------------------------------------------------

echo "📦 repository-doc-extractor..."
pipx install --force $EDITABLE "$REPO_ROOT/extractors/repository-doc-extractor"
echo ""

echo "📦 bear-notes-extractor..."
pipx install --force $EDITABLE "$REPO_ROOT/extractors/bear-notes-extractor"
echo ""

echo "📦 markdown-books-extractor..."
pipx install --force $EDITABLE "$REPO_ROOT/extractors/markdown-books-extractor"
echo ""

echo "📦 zim-extractor..."
pipx install --force $EDITABLE "$REPO_ROOT/extractors/zim-extractor"
echo ""

echo "📦 github-webhook-orchestrator..."
pipx install --force $EDITABLE "$REPO_ROOT/extractors/github-webhook-orchestrator"
echo ""

# --- pipx inject --force -----------------------------------------------------

echo "💉 minerva-common → minerva-kb..."
pipx inject minerva-kb "$REPO_ROOT/tools/minerva-common" --force $EDITABLE
echo ""

echo "💉 minerva-common → minerva-doc..."
pipx inject minerva-doc "$REPO_ROOT/tools/minerva-common" --force $EDITABLE
echo ""

echo "============================================================"
echo "✅ All packages reinstalled ($mode)."
