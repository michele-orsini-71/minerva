import sys
from config_loader import load_collection_config, ConfigError
from validation import validate_collection_name, validate_description_hybrid, ValidationError

def load_and_validate_config(config_path: str, verbose: bool = False):
    # Step 1: Load configuration
    print("Loading collection configuration...")
    try:
        config = load_collection_config(config_path)
        print(f"   Configuration loaded from: {config_path}")
        print(f"   Json file: {config.json_file}")
        print(f"   ChromaDB path: {config.chromadb_path}")
        print(f"   Chunk size: {config.chunk_size}")
        print(f"   Collection name: {config.collection_name}")
        print(f"   Description: {config.description[:80]}...")
        print(f"   Force recreate: {config.force_recreate}")
        print(f"   Skip AI validation: {config.skip_ai_validation}")
        print()
    except ConfigError as error:
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"CONFIGURATION ERROR", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
        print(f"\n{error}", file=sys.stderr)
        print(f"\nConfiguration file: {config_path}", file=sys.stderr)
        print(f"\nActionable Steps:", file=sys.stderr)
        print(f"  1. Review the error message above for specific issues", file=sys.stderr)
        print(f"  2. Check example configurations in collections/ directory", file=sys.stderr)
        print(f"  3. Validate JSON syntax using a JSON linter", file=sys.stderr)
        print(f"  4. Ensure all required fields are present:", file=sys.stderr)
        print(f"     - collection_name, description, chromadb_path, json_file", file=sys.stderr)
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
        elif config.skip_ai_validation:
            # Warning when AI validation is skipped
            print(f"\n   WARNING: AI validation was skipped (skipAiValidation: true)")
            print(f"   You are responsible for ensuring the description is:")
            print(f"     - Clear and specific about when to use this collection")
            print(f"     - Detailed enough for accurate AI-powered collection selection")
            print(f"     - Not vague or generic (avoid 'various topics', 'miscellaneous', etc.)")
            print(f"   Consequences of poor descriptions:")
            print(f"     - Reduced accuracy in multi-collection RAG systems")
            print(f"     - Confusion when selecting the right collection for queries")
            print(f"     - Poor AI routing decisions in production")
        print()
    except ValidationError as error:
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"VALIDATION ERROR", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)
        print(f"\n{error}", file=sys.stderr)
        print(f"\nConfiguration file: {config_path}", file=sys.stderr)
        print(f"Collection name: {config.collection_name}", file=sys.stderr)
        print(f"\nActionable Steps:", file=sys.stderr)
        print(f"  1. Review the validation error details above", file=sys.stderr)
        print(f"  2. Fix the collection name or description as needed", file=sys.stderr)
        print(f"  3. If AI validation is too strict, consider:", file=sys.stderr)
        print(f"     - Improving the description to be more specific", file=sys.stderr)
        print(f"     - Adding 'skipAiValidation': true (use with caution)", file=sys.stderr)
        print(f"  4. Ensure AI model is available if using AI validation:", file=sys.stderr)
        print(f"     $ ollama pull llama3.1:8b", file=sys.stderr)
        sys.exit(1)

    return config
