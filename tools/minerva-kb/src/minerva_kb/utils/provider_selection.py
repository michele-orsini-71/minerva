import os
import subprocess
from typing import Any

from minerva_common.provider_setup import select_provider_interactive as _shared_select_provider

CLOUD_ENV_VARS = ("OPENAI_API_KEY", "GEMINI_API_KEY")


def interactive_select_provider() -> dict[str, Any]:
    _prime_provider_credentials()
    return _shared_select_provider()


def _prime_provider_credentials() -> None:
    for env_var in CLOUD_ENV_VARS:
        if os.environ.get(env_var):
            continue
        secret = _read_keychain_secret(env_var)
        if secret:
            os.environ[env_var] = secret


def _read_keychain_secret(key_name: str) -> str | None:
    try:
        result = subprocess.run(
            ["minerva", "keychain", "get", key_name],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    secret = result.stdout.strip()
    return secret or None
