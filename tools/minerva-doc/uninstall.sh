#!/usr/bin/env bash
set -e

echo "🗑️  Minerva Doc Uninstaller"
echo "============================================================"
echo ""

# Uninstall packages
echo "Removing installed packages..."
echo ""

# Check if minerva-doc is installed
if pipx list | grep -q "minerva-doc"; then
    echo "Uninstalling minerva-doc..."
    pipx uninstall minerva-doc
    echo "✓ minerva-doc removed (including bundled minerva-common)"
else
    echo "⚠ minerva-doc not found (already uninstalled)"
fi

echo ""

# Check if minerva core is installed
if pipx list | grep -q "^   package minerva "; then
    echo "Uninstalling Minerva core..."
    pipx uninstall minerva
    echo "✓ Minerva core removed"
else
    echo "⚠ Minerva core not found (already uninstalled)"
fi

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
