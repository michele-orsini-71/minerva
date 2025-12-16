#!/usr/bin/env bash
set -e

echo "🏗️  Building minerva-kb.pyz"
echo "============================================================"
echo ""

# Get minerva repository path
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
minerva_repo="$(cd "$script_dir/../.." && pwd)"

echo "📦 Step 1: Building wheels..."
cd "$minerva_repo/tools/minerva-common"
python -m build --wheel > /dev/null 2>&1
echo "✓ minerva-common wheel built"

cd "$minerva_repo/tools/minerva-kb"
python -m build --wheel > /dev/null 2>&1
echo "✓ minerva-kb wheel built"

echo ""
echo "📦 Step 2: Bundling with Shiv..."
cd "$minerva_repo"

shiv -c minerva-kb -o minerva-kb.pyz \
  tools/minerva-common/dist/minerva_common-1.0.0-py3-none-any.whl \
  tools/minerva-kb/dist/minerva_kb-1.0.0-py3-none-any.whl

echo ""
echo "============================================================"
echo "✅ Build complete!"
echo "============================================================"
echo ""
echo "Output: $minerva_repo/minerva-kb.pyz"
echo "Size: $(du -h "$minerva_repo/minerva-kb.pyz" | cut -f1)"
echo ""
echo "Test it:"
echo "  ./minerva-kb.pyz --version"
echo "  ./minerva-kb.pyz list"
echo ""
echo "Share it:"
echo "  Send the .pyz file to anyone with Python 3.10+"
echo "  They can run it directly: ./minerva-kb.pyz add /path/to/repo"
echo ""
