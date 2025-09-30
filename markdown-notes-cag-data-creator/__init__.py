"""
Markdown Notes CAG Data Creator - CLI tool for markdown notes RAG pipeline.

This package provides the 'create-cag-from-markdown-notes' command-line tool for
processing markdown notes JSON files through a complete RAG pipeline:
chunking, embedding generation, and ChromaDB storage.

Usage:
    create-cag-from-markdown-notes "path/to/notes.json"
    create-cag-from-markdown-notes --verbose --chunk-size 1200 "path/to/notes.json"

The package is designed as a CLI-only tool and does not expose
importable functionality.
"""

__version__ = "1.0.0"
__author__ = "Michele"

# CLI-only package - no public API exposed
__all__ = []