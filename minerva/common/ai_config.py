import os
import re
from dataclasses import dataclass
from typing import Optional

from minerva.common.exceptions import APIKeyMissingError


def resolve_env_variable(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    env_var_pattern = re.compile(r'\$\{([^}]+)\}')

    def replace_env_var(match):
        var_name = match.group(1)
        env_value = os.environ.get(var_name)

        if env_value is None:
            raise APIKeyMissingError(
                f"Environment variable '{var_name}' is not set.\n"
                f"  Required for: {value}\n"
                f"  Suggestion: Set the environment variable before running:\n"
                f"    export {var_name}='your-api-key-here'"
            )

        return env_value

    resolved = env_var_pattern.sub(replace_env_var, value)
    return resolved


@dataclass(frozen=True)
class AIProviderConfig:
    provider_type: str
    embedding_model: str
    llm_model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        valid_providers = ['ollama', 'openai', 'gemini', 'azure', 'anthropic']
        if self.provider_type not in valid_providers:
            raise ValueError(
                f"Invalid provider_type: {self.provider_type}\n"
                f"Must be one of: {', '.join(valid_providers)}"
            )

        if not self.embedding_model:
            raise ValueError("embedding_model cannot be empty")

        if not self.llm_model:
            raise ValueError("llm_model cannot be empty")

    def resolve_api_key(self) -> Optional[str]:
        return resolve_env_variable(self.api_key)
