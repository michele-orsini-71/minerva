#!/usr/bin/env python3
"""
Minerva Setup Wizard
Interactive setup for personal local knowledge base deployment
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


def main():
    print("🚀 Minerva Setup Wizard")
    print("=" * 60)
    print()

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Install/upgrade Minerva
    minerva_repo = get_minerva_repo_path()
    if not check_and_install_minerva(minerva_repo):
        sys.exit(1)

    # Select AI provider
    provider_config = select_ai_provider()

    # Store API key if needed
    if provider_config.get('needs_api_key'):
        if not store_api_key(provider_config):
            sys.exit(1)

    # Select repository to index
    repo_path = select_repository()

    # Generate collection name
    collection_name = generate_collection_name(repo_path)

    # Generate collection description using AI
    description = generate_description(
        repo_path=repo_path,
        collection_name=collection_name,
        provider_config=provider_config
    )

    # Create directory structure and config files
    create_configs(
        collection_name=collection_name,
        description=description,
        repo_path=repo_path,
        provider_config=provider_config
    )

    # Extract and index
    extract_and_index(
        collection_name=collection_name,
        repo_path=repo_path,
        provider_config=provider_config
    )

    # Show completion summary
    show_completion_summary(
        collection_name=collection_name,
        repo_path=repo_path,
        provider_config=provider_config
    )


def check_prerequisites() -> bool:
    """Check that Python and pipx are installed."""
    print("Checking prerequisites...")

    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"✓ Python {python_version} found")

    # Check pipx
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
    """Get the minerva repository root path."""
    # Script is in apps/local-repo-kb/
    script_dir = Path(__file__).parent.resolve()
    minerva_repo = script_dir.parent.parent

    if not (minerva_repo / 'setup.py').exists():
        print(f"❌ Cannot find minerva setup.py at: {minerva_repo / 'setup.py'}")
        print("   Make sure this script is in minerva/apps/local-repo-kb/")
        sys.exit(1)

    return minerva_repo


def check_and_install_minerva(minerva_repo: Path) -> bool:
    """Check if minerva is installed and install/upgrade if needed."""
    print("📦 Checking Minerva installation...")
    print()

    # Get repository version
    init_file = minerva_repo / 'minerva' / '__init__.py'
    repo_version = None
    for line in init_file.read_text().splitlines():
        if line.startswith('__version__'):
            repo_version = line.split('"')[1]
            break

    if not repo_version:
        print("❌ Could not determine repository version")
        return False

    # Check if minerva is installed
    try:
        result = subprocess.run(
            ['pipx', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        minerva_installed = 'minerva' in result.stdout
    except subprocess.CalledProcessError:
        minerva_installed = False

    if minerva_installed:
        # Get installed version
        try:
            result = subprocess.run(
                ['pipx', 'runpip', 'minerva', 'show', 'minerva'],
                capture_output=True,
                text=True,
                check=True
            )
            installed_version = None
            for line in result.stdout.splitlines():
                if line.startswith('Version:'):
                    installed_version = line.split()[1]
                    break

            if installed_version == repo_version:
                print(f"✓ Minerva v{installed_version} is already installed (up to date)")
                print()
                return True
            else:
                print(f"⚠️  Version mismatch detected:")
                print(f"   Installed: v{installed_version}")
                print(f"   Repository: v{repo_version}")
                print()
                upgrade = input(f"Upgrade to v{repo_version}? [Y/n]: ").strip().lower()

                if upgrade not in ['n', 'no']:
                    print()
                    print("Upgrading Minerva...")
                    subprocess.run(['pipx', 'uninstall', 'minerva'], check=True)
                    subprocess.run(['pipx', 'install', str(minerva_repo)], check=True)
                    print(f"✓ Minerva v{repo_version} installed")
                    print()
                else:
                    print(f"ℹ️  Continuing with v{installed_version}")
                    print()

                return True
        except subprocess.CalledProcessError:
            print("⚠️  Could not determine installed version, reinstalling...")
            subprocess.run(['pipx', 'uninstall', 'minerva'], check=True)
            subprocess.run(['pipx', 'install', str(minerva_repo)], check=True)
            print(f"✓ Minerva v{repo_version} installed")
            print()
            return True
    else:
        print(f"Minerva not found. Installing v{repo_version}...")
        print()
        try:
            subprocess.run(['pipx', 'install', str(minerva_repo)], check=True)
            print(f"✓ Minerva v{repo_version} installed")
            print()
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Minerva: {e}")
            return False


def select_ai_provider() -> Dict[str, Any]:
    """Interactive AI provider selection."""
    print("🤖 AI Provider Selection")
    print("=" * 60)
    print()
    print("Which AI provider do you want to use?")
    print()
    print("  1. OpenAI (cloud, requires API key)")
    print("     • Embedding: text-embedding-3-small")
    print("     • LLM: gpt-4o-mini")
    print()
    print("  2. Google Gemini (cloud, requires API key)")
    print("     • Embedding: text-embedding-004")
    print("     • LLM: gemini-1.5-flash")
    print()
    print("  3. Ollama (local, free, no API key)")
    print("     • You specify which models you've pulled")
    print()
    print("  4. LM Studio (local, free, no API key)")
    print("     • You specify which models you've loaded")
    print()

    while True:
        choice = input("Choice [1-4]: ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")

    print()

    if choice == '1':
        return {
            'provider_type': 'openai',
            'provider_name': 'OpenAI',
            'env_var_name': 'OPENAI_API_KEY',
            'keychain_name': 'openai',
            'needs_api_key': True,
            'embedding_model': 'text-embedding-3-small',
            'llm_model': 'gpt-4o-mini'
        }
    elif choice == '2':
        return {
            'provider_type': 'gemini',
            'provider_name': 'Google Gemini',
            'env_var_name': 'GEMINI_API_KEY',
            'keychain_name': 'gemini',
            'needs_api_key': True,
            'embedding_model': 'text-embedding-004',
            'llm_model': 'gemini-1.5-flash'
        }
    elif choice == '3':
        print("✓ Selected: Ollama (local)")
        print()
        print("📝 Ollama Model Configuration")
        print("-" * 60)
        print("Make sure you've pulled an LLM (e.g. llama3.1:8b) and an embedding model (e.g. mxbai-embed-large) first")
        print()

        embed_model = input("Embedding model (mxbai-embed-large:latest): ").strip()
        embed_model = embed_model or 'mxbai-embed-large:latest'

        llm_model = input("LLM model (llama3.1:8b): ").strip()
        llm_model = llm_model or 'llama3.1:8b'

        return {
            'provider_type': 'ollama',
            'provider_name': 'Ollama',
            'needs_api_key': False,
            'base_url': 'http://localhost:11434',
            'embedding_model': embed_model,
            'llm_model': llm_model
        }
    else:  # choice == '4'
        print("✓ Selected: LM Studio (local)")
        print()
        print("📝 LM Studio Model Configuration")
        print("-" * 60)
        print("⚠️  Make sure your models are loaded in LM Studio first!")
        print()

        embed_model = input("Embedding model name: ").strip()
        if not embed_model:
            print("❌ Embedding model cannot be empty")
            sys.exit(1)

        llm_model = input("LLM model name: ").strip()
        if not llm_model:
            print("❌ LLM model cannot be empty")
            sys.exit(1)

        return {
            'provider_type': 'lmstudio',
            'provider_name': 'LM Studio',
            'needs_api_key': False,
            'base_url': 'http://localhost:1234/v1',
            'embedding_model': embed_model,
            'llm_model': llm_model
        }


def store_api_key(provider_config: Dict[str, Any]) -> bool:
    """Store API key in OS keychain."""
    print()
    print("🔑 API Key Configuration")
    print("=" * 60)
    print()
    print(f"Your {provider_config['provider_name']} API key will be stored securely in OS keychain")
    print("  • macOS: Keychain Access (encrypted)")
    print("  • Linux: Secret Service (encrypted)")
    print("  • Windows: Credential Manager (encrypted)")
    print()
    print(f"The key will be stored as: '{provider_config['keychain_name']}'")
    print(f"Config files will reference: ${{{provider_config['env_var_name']}}}")
    print()

    # Check if key already exists
    try:
        result = subprocess.run(
            ['minerva', 'keychain', 'get', provider_config['keychain_name']],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"⚠️  An API key for {provider_config['keychain_name']} already exists in keychain")
            update = input("Update it? [y/N]: ").strip().lower()
            if update in ['y', 'yes']:
                subprocess.run(['minerva', 'keychain', 'set', provider_config['keychain_name']], check=True)
            else:
                print("ℹ️  Keeping existing key")
        else:
            subprocess.run(['minerva', 'keychain', 'set', provider_config['keychain_name']], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to store API key: {e}")
        return False

    print()
    return True


def select_repository() -> Path:
    """Interactive repository selection."""
    print("📁 Repository to Index")
    print("=" * 60)
    print()

    while True:
        repo_path_str = input("Path to repository: ").strip()
        if not repo_path_str:
            print("❌ Path cannot be empty")
            continue

        # Expand ~ to home directory
        repo_path = Path(repo_path_str).expanduser().resolve()

        if not repo_path.is_dir():
            print(f"❌ Directory not found: {repo_path}")
            continue

        print(f"✓ Repository found: {repo_path}")
        print()
        return repo_path


def generate_collection_name(repo_path: Path) -> str:
    """Generate and validate collection name."""
    print("📚 Collection Name")
    print("=" * 60)
    print()
    print("The collection name is used to identify this knowledge base.")
    print("It should be unique and descriptive (e.g., 'my-project', 'work-docs').")
    print()
    print("Requirements:")
    print("  • 3-512 characters")
    print("  • Letters, numbers, dots, underscores, hyphens only")
    print("  • Must start and end with a letter or number")
    print()

    # Default: sanitized repo folder name
    default_name = repo_path.name.lower().replace(' ', '-').replace('_', '-')
    # Keep only alphanumeric and hyphens
    default_name = ''.join(c for c in default_name if c.isalnum() or c == '-')
    # Ensure it meets minimum length
    if len(default_name) < 3:
        default_name = f"{default_name}-kb"

    while True:
        collection_name = input(f"Collection name ({default_name}): ").strip()
        collection_name = collection_name or default_name

        # Sanitize
        collection_name = collection_name.lower().replace(' ', '-')
        collection_name = ''.join(c for c in collection_name if c.isalnum() or c in '-_.')

        # Validate ChromaDB requirements
        if len(collection_name) < 3:
            print(f"❌ Name too short: '{collection_name}' (minimum 3 characters)")
            print()
            continue

        if len(collection_name) > 512:
            print(f"❌ Name too long: {len(collection_name)} characters (maximum 512)")
            print()
            continue

        if not collection_name[0].isalnum():
            print(f"❌ Name must start with a letter or number: '{collection_name}'")
            print()
            continue

        if not collection_name[-1].isalnum():
            print(f"❌ Name must end with a letter or number: '{collection_name}'")
            print()
            continue

        print(f"✓ Collection: {collection_name}")
        print()
        return collection_name


def generate_description(
    repo_path: Path,
    collection_name: str,
    provider_config: Dict[str, Any]
) -> str:
    """Generate optimized collection description using AI."""
    print("💬 Collection Description")
    print("=" * 60)
    print()
    print("This description helps Claude understand what information is in this collection.")
    print("A good description improves search quality and indexing validation.")
    print()

    # Check for README
    readme_path = repo_path / 'README.md'

    if readme_path.exists():
        print("📄 Found README.md in repository")
        print("🤖 Using AI to generate optimized description from README...")
        print()

        # Read README (first 3000 chars)
        readme_content = readme_path.read_text(encoding='utf-8')[:3000]
        input_type = "README"
        input_content = readme_content
    else:
        print("ℹ️  No README.md found in repository")
        print()
        print("Please describe what's in this repository so AI can generate an optimized description.")
        print("Examples:")
        print("  • 'Python web framework with REST API and documentation'")
        print("  • 'React component library for building dashboards'")
        print("  • 'Internal documentation for infrastructure setup'")
        print()

        user_desc = input("Brief description: ").strip()
        if not user_desc:
            print("❌ Description cannot be empty")
            sys.exit(1)

        input_type = "USER"
        input_content = user_desc

    # Generate description using AI
    try:
        description = call_ai_for_description(
            input_content=input_content,
            input_type=input_type,
            collection_name=collection_name,
            provider_config=provider_config
        )

        print()
        print("✨ Generated description:")
        print(f"   {description}")
        print()
        print("✓ Description ready")
        print()

        return description

    except Exception as e:
        print()
        print(f"❌ Failed to generate description: {e}")
        print()
        print("Common causes:")
        print("  • Ollama: Service not running (run 'ollama serve')")
        print("  • LM Studio: App not started or models not loaded")
        print(f"  • {provider_config['provider_name']}: API key not stored")
        print("  • Provider: Connection timeout or rate limit")
        print()
        sys.exit(1)


def call_ai_for_description(
    input_content: str,
    input_type: str,
    collection_name: str,
    provider_config: Dict[str, Any]
) -> str:
    """Call AI provider to generate description."""
    # Import minerva modules - add repo to path since pipx isolates packages
    minerva_repo = get_minerva_repo_path()
    if str(minerva_repo) not in sys.path:
        sys.path.insert(0, str(minerva_repo))

    try:
        from minerva.common.ai_config import AIProviderConfig
        from minerva.common.ai_provider import AIProvider
    except ImportError as e:
        raise Exception(
            f"Could not import minerva modules: {e}\n"
            f"Make sure minerva dependencies are installed.\n"
            f"Try: cd {minerva_repo} && pip install -e ."
        )

    # Build provider config
    config_dict = {
        "provider_type": provider_config['provider_type'],
        "embedding_model": provider_config['embedding_model'],
        "llm_model": provider_config['llm_model']
    }

    # Add provider-specific fields
    if provider_config['needs_api_key']:
        config_dict["api_key"] = f"${{{provider_config['env_var_name']}}}"
    else:
        config_dict["base_url"] = provider_config['base_url']

    # Create AI provider
    config = AIProviderConfig(**config_dict)
    provider = AIProvider(config)

    # Craft prompt
    context_label = "README Content (excerpt)" if input_type == "README" else "User Description"

    prompt = f"""You are creating a description for a semantic search knowledge base collection.

