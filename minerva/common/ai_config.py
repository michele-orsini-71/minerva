import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from minerva.common.exceptions import APIKeyMissingError, ConfigError
from minerva.common.credential_helper import get_credential


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: Optional[int] = None
    concurrency: Optional[int] = None

    def __post_init__(self):
        if self.requests_per_minute is not None and self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive when provided")
        if self.concurrency is not None and self.concurrency <= 0:
            raise ValueError("concurrency must be positive when provided")


def resolve_env_variable(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    env_var_pattern = re.compile(r'\$\{([^}]+)\}')

    def replace_env_var(match):
        var_name = match.group(1)
        credential = get_credential(var_name)

        if credential is None:
            raise APIKeyMissingError(
                f"Credential '{var_name}' not found.\n\n"
                f"Options:\n"
                f"  1. Keychain: minerva keychain set {var_name}\n"
                f"  2. Environment: export {var_name}='your-key'\n"
                f"  3. Shell profile: Add export to ~/.zshrc"
            )

        return credential

    resolved = env_var_pattern.sub(replace_env_var, value)
    return resolved


@dataclass(frozen=True)
class AIProviderConfig:
    provider_type: str
    embedding_model: Optional[str] = None
    llm_model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    rate_limit: Optional[RateLimitConfig] = None

    def __post_init__(self):
        valid_providers = ['ollama', 'openai', 'gemini', 'lmstudio']
        if self.provider_type not in valid_providers:
            raise ValueError(
                f"Invalid provider_type: {self.provider_type}\n"
                f"Must be one of: {', '.join(valid_providers)}"
            )

        # At least one model must be specified
        if not self.embedding_model and not self.llm_model:
            raise ValueError(
                "At least one of embedding_model or llm_model must be specified"
            )

        # If specified, models cannot be empty strings
        if self.embedding_model is not None and not self.embedding_model:
            raise ValueError("embedding_model cannot be empty string")

        if self.llm_model is not None and not self.llm_model:
            raise ValueError("llm_model cannot be empty string")

    def resolve_api_key(self) -> Optional[str]:
        return resolve_env_variable(self.api_key)


ENV_VAR_REFERENCE_PATTERN = r"^\$\{[A-Z_][A-Z0-9_]*\}$"


AI_PROVIDER_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["provider_type"],
    "properties": {
        "provider_type": {
            "type": "string",
            "enum": ['ollama', 'openai', 'gemini', 'lmstudio']
        },
        "embedding_model": {"type": "string", "minLength": 1},
        "llm_model": {"type": "string", "minLength": 1},
        "base_url": {"type": ["string", "null"], "minLength": 1},
        "api_key": {
            "type": ["string", "null"],
            "minLength": 1,
            "pattern": f"({ENV_VAR_REFERENCE_PATTERN})|^.+$"
        },
        "embedding": {
            "type": "object",
            "required": ["model"],
            "properties": {
                "model": {"type": "string", "minLength": 1},
                "base_url": {"type": ["string", "null"], "minLength": 1},
                "api_key": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "pattern": f"({ENV_VAR_REFERENCE_PATTERN})|^.+$"
                }
            },
            "additionalProperties": False
        },
        "llm": {
            "type": "object",
            "required": ["model"],
            "properties": {
                "model": {"type": "string", "minLength": 1},
                "base_url": {"type": ["string", "null"], "minLength": 1},
                "api_key": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "pattern": f"({ENV_VAR_REFERENCE_PATTERN})|^.+$"
                }
            },
            "additionalProperties": False
        },
        "rate_limit": {
            "type": "object",
            "properties": {
                "requests_per_minute": {
                    "type": ["integer", "null"],
                    "minimum": 1
                },
                "concurrency": {
                    "type": ["integer", "null"],
                    "minimum": 1
                }
            },
            "additionalProperties": False
        }
    },
    "anyOf": [
        # At least one of: embedding_model, embedding, llm_model, or llm must be present
        {"required": ["embedding_model"]},
        {"required": ["embedding"]},
        {"required": ["llm_model"]},
        {"required": ["llm"]}
    ],
    "additionalProperties": False
}


