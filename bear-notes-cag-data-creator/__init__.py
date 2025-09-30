"""
Bear Notes CAG Data Creator - CLI tool for Bear Notes RAG pipeline.

This package provides the 'bear-rag-pipeline' command-line tool for
processing Bear Notes JSON files through a complete RAG pipeline:
chunking, embedding generation, and ChromaDB storage.

Usage:
    bear-rag-pipeline "path/to/notes.json"
    bear-rag-pipeline --verbose --chunk-size 1200 "path/to/notes.json"

The package is designed as a CLI-only tool and does not expose
importable functionality.
"""

__version__ = "1.0.0"
__author__ = "Michele"

# CLI-only package - no public API exposed
__all__ = []