Repository Name: {collection_name}

{context_label}:
{input_content}

Generate a concise, informative description (2-3 sentences, max 250 chars) for this collection that:
1. CLARITY: Clearly states what content is in this collection
2. SPECIFICITY: Describes the specific domain, technology, or topic area
3. USEFULNESS: Helps users understand what they can search for

The description MUST have two parts:
1. First sentence: Type of content + Primary technology/domain + Purpose
2. Second sentence: Start with "Best for questions about" and list 5-7 specific use cases

You should include a mix of these generic use cases (pick 3-4 that fit):
- code architecture / system design
- component interactions / module integration
- API design / interface contracts
- implementation details / feature development
- design patterns / coding practices
- testing strategies / test coverage
- refactoring approaches / code optimization
- configuration / setup procedures
- debugging / troubleshooting
- deployment / CI/CD workflows

Plus 2-3 domain-specific use cases based on the technology.

Format: "[Content type and technology description]. Best for questions about [generic use case 1], [generic use case 2], [domain-specific use case 1], [domain-specific use case 2], and [generic/specific use case 3]."

Example descriptions:
- "Python RAG system with vector search, embeddings, and MCP server integration for personal knowledge management. Best for questions about code architecture, component interactions, testing strategies, API design, indexing strategies, search implementation, and refactoring approaches."
- "React component library with TypeScript, Storybook documentation, and accessibility features for building enterprise dashboards. Best for questions about component interactions, UI patterns, testing strategies, design patterns, component APIs, integration examples, and debugging approaches."
- "PostgreSQL database administration guides covering installation, configuration, performance tuning, and backup procedures. Best for questions about setup procedures, configuration options, performance optimization, testing strategies, troubleshooting issues, backup strategies, and deployment workflows."

