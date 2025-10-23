import re
import sys
from typing import Dict, Any, Optional, Tuple

from minerva.common.logger import get_logger

logger = get_logger(__name__, simple=True, mode="cli")

try:
    from ollama import chat as ollama_chat
    from ollama import list as ollama_list
except ImportError as error:
    logger.error("ollama library not installed. Run: pip install ollama")
    raise SystemExit(1) from error


class ValidationError(Exception):
    pass


# Constants for validation rules
COLLECTION_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'
COLLECTION_NAME_MAX_LENGTH = 63
DESCRIPTION_MIN_LENGTH = 50
DESCRIPTION_MAX_LENGTH = 1000

# Required phrases for description (at least one must be present)
REQUIRED_PHRASES = [
    "use this when",
    "use this collection when",
    "use this collection for",
    "this collection contains",
    "search this when",
    "query this when",
    "ideal for",
    "best for"
]

# Vague descriptions that should be rejected
VAGUE_DESCRIPTIONS_BLACKLIST = [
    "general purpose",
    "miscellaneous",
    "various things",
    "stuff",
    "documents",
    "files",
    "data",
    "information",
    "content"
]

# AI validation configuration
AI_MODEL = "llama3.1:8b"
AI_VALIDATION_THRESHOLD = 7
AI_VALIDATION_PROMPT = """You are a technical reviewer evaluating collection descriptions for a RAG (Retrieval-Augmented Generation) system.

Evaluate the following collection description for clarity, specificity, and actionability.

Collection Name: {collection_name}
Description: {description}

Scoring criteria:
1. Clarity: Is it immediately clear what content this collection contains?
2. Specificity: Does it avoid vague terms like "general purpose", "miscellaneous", "various things"?
3. Actionability: Does it clearly explain WHEN to search this collection vs others?
4. Completeness: Does it describe the content type, use cases, and search scenarios?

Rate this description on a scale of 0-10:
- 0-3: Vague, unclear, not actionable
- 4-6: Somewhat clear but missing important details
- 7-8: Clear, specific, and actionable
- 9-10: Excellent - crystal clear with comprehensive guidance

Respond with ONLY a JSON object in this exact format:
{{"score": <number 0-10>, "reasoning": "<brief explanation>", "suggestions": "<improvements if score < 7>"}}

Do not include any text before or after the JSON object."""


def validate_collection_name(name: str) -> None:
    if not name:
        raise ValidationError(
            "Collection name cannot be empty\n"
            "  Suggestion: Provide a descriptive name like 'bear_notes' or 'project-docs'"
        )

    if len(name) > COLLECTION_NAME_MAX_LENGTH:
        raise ValidationError(
            f"Collection name too long: {len(name)} characters (max: {COLLECTION_NAME_MAX_LENGTH})\n"
            f"  Name: {name}\n"
            f"  Suggestion: Use a shorter, more concise name"
        )

    if not re.match(COLLECTION_NAME_PATTERN, name):
        raise ValidationError(
            f"Invalid collection name: {name}\n"
            f"  Pattern requirements:\n"
            f"    - Must start with alphanumeric character (a-z, A-Z, 0-9)\n"
            f"    - Can contain: letters, numbers, underscores, hyphens\n"
            f"    - Cannot start with underscore or hyphen\n"
            f"  Valid examples:\n"
            f"    ✓ bear_notes\n"
            f"    ✓ project-docs\n"
            f"    ✓ team123\n"
            f"    ✓ research_papers_2024\n"
            f"  Invalid examples:\n"
            f"    ✗ -invalid (starts with hyphen)\n"
            f"    ✗ _invalid (starts with underscore)\n"
            f"    ✗ invalid space (contains space)\n"
            f"    ✗ invalid@name (special characters)"
        )


def validate_description_regex(description: str, collection_name: str) -> None:
    if not description:
        raise ValidationError(
            f"Description cannot be empty for collection '{collection_name}'\n"
            f"  Suggestion: Add a detailed description explaining when to use this collection"
        )

    if len(description) < DESCRIPTION_MIN_LENGTH:
        raise ValidationError(
            f"Description too short for collection '{collection_name}'\n"
            f"  Current length: {len(description)} characters\n"
            f"  Minimum required: {DESCRIPTION_MIN_LENGTH} characters\n"
            f"  Suggestion: Expand the description to include:\n"
            f"    - What content the collection contains\n"
            f"    - When to search this collection\n"
            f"    - Example use cases or search scenarios"
        )

    if len(description) > DESCRIPTION_MAX_LENGTH:
        raise ValidationError(
            f"Description too long for collection '{collection_name}'\n"
            f"  Current length: {len(description)} characters\n"
            f"  Maximum allowed: {DESCRIPTION_MAX_LENGTH} characters\n"
            f"  Suggestion: Make the description more concise while keeping key details"
        )

    # Check for required phrases
    description_lower = description.lower()
    has_required_phrase = any(phrase in description_lower for phrase in REQUIRED_PHRASES)

    if not has_required_phrase:
        raise ValidationError(
            f"Description for collection '{collection_name}' must include guidance on when to use it\n"
            f"  Required: Include at least one of these phrases:\n" +
            "".join(f"    - \"{phrase}\"\n" for phrase in REQUIRED_PHRASES) +
            f"  Suggestion: Start with 'Use this collection when...' or 'This collection contains...'"
        )

    # Check for vague descriptions
    blacklisted_terms_in_description = [term for term in VAGUE_DESCRIPTIONS_BLACKLIST if term in description_lower]
    if blacklisted_terms_in_description:
        # Warning only if description is mostly vague terms
        if len(" ".join(blacklisted_terms_in_description)) / len(description) > 0.3:
            raise ValidationError(
                f"Description for collection '{collection_name}' is too vague\n"
                f"  Vague terms found: {', '.join(blacklisted_terms_in_description)}\n"
                f"  Suggestion: Be more specific about:\n"
                f"    - What TYPE of content is in the collection\n"
                f"    - What TOPICS or DOMAINS it covers\n"
                f"    - What QUESTIONS it can answer\n"
                f"  Example: Instead of 'general documents', say 'technical documentation for Python libraries'\n"
                f"  Example: Instead of 'various information', say 'historical articles about European Renaissance'"
            )


