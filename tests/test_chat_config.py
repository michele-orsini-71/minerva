import json
import os
import pytest
from pathlib import Path
from minerva.chat.config import (
    ChatConfig,
    ChatConfigError,
    load_chat_config,
    validate_config_schema,
    validate_config_file_exists,
    read_json_config_file,
    expand_path,
    create_ai_provider_config,
    extract_config_fields,
    CHAT_CONFIG_SCHEMA
)


def test_chat_config_dataclass_creation():
    config = ChatConfig(
        chromadb_path='/absolute/path/to/chromadb',
        ai_provider=create_ai_provider_config({
            'type': 'ollama',
            'embedding': {'model': 'mxbai-embed-large'},
            'llm': {'model': 'llama3.1:8b'}
        }),
        conversation_dir='/home/user/.minerva/conversations',
        default_max_results=3,
        enable_streaming=True
    )

    assert config.chromadb_path == '/absolute/path/to/chromadb'
    assert config.default_max_results == 3
    assert config.enable_streaming is True


def test_chat_config_rejects_relative_path():
    with pytest.raises(ValueError, match='must be an absolute path'):
        ChatConfig(
            chromadb_path='relative/path',
            ai_provider=create_ai_provider_config({
                'type': 'ollama',
                'embedding': {'model': 'model1'},
                'llm': {'model': 'model2'}
            }),
            conversation_dir='/home/user/.minerva',
            default_max_results=3,
            enable_streaming=True
        )


def test_chat_config_rejects_empty_chromadb_path():
    with pytest.raises(ValueError, match='cannot be empty'):
        ChatConfig(
            chromadb_path='',
            ai_provider=create_ai_provider_config({
                'type': 'ollama',
                'embedding': {'model': 'model1'},
                'llm': {'model': 'model2'}
            }),
            conversation_dir='/home/user/.minerva',
            default_max_results=3,
            enable_streaming=True
        )


def test_validate_config_file_exists_missing_file(tmp_path):
    missing_file = tmp_path / 'nonexistent.json'

    with pytest.raises(ChatConfigError, match='Configuration file not found'):
        validate_config_file_exists(str(missing_file))


def test_validate_config_file_exists_success(tmp_path):
    config_file = tmp_path / 'config.json'
    config_file.write_text('{}')

    result = validate_config_file_exists(str(config_file))

    assert result == config_file
    assert result.exists()


def test_read_json_config_file_success(tmp_path):
    config_file = tmp_path / 'config.json'
    config_data = {'chromadb_path': '/path', 'ai_provider': {}}
    config_file.write_text(json.dumps(config_data))

    result = read_json_config_file(config_file, str(config_file))

    assert result == config_data


def test_read_json_config_file_invalid_json(tmp_path):
    config_file = tmp_path / 'config.json'
    config_file.write_text('{ invalid json }')

    with pytest.raises(ChatConfigError, match='Invalid JSON syntax'):
        read_json_config_file(config_file, str(config_file))


def test_read_json_config_file_not_dict(tmp_path):
    config_file = tmp_path / 'config.json'
    config_file.write_text('["array", "not", "dict"]')

    with pytest.raises(ChatConfigError, match='must contain a JSON object'):
        read_json_config_file(config_file, str(config_file))


def test_validate_config_schema_missing_chromadb_path(tmp_path):
    config_data = {
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        }
    }

    with pytest.raises(ChatConfigError, match="Missing required field"):
        validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_missing_ai_provider(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path'
    }

    with pytest.raises(ChatConfigError, match="Missing required field"):
        validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_invalid_provider_type(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path',
        'ai_provider': {
            'type': 'invalid_provider',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        }
    }

    with pytest.raises(ChatConfigError, match='Invalid AI provider type'):
        validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_additional_properties(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path',
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        },
        'unknown_field': 'value'
    }

    with pytest.raises(ChatConfigError, match='Unknown fields'):
        validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_invalid_max_results_too_low(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path',
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        },
        'default_max_results': 0
    }

    with pytest.raises(ChatConfigError):
        validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_invalid_max_results_too_high(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path',
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        },
        'default_max_results': 20
    }

    with pytest.raises(ChatConfigError):
        validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_success_minimal(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path',
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        }
    }

    validate_config_schema(config_data, 'test.json')


def test_validate_config_schema_success_full(tmp_path):
    config_data = {
        'chromadb_path': '/absolute/path',
        'ai_provider': {
            'type': 'openai',
            'embedding': {
                'model': 'text-embedding-3-small',
                'base_url': 'https://api.openai.com/v1',
                'api_key': '${OPENAI_API_KEY}'
            },
            'llm': {
                'model': 'gpt-4o-mini',
                'base_url': 'https://api.openai.com/v1',
                'api_key': '${OPENAI_API_KEY}'
            }
        },
        'conversation_dir': '~/.minerva/conversations',
        'default_max_results': 5,
        'enable_streaming': False
    }

    validate_config_schema(config_data, 'test.json')


def test_expand_path_with_tilde():
    path = '~/test/path'
    expanded = expand_path(path)

    assert not expanded.startswith('~')
    assert os.path.isabs(expanded)


def test_expand_path_absolute():
    path = '/absolute/path'
    expanded = expand_path(path)

    assert expanded == path
    assert os.path.isabs(expanded)


def test_expand_path_relative():
    path = 'relative/path'
    expanded = expand_path(path)

    assert os.path.isabs(expanded)


