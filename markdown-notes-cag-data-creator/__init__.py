"""
Markdown Notes CAG Data Creator - Multi-collection RAG pipeline tool.

This package provides a config-based CLI tool for processing markdown notes JSON
files through a complete RAG pipeline: semantic chunking, embedding generation,
and multi-collection ChromaDB storage with intelligent routing support.

Key Features:
- Config-based workflow with JSON configuration files
- Multi-collection architecture with named, described collections
- AI-powered validation of collection descriptions (optional)
- Dry-run mode for validation without data modification
- Immutable API design throughout the pipeline
- Local AI processing via Ollama (privacy-first)

Usage:
    # Create a collection configuration file
    cat > collections/my_collection.json <<EOF
    {
      "collection_name": "my_notes",
      "description": "Personal notes about software development and research...",
      "chromadb_path": "/path/to/chromadb_data",
      "json_file": "/path/to/notes.json",
      "chunk_size": 1200,
      "forceRecreate": false,
      "skipAiValidation": false
    }
    EOF

    # Run the pipeline
    create-cag-from-markdown-notes --config collections/my_collection.json --verbose

    # Dry-run mode (validation only, no data changes)
    create-cag-from-markdown-notes --config collections/my_collection.json --dry-run

The package is designed as a CLI-only tool and does not expose
importable functionality for direct use.
"""

__version__ = "2.0.0"
__author__ = "Michele"

# CLI-only package - no public API exposed
__all__ = []