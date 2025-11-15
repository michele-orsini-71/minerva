import json
import os
import re
import shutil
from pathlib import Path
from .config import WebhookConfig


def validate_prerequisites(config: WebhookConfig) -> None:
    _validate_required_tools()
    _validate_required_env_vars(config)


def _validate_required_tools() -> None:
    required_tools = ['git', 'repository-doc-extractor', 'minerva']
    missing_tools = []

    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)

    if missing_tools:
        raise RuntimeError(
            f"Missing required tools: {', '.join(missing_tools)}. "
            f"Please ensure they are installed and available in PATH."
        )


def _validate_required_env_vars(config: WebhookConfig) -> None:
    required_env_vars = set()

    required_env_vars.update(_extract_env_vars_from_string(config.webhook_secret))
    required_env_vars.update(_extract_env_vars_from_string(config.github_token))

    for repo in config.repositories:
        index_env_vars = _extract_env_vars_from_index_config(repo.index_config)
        required_env_vars.update(index_env_vars)

    missing_env_vars = []
    for env_var in required_env_vars:
        if not os.getenv(env_var):
            missing_env_vars.append(env_var)

    if missing_env_vars:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(sorted(missing_env_vars))}. "
            f"Please set them before starting the orchestrator."
        )


def _extract_env_vars_from_string(value: str) -> set[str]:
    pattern = re.compile(r'\$\{([^}]+)\}')
    matches = pattern.findall(value)
    return set(matches)


def _extract_env_vars_from_index_config(index_config_path: str) -> set[str]:
    env_vars = set()

    with open(index_config_path, 'r') as f:
        config = json.load(f)

    _extract_env_vars_recursive(config, env_vars)

    return env_vars


def _extract_env_vars_recursive(obj, env_vars: set) -> None:
    if isinstance(obj, dict):
        for value in obj.values():
            _extract_env_vars_recursive(value, env_vars)
    elif isinstance(obj, list):
        for item in obj:
            _extract_env_vars_recursive(item, env_vars)
    elif isinstance(obj, str):
        env_vars.update(_extract_env_vars_from_string(obj))
