import json
import pytest
from datetime import datetime
from pathlib import Path

from minerva.chat.history import (
    generate_conversation_id,
    save_conversation,
    load_conversation,
    list_conversations,
    ConversationHistory,
    _expand_conversation_path,
    _ensure_conversation_directory,
    _generate_conversation_title,
)


def test_generate_conversation_id():
    conv_id = generate_conversation_id()

    assert isinstance(conv_id, str)
    assert len(conv_id) > 0

    parts = conv_id.split('-')
    assert len(parts) == 3

    timestamp_part = f"{parts[0]}-{parts[1]}"
    datetime.strptime(timestamp_part, '%Y%m%d-%H%M%S')

    random_part = parts[2]
    assert len(random_part) == 6
    assert random_part.isalnum()


def test_generate_conversation_id_uniqueness():
    id1 = generate_conversation_id()
    id2 = generate_conversation_id()

    assert id1 != id2


def test_expand_conversation_path_with_tilde(tmp_path):
    path = Path('~/test/conversations')
    expanded = _expand_conversation_path(path)

    assert not str(expanded).startswith('~')
    assert expanded.is_absolute()


def test_expand_conversation_path_without_tilde(tmp_path):
    path = tmp_path / 'conversations'
    expanded = _expand_conversation_path(path)

    assert expanded == path


def test_ensure_conversation_directory_creates_directory(tmp_path):
    conv_dir = tmp_path / 'conversations' / 'nested'

    assert not conv_dir.exists()

    result = _ensure_conversation_directory(conv_dir)

    assert result.exists()
    assert result.is_dir()
    assert result == conv_dir


