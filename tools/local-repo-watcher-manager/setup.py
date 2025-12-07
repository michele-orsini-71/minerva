"""Setup for minerva-local-watcher manager."""

from pathlib import Path
from setuptools import setup, find_packages

PACKAGE_NAME = 'local-repo-watcher-manager'
MODULE_PATH = Path(__file__).parent / 'local_repo_watcher_manager'

# Basic metadata
setup(
    name=PACKAGE_NAME,
    version='0.1.0',
    description='Helper CLI to launch minerva local repo watchers',
    long_description=(Path(__file__).parent / 'README.md').read_text(),
    long_description_content_type='text/markdown',
    author='Minerva Contributors',
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'minerva-local-watcher=local_repo_watcher_manager.cli:main',
        ],
    },
    python_requires='>=3.10',
)
