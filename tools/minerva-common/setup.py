from setuptools import setup, find_packages

setup(
    name="minerva-common",
    version="1.0.0",
    description="Shared library for Minerva tools (minerva-kb, minerva-doc)",
    author="Minerva Project",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "chromadb>=0.6.4",
        "openai>=1.0.0",
        "google-generativeai>=0.8.3",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={},
)