def build_ai_provider_config(
    provider_data: Mapping[str, Any],
    *,
    source_path: Path,
    context: str
) -> AIProviderConfig:
    provider_type = _string_field(provider_data, "provider_type", context, source_path)

    embedding_model = _resolve_model(provider_data, "embedding", context, source_path)
    llm_model = _resolve_model(provider_data, "llm", context, source_path)

    base_url = _resolve_endpoint(provider_data)
    api_key = _resolve_api_key(provider_data, context, source_path)
    rate_limit = _resolve_rate_limit(provider_data, context, source_path)

    return AIProviderConfig(
        provider_type=provider_type,
        embedding_model=embedding_model,
        llm_model=llm_model,
        base_url=base_url,
        api_key=api_key,
        rate_limit=rate_limit,
    )


def _string_field(
    data: Mapping[str, Any],
    key: str,
    context: str,
    source_path: Path
) -> str:
    value = data.get(key)
    if value is None:
        raise ConfigError(
            f"Missing required field '{key}' in {context}\n"
            f"  File: {source_path}"
        )

    value_str = str(value).strip()
    if not value_str:
        raise ConfigError(
            f"Field '{key}' in {context} cannot be empty\n"
            f"  File: {source_path}"
        )
    return value_str


def _resolve_model(
    provider_data: Mapping[str, Any],
    key: str,
    context: str,
    source_path: Path
) -> Optional[str]:
    explicit_key = f"{key}_model"
    model_value = provider_data.get(explicit_key)

    if model_value:
        model = str(model_value).strip()
        if model:
            return model

    nested = provider_data.get(key)
    if isinstance(nested, Mapping):
        nested_model = nested.get("model")
        if nested_model:
            candidate = str(nested_model).strip()
            if candidate:
                return candidate

    # Models are now optional - return None if not specified
    return None


def _resolve_endpoint(provider_data: Mapping[str, Any]) -> Optional[str]:
    base_url = provider_data.get("base_url")
    if base_url:
        value = str(base_url).strip()
        if value:
            return value

    for nested_key in ("embedding", "llm"):
        nested = provider_data.get(nested_key)
        if isinstance(nested, Mapping):
            nested_url = nested.get("base_url")
            if nested_url:
                candidate = str(nested_url).strip()
                if candidate:
                    return candidate
    return None


def _resolve_api_key(
    provider_data: Mapping[str, Any],
    context: str,
    source_path: Path
) -> Optional[str]:
    primary = provider_data.get("api_key")
    if primary:
        api_key = str(primary).strip()
        _validate_env_reference(api_key, context, source_path)
        return api_key or None

    for nested_key in ("embedding", "llm"):
        nested = provider_data.get(nested_key)
        if isinstance(nested, Mapping):
            nested_value = nested.get("api_key")
            if nested_value:
                api_key = str(nested_value).strip()
                _validate_env_reference(api_key, context, source_path)
                return api_key or None
    return None


def _validate_env_reference(value: str, context: str, source_path: Path) -> None:
    if not value:
        return

    try:
        resolve_env_variable(value)
    except APIKeyMissingError as error:
        raise ConfigError(
            f"Environment variable for API key not set in {context}\n"
            f"  Value: {value}\n"
            f"  File: {source_path}"
        ) from error


def _resolve_rate_limit(
    provider_data: Mapping[str, Any],
    context: str,
    source_path: Path
) -> Optional[RateLimitConfig]:
    raw = provider_data.get("rate_limit")
    if not isinstance(raw, Mapping):
        return None

    rpm = raw.get("requests_per_minute")
    concurrency = raw.get("concurrency")

    if rpm is None and concurrency is None:
        return None

    try:
        return RateLimitConfig(
            requests_per_minute=int(rpm) if rpm is not None else None,
            concurrency=int(concurrency) if concurrency is not None else None,
        )
    except (TypeError, ValueError):
        raise ConfigError(
            f"Invalid rate_limit values in {context}\n"
            f"  File: {source_path}\n"
            f"  Both 'requests_per_minute' and 'concurrency' must be positive integers"
        )
