import subprocess
import urllib.error
import urllib.request
from typing import Any

from minerva_kb.constants import DEFAULT_PROVIDER_MODELS, PROVIDER_DISPLAY_NAMES
from minerva_kb.utils.display import display_error

MAX_API_VALIDATION_ATTEMPTS = 3

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

REMOTE_VALIDATION_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/models",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
}


def interactive_select_provider() -> dict[str, Any]:
    while True:
        provider_type = _prompt_provider_choice()
        model_config = prompt_for_models(provider_type)
        embedding_model = model_config["embedding_model"].strip()
        llm_model = model_config["llm_model"].strip()
        if not embedding_model or not llm_model:
            display_error("Model names must be non-empty strings")
            continue
        config = {
            "provider_type": provider_type,
            "embedding_model": embedding_model,
            "llm_model": llm_model,
        }

        key_name = _provider_key_name(provider_type)
        if key_name:
            if not check_api_key_exists(provider_type):
                if not prompt_for_api_key(provider_type):
                    continue
            if not validate_api_key(provider_type):
                retry = input("Select a different provider? [y/N]: ").strip().lower()
                if retry in {"y", "yes"}:
                    continue
                raise RuntimeError("API key validation failed")
            config["api_key_name"] = key_name
        else:
            if not validate_local_provider(provider_type):
                retry = input("Retry connection? [y/N]: ").strip().lower()
                if retry in {"y", "yes"}:
                    continue
                raise RuntimeError(f"{PROVIDER_DISPLAY_NAMES[provider_type]} is not available")

        return config


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

    embedding_model = _prompt_model_value(embedding_prompt, default_embedding)
    llm_model = _prompt_model_value(llm_prompt, default_llm)

    return {
        "embedding_model": embedding_model,
        "llm_model": llm_model,
    }


def _prompt_model_value(prompt: str, fallback: str | None) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        if fallback:
            return fallback
        print("❌ Value cannot be empty")


def _prompt_provider_choice() -> str:
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
    print("     • Pull and select models you have locally")
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
        display_error("Invalid choice. Please enter 1, 2, 3, or 4.")


def check_api_key_exists(provider_type: str) -> bool:
    key_name = _provider_key_name(provider_type)
    if not key_name:
        return True

    result = subprocess.run(
        ["minerva", "keychain", "get", key_name],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def prompt_for_api_key(provider_type: str) -> bool:
    key_name = _provider_key_name(provider_type)
    if not key_name:
        return True

    print()
    print(f"🔑 API Key Configuration ({PROVIDER_DISPLAY_NAMES[provider_type]})")
    print("=" * 60)
    print(f"Key will be stored as: '{key_name}' in the Minerva keychain")
    print("The keychain entry will be referenced as ${" + key_name + "} in configs")

    try:
        subprocess.run(["minerva", "keychain", "set", key_name], check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"❌ Failed to store API key: {exc}")
        return False


def validate_api_key(provider_type: str) -> bool:
    key_name = _provider_key_name(provider_type)
    if not key_name:
        return True

    display_name = PROVIDER_DISPLAY_NAMES.get(provider_type, provider_type)

    attempts = 0
    while True:
        api_key = _read_api_key(provider_type)
        if not api_key:
            display_error(f"No API key found for {display_name}")
            if not prompt_for_api_key(provider_type):
                return False
            continue

        attempts += 1
        try:
            _perform_remote_validation(provider_type, api_key)
            print(f"✓ {display_name} API key is valid")
            return True
        except Exception as exc:  # noqa: BLE001
            display_error(f"Failed to connect to {display_name}: {exc}")
            _print_api_key_troubleshooting(display_name)
            if attempts >= MAX_API_VALIDATION_ATTEMPTS:
                print("Maximum validation attempts reached.")
                return False
            retry = input("Try again with a different API key? [y/N]: ").strip().lower()
            if retry in {"y", "yes"}:
                if not prompt_for_api_key(provider_type):
                    return False
                continue
            return False


def _read_api_key(provider_type: str) -> str | None:
    key_name = _provider_key_name(provider_type)
    if not key_name:
        return None

    result = subprocess.run(
        ["minerva", "keychain", "get", key_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value:
        return None
    return value


def _perform_remote_validation(provider_type: str, api_key: str) -> None:
    url = REMOTE_VALIDATION_ENDPOINTS.get(provider_type)
    if not url:
        raise ValueError(f"No validation endpoint for provider: {provider_type}")

    if provider_type == "gemini":
        url = f"{url}?key={api_key}"
        request = urllib.request.Request(url)
    else:
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {api_key}")

    with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
        if response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}")


def validate_local_provider(provider_type: str) -> bool:
    details = LOCAL_PROVIDER_ENDPOINTS.get(provider_type)
    if not details:
        return True

    try:
        with urllib.request.urlopen(details["url"], timeout=5) as response:  # noqa: S310
            if response.status < 400:
                return True
            display_error(
                f"Cannot connect to {PROVIDER_DISPLAY_NAMES[provider_type]} at {details['url']}"
            )
            print(details["instruction"])
            return False
    except urllib.error.URLError as exc:
        display_error(f"Cannot connect to {PROVIDER_DISPLAY_NAMES[provider_type]} at {details['url']}")
        print(details["instruction"])
        if getattr(exc, "reason", None):
            print(f"Reason: {exc.reason}")
        return False


def _provider_key_name(provider_type: str) -> str | None:
    defaults = DEFAULT_PROVIDER_MODELS.get(provider_type)
    if not defaults:
        raise ValueError(f"Unknown provider type: {provider_type}")
    return defaults.get("api_key_name")


def _print_api_key_troubleshooting(display_name: str) -> None:
    print("Possible issues:")
    print("  • Invalid or expired API key")
    print("  • No internet connection")
    print(f"  • {display_name} service is unavailable")
