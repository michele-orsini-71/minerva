"""
Setup configuration for minerva package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from package __init__.py
init_file = Path(__file__).parent / "minerva" / "__init__.py"
version = "1.0.0"
author = "Michele Orsini"

for line in init_file.read_text().splitlines():
    if line.startswith("__version__"):
        version = line.split('"')[1]
    elif line.startswith("__author__"):
        author = line.split('"')[1]

# Read long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="minerva",
    version=version,
    author=author,
    description="A unified RAG system for personal knowledge management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/minerva",
    packages=find_packages(include=["minerva", "minerva.*"]),
    python_requires=">=3.10",
    install_requires=[
        # Vector database and AI providers
        "chromadb>=1.3.6",  # Pinned to 1.3.6+ to avoid corruption bugs in earlier versions
        "ollama>=0.1.0",
        "litellm>=1.79.0",
        "httpx>=0.28.0",

        # Text processing and embeddings
        "numpy>=1.21.0",
        "tiktoken>=0.4.0",
        "nltk>=3.8",

        # LangChain for document chunking
        "langchain>=0.1.0",
        "langchain-text-splitters>=0.0.1",

        # FastMCP for MCP server
        "mcp>=0.1.0",

        # JSON schema validation
        "jsonschema>=4.0.0",

        # OS keychain integration
        "keyring>=24.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "minerva=minerva.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Markup :: Markdown",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    keywords="rag, vector-database, embeddings, markdown, knowledge-management, mcp, ai",
    project_urls={
        "Documentation": "https://github.com/yourusername/minerva/blob/main/README.md",
        "Source": "https://github.com/yourusername/minerva",
        "Tracker": "https://github.com/yourusername/minerva/issues",
    },
)