def test_create_ai_provider_config_ollama():
    ai_provider_data = {
        'type': 'ollama',
        'embedding': {'model': 'mxbai-embed-large'},
        'llm': {'model': 'llama3.1:8b'}
    }

    config = create_ai_provider_config(ai_provider_data)

    assert config.provider_type == 'ollama'
    assert config.embedding_model == 'mxbai-embed-large'
    assert config.llm_model == 'llama3.1:8b'
    assert config.base_url is None
    assert config.api_key is None


def test_create_ai_provider_config_openai_with_api_key():
    ai_provider_data = {
        'type': 'openai',
        'embedding': {
            'model': 'text-embedding-3-small',
            'api_key': '${OPENAI_API_KEY}'
        },
        'llm': {
            'model': 'gpt-4o-mini',
            'api_key': '${OPENAI_API_KEY}'
        }
    }

    config = create_ai_provider_config(ai_provider_data)

    assert config.provider_type == 'openai'
    assert config.api_key == '${OPENAI_API_KEY}'


def test_create_ai_provider_config_with_base_url():
    ai_provider_data = {
        'type': 'ollama',
        'embedding': {
            'model': 'model1',
            'base_url': 'http://custom:11434'
        },
        'llm': {
            'model': 'model2',
            'base_url': 'http://custom:11434'
        }
    }

    config = create_ai_provider_config(ai_provider_data)

    assert config.base_url == 'http://custom:11434'


def test_extract_config_fields_minimal(tmp_path):
    chromadb_path = tmp_path / 'chromadb'
    chromadb_path.mkdir()

    config_data = {
        'chromadb_path': str(chromadb_path),
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        }
    }

    config = extract_config_fields(config_data)

    assert os.path.isabs(config.chromadb_path)
    assert config.default_max_results == 3
    assert config.enable_streaming is True
    assert '.minerva/conversations' in config.conversation_dir


def test_extract_config_fields_full(tmp_path):
    chromadb_path = tmp_path / 'chromadb'
    chromadb_path.mkdir()
    conv_dir = tmp_path / 'conversations'

    config_data = {
        'chromadb_path': str(chromadb_path),
        'ai_provider': {
            'type': 'openai',
            'embedding': {'model': 'text-embedding-3-small'},
            'llm': {'model': 'gpt-4o-mini'}
        },
        'conversation_dir': str(conv_dir),
        'default_max_results': 10,
        'enable_streaming': False
    }

    config = extract_config_fields(config_data)

    assert os.path.isabs(config.chromadb_path)
    assert config.default_max_results == 10
    assert config.enable_streaming is False
    assert os.path.isabs(config.conversation_dir)


def test_load_chat_config_success(tmp_path):
    chromadb_path = tmp_path / 'chromadb'
    chromadb_path.mkdir()

    config_file = tmp_path / 'config.json'
    config_data = {
        'chromadb_path': str(chromadb_path),
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'mxbai-embed-large'},
            'llm': {'model': 'llama3.1:8b'}
        },
        'default_max_results': 5
    }
    config_file.write_text(json.dumps(config_data))

    config = load_chat_config(str(config_file))

    assert isinstance(config, ChatConfig)
    assert config.ai_provider.provider_type == 'ollama'
    assert config.default_max_results == 5


def test_load_chat_config_file_not_found(tmp_path):
    missing_file = tmp_path / 'nonexistent.json'

    with pytest.raises(ChatConfigError, match='Configuration file not found'):
        load_chat_config(str(missing_file))


def test_load_chat_config_invalid_json(tmp_path):
    config_file = tmp_path / 'config.json'
    config_file.write_text('{ invalid }')

    with pytest.raises(ChatConfigError, match='Invalid JSON syntax'):
        load_chat_config(str(config_file))


def test_load_chat_config_missing_required_fields(tmp_path):
    config_file = tmp_path / 'config.json'
    config_data = {
        'chromadb_path': '/path/to/chromadb'
    }
    config_file.write_text(json.dumps(config_data))

    with pytest.raises(ChatConfigError, match='Missing required field'):
        load_chat_config(str(config_file))


def test_chat_config_schema_has_required_fields():
    assert 'chromadb_path' in CHAT_CONFIG_SCHEMA['required']
    assert 'ai_provider' in CHAT_CONFIG_SCHEMA['required']


def test_chat_config_schema_allows_all_provider_types():
    provider_enum = CHAT_CONFIG_SCHEMA['properties']['ai_provider']['properties']['type']['enum']

    assert 'ollama' in provider_enum
    assert 'openai' in provider_enum
    assert 'gemini' in provider_enum
    assert 'azure' in provider_enum
    assert 'anthropic' in provider_enum


def test_chat_config_frozen_immutable():
    config = ChatConfig(
        chromadb_path='/absolute/path',
        ai_provider=create_ai_provider_config({
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        }),
        conversation_dir='/home/user/.minerva',
        default_max_results=3,
        enable_streaming=True
    )

    with pytest.raises(Exception):
        config.chromadb_path = '/new/path'


def test_load_chat_config_expands_tilde_in_paths(tmp_path):
    chromadb_path = tmp_path / 'chromadb'
    chromadb_path.mkdir()

    config_file = tmp_path / 'config.json'
    config_data = {
        'chromadb_path': str(chromadb_path),
        'ai_provider': {
            'type': 'ollama',
            'embedding': {'model': 'model1'},
            'llm': {'model': 'model2'}
        },
        'conversation_dir': '~/test/conversations'
    }
    config_file.write_text(json.dumps(config_data))

    config = load_chat_config(str(config_file))

    assert not config.conversation_dir.startswith('~')
    assert os.path.isabs(config.conversation_dir)
