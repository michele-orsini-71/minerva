import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from minervium.common.logger import get_logger

console_logger = get_logger(__name__, simple=True)


class ConfigError(Exception):
    pass


class ConfigValidationError(ConfigError):
    pass


def load_json_file(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigError(
            f"Configuration file not found: {config_path}\n"
            f"\n"
            f"  Please create a configuration file with the following steps:\n"
            f"  1. Copy the example configuration:\n"
            f"     cp config.json.example config.json\n"
            f"\n"
            f"  2. Edit config.json and set the absolute path to your ChromaDB directory\n"
            f"\n"
            f"  Example configuration:\n"
            f"  {{\n"
            f"    \"chromadb_path\": \"/absolute/path/to/chromadb_data\",\n"
            f"    \"default_max_results\": 5\n"
            f"  }}"
        )
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Invalid JSON in configuration file: {config_path}\n"
            f"  Error: {e}\n"
            f"\n"
            f"  Please ensure the file contains valid JSON.\n"
            f"  Check for:\n"
            f"  - Missing or extra commas\n"
            f"  - Unclosed quotes or brackets\n"
            f"  - Invalid escape sequences"
        )
    except Exception as e:
        raise ConfigError(f"Failed to read configuration file: {e}")


def validate_chromadb_path(config: Dict[str, Any]) -> None:
    if 'chromadb_path' not in config:
        raise ConfigValidationError(
            "Missing required field: 'chromadb_path'\n"
            f"\n"
            f"  Your configuration must include the absolute path to ChromaDB storage.\n"
            f"\n"
            f"  Add this to your config.json:\n"
            f"  {{\n"
            f"    \"chromadb_path\": \"/absolute/path/to/chromadb_data\",\n"
            f"    ...\n"
            f"  }}"
        )

    path = config['chromadb_path']

    if not isinstance(path, str):
        raise ConfigValidationError(
            f"Invalid 'chromadb_path': must be a string\n"
            f"  Got: {type(path).__name__}"
        )

    if not path or not path.strip():
        raise ConfigValidationError(
            "Invalid 'chromadb_path': cannot be empty\n"
            f"\n"
            f"  Please specify an absolute path to your ChromaDB directory:\n"
            f"  \"chromadb_path\": \"/absolute/path/to/chromadb_data\""
        )

    if not os.path.isabs(path):
        raise ConfigValidationError(
            f"Invalid 'chromadb_path': must be an absolute path\n"
            f"  Got: {path}\n"
            f"\n"
            f"  Relative paths are not allowed for reliability and clarity.\n"
            f"\n"
            f"  Examples of valid absolute paths:\n"
            f"  - Linux/Mac: \"/Users/username/chromadb_data\"\n"
            f"  - Linux/Mac: \"/home/username/chromadb_data\"\n"
            f"\n"
            f"  To fix this:\n"
            f"  1. Use 'pwd' to get your current directory\n"
            f"  2. Construct the full absolute path\n"
            f"  3. Update config.json with the absolute path"
        )


def validate_default_max_results(config: Dict[str, Any]) -> None:
    if 'default_max_results' not in config:
        raise ConfigValidationError(
            "Missing required field: 'default_max_results'\n"
            f"\n"
            f"  This specifies how many search results to return by default.\n"
            f"\n"
            f"  Add this to your config.json:\n"
            f"  {{\n"
            f"    \"default_max_results\": 5,\n"
            f"    ...\n"
            f"  }}\n"
            f"\n"
            f"  Recommended values: 3-10"
        )

    max_results = config['default_max_results']

    if not isinstance(max_results, int):
        raise ConfigValidationError(
            f"Invalid 'default_max_results': must be an integer\n"
            f"  Got: {type(max_results).__name__} = {max_results}\n"
            f"\n"
            f"  Example: \"default_max_results\": 5"
        )

    if max_results < 1 or max_results > 100:
        raise ConfigValidationError(
            f"Invalid 'default_max_results': must be between 1 and 100\n"
            f"  Got: {max_results}\n"
            f"\n"
            f"  Rationale:\n"
            f"  - Minimum 1: At least one result is needed for useful search\n"
            f"  - Maximum 100: Prevents excessive results that may slow down AI processing\n"
            f"\n"
            f"  Recommended values: 3-10"
        )


def validate_config(config: Dict[str, Any]) -> None:
    # Check for unexpected fields (helps catch typos)
    expected_fields = {'chromadb_path', 'default_max_results'}
    unexpected_fields = set(config.keys()) - expected_fields

    if unexpected_fields:
        raise ConfigValidationError(
            f"Unexpected field(s) in configuration: {', '.join(sorted(unexpected_fields))}\n"
            f"\n"
            f"  Expected fields: {', '.join(sorted(expected_fields))}\n"
            f"\n"
            f"  Please check for typos in your config.json file.\n"
            f"  Remove or correct the unexpected fields.\n"
            f"\n"
            f"  Note: The MCP server no longer requires 'embedding_model' in its config.\n"
            f"  AI provider information is now read from each collection's metadata,\n"
            f"  which was set when the collection was created by the pipeline."
        )

    validate_chromadb_path(config)
    validate_default_max_results(config)


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    config = load_json_file(config_path)

    validate_config(config)

    return config


def get_config_file_path() -> str:
    module_dir = Path(__file__).parent
    return str(module_dir / "config.json")


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else get_config_file_path()

    try:
        config = load_config(config_file)
        console_logger.success("✓ Configuration loaded successfully!")
        console_logger.info(json.dumps(config, indent=2))
    except (ConfigError, ConfigValidationError) as e:
        console_logger.error(f"Configuration error:\n{e}")
        sys.exit(1)
