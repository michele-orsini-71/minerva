#!/usr/bin/env bash
set -e

echo "🗑️  Minerva Doc Uninstaller"
echo "============================================================"
echo ""

# Uninstall packages
echo "Removing installed packages..."
echo ""

# Remove minerva-doc (this also removes injected minerva-common)
if pipx list | grep -q "minerva-doc"; then
    echo "Uninstalling minerva-doc..."
    pipx uninstall minerva-doc
    echo "✓ minerva-doc removed (including bundled minerva-common)"
else
    echo "⚠ minerva-doc not found (already uninstalled)"
fi

echo ""

# Note: We don't uninstall minerva (shared dependency)
# Reasons:
#   - minerva might be used by other tools (e.g., minerva-kb)
#   - User might have installed it standalone
#   - Avoids complexity of tracking dependencies across tools
echo "Note: minerva not removed (may be used by other tools or standalone)"
echo ""
echo "To remove minerva manually:"
echo "  pipx uninstall minerva"

echo ""
echo "============================================================"
echo "✅ Uninstallation complete!"
echo "============================================================"
echo ""
echo "Note: Your data remains intact at ~/.minerva/"
echo ""
echo "To completely remove all data:"
echo "  rm -rf ~/.minerva/apps/minerva-doc"
echo ""
echo "To remove shared ChromaDB (affects all minerva tools):"
echo "  rm -rf ~/.minerva/chromadb"
echo ""
echo "To remove everything:"
echo "  rm -rf ~/.minerva"
echo ""