def test_ensure_conversation_directory_with_existing_directory(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conv_dir.mkdir()

    result = _ensure_conversation_directory(conv_dir)

    assert result.exists()
    assert result == conv_dir


def test_generate_conversation_title_with_user_message():
    conversation = {
        'messages': [
            {'role': 'system', 'content': 'System prompt'},
            {'role': 'user', 'content': 'What is the meaning of life?'},
            {'role': 'assistant', 'content': '42'},
        ]
    }

    title = _generate_conversation_title(conversation)
    assert title == 'What is the meaning of life?'


def test_generate_conversation_title_with_long_message():
    long_message = 'a' * 100
    conversation = {
        'messages': [
            {'role': 'user', 'content': long_message},
        ]
    }

    title = _generate_conversation_title(conversation)
    assert len(title) == 63
    assert title.endswith('...')


def test_generate_conversation_title_with_no_messages():
    conversation = {'messages': []}

    title = _generate_conversation_title(conversation)
    assert title == 'Empty conversation'


def test_save_conversation(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conversation = {
        'conversation_id': '20251030-120000-abc123',
        'messages': [
            {'role': 'user', 'content': 'Hello'}
        ]
    }

    conv_id = save_conversation(conversation, conv_dir)

    assert conv_id == '20251030-120000-abc123'
    assert conv_dir.exists()

    saved_file = conv_dir / f"{conv_id}.json"
    assert saved_file.exists()

    with open(saved_file, 'r') as f:
        loaded = json.load(f)

    assert loaded['conversation_id'] == conv_id
    assert loaded['messages'] == conversation['messages']
    assert 'last_modified' in loaded


def test_save_conversation_generates_id_if_missing(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conversation = {
        'messages': [
            {'role': 'user', 'content': 'Hello'}
        ]
    }

    conv_id = save_conversation(conversation, conv_dir)

    assert conv_id is not None
    assert len(conv_id) > 0
    assert conversation['conversation_id'] == conv_id


def test_load_conversation(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conv_dir.mkdir()

    conv_id = '20251030-120000-abc123'
    conversation_data = {
        'conversation_id': conv_id,
        'messages': [
            {'role': 'user', 'content': 'Hello'}
        ]
    }

    file_path = conv_dir / f"{conv_id}.json"
    with open(file_path, 'w') as f:
        json.dump(conversation_data, f)

    loaded = load_conversation(conv_id, conv_dir)

    assert loaded['conversation_id'] == conv_id
    assert loaded['messages'] == conversation_data['messages']


def test_load_conversation_not_found(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conv_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        load_conversation('nonexistent', conv_dir)


def test_list_conversations_empty_directory(tmp_path):
    conv_dir = tmp_path / 'conversations'

    conversations = list_conversations(conv_dir)

    assert conversations == []


def test_list_conversations(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conv_dir.mkdir()

    conv1 = {
        'conversation_id': '20251030-120000-abc123',
        'created_at': '2025-10-30T12:00:00',
        'last_modified': '2025-10-30T12:05:00',
        'messages': [
            {'role': 'user', 'content': 'First message'},
            {'role': 'assistant', 'content': 'Response'},
        ]
    }

    conv2 = {
        'conversation_id': '20251030-130000-def456',
        'created_at': '2025-10-30T13:00:00',
        'last_modified': '2025-10-30T13:10:00',
        'messages': [
            {'role': 'user', 'content': 'Second message'},
        ]
    }

    with open(conv_dir / '20251030-120000-abc123.json', 'w') as f:
        json.dump(conv1, f)

    with open(conv_dir / '20251030-130000-def456.json', 'w') as f:
        json.dump(conv2, f)

    conversations = list_conversations(conv_dir)

    assert len(conversations) == 2

    assert conversations[0]['conversation_id'] == '20251030-130000-def456'
    assert conversations[0]['message_count'] == 1
    assert conversations[0]['title'] == 'Second message'

    assert conversations[1]['conversation_id'] == '20251030-120000-abc123'
    assert conversations[1]['message_count'] == 2
    assert conversations[1]['title'] == 'First message'


def test_list_conversations_skips_invalid_files(tmp_path):
    conv_dir = tmp_path / 'conversations'
    conv_dir.mkdir()

    valid_conv = {
        'conversation_id': '20251030-120000-abc123',
        'messages': [{'role': 'user', 'content': 'Hello'}]
    }

    with open(conv_dir / '20251030-120000-abc123.json', 'w') as f:
        json.dump(valid_conv, f)

    with open(conv_dir / 'invalid.json', 'w') as f:
        f.write('invalid json {{{')

    conversations = list_conversations(conv_dir)

    assert len(conversations) == 1
    assert conversations[0]['conversation_id'] == '20251030-120000-abc123'


def test_conversation_history_start_new_conversation(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    conv_id = history.start_new_conversation(system_prompt='You are a helpful assistant.')

    assert conv_id is not None
    assert history.conversation_id == conv_id
    assert history.current_conversation is not None

    messages = history.get_messages()
    assert len(messages) == 1
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'You are a helpful assistant.'


def test_conversation_history_add_message(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    history.start_new_conversation()
    history.add_message('user', 'Hello, AI!')
    history.add_message('assistant', 'Hello! How can I help you?')

    messages = history.get_messages()
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Hello, AI!'
    assert messages[1]['role'] == 'assistant'
    assert messages[1]['content'] == 'Hello! How can I help you?'

    metadata = history.get_metadata()
    assert metadata['message_count'] == 2


def test_conversation_history_add_message_without_conversation(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    with pytest.raises(RuntimeError, match='No active conversation'):
        history.add_message('user', 'Hello')


def test_conversation_history_add_tool_result(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    history.start_new_conversation()
    history.add_tool_result('call_123', 'search_knowledge_base', 'Found 3 results')

    messages = history.get_messages()
    assert len(messages) == 1
    assert messages[0]['role'] == 'tool'
    assert messages[0]['tool_call_id'] == 'call_123'
    assert messages[0]['name'] == 'search_knowledge_base'
    assert messages[0]['content'] == 'Found 3 results'


def test_conversation_history_update_metadata(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    history.start_new_conversation()
    history.update_metadata(total_tokens=150, custom_field='value')

    metadata = history.get_metadata()
    assert metadata['total_tokens'] == 150
    assert metadata['custom_field'] == 'value'


def test_conversation_history_save_and_load(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    conv_id = history.start_new_conversation(system_prompt='System prompt')
    history.add_message('user', 'Test message')
    history.save()

    saved_file = conv_dir / f"{conv_id}.json"
    assert saved_file.exists()

    new_history = ConversationHistory(conv_dir, auto_save=False)
    new_history.resume_conversation(conv_id)

    messages = new_history.get_messages()
    assert len(messages) == 2
    assert messages[0]['content'] == 'System prompt'
    assert messages[1]['content'] == 'Test message'


def test_conversation_history_auto_save(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=True)

    conv_id = history.start_new_conversation()

    saved_file = conv_dir / f"{conv_id}.json"
    assert saved_file.exists()

    history.add_message('user', 'Auto-saved message')

    with open(saved_file, 'r') as f:
        loaded = json.load(f)

    assert len(loaded['messages']) == 1
    assert loaded['messages'][0]['content'] == 'Auto-saved message'


def test_conversation_history_list_all(tmp_path):
    conv_dir = tmp_path / 'conversations'

    history1 = ConversationHistory(conv_dir, auto_save=True)
    history1.start_new_conversation()
    history1.add_message('user', 'First conversation')

    history2 = ConversationHistory(conv_dir, auto_save=True)
    history2.start_new_conversation()
    history2.add_message('user', 'Second conversation')

    conversations = history2.list_all()

    assert len(conversations) == 2
    assert conversations[0]['title'] == 'Second conversation'
    assert conversations[1]['title'] == 'First conversation'


def test_conversation_history_resume_nonexistent(tmp_path):
    conv_dir = tmp_path / 'conversations'
    history = ConversationHistory(conv_dir, auto_save=False)

    with pytest.raises(FileNotFoundError):
        history.resume_conversation('nonexistent')
