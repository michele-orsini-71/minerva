import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RepositoryConfig:
    name: str
    github_url: str
    local_path: str
    collection: str
    index_config: str


@dataclass
class WebhookConfig:
    webhook_secret: str
    github_token: str
    repositories: list[RepositoryConfig]
    log_file: str


def resolve_env_vars(value: str) -> str:
    if not isinstance(value, str):
        return value

    pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match):
        env_var = match.group(1)
        env_value = os.getenv(env_var)
        if env_value is None:
            raise ValueError(f"Environment variable {env_var} is not set")
        return env_value

    return pattern.sub(replacer, value)


def resolve_env_vars_recursive(obj):
    if isinstance(obj, dict):
        return {key: resolve_env_vars_recursive(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars_recursive(item) for item in obj]
    elif isinstance(obj, str):
        return resolve_env_vars(obj)
    else:
        return obj


def validate_config(config_data: dict, config_path: str) -> None:
    required_fields = ['webhook_secret', 'github_token', 'repositories', 'log_file']
    for field in required_fields:
        if field not in config_data:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(config_data['repositories'], list):
        raise ValueError("Field 'repositories' must be a list")

    if len(config_data['repositories']) == 0:
        raise ValueError("Field 'repositories' cannot be empty")

    config_dir = Path(config_path).parent.resolve()

    for i, repo in enumerate(config_data['repositories']):
        repo_required = ['name', 'github_url', 'local_path', 'collection', 'index_config']
        for field in repo_required:
            if field not in repo:
                raise ValueError(f"Repository {i}: missing required field '{field}'")

        local_path = Path(repo['local_path']).expanduser()
        if not local_path.is_absolute():
            local_path = config_dir / local_path

        if not local_path.exists():
            raise ValueError(f"Repository {i}: local_path does not exist: {local_path}")

        if not local_path.is_dir():
            raise ValueError(f"Repository {i}: local_path is not a directory: {local_path}")

        index_config_path = Path(repo['index_config']).expanduser()
        if not index_config_path.is_absolute():
            index_config_path = config_dir / index_config_path

        if not index_config_path.exists():
            raise ValueError(f"Repository {i}: index_config does not exist: {index_config_path}")

        if not index_config_path.is_file():
            raise ValueError(f"Repository {i}: index_config is not a file: {index_config_path}")


def load_config(config_path: str) -> WebhookConfig:
    config_file = Path(config_path).expanduser().resolve()

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    if not config_file.is_file():
        raise ValueError(f"Configuration path is not a file: {config_file}")

    with open(config_file, 'r') as f:
        config_data = json.load(f)

    config_data = resolve_env_vars_recursive(config_data)

    validate_config(config_data, str(config_file))

    config_dir = config_file.parent

    repositories = []
    for repo in config_data['repositories']:
        local_path = Path(repo['local_path']).expanduser()
        if not local_path.is_absolute():
            local_path = config_dir / local_path
        local_path = local_path.resolve()

        index_config = Path(repo['index_config']).expanduser()
        if not index_config.is_absolute():
            index_config = config_dir / index_config
        index_config = index_config.resolve()

        repositories.append(RepositoryConfig(
            name=repo['name'],
            github_url=repo['github_url'],
            local_path=str(local_path),
            collection=repo['collection'],
            index_config=str(index_config)
        ))

    log_file_path = Path(config_data['log_file']).expanduser()
    if not log_file_path.is_absolute():
        log_file_path = config_dir / log_file_path
    log_file_path = log_file_path.resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    return WebhookConfig(
        webhook_secret=config_data['webhook_secret'],
        github_token=config_data['github_token'],
        repositories=repositories,
        log_file=str(log_file_path.resolve())
    )
