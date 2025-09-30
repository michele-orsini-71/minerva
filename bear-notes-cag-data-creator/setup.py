#!/usr/bin/env python3
"""
Setup script for bear-notes-cag-data-creator package.

This package provides a complete RAG (Retrieval-Augmented Generation) pipeline
for Bear Notes, including chunking, embedding generation, and ChromaDB storage.
"""

from setuptools import setup, find_packages
import os


def read_long_description():
    """Read long description from README if it exists."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Bear Notes CAG Data Creator - Complete RAG pipeline for Bear Notes"


def read_version():
    """Read version from module or default."""
    # You could also read from a __version__.py file if you create one
    return "1.0.0"


setup(
    name="bear-notes-cag-data-creator",
    version=read_version(),
    author="Michele",
    description="CLI tool for Bear Notes RAG pipeline: chunking, embeddings, and ChromaDB storage",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",

    # Package discovery - CLI-only tool
    packages=find_packages(),
    py_modules=[
        "full_pipeline",
        "models",
        "embedding",
        "chunk_creator",
        "storage",
        "json_loader"
    ],  # Internal modules for CLI functionality

    # Dependencies for the RAG pipeline
    install_requires=[
        "chromadb>=0.4.0",
        "ollama>=0.1.0",
        "numpy>=1.21.0",
        "langchain>=0.1.0",
        "langchain-text-splitters>=0.0.1",
        "tiktoken>=0.4.0",
        "nltk>=3.8",
    ],

    # Optional dependencies for development and testing
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.910",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.12",
        ]
    },

    # Python version requirement
    python_requires=">=3.8",  # ChromaDB requires Python 3.8+

    # Console scripts for CLI entry points
    entry_points={
        "console_scripts": [
            "bear-rag-pipeline=full_pipeline:main",  # Makes 'bear-rag-pipeline' command available
        ],
    },

    # Package metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Database",
    ],

    # Include additional files
    include_package_data=True,

    # Zip safety
    zip_safe=False,

    # Keywords for package discovery
    keywords="bear-notes rag retrieval-augmented-generation embeddings chromadb ollama nlp",
)