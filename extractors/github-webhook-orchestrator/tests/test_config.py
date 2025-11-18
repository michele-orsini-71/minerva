import json
import os
import pytest
from pathlib import Path
from github_webhook_orchestrator.config import (
    RepositoryConfig,
    WebhookConfig,
    resolve_env_vars,
    resolve_env_vars_recursive,
    validate_config,
    load_config
)


def test_resolve_env_vars_with_set_variable():
    os.environ['TEST_VAR'] = 'test_value'
    result = resolve_env_vars('prefix_${TEST_VAR}_suffix')
    assert result == 'prefix_test_value_suffix'
    del os.environ['TEST_VAR']


def test_resolve_env_vars_with_unset_variable():
    if 'NONEXISTENT_VAR' in os.environ:
        del os.environ['NONEXISTENT_VAR']

    with pytest.raises(ValueError, match="Environment variable NONEXISTENT_VAR is not set"):
        resolve_env_vars('${NONEXISTENT_VAR}')


def test_resolve_env_vars_with_multiple_variables():
    os.environ['VAR1'] = 'value1'
    os.environ['VAR2'] = 'value2'
    result = resolve_env_vars('${VAR1}_middle_${VAR2}')
    assert result == 'value1_middle_value2'
    del os.environ['VAR1']
    del os.environ['VAR2']


def test_resolve_env_vars_with_no_variables():
    result = resolve_env_vars('plain_string')
    assert result == 'plain_string'


def test_resolve_env_vars_recursive_dict():
    os.environ['TEST_SECRET'] = 'secret123'
    data = {
        'key1': '${TEST_SECRET}',
        'key2': 'plain',
        'nested': {
            'key3': '${TEST_SECRET}'
        }
    }
    result = resolve_env_vars_recursive(data)
    assert result['key1'] == 'secret123'
    assert result['key2'] == 'plain'
    assert result['nested']['key3'] == 'secret123'
    del os.environ['TEST_SECRET']


def test_resolve_env_vars_recursive_list():
    os.environ['TEST_VAR'] = 'test'
    data = ['${TEST_VAR}', 'plain', {'key': '${TEST_VAR}'}]
    result = resolve_env_vars_recursive(data)
    assert result[0] == 'test'
    assert result[1] == 'plain'
    assert result[2]['key'] == 'test'
    del os.environ['TEST_VAR']


def test_validate_config_missing_required_field():
    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': []
    }
    with pytest.raises(ValueError, match="Missing required field: log_file"):
        validate_config(config_data, '/tmp/config.json')


def test_validate_config_repositories_not_list():
    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': 'not_a_list',
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Field 'repositories' must be a list"):
        validate_config(config_data, '/tmp/config.json')


def test_validate_config_empty_repositories():
    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [],
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Field 'repositories' cannot be empty"):
        validate_config(config_data, '/tmp/config.json')


def test_validate_config_repository_missing_field(tmp_path):
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    test_config = tmp_path / "test_config.json"

    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test'
            }
        ],
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Repository 0: missing required field 'local_path'"):
        validate_config(config_data, str(test_config))


def test_validate_config_local_path_not_exists(tmp_path):
    test_config = tmp_path / "test_config.json"

    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': '/nonexistent/path',
                'index_config': '/tmp/config.json'
            }
        ],
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Repository 0: local_path does not exist"):
        validate_config(config_data, str(test_config))


def test_validate_config_local_path_not_directory(tmp_path):
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test")
    test_config = tmp_path / "test_config.json"

    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': str(test_file),
                'index_config': '/tmp/config.json'
            }
        ],
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Repository 0: local_path is not a directory"):
        validate_config(config_data, str(test_config))


def test_validate_config_index_config_not_exists(tmp_path):
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    test_config = tmp_path / "test_config.json"

    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': str(test_repo),
                'index_config': '/nonexistent/config.json'
            }
        ],
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Repository 0: index_config does not exist"):
        validate_config(config_data, str(test_config))


def test_validate_config_index_config_not_file(tmp_path):
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    test_index_dir = tmp_path / "index_dir"
    test_index_dir.mkdir()
    test_config = tmp_path / "test_config.json"

    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': str(test_repo),
                'index_config': str(test_index_dir)
            }
        ],
        'log_file': '/tmp/log.txt'
    }
    with pytest.raises(ValueError, match="Repository 0: index_config is not a file"):
        validate_config(config_data, str(test_config))


def test_validate_config_success(tmp_path):
    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    test_index = tmp_path / "index.json"
    test_index.write_text("{}")
    test_config = tmp_path / "test_config.json"

    config_data = {
        'webhook_secret': 'secret',
        'github_token': 'token',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': str(test_repo),
                'index_config': str(test_index)
            }
        ],
        'log_file': '/tmp/log.txt'
    }
    validate_config(config_data, str(test_config))


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        load_config('/nonexistent/config.json')


