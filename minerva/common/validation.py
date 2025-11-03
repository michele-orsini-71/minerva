import re
import sys
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

from minerva.common.exceptions import ValidationError
from minerva.common.logger import get_logger

if TYPE_CHECKING:
    from minerva.common.ai_provider import AIProvider

logger = get_logger(__name__, simple=True, mode="cli")

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


def call_llm_for_validation(provider: 'AIProvider', description: str, collection_name: str) -> str:
    prompt = AI_VALIDATION_PROMPT.format(
        collection_name=collection_name,
        description=description
    )

    messages = [{'role': 'user', 'content': prompt}]
    response = provider.chat_completion(messages, temperature=0.1, max_tokens=500)

    return response['content'].strip()


def wrap_generic_ai_error(error: Exception, provider_type: str) -> ValidationError:
    if isinstance(error, ValidationError):
        return error

    return ValidationError(
        f"AI validation failed: {error}\n"
        f"  Provider: {provider_type}\n"
        f"  Suggestion: Ensure the AI provider is available or skip AI validation with 'skip_ai_validation': true"
    )


def validate_with_ai(provider: 'AIProvider', description: str, collection_name: str) -> Tuple[int, str, str]:
    try:
        response_text = call_llm_for_validation(provider, description, collection_name)
        score, reasoning, suggestions = parse_ai_validation_response(response_text)
        validated_score = validate_ai_score(score)
        return (validated_score, reasoning, suggestions)
    except Exception as error:
        raise wrap_generic_ai_error(error, provider.provider_type)


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
    provider: 'AIProvider',
    description: str,
    collection_name: str
) -> Dict[str, Any]:
    validate_description_regex(description, collection_name)

    logger.info(f"Running AI validation for collection '{collection_name}'...")
    logger.info(f"   Provider: {provider.provider_type}")
    logger.info(f"   Model: {provider.llm_model}")

    score, reasoning, suggestions = validate_with_ai(provider, description, collection_name)

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
            f"    2. Skip AI validation with 'skip_ai_validation': true in your config\n"
        )

        raise ValidationError(error_msg)

    logger.success("   Description passed AI validation")

    return {
        'score': score,
        'reasoning': reasoning,
        'suggestions': suggestions
    }


def validate_description_hybrid(
    provider: Optional['AIProvider'],
    description: str,
    collection_name: str,
    skip_ai_validation: bool = False
) -> Optional[Dict[str, Any]]:
    if skip_ai_validation or provider is None:
        validate_description_regex_only(description, collection_name)
        return None
    else:
        return validate_description_with_ai(provider, description, collection_name)


