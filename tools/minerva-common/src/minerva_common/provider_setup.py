import os
import urllib.error
import urllib.request
from typing import Any

PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "gemini": "Google Gemini",
    "ollama": "Ollama",
    "lmstudio": "LM Studio",
}

DEFAULT_PROVIDER_MODELS = {
    "openai": {
        "embedding_model": "text-embedding-3-small",
        "llm_model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
    "gemini": {
        "embedding_model": "text-embedding-004",
        "llm_model": "gemini-1.5-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "ollama": {
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "api_key_env": None,
    },
    "lmstudio": {
        "embedding_model": None,
        "llm_model": None,
        "api_key_env": None,
    },
}

LOCAL_PROVIDER_ENDPOINTS = {
    "ollama": {
        "url": "http://localhost:11434/api/tags",
        "instruction": "Run 'ollama serve' to start the Ollama API",
    },
    "lmstudio": {
        "url": "http://localhost:1234/v1/models",
        "instruction": "Open LM Studio and ensure the local server is running",
    },
}


def select_provider_interactive() -> dict[str, Any]:
    while True:
        provider_type = prompt_provider_choice()
        model_config = prompt_for_models(provider_type)
        embedding_model = model_config["embedding_model"].strip()
        llm_model = model_config["llm_model"].strip()

        if not embedding_model or not llm_model:
            print("❌ Model names must be non-empty strings")
            continue

        config = build_provider_config(provider_type, embedding_model, llm_model)

        is_valid, error = validate_provider_config(config)
        if not is_valid:
            print(f"❌ {error}")
            retry = input("Select a different provider? [y/N]: ").strip().lower()
            if retry in {"y", "yes"}:
                continue
            raise RuntimeError(f"Provider validation failed: {error}")

        return config


def prompt_provider_choice() -> str:
    print("🤖 AI Provider Selection")
    print("=" * 60)
    print()
    print("Which AI provider do you want to use?")
    print()
    print("  1. OpenAI (cloud, requires API key)")
    print("     • Default embedding: text-embedding-3-small")
    print("     • Default LLM: gpt-4o-mini")
    print()
    print("  2. Google Gemini (cloud, requires API key)")
    print("     • Default embedding: text-embedding-004")
    print("     • Default LLM: gemini-1.5-flash")
    print()
    print("  3. Ollama (local, free, no API key)")
    print("     • Default embedding: mxbai-embed-large:latest")
    print("     • Default LLM: llama3.1:8b")
    print()
    print("  4. LM Studio (local, free, no API key)")
    print("     • Enter the model names you loaded in LM Studio")
    print()

    valid_choices = {"1": "openai", "2": "gemini", "3": "ollama", "4": "lmstudio"}

    while True:
        choice = input("Choice [1-4, default 1]: ").strip()
        if not choice:
            return valid_choices["1"]
        if choice in valid_choices:
            return valid_choices[choice]
        print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")


def prompt_for_models(provider_type: str) -> dict[str, str]:
    defaults = DEFAULT_PROVIDER_MODELS.get(provider_type)
    if defaults is None:
        raise ValueError(f"Unknown provider type: {provider_type}")

    default_embedding = defaults.get("embedding_model")
    default_llm = defaults.get("llm_model")
    display_name = PROVIDER_DISPLAY_NAMES.get(provider_type, provider_type)

    print()
    print(f"🎯 Model Selection ({display_name})")
    print("=" * 40)

    if default_embedding and default_llm:
        print(f"Default embedding: {default_embedding}")
        print(f"Default LLM: {default_llm}")
        use_default = input("Use default models? [Y/n]: ").strip().lower()
        if use_default not in {"n", "no"}:
            return {
                "embedding_model": default_embedding,
                "llm_model": default_llm,
            }

    embedding_prompt = f"Embedding model ({default_embedding or 'required'}): "
    llm_prompt = f"LLM model ({default_llm or 'required'}): "

    embedding_model = prompt_model_value(embedding_prompt, default_embedding)
    llm_model = prompt_model_value(llm_prompt, default_llm)

    return {
        "embedding_model": embedding_model,
        "llm_model": llm_model,
    }


def prompt_model_value(prompt: str, fallback: str | None) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        if fallback:
            return fallback
        print("❌ Value cannot be empty")


def build_provider_config(provider_type: str, embedding_model: str, llm_model: str) -> dict[str, Any]:
    config: dict[str, Any] = {
        "provider_type": provider_type,
        "embedding_model": embedding_model,
        "llm_model": llm_model,
    }

    defaults = DEFAULT_PROVIDER_MODELS.get(provider_type, {})
    api_key_env = defaults.get("api_key_env")

    if api_key_env:
        config["api_key"] = f"${{{api_key_env}}}"

    if provider_type == "ollama":
        config["base_url"] = "http://localhost:11434"
    elif provider_type == "lmstudio":
        config["base_url"] = "http://localhost:1234/v1"

    return config


def validate_provider_config(config: dict[str, Any]) -> tuple[bool, str | None]:
    provider_type = config.get("provider_type")
    if not provider_type:
        return False, "Missing provider_type"

    if provider_type not in DEFAULT_PROVIDER_MODELS:
        return False, f"Unknown provider type: {provider_type}"

    if not config.get("embedding_model"):
        return False, "Missing embedding_model"

    if not config.get("llm_model"):
        return False, "Missing llm_model"

    defaults = DEFAULT_PROVIDER_MODELS[provider_type]
    api_key_env = defaults.get("api_key_env")

    if api_key_env:
        if not os.environ.get(api_key_env):
            return False, f"Environment variable {api_key_env} is not set"

    if provider_type in LOCAL_PROVIDER_ENDPOINTS:
        endpoint = LOCAL_PROVIDER_ENDPOINTS[provider_type]
        try:
            with urllib.request.urlopen(endpoint["url"], timeout=5) as response:  # noqa: S310
                if response.status >= 400:
                    return False, f"Cannot connect to {PROVIDER_DISPLAY_NAMES[provider_type]}"
        except urllib.error.URLError:
            return (
                False,
                f"Cannot connect to {PROVIDER_DISPLAY_NAMES[provider_type]} at {endpoint['url']}. {endpoint['instruction']}",
            )

    return True, None
