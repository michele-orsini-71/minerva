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

try:
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    from jsonschema import Draft7Validator
except ImportError:
    print("Error: jsonschema library not installed. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


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


# JSON Schema for collection configuration validation
COLLECTION_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["collection_name", "description"],
    "properties": {
        "collection_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 63,
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
            "description": "Collection name (alphanumeric, underscore, hyphen; 1-63 chars)"
        },
        "description": {
            "type": "string",
            "minLength": 10,
            "maxLength": 1000,
            "description": "Detailed description of when to use this collection (10-1000 chars)"
        },
        "forceRecreate": {
            "type": "boolean",
            "default": False,
            "description": "Force recreation of collection if it exists"
        },
        "skipAiValidation": {
            "type": "boolean",
            "default": False,
            "description": "Skip AI-based validation of collection name and description"
        }
    },
    "additionalProperties": False
}


def validate_config_schema(data: Dict[str, Any], config_path: str) -> None:
    """
    Validate configuration data against JSON schema.

    Args:
        data: Configuration dictionary to validate
        config_path: Path to config file (for error messages)

    Raises:
        ConfigError: If schema validation fails
    """
    try:
        validate(instance=data, schema=COLLECTION_CONFIG_SCHEMA)
    except JsonSchemaValidationError as e:
        # Convert jsonschema validation error to user-friendly ConfigError
        error_path = " → ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"

        # Provide helpful error messages based on error type
        if "is a required property" in e.message:
            missing_field = e.message.split("'")[1]
            raise ConfigError(
                f"Missing required field in configuration file: {config_path}\n"
                f"  Missing field: '{missing_field}'\n"
                f"  Location: {error_path}\n"
                f"  Suggestion: Add the required field:\n"
                f"    {{\n"
                f'      "collection_name": "your_collection_name",\n'
                f'      "description": "Detailed description (at least 10 characters)..."\n'
                f"    }}"
            )
        elif "is not of type" in e.message:
            raise ConfigError(
                f"Type validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {e.message}\n"
                f"  Suggestion: Check the field type:\n"
                f"    - Strings: \"value\" (with quotes)\n"
                f"    - Booleans: true or false (lowercase, no quotes)"
            )
        elif "is too short" in e.message or "is too long" in e.message:
            raise ConfigError(
                f"Length validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {e.message}\n"
                f"  Suggestion: Check the field length requirements in the schema"
            )
        elif "does not match" in e.message:
            raise ConfigError(
                f"Pattern validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {e.message}\n"
                f"  Suggestion: collection_name must:\n"
                f"    - Start with alphanumeric character\n"
                f"    - Contain only alphanumeric, underscore, or hyphen\n"
                f"    - Be 1-63 characters long\n"
                f"  Examples: 'bear_notes', 'project-docs', 'team123'"
            )
        elif "Additional properties are not allowed" in e.message:
            extra_props = [p for p in e.instance.keys() if p not in COLLECTION_CONFIG_SCHEMA['properties']]
            raise ConfigError(
                f"Unknown fields in configuration file: {config_path}\n"
                f"  Unknown fields: {', '.join(extra_props)}\n"
                f"  Allowed fields: {', '.join(COLLECTION_CONFIG_SCHEMA['properties'].keys())}\n"
                f"  Suggestion: Remove the unknown fields or check for typos"
            )
        else:
            # Generic schema validation error
            raise ConfigError(
                f"Schema validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {e.message}\n"
                f"  Suggestion: Check the configuration format against the schema"
            )


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

        # Validate against JSON schema (replaces manual validation)
        validate_config_schema(data, config_path)

        # Extract validated fields
        collection_name = data['collection_name'].strip()
        description = data['description'].strip()
        force_recreate = data.get('forceRecreate', False)
        skip_ai_validation = data.get('skipAiValidation', False)

        # Create and return immutable config object
        return CollectionConfig(
            collection_name=collection_name,
            description=description,
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
    import tempfile
    import os

    print("🧪 Testing config_loader.py module")
    print("=" * 60)

    # Test 1: Non-existent file
    print("\n📋 Test 1: Non-existent file")
    try:
        config = load_collection_config("nonexistent.json")
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for missing file")

    # Test 2: Invalid JSON syntax
    print("\n📋 Test 2: Invalid JSON syntax")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{ "invalid": json syntax }')
        invalid_json_path = f.name
    try:
        config = load_collection_config(invalid_json_path)
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for invalid JSON")
    finally:
        os.unlink(invalid_json_path)

    # Test 3: Missing required fields
    print("\n📋 Test 3: Missing required fields")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"collection_name": "test"}')
        missing_field_path = f.name
    try:
        config = load_collection_config(missing_field_path)
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for missing 'description'")
    finally:
        os.unlink(missing_field_path)

    # Test 4: Invalid collection name (pattern mismatch)
    print("\n📋 Test 4: Invalid collection name pattern")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"collection_name": "-invalid-name", "description": "This should fail because name starts with hyphen"}')
        invalid_name_path = f.name
    try:
        config = load_collection_config(invalid_name_path)
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for invalid name pattern")
    finally:
        os.unlink(invalid_name_path)

    # Test 5: Description too short
    print("\n📋 Test 5: Description too short")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"collection_name": "test", "description": "short"}')
        short_desc_path = f.name
    try:
        config = load_collection_config(short_desc_path)
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for short description")
    finally:
        os.unlink(short_desc_path)

    # Test 6: Invalid field type
    print("\n📋 Test 6: Invalid field type")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"collection_name": "test", "description": "This is a valid description", "forceRecreate": "yes"}')
        invalid_type_path = f.name
    try:
        config = load_collection_config(invalid_type_path)
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for invalid boolean type")
    finally:
        os.unlink(invalid_type_path)

    # Test 7: Additional properties not allowed
    print("\n📋 Test 7: Additional unknown fields")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"collection_name": "test", "description": "Valid description here", "unknown_field": "value"}')
        extra_field_path = f.name
    try:
        config = load_collection_config(extra_field_path)
        print("❌ Should have raised ConfigError")
        sys.exit(1)
    except ConfigError as e:
        print(f"✅ Correctly raised ConfigError for unknown fields")
    finally:
        os.unlink(extra_field_path)

    # Test 8: Valid configuration
    print("\n📋 Test 8: Valid configuration")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('''{
            "collection_name": "bear_notes_123",
            "description": "This is a comprehensive description that meets the minimum length requirement",
            "forceRecreate": true,
            "skipAiValidation": false
        }''')
        valid_config_path = f.name
    try:
        config = load_collection_config(valid_config_path)
        print(f"✅ Configuration loaded successfully:")
        print(f"   Collection name: {config.collection_name}")
        print(f"   Description: {config.description[:50]}...")
        print(f"   Force recreate: {config.force_recreate}")
        print(f"   Skip AI validation: {config.skip_ai_validation}")

        # Verify immutability
        try:
            config.collection_name = "should_fail"
            print("❌ Should not be able to modify frozen dataclass")
            sys.exit(1)
        except:
            print("✅ Configuration is immutable (as expected)")

    except ConfigError as e:
        print(f"❌ Should have loaded successfully: {e}")
        sys.exit(1)
    finally:
        os.unlink(valid_config_path)

    # Test 9: Load from actual config file (if it exists)
    test_config_path = "collections/bear_notes_config.json"
    print(f"\n📋 Test 9: Load {test_config_path} (if exists)")
    try:
        config = load_collection_config(test_config_path)
        print(f"✅ Real configuration loaded successfully:")
        print(f"   Collection name: {config.collection_name}")
        print(f"   Description: {config.description[:50]}...")
        print(f"   Force recreate: {config.force_recreate}")
        print(f"   Skip AI validation: {config.skip_ai_validation}")
    except ConfigError as e:
        print(f"ℹ️  Config file not found (expected if not created yet)")

    print("\n🎉 All config_loader.py tests passed!")
