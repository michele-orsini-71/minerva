from minerva.common.exceptions import ConfigError, ValidationError
from minerva.common.index_config import load_index_config
from minerva.common.validation import (
    validate_collection_name,
    validate_description_regex_only,
    validate_description_with_ai,
)
from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")

def load_and_validate_config(config_path: str, verbose: bool = False):
    logger.info("Loading collection configuration...")
    try:
        index_config = load_index_config(config_path)
        collection = index_config.collection
        logger.info(f"   Configuration loaded from: {config_path}")
        logger.info(f"   Json file: {collection.json_file}")
        logger.info(f"   ChromaDB path: {index_config.chromadb_path}")
        logger.info(f"   Chunk size: {collection.chunk_size}")
        logger.info(f"   Collection name: {collection.name}")
        logger.info(f"   Description: {collection.description[:80]}...")
        logger.info(f"   Force recreate: {collection.force_recreate}")
        logger.info(f"   Skip AI validation: {collection.skip_ai_validation}")
        logger.info("")
    except ConfigError as error:
        logger.error("=" * 60)
        logger.error("CONFIGURATION ERROR")
        logger.error("=" * 60)
        logger.error("")
        logger.error(str(error))
        logger.error("")
        logger.error(f"Configuration file: {config_path}")
        logger.error("")
        logger.error("Actionable Steps:")
        logger.error("  1. Review the error message above for specific issues")
        logger.error("  2. Check example configurations in collections/ directory")
        logger.error("  3. Validate JSON syntax using a JSON linter")
        logger.error("  4. Ensure all required fields are present:")
        logger.error("     - collection_name, description, chromadb_path, json_file")
        raise

    logger.info("Validating collection metadata...")
    try:
        validate_collection_name(collection.name)
        logger.info(f"   Collection name validated: {collection.name}")

        if collection.skip_ai_validation:
            validate_description_regex_only(collection.description, collection.name)

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
                collection.description,
                collection.name
            )
            logger.info("   Description validated successfully")
            logger.info(f"   AI Quality Score: {validation_result['score']}/10")
        logger.info("")
    except ValidationError as error:
        logger.error("=" * 60)
        logger.error("VALIDATION ERROR")
        logger.error("=" * 60)
        logger.error("")
        logger.error(str(error))
        logger.error("")
        logger.error(f"Configuration file: {config_path}")
        logger.error(f"Collection name: {collection.name}")
        logger.error("")
        logger.error("Actionable Steps:")
        logger.error("  1. Review the validation error details above")
        logger.error("  2. Fix the collection name or description as needed")
        logger.error("  3. If AI validation is too strict, consider:")
        logger.error("     - Improving the description to be more specific")
        logger.error("     - Adding 'skipAiValidation': true (use with caution)")
        logger.error("  4. Ensure AI model is available if using AI validation:")
        logger.error("     $ ollama pull llama3.1:8b")
        raise

    return index_config
