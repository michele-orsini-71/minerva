#!/usr/bin/env bash
set -e

echo "🚀 Minerva KB Installer"
echo "============================================================"
echo ""

# Check Python version
check_python() {
    echo "Checking prerequisites..."

    if ! command -v python3 &> /dev/null; then
        echo "❌ python3 not found"
        echo ""
        echo "Please install Python 3.10 or higher"
        exit 1
    fi

    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    python_major=$(python3 -c 'import sys; print(sys.version_info.major)')
    python_minor=$(python3 -c 'import sys; print(sys.version_info.minor)')

    if [ "$python_major" -lt 3 ] || { [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 10 ]; }; then
        echo "❌ Python $python_version found, but 3.10+ required"
        echo ""
        echo "Please upgrade Python to version 3.10 or higher"
        exit 1
    fi

    echo "✓ Python $python_version found"
}

# Check pipx
check_pipx() {
    if ! command -v pipx &> /dev/null; then
        echo "❌ pipx not found"
        echo ""
        echo "Install pipx first:"
        echo "  python3 -m pip install --user pipx"
        echo "  python3 -m pipx ensurepath"
        echo ""
        exit 1
    fi

    echo "✓ pipx found"
    echo ""
}

# Get minerva repository path
get_repo_path() {
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    minerva_repo="$(cd "$script_dir/../.." && pwd)"

    if [ ! -f "$minerva_repo/setup.py" ]; then
        echo "❌ Cannot find minerva setup.py at: $minerva_repo/setup.py"
        echo "   Make sure this script is in minerva/tools/minerva-kb/"
        exit 1
    fi

    echo "$minerva_repo"
}

# Install packages
install_packages() {
    local minerva_repo="$1"

    echo "📦 Installing Minerva packages..."
    echo ""

    packages=(
        "Minerva core:$minerva_repo"
        "repository-doc-extractor:$minerva_repo/extractors/repository-doc-extractor"
        "local-repo-watcher:$minerva_repo/tools/local-repo-watcher"
        "minerva-kb:$minerva_repo/tools/minerva-kb"
    )

    for pkg in "${packages[@]}"; do
        name="${pkg%%:*}"
        path="${pkg##*:}"

        echo "Installing $name..."

        if [ ! -d "$path" ]; then
            echo "❌ Package not found at: $path"
            exit 1
        fi

        if ! pipx install --force "$path" > /dev/null 2>&1; then
            echo "❌ Failed to install $name"
            exit 1
        fi

        echo "✓ $name installed"
        echo ""
    done
}

# Show completion message
show_completion() {
    echo ""
    echo "============================================================"
    echo "✅ Installation complete!"
    echo "============================================================"
    echo ""
    echo "Next step: Create your first collection"
    echo "------------------------------------------------------------"
    echo ""
    echo "Run the following command to add a repository:"
    echo ""
    echo "  minerva-kb add /path/to/your/repository"
    echo ""
    echo "What happens during 'minerva-kb add':"
    echo "  1. Generates optimized description from your README"
    echo "  2. Prompts you to select an AI provider:"
    echo "     - OpenAI (cloud, requires API key)"
    echo "     - Google Gemini (cloud, requires API key)"
    echo "     - Ollama (local, free)"
    echo "     - LM Studio (local, free)"
    echo "  3. Extracts documentation from your repository"
    echo "  4. Creates searchable embeddings and indexes them"
    echo "  5. Creates configuration files for management"
    echo ""
    echo "Time to first collection: ~5 minutes"
    echo "Time to second collection: <2 minutes"
    echo ""
    echo "For detailed instructions and examples:"
    echo "  - Quick start: tools/minerva-kb/README.md"
    echo "  - Complete guide: docs/MINERVA_KB_GUIDE.md"
    echo "  - Example workflows: docs/MINERVA_KB_EXAMPLES.md"
    echo ""
    echo "Common commands:"
    echo "  minerva-kb list              # Show all collections"
    echo "  minerva-kb status <name>     # Check collection status"
    echo "  minerva-kb watch <name>      # Start auto-update watcher"
    echo "  minerva-kb sync <name>       # Manually re-index"
    echo "  minerva-kb remove <name>     # Delete collection"
    echo ""
}

# Main execution
main() {
    check_python
    check_pipx

    minerva_repo=$(get_repo_path)

    install_packages "$minerva_repo"

    show_completion
}

# Handle Ctrl+C
trap 'echo ""; echo "Installation cancelled by user"; exit 130' INT

main