def test_load_config_not_a_file(tmp_path):
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    with pytest.raises(ValueError, match="Configuration path is not a file"):
        load_config(str(test_dir))


def test_load_config_success(tmp_path):
    os.environ['TEST_WEBHOOK_SECRET'] = 'my_secret'
    os.environ['TEST_GITHUB_TOKEN'] = 'my_token'

    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    test_index = tmp_path / "index.json"
    test_index.write_text("{}")

    config_data = {
        'webhook_secret': '${TEST_WEBHOOK_SECRET}',
        'github_token': '${TEST_GITHUB_TOKEN}',
        'repositories': [
            {
                'name': 'test_repo',
                'github_url': 'https://github.com/test/test',
                'local_path': str(test_repo),
                'index_config': str(test_index)
            }
        ],
        'log_file': str(tmp_path / 'logs' / 'webhook.log')
    }

    test_config = tmp_path / "config.json"
    test_config.write_text(json.dumps(config_data))

    config = load_config(str(test_config))

    assert config.webhook_secret == 'my_secret'
    assert config.github_token == 'my_token'
    assert len(config.repositories) == 1
    assert config.repositories[0].name == 'test_repo'
    assert config.repositories[0].github_url == 'https://github.com/test/test'
    assert config.repositories[0].local_path == str(test_repo.resolve())
    assert config.repositories[0].index_config == str(test_index.resolve())
    assert config.log_file == str((tmp_path / 'logs' / 'webhook.log').resolve())

    assert (tmp_path / 'logs').exists()

    del os.environ['TEST_WEBHOOK_SECRET']
    del os.environ['TEST_GITHUB_TOKEN']


def test_load_config_with_relative_paths(tmp_path):
    os.environ['TEST_SECRET'] = 'secret'
    os.environ['TEST_TOKEN'] = 'token'

    config_dir = tmp_path / "configs"
    config_dir.mkdir()

    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    test_repo = repos_dir / "test_repo"
    test_repo.mkdir()

    index_dir = tmp_path / "indices"
    index_dir.mkdir()
    test_index = index_dir / "index.json"
    test_index.write_text("{}")

    config_data = {
        'webhook_secret': '${TEST_SECRET}',
        'github_token': '${TEST_TOKEN}',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': '../repos/test_repo',
                'index_config': '../indices/index.json'
            }
        ],
        'log_file': 'webhook.log'
    }

    test_config = config_dir / "config.json"
    test_config.write_text(json.dumps(config_data))

    config = load_config(str(test_config))

    assert config.repositories[0].local_path == str(test_repo.resolve())
    assert config.repositories[0].index_config == str(test_index.resolve())

    del os.environ['TEST_SECRET']
    del os.environ['TEST_TOKEN']


def test_load_config_creates_log_directory(tmp_path):
    os.environ['TEST_SECRET'] = 'secret'
    os.environ['TEST_TOKEN'] = 'token'

    test_repo = tmp_path / "test_repo"
    test_repo.mkdir()
    test_index = tmp_path / "index.json"
    test_index.write_text("{}")

    log_dir = tmp_path / "logs" / "nested" / "deep"

    config_data = {
        'webhook_secret': '${TEST_SECRET}',
        'github_token': '${TEST_TOKEN}',
        'repositories': [
            {
                'name': 'test',
                'github_url': 'https://github.com/test/test',
                'local_path': str(test_repo),
                'index_config': str(test_index)
            }
        ],
        'log_file': str(log_dir / 'webhook.log')
    }

    test_config = tmp_path / "config.json"
    test_config.write_text(json.dumps(config_data))

    config = load_config(str(test_config))

    assert log_dir.exists()
    assert config.log_file == str((log_dir / 'webhook.log').resolve())

    del os.environ['TEST_SECRET']
    del os.environ['TEST_TOKEN']


def test_repository_config_dataclass():
    repo = RepositoryConfig(
        name='test',
        github_url='https://github.com/test/test',
        local_path='/path/to/repo',
        index_config='/path/to/config.json'
    )

    assert repo.name == 'test'
    assert repo.github_url == 'https://github.com/test/test'
    assert repo.local_path == '/path/to/repo'
    assert repo.index_config == '/path/to/config.json'
    assert repo.branch == 'main'  # Default value


def test_webhook_config_dataclass():
    repo = RepositoryConfig(
        name='test',
        github_url='https://github.com/test/test',
        local_path='/path/to/repo',
        index_config='/path/to/config.json',
        branch='master'
    )

    config = WebhookConfig(
        webhook_secret='secret',
        github_token='token',
        repositories=[repo],
        log_file='/path/to/log.txt'
    )

    assert config.webhook_secret == 'secret'
    assert config.github_token == 'token'
    assert len(config.repositories) == 1
    assert config.repositories[0].name == 'test'
    assert config.log_file == '/path/to/log.txt'
