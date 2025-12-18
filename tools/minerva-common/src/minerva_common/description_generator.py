import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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

    prompt = _build_description_prompt(sample_titles, sample_content, len(records))

    description = _call_provider(prompt, provider_config)

    return description.strip()


def _build_description_prompt(titles: list[str], content_previews: list[str], total_count: int) -> str:
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


def _call_provider(prompt: str, provider_config: dict[str, Any]) -> str:
    provider_type = provider_config.get("provider_type")
    llm_model = provider_config.get("llm_model")

    if not provider_type or not llm_model:
        raise RuntimeError("Provider configuration must include provider_type and llm_model")

    if provider_type == "openai":
        return _call_openai(prompt, llm_model, provider_config)
    if provider_type == "gemini":
        return _call_gemini(prompt, llm_model, provider_config)
    if provider_type == "ollama":
        return _call_ollama(prompt, llm_model)
    if provider_type == "lmstudio":
        return _call_lmstudio(prompt, llm_model)

    raise RuntimeError(f"Unsupported provider type: {provider_type}")


def _call_openai(prompt: str, model: str, provider_config: dict[str, Any]) -> str:
    api_key = _resolve_api_key(provider_config)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 200,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    return _extract_openai_response(_perform_request(request))


def _call_gemini(prompt: str, model: str, provider_config: dict[str, Any]) -> str:
    api_key = _resolve_api_key(provider_config)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 200,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return _extract_gemini_response(_perform_request(request))


def _call_ollama(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    request = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return _extract_ollama_response(_perform_request(request))


def _call_lmstudio(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 200,
    }
    request = urllib.request.Request(
        "http://localhost:1234/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return _extract_openai_response(_perform_request(request))


def _perform_request(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            data = response.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as exc:  # noqa: PERF203
        body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection error: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse provider response") from exc


def _extract_openai_response(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not choices:
        raise RuntimeError("Provider returned no choices")
    message = choices[0].get("message", {})
    content = message.get("content", "").strip()
    if not content:
        raise RuntimeError("Provider returned empty description")
    return _sanitize_description(content)


def _extract_gemini_response(data: dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Provider returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [part.get("text", "") for part in parts if part.get("text")]
    if not texts:
        raise RuntimeError("Provider returned empty description")
    return _sanitize_description("\n".join(texts))


def _extract_ollama_response(data: dict[str, Any]) -> str:
    message = data.get("message") or {}
    content = message.get("content", "").strip()
    if not content:
        raise RuntimeError("Provider returned empty description")
    return _sanitize_description(content)


def _sanitize_description(value: str) -> str:
    cleaned = value.strip().strip('"').strip("'")
    return cleaned


def _resolve_api_key(provider_config: dict[str, Any]) -> str:
    reference = provider_config.get("api_key")
    if not reference:
        raise RuntimeError("Provider requires API key but none configured")

    # Extract environment variable name
    env_var = _extract_env_var_name(reference)

    # Try environment variable first
    secret = os.environ.get(env_var)
    if secret:
        return secret

    raise RuntimeError(
        f"Missing API key '{env_var}' in environment. "
        f"Set it with: export {env_var}=your-key-here"
    )


def _extract_env_var_name(reference: str) -> str:
    value = reference.strip()
    if value.startswith("${") and value.endswith("}"):
        return value[2:-1]
    return value


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
