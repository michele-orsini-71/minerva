import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

README_NAME = "README.md"
README_PREVIEW_CHARS = 4000
PROMPT_TEMPLATE = (
    "Generate a 1-2 sentence description optimized for RAG search collections. "
    "Use the details below to craft clear, specific language that helps users understand what "
    "this repository contains and which questions it can answer."
    "\n\n"
    "Repository Name: {collection_name}\n"
    "Source Type: {source_type}\n"
    "Source Content:\n{content}\n\n"
    "Instructions:\n"
    "1. First sentence: Describe the type of content, primary technologies, and core purpose.\n"
    "2. Second sentence: Start with 'Best for questions about' and list 5-7 use cases separated by commas.\n"
    "3. Combine technology-specific use cases with generic ones like architecture, API design, testing, setup, and troubleshooting.\n"
    "4. Output only the final description without quotes or bullet points."
)


def generate_description(repo_path: Path | str, collection_name: str, provider_config: dict[str, Any]) -> str:
    repository = Path(repo_path)
    print("💬 Collection Description")
    print("=" * 60)

    source_type, content = _prepare_source_text(repository)
    prompt = PROMPT_TEMPLATE.format(
        collection_name=collection_name,
        source_type=source_type,
        content=content,
    )

    print("🤖 Generating optimized description...")
    description = _call_provider(prompt, provider_config)
    _display_generated_description(description)
    return description


def _prepare_source_text(repository: Path) -> tuple[str, str]:
    readme_path = repository / README_NAME
    if readme_path.exists() and readme_path.is_file():
        print(f"📄 Found {README_NAME} in repository")
        raw = readme_path.read_text(encoding="utf-8", errors="ignore")
        content = raw[:README_PREVIEW_CHARS]
        return "README", content

    print("ℹ️  No README.md found in repository")
    print("Please describe what's in this repository so AI can optimize it.")
    print("Examples:")
    print("  • Python web framework with REST API and documentation")
    print("  • React component library for dashboards")
    print("  • Internal documentation for infrastructure setup")

    while True:
        user_input = input("Brief description: ").strip()
        if user_input:
            return "USER_INPUT", user_input
        print("❌ Description cannot be empty")


def _display_generated_description(description: str) -> None:
    print()
    print("✨ Generated description:")
    for line in description.splitlines():
        print(f"   {line}")
    print()
    print("✓ Description ready")
    print()


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
        "temperature": 0.4,
        "max_tokens": 320,
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
            "temperature": 0.4,
            "maxOutputTokens": 320,
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
        "temperature": 0.4,
        "max_tokens": 320,
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
    except urllib.error.HTTPError as exc:  # noqa: PERF203 - explicit error path
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
        key_name = provider_config.get("api_key_name")
        if not key_name:
            raise RuntimeError("Provider requires API key but none configured")
        reference = key_name

    env_var = _extract_env_var_name(reference)
    secret = os.environ.get(env_var)
    if secret:
        return secret

    result = subprocess.run(
        ["minerva", "keychain", "get", env_var],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        raise RuntimeError(
            f"Missing API key '{env_var}' in keychain. Run 'minerva keychain set {env_var}'."
        )
    os.environ[env_var] = output
    return output


def _extract_env_var_name(reference: str) -> str:
    value = reference.strip()
    if value.startswith("${") and value.endswith("}"):
        return value[2:-1]
    return value
