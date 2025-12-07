"""Setup script for local-repo-watcher."""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
init_file = Path(__file__).parent / 'local_repo_watcher' / '__init__.py'
version = None
for line in init_file.read_text().splitlines():
    if line.startswith('__version__'):
        version = line.split('"')[1]
        break

if not version:
    raise RuntimeError("Could not determine version")

# Read README if it exists
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text() if readme_file.exists() else ''

setup(
    name='local-repo-watcher',
    version=version,
    description='Local repository watcher for Minerva - triggers indexing on file changes',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Minerva Contributors',
    packages=find_packages(),
    install_requires=[
        'watchdog>=3.0.0',
    ],
    entry_points={
        'console_scripts': [
            'local-repo-watcher=local_repo_watcher.cli:main',
        ],
    },
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
)
