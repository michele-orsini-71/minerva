#!/usr/bin/env bash
set -e

echo "🗑️  Minerva KB Uninstaller"
echo "============================================================"
echo ""

# Uninstall packages
echo "Removing installed packages..."
echo ""

# Remove minerva-kb (this also removes injected minerva-common)
if pipx list | grep -q "minerva-kb"; then
    echo "Uninstalling minerva-kb..."
    pipx uninstall minerva-kb
    echo "✓ minerva-kb removed (including bundled minerva-common)"
else
    echo "⚠ minerva-kb not found (already uninstalled)"
fi

echo ""

# Note: We don't uninstall shared dependencies (minerva, repository-doc-extractor, local-repo-watcher)
# Reasons:
#   - minerva might be used by other tools or installed standalone by user
#   - Avoids complexity of tracking which tool installed what
#   - User can manually remove with: pipx uninstall <package>
echo "Note: Shared dependencies not removed:"
echo "  - minerva (may be used by other tools or standalone)"
echo "  - repository-doc-extractor"
echo "  - local-repo-watcher"
echo ""
echo "To remove them manually:"
echo "  pipx uninstall minerva"
echo "  pipx uninstall repository-doc-extractor"
echo "  pipx uninstall local-repo-watcher"

echo ""
echo "============================================================"
echo "✅ Uninstallation complete!"
echo "============================================================"
echo ""
echo "Note: Your data remains intact at ~/.minerva/"
echo ""
echo "To completely remove all data:"
echo "  rm -rf ~/.minerva/apps/minerva-kb"
echo ""
echo "To remove shared ChromaDB (affects all minerva tools):"
echo "  rm -rf ~/.minerva/chromadb"
echo ""
echo "To remove everything:"
echo "  rm -rf ~/.minerva"
echo ""