Output ONLY the description text, nothing else. Be direct and informative."""

    messages = [{"role": "user", "content": prompt}]
    response = provider.chat_completion(messages=messages, temperature=0.3, max_tokens=250)

    description = response.get('content', '').strip()
    description = description.strip('"').strip("'").strip()

    # Truncate if too long
    if len(description) > 300:
        description = description[:297] + "..."

    return description


def create_configs(
    collection_name: str,
    description: str,
    repo_path: Path,  # noqa: ARG001 - unused but kept for API consistency
    provider_config: Dict[str, Any]
) -> None:
    """Create directory structure and configuration files."""
    print("📂 Setting up directories...")
    print()

    # Fixed paths
    minerva_root = Path.home() / '.minerva'
    app_dir = minerva_root / 'apps' / 'local-repo-kb'
    chromadb_path = minerva_root / 'chromadb'

    app_dir.mkdir(parents=True, exist_ok=True)
    chromadb_path.mkdir(parents=True, exist_ok=True)

    print("✓ Directories created:")
    print(f"  • App:      {app_dir}")
    print(f"  • ChromaDB: {chromadb_path}")
    print()

    # Generate config files
    print("📝 Generating configuration files...")
    print()

    server_config_path = app_dir / 'server.json'
    index_config_path = app_dir / f'{collection_name}-index.json'
    extracted_json_path = app_dir / f'{collection_name}-extracted.json'

    # Server config (shared across all collections)
    if not server_config_path.exists():
        server_config = {
            "chromadb_path": str(chromadb_path),
            "default_max_results": 5
        }
        server_config_path.write_text(json.dumps(server_config, indent=2))
        print(f"✓ Created: {server_config_path}")
    else:
        print(f"ℹ️  Using existing: {server_config_path}")

    # Index config (collection-specific, provider-specific)
    index_config = {
        "chromadb_path": str(chromadb_path),
        "collection": {
            "name": collection_name,
            "description": description,
            "json_file": str(extracted_json_path),
            "chunk_size": 1200
        },
        "provider": {
            "provider_type": provider_config['provider_type'],
            "embedding_model": provider_config['embedding_model'],
            "llm_model": provider_config['llm_model']
        }
    }

    # Add provider-specific fields
    if provider_config['needs_api_key']:
        index_config["provider"]["api_key"] = f"${{{provider_config['env_var_name']}}}"
    else:
        index_config["provider"]["base_url"] = provider_config['base_url']

    index_config_path.write_text(json.dumps(index_config, indent=2))
    print(f"✓ Created: {index_config_path}")
    print()

    # Store paths for later use
    provider_config['_server_config'] = server_config_path
    provider_config['_index_config'] = index_config_path
    provider_config['_extracted_json'] = extracted_json_path
    provider_config['_chromadb_path'] = chromadb_path


def extract_and_index(
    collection_name: str,  # noqa: ARG001 - unused but kept for API consistency
    repo_path: Path,
    provider_config: Dict[str, Any]
) -> None:
    """Extract repository and index collection."""
    print("🔍 Extracting and Indexing")
    print("=" * 60)
    print()

    # Extract repository
    print("📚 Extracting repository contents...")
    print()

    # Check and install repository-doc-extractor if needed
    if not shutil.which('repository-doc-extractor'):
        print("📦 repository-doc-extractor not found. Installing...")
        print()
        extractor_path = get_minerva_repo_path() / 'extractors' / 'repository-doc-extractor'

        try:
            subprocess.run(
                ['pipx', 'install', str(extractor_path)],
                check=True
            )
            print("✓ repository-doc-extractor installed")
            print()
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install repository-doc-extractor: {e}")
            print()
            print("You can try manually:")
            print(f"  pipx install {extractor_path}")
            print()
            sys.exit(1)

    try:
        subprocess.run(
            [
                'repository-doc-extractor',
                str(repo_path),
                '-o',
                str(provider_config['_extracted_json'])
            ],
            check=True
        )
        print(f"✓ Extraction complete: {provider_config['_extracted_json']}")
    except subprocess.CalledProcessError:
        print("❌ Extraction failed")
        sys.exit(1)

    print()
    print("🔍 Indexing collection...")
    try:
        subprocess.run(
            ['minerva', 'index', '--config', str(provider_config['_index_config'])],
            check=True
        )
        print("✓ Indexing complete")
    except subprocess.CalledProcessError:
        print("❌ Indexing failed")
        print()
        print("Try manually with verbose output:")
        print(f"  minerva index --config {provider_config['_index_config']} --verbose")
        sys.exit(1)


def show_completion_summary(
    collection_name: str,
    repo_path: Path,
    provider_config: Dict[str, Any]
) -> None:
    """Show completion summary and next steps."""
    print()
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()

    print("📊 Configuration Summary")
    print("-" * 60)
    print(f"  Provider:    {provider_config['provider_name']}")
    if provider_config['needs_api_key']:
        print(f"  API Key:     Stored in keychain as '{provider_config['keychain_name']}'")
    print(f"  Embedding:   {provider_config['embedding_model']}")
    print(f"  LLM:         {provider_config['llm_model']}")
    print(f"  Collection:  {collection_name}")
    print(f"  Repository:  {repo_path}")
    print()

    print("📝 Files Created")
    print("-" * 60)
    print(f"  Server config: {provider_config['_server_config']}")
    print(f"  Index config:  {provider_config['_index_config']}")
    print(f"  Extracted:     {provider_config['_extracted_json']}")
    print(f"  ChromaDB:      {provider_config['_chromadb_path']}")
    print()

    print("🔧 Next Steps")
    print("-" * 60)
    print()
    print("1. Configure Claude Desktop:")
    print()
    print("   Edit: ~/Library/Application Support/Claude/claude_desktop_config.json")
    print()
    print("   Add this MCP server configuration:")
    print()

    minerva_path = shutil.which('minerva') or '~/.local/bin/minerva'
    print("   {")
    print('     "mcpServers": {')
    print(f'       "minerva-{collection_name}": {{')
    print(f'         "command": "{minerva_path}",')
    print(f'         "args": ["serve", "--config", "{provider_config["_server_config"]}"]')
    print('       }')
    print('     }')
    print('   }')
    print()

    print("2. Restart Claude Desktop to load the MCP server")
    print()
    print("3. (Optional) Add to Claude Code:")
    print()
    print("   If you use Claude Code, you can import this MCP server:")
    print()
    print("   claude mcp add-from-claude-desktop")
    print()
    print("   Then select the minerva server from the list.")
    print()
    print("4. Test by asking Claude:")
    print()
    print(f'   "Search the {collection_name} collection for [your query]"')
    print()
    print(f'   Example:')
    print(f'   "Search the {collection_name} collection for API documentation"')
    print()

    if provider_config['needs_api_key']:
        print("🔐 API Key Management")
        print("-" * 60)
        print(f"  View:   minerva keychain get {provider_config['keychain_name']}")
        print(f"  Update: minerva keychain set {provider_config['keychain_name']}")
        print(f"  Delete: minerva keychain delete {provider_config['keychain_name']}")
        print()
    else:
        print(f"🔧 Local Provider: {provider_config['provider_name']}")
        print("-" * 60)
        print(f"  Make sure {provider_config['provider_name']} is running before using:")
        if provider_config['provider_type'] == 'ollama':
            print("    ollama serve")
            print()
            print("  Verify models:")
            print("    ollama list")
        else:
            print("    Start LM Studio and load your models")
        print()

    print("📚 Documentation")
    print("-" * 60)
    print("  README:   apps/local-repo-kb/README.md")
    print("  Security: apps/local-repo-kb/SECURITY.md")
    print()
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
