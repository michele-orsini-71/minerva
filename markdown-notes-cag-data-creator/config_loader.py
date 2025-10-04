#!/usr/bin/env python3
"""
Configuration file loader and validator for multi-collection support.

Loads and validates JSON configuration files that specify collection metadata
including name, description, and operational flags.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class CollectionConfig:
    """
    Immutable configuration for a ChromaDB collection.

    Follows the codebase pattern of using frozen dataclasses for
    data integrity throughout the pipeline.
    """
    collection_name: str
    description: str
    force_recreate: bool = False
    skip_ai_validation: bool = False

    def __post_init__(self):
        """Validate configuration on creation."""
        if not self.collection_name:
            raise ValueError("collection_name cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")


class ConfigError(Exception):
    """Exception raised when configuration loading or validation fails."""
    pass


def load_collection_config(config_path: str) -> CollectionConfig:
    """
    Load and validate a collection configuration file.

    Args:
        config_path: Path to JSON configuration file

    Returns:
        CollectionConfig object with validated configuration

    Raises:
        ConfigError: If file not found, invalid JSON, or validation fails

    Example:
        config = load_collection_config("collections/bear_notes_config.json")
        print(f"Collection: {config.collection_name}")
        print(f"Description: {config.description}")
    """
    try:
        # Convert to Path object for better error messages
        config_file = Path(config_path)

        # Check if file exists
        if not config_file.exists():
            raise ConfigError(
                f"Configuration file not found: {config_path}\n"
                f"  Expected location: {config_file.absolute()}\n"
                f"  Suggestion: Create a JSON config file with required fields:\n"
                f"    - collection_name (required, string)\n"
                f"    - description (required, string)\n"
                f"    - forceRecreate (optional, boolean, default: false)\n"
                f"    - skipAiValidation (optional, boolean, default: false)"
            )

        # Read and parse JSON
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON syntax in configuration file: {config_path}\n"
                f"  Error: {e.msg} at line {e.lineno}, column {e.colno}\n"
                f"  Suggestion: Validate your JSON using a JSON validator or linter"
            )
        except Exception as e:
            raise ConfigError(
                f"Failed to read configuration file: {config_path}\n"
                f"  Error: {e}\n"
                f"  Suggestion: Check file permissions and encoding"
            )

        # Validate data is a dictionary
        if not isinstance(data, dict):
            raise ConfigError(
                f"Configuration file must contain a JSON object, got {type(data).__name__}\n"
                f"  File: {config_path}\n"
                f"  Suggestion: Ensure the file contains {{ ... }} at the top level"
            )

        # Extract and validate required fields
        missing_fields = []
        if 'collection_name' not in data:
            missing_fields.append('collection_name')
        if 'description' not in data:
            missing_fields.append('description')

        if missing_fields:
            raise ConfigError(
                f"Missing required fields in configuration file: {config_path}\n"
                f"  Missing fields: {', '.join(missing_fields)}\n"
                f"  Suggestion: Add these fields to your JSON configuration:\n"
                f"    {{\n"
                f'      "collection_name": "your_collection_name",\n'
                f'      "description": "Detailed description of when to use this collection..."\n'
                f"    }}"
            )

        # Validate field types
        type_errors = []

        collection_name = data['collection_name']
        if not isinstance(collection_name, str):
            type_errors.append(
                f"  - collection_name must be a string, got {type(collection_name).__name__}"
            )

        description = data['description']
        if not isinstance(description, str):
            type_errors.append(
                f"  - description must be a string, got {type(description).__name__}"
            )

        # Optional fields with defaults
        force_recreate = data.get('forceRecreate', False)
        if not isinstance(force_recreate, bool):
            type_errors.append(
                f"  - forceRecreate must be a boolean, got {type(force_recreate).__name__}"
            )

        skip_ai_validation = data.get('skipAiValidation', False)
        if not isinstance(skip_ai_validation, bool):
            type_errors.append(
                f"  - skipAiValidation must be a boolean, got {type(skip_ai_validation).__name__}"
            )

        if type_errors:
            raise ConfigError(
                f"Type validation errors in configuration file: {config_path}\n"
                + "\n".join(type_errors) + "\n"
                f"  Suggestion: Ensure all fields have the correct type:\n"
                f"    - Strings: \"value\" (with quotes)\n"
                f"    - Booleans: true or false (lowercase, no quotes)\n"
                f"    - Numbers: 123 (no quotes)"
            )

        # Validate that strings are not empty
        if not collection_name.strip():
            raise ConfigError(
                f"collection_name cannot be empty or whitespace-only\n"
                f"  File: {config_path}\n"
                f"  Suggestion: Provide a meaningful collection name"
            )

        if not description.strip():
            raise ConfigError(
                f"description cannot be empty or whitespace-only\n"
                f"  File: {config_path}\n"
                f"  Suggestion: Provide a detailed description of when to use this collection"
            )

        # Create and return immutable config object
        return CollectionConfig(
            collection_name=collection_name.strip(),
            description=description.strip(),
            force_recreate=force_recreate,
            skip_ai_validation=skip_ai_validation
        )

    except ConfigError:
        # Re-raise ConfigError as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        raise ConfigError(
            f"Unexpected error loading configuration: {config_path}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Verify the file is accessible and properly formatted"
        )


if __name__ == "__main__":
    # Simple test when run directly
    print("🧪 Testing config_loader.py module")
    print("=" * 60)

    # Test with non-existent file (should fail gracefully)
    print("\n📋 Test 1: Non-existent file")
    try:
        config = load_collection_config("nonexistent.json")
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError:\n{e}")

    # Test with actual config file (if it exists)
    test_config_path = "collections/bear_notes_config.json"
    print(f"\n📋 Test 2: Load {test_config_path} (if exists)")
    try:
        config = load_collection_config(test_config_path)
        print(f"✅ Configuration loaded successfully:")
        print(f"   Collection name: {config.collection_name}")
        print(f"   Description: {config.description[:50]}...")
        print(f"   Force recreate: {config.force_recreate}")
        print(f"   Skip AI validation: {config.skip_ai_validation}")
    except ConfigError as e:
        print(f"ℹ️  Config file not found (expected if not created yet):\n{e}")

    print("\n🎉 config_loader.py tests completed!")
