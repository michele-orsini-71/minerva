#!/usr/bin/env python3

from pathlib import Path
from setuptools import find_packages, setup

BASE_DIR = Path(__file__).parent


def read_long_description() -> str:
    readme = BASE_DIR / "README.md"
    if readme.exists():
        return readme.read_text(encoding="utf-8")
    return "Markdown books extractor that converts structured markdown files into JSON records."


setup(
    name="markdown-books-extractor",
    version="1.0.0",
    author="Minerva Contributors",
    description="Standalone CLI for extracting metadata from markdown book files",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["markdown_books_extractor", "markdown_books_extractor.*"]),
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=23.0",
            "flake8>=6.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "markdown-books-extractor=markdown_books_extractor.cli:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Topic :: Utilities",
        "Topic :: Text Processing",
    ],
    include_package_data=True,
    zip_safe=False,
)