def extract_models_list(models_response):
    if hasattr(models_response, 'models'):
        return models_response.models

    if isinstance(models_response, dict):
        return models_response.get('models', [])

    return None


def extract_model_name(model_entry):
    if hasattr(model_entry, 'model'):
        return model_entry.model

    if isinstance(model_entry, dict) and 'name' in model_entry:
        return model_entry['name']

    return None


def is_model_match(model_name: str, available_model: str) -> bool:
    return model_name in available_model or available_model in model_name


def check_model_availability(model_name: str = AI_MODEL) -> bool:
    try:
        models_response = ollama_list()
        models_list = extract_models_list(models_response)

        if not models_list:
            return False

        available_models = [extract_model_name(m) for m in models_list]
        available_models = [name for name in available_models if name is not None]

        return any(is_model_match(model_name, model) for model in available_models)
    except Exception:
        return False


def extract_json_from_response(response_text: str) -> str:
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return response_text


def parse_ai_validation_response(response_text: str) -> Tuple[int, str, str]:
    import json

    try:
        cleaned_response = extract_json_from_response(response_text)
        result = json.loads(cleaned_response)

        score = result.get('score', 0)
        reasoning = result.get('reasoning', 'No reasoning provided')
        suggestions = result.get('suggestions', '')

        return (score, reasoning, suggestions)
    except json.JSONDecodeError:
        raise ValidationError(
            f"AI model returned invalid response format\n"
            f"  Response: {response_text[:200]}...\n"
            f"  Suggestion: Try again or skip AI validation with 'skipAiValidation': true"
        )


def validate_ai_score(score: Any) -> int:
    if not isinstance(score, (int, float)) or score < 0 or score > 10:
        raise ValidationError(
            f"AI model returned invalid score: {score}\n"
            f"  Expected: number between 0-10\n"
            f"  Suggestion: Try again or skip AI validation with 'skipAiValidation': true"
        )
    return int(score)


def call_ollama_ai(description: str, collection_name: str, model: str) -> str:
    prompt = AI_VALIDATION_PROMPT.format(
        collection_name=collection_name,
        description=description
    )

    response = ollama_chat(
        model=model,
        messages=[{
            'role': 'user',
            'content': prompt
        }],
        options={
            'temperature': 0.1,  # Low temperature for consistent scoring
            'num_predict': 500
        }
    )

    return response['message']['content'].strip()


def check_model_availability_or_raise(model: str) -> None:
    if not check_model_availability(model):
        raise ValidationError(
            f"AI model '{model}' not available for validation\n"
            f"  Suggestion: Pull the model first:\n"
            f"    ollama pull {model}\n"
            f"  Or skip AI validation by setting:\n"
            f'    "skipAiValidation": true\n'
            f"  in your configuration file"
        )


def wrap_generic_ai_error(error: Exception) -> ValidationError:
    if isinstance(error, ValidationError):
        return error

    return ValidationError(
        f"AI validation failed: {error}\n"
        f"  Suggestion: Check Ollama is running (ollama serve) or skip AI validation with 'skipAiValidation': true"
    )


def validate_with_ai(description: str, collection_name: str, model: str = AI_MODEL) -> Tuple[int, str, str]:
    check_model_availability_or_raise(model)

    try:
        response_text = call_ollama_ai(description, collection_name, model)
        score, reasoning, suggestions = parse_ai_validation_response(response_text)
        validated_score = validate_ai_score(score)
        return (validated_score, reasoning, suggestions)
    except Exception as error:
        raise wrap_generic_ai_error(error)


def validate_description_regex_only(
    description: str,
    collection_name: str
) -> None:
    # Mandatory regex validation
    validate_description_regex(description, collection_name)

    logger.info("   Description validated (regex only)")
    logger.warning("   NOTE: AI validation was skipped")
    logger.warning("   Ensure your description is:")
    logger.warning("     - Clear and specific (not vague)")
    logger.warning("     - Actionable (explains when to use this collection)")
    logger.warning("     - Distinguishable from other collections")


