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
    collection_name: str
    description: str
    chromadb_path: str
    json_file: str
    force_recreate: bool = False
    skip_ai_validation: bool = False
    chunk_size: int = 1200

    def __post_init__(self):
        if not self.collection_name:
            raise ValueError("collection_name cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")


class ConfigError(Exception):
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
        },
        "chromadb_path": {
            "type": "string",
            "minLength": 1,
            "description": "Path to ChromaDB storage location"
        },
        "json_file": {
            "type": "string",
            "minLength": 1,
            "description": "Path to Bear notes JSON file"
        },
        "chunk_size": {
            "type": "number",
            "minimum": 300,
            "maximum": 20000,
            "default": 1200,
            "description": "Target chunk size in characters (100-10000)"
        }
    },
    "additionalProperties": False
}


def validate_config_schema(data: Dict[str, Any], config_path: str) -> None:
    try:
        validate(instance=data, schema=COLLECTION_CONFIG_SCHEMA)
    except JsonSchemaValidationError as error:
        # Convert jsonschema validation error to user-friendly ConfigError
        error_path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"

        # Provide helpful error messages based on error type
        if "is a required property" in error.message:
            missing_field = error.message.split("'")[1]
            raise ConfigError(
                f"Missing required field in configuration file: {config_path}\n"
                f"  Missing field: '{missing_field}'\n"
                f"  Location: {error_path}\n"
                f"  Suggestion: Add the required field:\n"
                f"    {{\n"
                f'      "collection_name": "your_collection_name",\n'
                f'      "description": "Detailed description (at least 10 characters)..."\n'
                f'      "chromadb_path = Path to chromadb file"\n'
                f'      "json_file = Path to the json data file"\n'
                f'      "chunk_size = Size of the chunks in characters (defaults to 1200)"\n'
                f"    }}"
            )
        elif "is not of type" in error.message:
            raise ConfigError(
                f"Type validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {error.message}\n"
                f"  Suggestion: Check the field type:\n"
                f"    - Strings: \"value\" (with quotes)\n"
                f"    - Booleans: true or false (lowercase, no quotes)"
            )
        elif "is too short" in error.message or "is too long" in error.message:
            raise ConfigError(
                f"Length validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {error.message}\n"
                f"  Suggestion: Check the field length requirements in the schema"
            )
        elif "does not match" in error.message:
            raise ConfigError(
                f"Pattern validation error in configuration file: {config_path}\n"
                f"  Field: {error_path}\n"
                f"  Error: {error.message}\n"
                f"  Suggestion: collection_name must:\n"
                f"    - Start with alphanumeric character\n"
                f"    - Contain only alphanumeric, underscore, or hyphen\n"
                f"    - Be 1-63 characters long\n"
                f"  Examples: 'bear_notes', 'project-docs', 'team123'"
            )
        elif "Additional properties are not allowed" in error.message:
            extra_props = [p for p in error.instance.keys() if p not in COLLECTION_CONFIG_SCHEMA['properties']]
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
                f"  Error: {error.message}\n"
                f"  Suggestion: Check the configuration format against the schema"
            )


def validate_config_file_exists(config_path: str) -> Path:
    """Validate that configuration file exists and return Path object."""
    config_file = Path(config_path)

    if not config_file.exists():
        raise ConfigError(
            f"Configuration file not found: {config_path}\n"
            f"  Expected location: {config_file.absolute()}\n"
            f"  Suggestion: Create a JSON config file with required fields:\n"
            f"    - collection_name (required, string)\n"
            f"    - chromadb_path (required, string)\n"
            f"    - json_file (required, string)\n"
            f"    - chunk_size (defaults to 1200, number)\n"
            f"    - description (required, string)\n"
            f"    - forceRecreate (optional, boolean, default: false)\n"
            f"    - skipAiValidation (optional, boolean, default: false)"
        )

    return config_file


def read_json_config_file(config_file: Path, config_path: str) -> Dict[str, Any]:
    """Read and parse JSON configuration file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Invalid JSON syntax in configuration file: {config_path}\n"
            f"  Error: {error.msg} at line {error.lineno}, column {error.colno}\n"
            f"  Suggestion: Validate your JSON using a JSON validator or linter"
        )
    except Exception as error:
        raise ConfigError(
            f"Failed to read configuration file: {config_path}\n"
            f"  Error: {error}\n"
            f"  Suggestion: Check file permissions and encoding"
        )

    # Validate data is a dictionary
    if not isinstance(data, dict):
        raise ConfigError(
            f"Configuration file must contain a JSON object, got {type(data).__name__}\n"
            f"  File: {config_path}\n"
            f"  Suggestion: Ensure the file contains {{ ... }} at the top level"
        )

    return data


def extract_config_fields(data: Dict[str, Any]) -> CollectionConfig:
    """Extract and build CollectionConfig from validated data."""
    collection_name = data['collection_name'].strip()
    description = data['description'].strip()
    force_recreate = data.get('forceRecreate', False)
    skip_ai_validation = data.get('skipAiValidation', False)
    chromadb_path = data['chromadb_path'].strip()
    json_file = data['json_file'].strip()
    chunk_size = data.get('chunk_size', 1200)

    return CollectionConfig(
        collection_name=collection_name,
        description=description,
        force_recreate=force_recreate,
        skip_ai_validation=skip_ai_validation,
        chromadb_path=chromadb_path,
        json_file=json_file,
        chunk_size=chunk_size,
    )


def load_collection_config(config_path: str) -> CollectionConfig:
    """Load and validate collection configuration from JSON file."""
    try:
        # Step 1: Validate file exists
        config_file = validate_config_file_exists(config_path)

        # Step 2: Read and parse JSON
        data = read_json_config_file(config_file, config_path)

        # Step 3: Validate against JSON schema
        validate_config_schema(data, config_path)

        # Step 4: Extract fields and create config object
        return extract_config_fields(data)

    except ConfigError:
        # Re-raise ConfigError as-is
        raise
    except Exception as error:
        # Wrap unexpected errors
        raise ConfigError(
            f"Unexpected error loading configuration: {config_path}\n"
            f"  Error: {error}\n"
            f"  Suggestion: Verify the file is accessible and properly formatted"
        )
