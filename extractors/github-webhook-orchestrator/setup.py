#!/usr/bin/env python3

from pathlib import Path
from setuptools import find_packages, setup

BASE_DIR = Path(__file__).parent


def read_long_description() -> str:
    readme = BASE_DIR / "README.md"
    if readme.exists():
        return readme.read_text(encoding="utf-8")
    return "GitHub webhook receiver that triggers automatic reindexing of repository documentation in Minerva."


setup(
    name="github-webhook-orchestrator",
    version="1.0.0",
    author="Minerva Contributors",
    description="FastAPI webhook server for automatic repository reindexing on GitHub push events",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["github_webhook_orchestrator", "github_webhook_orchestrator.*"]),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=23.0",
            "flake8>=6.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "webhook-orchestrator=github_webhook_orchestrator.server:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Topic :: Utilities",
        "Topic :: Software Development :: Documentation",
    ],
    include_package_data=True,
    zip_safe=False,
)
