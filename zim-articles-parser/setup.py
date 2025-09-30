#!/usr/bin/env python3
"""
Setup script for zim-articles-parser package.

This package provides utilities for extracting articles from ZIM files
(Kiwix/Wikipedia offline format) and outputting structured article data
for further processing in RAG pipelines.
"""

from setuptools import setup, find_packages
import os


def read_long_description():
    """Read long description from README if it exists."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "ZIM Articles Parser - Extract articles from ZIM files"


def read_version():
    """Read version from module or default."""
    # You could also read from a __version__.py file if you create one
    return "1.0.0"


setup(
    name="zim-articles-parser",
    version=read_version(),
    author="Michele",
    description="CLI tool for extracting articles from ZIM files",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",

    # Package discovery - CLI-only tool
    packages=find_packages(),
    py_modules=["zim_parser", "zim_cli"],  # Internal modules for CLI functionality

    # Dependencies for ZIM file processing
    install_requires=[
        "libzim>=3.0.0",  # ZIM file reading
        "markdownify>=0.11.0",  # HTML to Markdown conversion
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
            "extract-zim-articles=zim_cli:main",  # Makes 'extract-zim-articles' command available
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

    # Keywords for package discovery
    keywords="zim kiwix wikipedia offline extraction markdown",
)