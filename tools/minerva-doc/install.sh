#!/usr/bin/env bash
set -e

echo "🚀 Minerva Doc Installer"
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
        echo "   Make sure this script is in minerva/tools/minerva-doc/"
        exit 1
    fi

    echo "$minerva_repo"
}

# Install packages
install_packages() {
    local minerva_repo="$1"

    echo "📦 Installing Minerva packages..."
    echo ""

    # Install Minerva core (CLI application)
    echo "Installing Minerva core..."

    if [ ! -d "$minerva_repo" ]; then
        echo "❌ Minerva core not found at: $minerva_repo"
        exit 1
    fi

    if ! pipx install --force "$minerva_repo" > /dev/null 2>&1; then
        echo "❌ Failed to install Minerva core"
        exit 1
    fi

    echo "✓ Minerva core installed"
    echo ""

    # Install minerva-doc (CLI app)
    echo "Installing minerva-doc..."

    if ! pipx install --force "$minerva_repo/tools/minerva-doc" > /dev/null 2>&1; then
        echo "❌ Failed to install minerva-doc"
        exit 1
    fi

    echo "✓ minerva-doc installed"
    echo ""

    # Inject minerva-common (shared library) into minerva-doc's venv
    echo "Bundling minerva-common into minerva-doc..."

    if ! pipx inject minerva-doc "$minerva_repo/tools/minerva-common" --force > /dev/null 2>&1; then
        echo "❌ Failed to inject minerva-common"
        exit 1
    fi

    echo "✓ minerva-common bundled"
    echo ""
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
    echo "minerva-doc manages document-based knowledge bases from"
    echo "pre-extracted JSON files (Bear notes, Zim archives, books)."
    echo ""
    echo "Example workflow:"
    echo ""
    echo "  # 1. Extract documents (using Bear as example)"
    echo "  bear-extractor 'Bear Notes.bear2bk' -o notes.json"
    echo ""
    echo "  # 2. Add to minerva-doc"
    echo "  minerva-doc add notes.json --name my-notes"
    echo ""
    echo "  # 3. Start MCP server"
    echo "  minerva-doc serve"
    echo ""
    echo "What happens during 'minerva-doc add':"
    echo "  1. Validates JSON document format"
    echo "  2. Prompts you to select an AI provider:"
    echo "     - OpenAI (cloud, requires API key)"
    echo "     - Google Gemini (cloud, requires API key)"
    echo "     - Ollama (local, free)"
    echo "     - LM Studio (local, free)"
    echo "  3. Generates AI-powered collection description"
    echo "  4. Creates searchable embeddings and indexes them"
    echo "  5. Saves configuration for management"
    echo ""
    echo "Time to first collection: <2 minutes"
    echo "Time to add more collections: <1 minute each"
    echo ""
    echo "Common commands:"
    echo "  minerva-doc list              # Show all collections"
    echo "  minerva-doc status <name>     # Check collection details"
    echo "  minerva-doc update <name> <file>  # Re-index with new data"
    echo "  minerva-doc remove <name>     # Delete collection"
    echo "  minerva-doc serve             # Start MCP server"
    echo ""
    echo "For detailed instructions:"
    echo "  - Quick start: tools/minerva-doc/README.md"
    echo "  - Extractor guide: docs/EXTRACTOR_GUIDE.md"
    echo ""
    echo "Available extractors (install separately):"
    echo "  - bear-extractor (Bear notes)"
    echo "  - zim-extractor (Zim archives)"
    echo "  - markdown-books-extractor (Markdown books)"
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