def validate_description_with_ai(
    description: str,
    collection_name: str,
    model: str = AI_MODEL
) -> Dict[str, Any]:
    validate_description_regex(description, collection_name)

    logger.info(f"Running AI validation for collection '{collection_name}'...")
    score, reasoning, suggestions = validate_with_ai(description, collection_name, model)

    logger.info(f"   AI Score: {score}/10")
    logger.info(f"   Reasoning: {reasoning}")

    if score < AI_VALIDATION_THRESHOLD:
        error_msg = (
            f"Description quality below threshold for collection '{collection_name}'\n"
            f"  AI Score: {score}/10 (threshold: {AI_VALIDATION_THRESHOLD}/10)\n"
            f"  Reasoning: {reasoning}\n"
        )

        if suggestions:
            error_msg += f"  Suggestions: {suggestions}\n"

        error_msg += (
            f"\n"
            f"  Options:\n"
            f"    1. Improve the description based on AI feedback\n"
            f"    2. Use validate_description_regex_only() if you believe AI is too strict\n"
        )

        raise ValidationError(error_msg)

    logger.success("   Description passed AI validation")

    return {
        'score': score,
        'reasoning': reasoning,
        'suggestions': suggestions
    }


# Backward compatibility: Keep old function but mark as deprecated
def validate_description_hybrid(
    description: str,
    collection_name: str,
    skip_ai_validation: bool = False,
    model: str = AI_MODEL
) -> Optional[Dict[str, Any]]:
    if skip_ai_validation:
        validate_description_regex_only(description, collection_name)
        return None
    else:
        return validate_description_with_ai(description, collection_name, model)


if __name__ == "__main__":
    # Simple tests when run directly
    logger.info("Testing validation.py module")
    logger.info("=" * 60)

    # Test 1: Valid collection name
    logger.info("")
    logger.info("📋 Test 1: Valid collection names")
    try:
        validate_collection_name("bear_notes")
        validate_collection_name("project-docs")
        validate_collection_name("team123")
        validate_collection_name("research_papers_2024")
        logger.success("   All valid names passed")
    except ValidationError as error:
        logger.error(f"   Valid names failed: {error}", print_to_stderr=False)
        sys.exit(1)

    # Test 2: Invalid collection names
    logger.info("")
    logger.info("📋 Test 2: Invalid collection names")
    invalid_names = ["-invalid", "_invalid", "invalid space", "invalid@name", "a" * 64]
    for name in invalid_names:
        try:
            validate_collection_name(name)
            logger.error(f"   Should have rejected: {name}", print_to_stderr=False)
            sys.exit(1)
        except ValidationError:
            logger.success(f"   Correctly rejected: {name}")

    # Test 3: Description too short
    logger.info("")
    logger.info("📋 Test 3: Description length validation")
    try:
        validate_description_regex("short", "test")
        logger.error("   Should have rejected short description", print_to_stderr=False)
        sys.exit(1)
    except ValidationError:
        logger.success("   Correctly rejected short description")

    # Test 4: Description missing required phrase
    logger.info("")
    logger.info("📋 Test 4: Required phrase validation")
    try:
        validate_description_regex("A" * 100, "test")  # Long but no required phrase
        logger.error("   Should have rejected description without required phrase", print_to_stderr=False)
        sys.exit(1)
    except ValidationError:
        logger.success("   Correctly rejected description without required phrase")

    # Test 5: Valid description
    logger.info("")
    logger.info("📋 Test 5: Valid description")
    try:
        validate_description_regex(
            "Use this collection when searching for personal notes and ideas from Bear Notes app. "
            "Contains project notes, research, and daily thoughts.",
            "bear_notes"
        )
        logger.success("   Valid description passed")
    except ValidationError as error:
        logger.error(f"   Valid description failed: {error}", print_to_stderr=False)
        sys.exit(1)

    # Test 6: Check model availability
    logger.info("")
    logger.info("📋 Test 6: Check AI model availability")
    is_available = check_model_availability(AI_MODEL)
    if is_available:
        logger.success(f"   AI model '{AI_MODEL}' is available")
    else:
        logger.warning(f"   AI model '{AI_MODEL}' is not available")
        logger.warning(f"   Run: ollama pull {AI_MODEL}")

    # Test 7: AI validation (only if model is available)
    if is_available:
        logger.info("")
        logger.info("📋 Test 7: AI validation")
        try:
            score, reasoning, suggestions = validate_with_ai(
                "Use this collection when searching through personal notes from Bear Notes app. "
                "Contains my private notes about projects, ideas, research, and daily thoughts.",
                "bear_notes"
            )
            logger.success("   AI validation completed:")
            logger.info(f"   Score: {score}/10")
            logger.info(f"   Reasoning: {reasoning[:80]}...")
        except ValidationError as error:
            logger.error(f"   AI validation error: {error}", print_to_stderr=False)
    else:
        logger.info("")
        logger.info("📋 Test 7: Skipping AI validation (model not available)")

    logger.success("\n🎉 All validation.py tests completed!")
