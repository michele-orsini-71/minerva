import re
import sys
from typing import Dict, Any, Optional, Tuple

try:
    from ollama import chat as ollama_chat
    from ollama import list as ollama_list
except ImportError:
    print("Error: ollama library not installed. Run: pip install ollama", file=sys.stderr)
    sys.exit(1)


class ValidationError(Exception):
    """Exception raised when validation fails."""
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
    vague_terms_found = [term for term in VAGUE_DESCRIPTIONS_BLACKLIST if term in description_lower]
    if vague_terms_found:
        # Warning only if description is mostly vague terms
        if len(" ".join(vague_terms_found)) / len(description) > 0.3:
            raise ValidationError(
                f"Description for collection '{collection_name}' is too vague\n"
                f"  Vague terms found: {', '.join(vague_terms_found)}\n"
                f"  Suggestion: Be more specific about:\n"
                f"    - What TYPE of content is in the collection\n"
                f"    - What TOPICS or DOMAINS it covers\n"
                f"    - What QUESTIONS it can answer\n"
                f"  Example: Instead of 'general documents', say 'technical documentation for Python libraries'\n"
                f"  Example: Instead of 'various information', say 'historical articles about European Renaissance'"
            )


def check_model_availability(model_name: str = AI_MODEL) -> bool:
    try:
        models_response = ollama_list()
        # Handle both dict and object responses from ollama
        if hasattr(models_response, 'models'):
            models_list = models_response.models
        elif isinstance(models_response, dict):
            models_list = models_response.get('models', [])
        else:
            return False

        # Extract model names (handle both dict and object models)
        available_models = []
        for m in models_list:
            if hasattr(m, 'model'):
                available_models.append(m.model)
            elif isinstance(m, dict) and 'name' in m:
                available_models.append(m['name'])

        # Check if model is in the list (handle with or without :latest suffix)
        return any(model_name in model or model in model_name for model in available_models)
    except Exception:
        return False


def validate_with_ai(description: str, collection_name: str, model: str = AI_MODEL) -> Tuple[int, str, str]:
    # Check model availability first
    if not check_model_availability(model):
        raise ValidationError(
            f"AI model '{model}' not available for validation\n"
            f"  Suggestion: Pull the model first:\n"
            f"    ollama pull {model}\n"
            f"  Or skip AI validation by setting:\n"
            f'    "skipAiValidation": true\n'
            f"  in your configuration file"
        )

    try:
        # Call Ollama with the validation prompt
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

        response_text = response['message']['content'].strip()

        # Parse JSON response
        import json
        try:
            # Try to extract JSON from response (handle cases where model adds extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)

            result = json.loads(response_text)
            score = result.get('score', 0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            suggestions = result.get('suggestions', '')

        except json.JSONDecodeError:
            raise ValidationError(
                f"AI model returned invalid response format\n"
                f"  Response: {response_text[:200]}...\n"
                f"  Suggestion: Try again or skip AI validation with 'skipAiValidation': true"
            )

        # Validate score is in range
        if not isinstance(score, (int, float)) or score < 0 or score > 10:
            raise ValidationError(
                f"AI model returned invalid score: {score}\n"
                f"  Expected: number between 0-10\n"
                f"  Suggestion: Try again or skip AI validation with 'skipAiValidation': true"
            )

        return (int(score), reasoning, suggestions)

    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(
            f"AI validation failed: {e}\n"
            f"  Suggestion: Check Ollama is running (ollama serve) or skip AI validation with 'skipAiValidation': true"
        )


def validate_description_hybrid(
    description: str,
    collection_name: str,
    skip_ai_validation: bool = False,
    model: str = AI_MODEL
) -> Optional[Dict[str, Any]]:
    # Step 1: Mandatory regex validation
    validate_description_regex(description, collection_name)

    # Step 2: Optional AI validation
    if skip_ai_validation:
        print(f"   AI validation skipped for collection '{collection_name}'")
        print(f"   You are responsible for ensuring the description is:")
        print(f"   - Clear and specific (not vague)")
        print(f"   - Actionable (explains when to use this collection)")
        print(f"   - Distinguishable from other collections")
        return None

    print(f"Running AI validation for collection '{collection_name}'...")
    score, reasoning, suggestions = validate_with_ai(description, collection_name, model)

    print(f"   AI Score: {score}/10")
    print(f"   Reasoning: {reasoning}")

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
            f"    2. Skip AI validation by setting 'skipAiValidation': true\n"
            f"       (use this if you believe AI is being too strict)\n"
        )

        raise ValidationError(error_msg)

    print(f"   Description passed AI validation")

    return {
        'score': score,
        'reasoning': reasoning,
        'suggestions': suggestions
    }


if __name__ == "__main__":
    # Simple tests when run directly
    print("Testing validation.py module")
    print("=" * 60)

    # Test 1: Valid collection name
    print("\n📋 Test 1: Valid collection names")
    try:
        validate_collection_name("bear_notes")
        validate_collection_name("project-docs")
        validate_collection_name("team123")
        validate_collection_name("research_papers_2024")
        print("   All valid names passed")
    except ValidationError as e:
        print(f"   Valid names failed: {e}")
        sys.exit(1)

    # Test 2: Invalid collection names
    print("\n📋 Test 2: Invalid collection names")
    invalid_names = ["-invalid", "_invalid", "invalid space", "invalid@name", "a" * 64]
    for name in invalid_names:
        try:
            validate_collection_name(name)
            print(f"   Should have rejected: {name}")
            sys.exit(1)
        except ValidationError:
            print(f"   Correctly rejected: {name}")

    # Test 3: Description too short
    print("\n📋 Test 3: Description length validation")
    try:
        validate_description_regex("short", "test")
        print("   Should have rejected short description")
        sys.exit(1)
    except ValidationError:
        print("   Correctly rejected short description")

    # Test 4: Description missing required phrase
    print("\n📋 Test 4: Required phrase validation")
    try:
        validate_description_regex("A" * 100, "test")  # Long but no required phrase
        print("   Should have rejected description without required phrase")
        sys.exit(1)
    except ValidationError:
        print("   Correctly rejected description without required phrase")

    # Test 5: Valid description
    print("\n📋 Test 5: Valid description")
    try:
        validate_description_regex(
            "Use this collection when searching for personal notes and ideas from Bear Notes app. "
            "Contains project notes, research, and daily thoughts.",
            "bear_notes"
        )
        print("   Valid description passed")
    except ValidationError as e:
        print(f"   Valid description failed: {e}")
        sys.exit(1)

    # Test 6: Check model availability
    print("\n📋 Test 6: Check AI model availability")
    is_available = check_model_availability(AI_MODEL)
    if is_available:
        print(f"   AI model '{AI_MODEL}' is available")
    else:
        print(f"   AI model '{AI_MODEL}' is not available")
        print(f"   Run: ollama pull {AI_MODEL}")

    # Test 7: AI validation (only if model is available)
    if is_available:
        print("\n📋 Test 7: AI validation")
        try:
            score, reasoning, suggestions = validate_with_ai(
                "Use this collection when searching through personal notes from Bear Notes app. "
                "Contains my private notes about projects, ideas, research, and daily thoughts.",
                "bear_notes"
            )
            print(f"   AI validation completed:")
            print(f"   Score: {score}/10")
            print(f"   Reasoning: {reasoning[:80]}...")
        except ValidationError as e:
            print(f"   AI validation error: {e}")
    else:
        print("\n📋 Test 7: Skipping AI validation (model not available)")

    print("\n🎉 All validation.py tests completed!")
