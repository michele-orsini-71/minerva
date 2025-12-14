import json
from pathlib import Path
from typing import Any

from minerva.common.ai_provider import AIProvider
from minerva.common.ai_config import AIProviderConfig


def generate_description_from_records(
    json_file: str | Path, provider_config: dict[str, Any], max_samples: int = 10
) -> str:
    with open(json_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("JSON file must contain a list of records")

    if not records:
        raise ValueError("JSON file contains no records")

    sample_records = records[:max_samples]

    sample_titles = [record.get("title", "Untitled") for record in sample_records]
    sample_content = []
    for record in sample_records:
        markdown = record.get("markdown", "")
        if markdown:
            preview = markdown[:200] + ("..." if len(markdown) > 200 else "")
            sample_content.append(preview)

    prompt = build_description_prompt(sample_titles, sample_content, len(records))

    ai_config = AIProviderConfig(
        provider_type=provider_config["provider_type"],
        embedding_model=provider_config["embedding_model"],
        llm_model=provider_config["llm_model"],
        base_url=provider_config.get("base_url"),
        api_key=provider_config.get("api_key"),
    )

    provider = AIProvider(ai_config)

    messages = [{"role": "user", "content": prompt}]

    response = provider.chat_completion(messages, temperature=0.7, max_tokens=200)

    content = extract_content_from_response(response)

    return content.strip()


def build_description_prompt(titles: list[str], content_previews: list[str], total_count: int) -> str:
    prompt_parts = [
        f"Generate a concise, informative description (1-2 sentences) for a collection of {total_count} documents.",
        "",
        "Sample document titles:",
    ]

    for i, title in enumerate(titles[:5], 1):
        prompt_parts.append(f"  {i}. {title}")

    if content_previews:
        prompt_parts.append("")
        prompt_parts.append("Sample content previews:")
        for i, preview in enumerate(content_previews[:3], 1):
            prompt_parts.append(f"  {i}. {preview}")

    prompt_parts.extend(
        [
            "",
            "Requirements:",
            "- Be specific about the subject matter and content type",
            "- Keep it concise (1-2 sentences, max 200 characters)",
            "- Focus on what the collection contains, not how it's organized",
            "- Do not include formatting, metadata, or explanations",
            "",
            "Description:",
        ]
    )

    return "\n".join(prompt_parts)


def extract_content_from_response(response: dict[str, Any]) -> str:
    try:
        choices = response.get("choices", [])
        if not choices:
            raise ValueError("No choices in response")

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content", "")

        if not content:
            raise ValueError("No content in response message")

        return content

    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Invalid response structure: {e}") from e


def prompt_for_description(
    json_file: str | Path, provider_config: dict[str, Any], auto_generate: bool = True
) -> str:
    print()
    print("📝 Collection Description")
    print("=" * 40)
    print("Enter a description for this collection.")
    print("Press Enter to auto-generate using AI.")
    print()

    user_input = input("Description: ").strip()

    if user_input:
        return user_input

    if not auto_generate:
        return ""

    print()
    print("⏳ Generating description using AI...")

    try:
        generated = generate_description_from_records(json_file, provider_config)

        print()
        print(f"Generated: {generated}")
        print()

        confirm = input("Use this description? [Y/n]: ").strip().lower()

        if confirm in {"n", "no"}:
            user_input = input("Enter your own description: ").strip()
            return user_input if user_input else generated

        return generated

    except Exception as e:
        print(f"❌ Failed to generate description: {e}")
        print()
        user_input = input("Enter a description manually: ").strip()
        return user_input if user_input else "Collection of documents"
