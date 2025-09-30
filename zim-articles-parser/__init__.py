"""
ZIM Articles Parser - CLI tool for extracting articles from ZIM files.

This package provides the 'extract-zim-articles' command-line tool for processing
ZIM files (Kiwix/Wikipedia offline format) and extracting structured article data.

Usage:
    extract-zim-articles file.zim --json catalog.json
    extract-zim-articles file.zim --json catalog.json --output-dir markdown_files --limit 1000

The package is designed as a CLI-only tool and does not expose
importable functionality.
"""

__version__ = "1.0.0"
__author__ = "Michele"

# CLI-only package - no public API exposed
__all__ = []