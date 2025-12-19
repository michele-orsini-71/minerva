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

# Get version from source package
get_source_version() {
    local pkg_path="$1"
    local version=""

    # Try pyproject.toml first (for minerva-kb, minerva-doc)
    if [ -f "$pkg_path/pyproject.toml" ]; then
        version=$(grep -E "^version\s*=" "$pkg_path/pyproject.toml" | sed 's/.*"\(.*\)".*/\1/' | head -1)
    fi

    # Try __init__.py (handle both hyphens and underscores in package names)
    if [ -z "$version" ] && [ -f "$pkg_path/setup.py" ]; then
        local pkg_name=$(basename "$pkg_path")
        local pkg_name_underscore="${pkg_name//-/_}"  # Replace hyphens with underscores

        # Try with hyphens first, then underscores
        if [ -f "$pkg_path/$pkg_name/__init__.py" ]; then
            version=$(grep -E "^__version__" "$pkg_path/$pkg_name/__init__.py" | sed 's/.*"\(.*\)".*/\1/' | head -1)
        elif [ -f "$pkg_path/$pkg_name_underscore/__init__.py" ]; then
            version=$(grep -E "^__version__" "$pkg_path/$pkg_name_underscore/__init__.py" | sed 's/.*"\(.*\)".*/\1/' | head -1)
        fi
    fi

    # Try setup.py directly as fallback (less reliable for dynamic versions)
    if [ -z "$version" ] && [ -f "$pkg_path/setup.py" ]; then
        version=$(grep -E "^\s*version\s*=" "$pkg_path/setup.py" | sed 's/.*"\(.*\)".*/\1/' | head -1)
    fi

    echo "$version"
}

# Get installed version from pipx
get_installed_version() {
    local pkg_name="$1"
    local version=""

    if command -v jq &> /dev/null; then
        # Use jq if available (more reliable)
        version=$(pipx list --json 2>/dev/null | jq -r ".venvs[\"$pkg_name\"].metadata.main_package.package_version // empty" 2>/dev/null)
    else
        # Fallback to text parsing
        version=$(pipx list 2>/dev/null | grep -A 5 "package $pkg_name " | grep "version" | sed 's/.*version \(.*\),.*/\1/' | xargs)
    fi

    echo "$version"
}

# Check if package is installed
is_installed() {
    local pkg_name="$1"
    pipx list 2>/dev/null | grep -q "package $pkg_name "
}

# Smart install: only reinstall if version changed
smart_install() {
    local display_name="$1"
    local pkg_name="$2"
    local install_path="$3"
    local force="${4:-false}"

    local source_version=$(get_source_version "$install_path")

    if [ -z "$source_version" ]; then
        echo "⚠️  Cannot determine version for $display_name, installing anyway..."
        if ! pipx install --force "$install_path" > /dev/null 2>&1; then
            echo "❌ Failed to install $display_name"
            exit 1
        fi
        echo "✓ $display_name installed"
        echo ""
        return 0
    fi

    if is_installed "$pkg_name"; then
        local installed_version=$(get_installed_version "$pkg_name")

        if [ "$installed_version" = "$source_version" ] && [ "$force" = "false" ]; then
            echo "✓ $display_name v$installed_version already installed (skipping)"
            echo ""
            return 0
        fi

        if [ "$installed_version" != "$source_version" ]; then
            echo "⟳ $display_name: upgrading $installed_version → $source_version..."
        else
            echo "⟳ $display_name: reinstalling v$source_version..."
        fi

        if ! pipx install --force "$install_path" > /dev/null 2>&1; then
            echo "❌ Failed to install $display_name"
            exit 1
        fi
        echo "✓ $display_name v$source_version installed"
        echo ""
    else
        echo "Installing $display_name v$source_version..."
        if ! pipx install "$install_path" > /dev/null 2>&1; then
            echo "❌ Failed to install $display_name"
            exit 1
        fi
        echo "✓ $display_name v$source_version installed"
        echo ""
    fi
}

# Get version of injected package
get_injected_version() {
    local main_pkg="$1"
    local injected_pkg="$2"
    local version=""

    if command -v jq &> /dev/null; then
        version=$(pipx list --json 2>/dev/null | jq -r ".venvs[\"$main_pkg\"].metadata.injected_packages[\"$injected_pkg\"].package_version // empty" 2>/dev/null)
    fi

    echo "$version"
}

# Smart inject: only inject if needed
smart_inject() {
    local main_pkg="$1"
    local inject_pkg_name="$2"
    local inject_pkg_path="$3"
    local force="${4:-false}"

    local source_version=$(get_source_version "$inject_pkg_path")
    local injected_version=$(get_injected_version "$main_pkg" "$inject_pkg_name")

    if [ -n "$injected_version" ] && [ "$injected_version" = "$source_version" ] && [ "$force" = "false" ]; then
        echo "✓ $inject_pkg_name v$injected_version already bundled (skipping)"
        echo ""
        return 0
    fi

    if [ -n "$injected_version" ] && [ "$injected_version" != "$source_version" ]; then
        echo "⟳ $inject_pkg_name: upgrading $injected_version → $source_version..."
    else
        echo "Bundling $inject_pkg_name into $main_pkg..."
    fi

    if ! pipx inject "$main_pkg" "$inject_pkg_path" --force > /dev/null 2>&1; then
        echo "❌ Failed to inject $inject_pkg_name"
        exit 1
    fi

    echo "✓ $inject_pkg_name v$source_version bundled"
    echo ""
}

# Install packages
install_packages() {
    local minerva_repo="$1"
    local force="${2:-false}"

    echo "📦 Installing Minerva packages..."
    echo ""

    # Install minerva as standalone CLI tool
    smart_install "Minerva core" "minerva" "$minerva_repo" "$force"

    # Install minerva-doc (main tool)
    smart_install "minerva-doc" "minerva-doc" "$minerva_repo/tools/minerva-doc" "$force"

    # Inject minerva-common shared library
    smart_inject "minerva-doc" "minerva-common" "$minerva_repo/tools/minerva-common" "$force"
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
    local force="false"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force="true"
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [--force]"
                echo ""
                echo "Options:"
                echo "  --force    Force reinstall even if versions match"
                echo "  --help     Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    check_python
    check_pipx

    minerva_repo=$(get_repo_path)

    install_packages "$minerva_repo" "$force"

    show_completion
}

# Handle Ctrl+C
trap 'echo ""; echo "Installation cancelled by user"; exit 130' INT

main "$@"
