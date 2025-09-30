"""
Bear Notes Parser - CLI tool for extracting notes from Bear backup files.

This package provides the 'bear-parser' command-line tool for processing
Bear backup files (.bear2bk) and extracting structured note data.

Usage:
    bear-parser "path/to/backup.bear2bk"

The package is designed as a CLI-only tool and does not expose
importable functionality.
"""

__version__ = "1.0.0"
__author__ = "Michele"

# CLI-only package - no public API exposed
__all__ = []