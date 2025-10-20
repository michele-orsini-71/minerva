import sys

from minervium.common.config_loader import load_collection_config, ConfigError
from minervium.common.validation import (
    validate_collection_name,
    validate_description_regex_only,
    validate_description_with_ai,
    ValidationError
)
from minervium.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")

def load_and_validate_config(config_path: str, verbose: bool = False):
    # Step 1: Load configuration
    logger.info("Loading collection configuration...")
    try:
        config = load_collection_config(config_path)
        logger.info(f"   Configuration loaded from: {config_path}")
        logger.info(f"   Json file: {config.json_file}")
        logger.info(f"   ChromaDB path: {config.chromadb_path}")
        logger.info(f"   Chunk size: {config.chunk_size}")
        logger.info(f"   Collection name: {config.collection_name}")
        logger.info(f"   Description: {config.description[:80]}...")
        logger.info(f"   Force recreate: {config.force_recreate}")
        logger.info(f"   Skip AI validation: {config.skip_ai_validation}")
        logger.info("")
    except ConfigError as error:
        logger.error("=" * 60, print_to_stderr=False)
        logger.error("CONFIGURATION ERROR", print_to_stderr=False)
        logger.error("=" * 60, print_to_stderr=False)
        logger.error("")
        logger.error(str(error), print_to_stderr=False)
        logger.error("")
        logger.error(f"Configuration file: {config_path}", print_to_stderr=False)
        logger.error("")
        logger.error("Actionable Steps:", print_to_stderr=False)
        logger.error("  1. Review the error message above for specific issues", print_to_stderr=False)
        logger.error("  2. Check example configurations in collections/ directory", print_to_stderr=False)
        logger.error("  3. Validate JSON syntax using a JSON linter", print_to_stderr=False)
        logger.error("  4. Ensure all required fields are present:", print_to_stderr=False)
        logger.error("     - collection_name, description, chromadb_path, json_file", print_to_stderr=False)
        sys.exit(1)

    # Step 2: Validate collection metadata
    logger.info("Validating collection metadata...")
    try:
        # Validate collection name
        validate_collection_name(config.collection_name)
        logger.info(f"   Collection name validated: {config.collection_name}")

        # Validate description using explicit function based on skip_ai_validation flag
        if config.skip_ai_validation:
            validate_description_regex_only(config.description, config.collection_name)
            validation_result = None

            # Warning when AI validation is skipped
            logger.warning("   WARNING: AI validation was skipped (skipAiValidation: true)")
            logger.warning("   You are responsible for ensuring the description is:")
            logger.warning("     - Clear and specific about when to use this collection")
            logger.warning("     - Detailed enough for accurate AI-powered collection selection")
            logger.warning("     - Not vague or generic (avoid 'various topics', 'miscellaneous', etc.)")
            logger.warning("   Consequences of poor descriptions:")
            logger.warning("     - Reduced accuracy in multi-collection RAG systems")
            logger.warning("     - Confusion when selecting the right collection for queries")
            logger.warning("     - Poor AI routing decisions in production")
        else:
            validation_result = validate_description_with_ai(
                config.description,
                config.collection_name
            )
            logger.info("   Description validated successfully")
            logger.info(f"   AI Quality Score: {validation_result['score']}/10")
        logger.info("")
    except ValidationError as error:
        logger.error("=" * 60, print_to_stderr=False)
        logger.error("VALIDATION ERROR", print_to_stderr=False)
        logger.error("=" * 60, print_to_stderr=False)
        logger.error("")
        logger.error(str(error), print_to_stderr=False)
        logger.error("")
        logger.error(f"Configuration file: {config_path}", print_to_stderr=False)
        logger.error(f"Collection name: {config.collection_name}", print_to_stderr=False)
        logger.error("")
        logger.error("Actionable Steps:", print_to_stderr=False)
        logger.error("  1. Review the validation error details above", print_to_stderr=False)
        logger.error("  2. Fix the collection name or description as needed", print_to_stderr=False)
        logger.error("  3. If AI validation is too strict, consider:", print_to_stderr=False)
        logger.error("     - Improving the description to be more specific", print_to_stderr=False)
        logger.error("     - Adding 'skipAiValidation': true (use with caution)", print_to_stderr=False)
        logger.error("  4. Ensure AI model is available if using AI validation:", print_to_stderr=False)
        logger.error("     $ ollama pull llama3.1:8b", print_to_stderr=False)
        sys.exit(1)

    return config
