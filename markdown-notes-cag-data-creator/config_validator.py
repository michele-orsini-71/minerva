import sys
from config_loader import load_collection_config, ConfigError
from validation import validate_collection_name, validate_description_hybrid, ValidationError


def load_and_validate_config(config_path: str, verbose: bool = False):
    # Step 1: Load configuration
    print("Loading collection configuration...")
    try:
        config = load_collection_config(config_path)
        print(f"   Configuration loaded from: {config_path}")
        print(f"   Collection name: {config.collection_name}")
        print(f"   Description: {config.description[:80]}...")
        print(f"   Force recreate: {config.force_recreate}")
        print(f"   Skip AI validation: {config.skip_ai_validation}")
        print()
    except ConfigError as e:
        print(f"\nConfiguration Error:\n{e}", file=sys.stderr)
        print(f"\nConfiguration file: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Validate collection metadata
    print("Validating collection metadata...")
    try:
        # Validate collection name
        validate_collection_name(config.collection_name)
        print(f"   Collection name validated: {config.collection_name}")

        # Validate description (hybrid: regex + optional AI)
        validation_result = validate_description_hybrid(
            config.description,
            config.collection_name,
            skip_ai_validation=config.skip_ai_validation
        )
        print(f"   Description validated successfully")
        if validation_result:
            print(f"   AI Quality Score: {validation_result['score']}/10")
        print()
    except ValidationError as e:
        print(f"\nValidation Error:\n{e}", file=sys.stderr)
        print(f"\nConfiguration file: {config_path}", file=sys.stderr)
        print(f"Collection name: {config.collection_name}", file=sys.stderr)
        sys.exit(1)

    return config
