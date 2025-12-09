#!/usr/bin/env python3
"""
Minerva Setup Wizard
Interactive setup for personal local knowledge base deployment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def main():
    print("🚀 Minerva Setup Wizard")
    print("=" * 60)
    print()

    if not check_prerequisites():
        sys.exit(1)

    minerva_repo = get_minerva_repo_path()

    if not install_packages(minerva_repo):
        sys.exit(1)

    show_completion_message()


def check_prerequisites() -> bool:
    print("Checking prerequisites...")

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    if sys.version_info < (3, 10):
        print(f"❌ Python {python_version} found, but 3.10+ required")
        print()
        print("Please upgrade Python to version 3.10 or higher")
        return False

    print(f"✓ Python {python_version} found")

    if not shutil.which('pipx'):
        print("❌ pipx not found")
        print()
        print("Install pipx first:")
        print("  python -m pip install --user pipx")
        print("  python -m pipx ensurepath")
        print()
        return False

    print("✓ pipx found")
    print()
    return True


def get_minerva_repo_path() -> Path:
    script_dir = Path(__file__).parent.resolve()
    minerva_repo = script_dir.parent.parent

    if not (minerva_repo / 'setup.py').exists():
        print(f"❌ Cannot find minerva setup.py at: {minerva_repo / 'setup.py'}")
        print("   Make sure this script is in minerva/apps/local-repo-kb/")
        sys.exit(1)

    return minerva_repo


def install_packages(minerva_repo: Path) -> bool:
    print("📦 Installing Minerva packages...")
    print()

    packages = [
        ("Minerva core", str(minerva_repo)),
        ("repository-doc-extractor", str(minerva_repo / "extractors" / "repository-doc-extractor")),
        ("local-repo-watcher", str(minerva_repo / "tools" / "local-repo-watcher")),
        ("minerva-kb", str(minerva_repo / "tools" / "minerva-kb")),
    ]

    for name, path in packages:
        print(f"Installing {name}...")

        if not Path(path).exists():
            print(f"❌ Package not found at: {path}")
            return False

        result = subprocess.run(
            ["pipx", "install", "--force", path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Failed to install {name}")
            print(result.stderr)
            return False

        print(f"✓ {name} installed")
        print()

    return True


def show_completion_message():
    print()
    print("=" * 60)
    print("✅ Installation complete!")
    print("=" * 60)
    print()
    print("Next step: Create your first collection")
    print("-" * 60)
    print()
    print("Run the following command to add a repository:")
    print()
    print("  minerva-kb add /path/to/your/repository")
    print()
    print("What happens during 'minerva-kb add':")
    print("  1. Generates optimized description from your README")
    print("  2. Prompts you to select an AI provider:")
    print("     - OpenAI (cloud, requires API key)")
    print("     - Google Gemini (cloud, requires API key)")
    print("     - Ollama (local, free)")
    print("     - LM Studio (local, free)")
    print("  3. Extracts documentation from your repository")
    print("  4. Creates searchable embeddings and indexes them")
    print("  5. Creates configuration files for management")
    print()
    print("Time to first collection: ~5 minutes")
    print("Time to second collection: <2 minutes")
    print()
    print("For detailed instructions and examples:")
    print("  - Quick start: tools/minerva-kb/README.md")
    print("  - Complete guide: docs/MINERVA_KB_GUIDE.md")
    print("  - Example workflows: docs/MINERVA_KB_EXAMPLES.md")
    print()
    print("Common commands:")
    print("  minerva-kb list              # Show all collections")
    print("  minerva-kb status <name>     # Check collection status")
    print("  minerva-kb watch <name>      # Start auto-update watcher")
    print("  minerva-kb sync <name>       # Manually re-index")
    print("  minerva-kb remove <name>     # Delete collection")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("Setup cancelled by user")
        sys.exit(130)
