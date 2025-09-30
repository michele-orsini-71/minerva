#!/usr/bin/env python3
"""
Setup script for bear-notes-parser package.

This package provides utilities for parsing Bear backup files (.bear2bk)
and extracting structured note data for further processing.
"""

from setuptools import setup, find_packages
import os


def read_long_description():
    """Read long description from README if it exists."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Bear Notes Parser - Extract and parse notes from Bear backup files"


def read_version():
    """Read version from module or default."""
    # You could also read from a __version__.py file if you create one
    return "1.0.0"


setup(
    name="bear-notes-parser",
    version=read_version(),
    author="Michele",
    description="CLI tool for parsing Bear backup files and extracting note data",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",

    # Package discovery - CLI-only tool
    packages=find_packages(),
    py_modules=["bear_parser", "cli"],  # Internal modules for CLI functionality

    # Dependencies - bear-notes-parser uses only standard library
    install_requires=[
        # No external dependencies - uses only Python standard library
    ],

    # Optional dependencies for development
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
        ]
    },

    # Python version requirement
    python_requires=">=3.6",

    # Console scripts for CLI entry points
    entry_points={
        "console_scripts": [
            "bear-parser=cli:main",  # Makes 'bear-parser' command available
        ],
    },

    # Package metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing",
        "Topic :: Utilities",
    ],

    # Include additional files
    include_package_data=True,

    # Zip safety
    zip_safe=False,
)