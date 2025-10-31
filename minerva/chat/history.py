import json
import os
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from minerva.common.logger import get_logger

logger = get_logger(__name__)


def generate_conversation_id() -> str:
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{timestamp}-{random_suffix}"


def _expand_conversation_path(conversation_dir: Path) -> Path:
    path_str = str(conversation_dir)
    if path_str.startswith('~'):
        return Path(os.path.expanduser(path_str))
    return conversation_dir


def _ensure_conversation_directory(conversation_dir: Path) -> Path:
    expanded_path = _expand_conversation_path(conversation_dir)
    expanded_path.mkdir(parents=True, exist_ok=True)
    return expanded_path


def save_conversation(conversation: Dict, conversation_dir: Path) -> str:
    directory = _ensure_conversation_directory(conversation_dir)

    conversation_id = conversation.get('conversation_id')
    if not conversation_id:
        conversation_id = generate_conversation_id()
        conversation['conversation_id'] = conversation_id

    conversation['last_modified'] = datetime.now().isoformat()

    file_path = directory / f"{conversation_id}.json"

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(conversation, f, indent=2, ensure_ascii=False)

    return conversation_id


def load_conversation(conversation_id: str, conversation_dir: Path) -> Dict:
    directory = _expand_conversation_path(conversation_dir)
    file_path = directory / f"{conversation_id}.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Conversation {conversation_id} not found at {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        conversation = json.load(f)

    return conversation


def list_conversations(conversation_dir: Path) -> List[Dict]:
    directory = _expand_conversation_path(conversation_dir)

    if not directory.exists():
        return []

    conversations_with_sort_key = []

    for file_path in directory.glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation = json.load(f)

            metadata = {
                'conversation_id': conversation.get('conversation_id', file_path.stem),
                'created_at': conversation.get('created_at'),
                'last_modified': conversation.get('last_modified'),
                'message_count': len(conversation.get('messages', [])),
                'title': _generate_conversation_title(conversation),
            }
            sort_timestamp = metadata['last_modified'] or metadata['created_at']
            if not sort_timestamp:
                sort_timestamp = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            conversations_with_sort_key.append((metadata, sort_timestamp, file_path.stat().st_mtime))

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping invalid conversation file {file_path}: {e}")
            continue

    conversations_with_sort_key.sort(key=lambda item: ((item[1] or ''), item[2]), reverse=True)
    return [item[0] for item in conversations_with_sort_key]


def _generate_conversation_title(conversation: Dict) -> str:
    messages = conversation.get('messages', [])

    for message in messages:
        if message.get('role') == 'user':
            content = message.get('content', '')
            if content:
                return content[:60] + '...' if len(content) > 60 else content

    return "Empty conversation"


class ConversationHistory:
    def __init__(self, conversation_dir: Path, auto_save: bool = True):
        self.conversation_dir = conversation_dir
        self.auto_save = auto_save
        self.current_conversation: Optional[Dict] = None
        self.conversation_id: Optional[str] = None

    def start_new_conversation(self, system_prompt: Optional[str] = None) -> str:
        self.conversation_id = generate_conversation_id()

        self.current_conversation = {
            'conversation_id': self.conversation_id,
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'messages': [],
            'metadata': {
                'total_tokens': 0,
                'message_count': 0,
            }
        }

        if system_prompt:
            self.current_conversation['messages'].append({
                'role': 'system',
                'content': system_prompt,
                'timestamp': datetime.now().isoformat(),
            })

        if self.auto_save:
            save_conversation(self.current_conversation, self.conversation_dir)

        logger.info(f"Started new conversation {self.conversation_id}")
        return self.conversation_id

    def resume_conversation(self, conversation_id: str) -> Dict:
        self.current_conversation = load_conversation(conversation_id, self.conversation_dir)
        self.conversation_id = conversation_id
        logger.info(f"Resumed conversation {conversation_id}")
        return self.current_conversation

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None):
        if not self.current_conversation:
            raise RuntimeError("No active conversation. Call start_new_conversation() first.")

        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
        }

        if tool_calls:
            message['tool_calls'] = tool_calls

        self.current_conversation['messages'].append(message)
        self.current_conversation['metadata']['message_count'] += 1

        if self.auto_save:
            save_conversation(self.current_conversation, self.conversation_dir)

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        if not self.current_conversation:
            raise RuntimeError("No active conversation. Call start_new_conversation() first.")

        message = {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'name': tool_name,
            'content': result,
            'timestamp': datetime.now().isoformat(),
        }

        self.current_conversation['messages'].append(message)

        if self.auto_save:
            save_conversation(self.current_conversation, self.conversation_dir)

    def update_metadata(self, **kwargs):
        if not self.current_conversation:
            raise RuntimeError("No active conversation. Call start_new_conversation() first.")

        self.current_conversation['metadata'].update(kwargs)

        if self.auto_save:
            save_conversation(self.current_conversation, self.conversation_dir)

    def get_messages(self) -> List[Dict]:
        if not self.current_conversation:
            return []
        return self.current_conversation['messages']

    def get_metadata(self) -> Dict:
        if not self.current_conversation:
            return {}
        return self.current_conversation.get('metadata', {})

    def save(self) -> str:
        if not self.current_conversation:
            raise RuntimeError("No active conversation to save.")
        return save_conversation(self.current_conversation, self.conversation_dir)

    def list_all(self) -> List[Dict]:
        return list_conversations(self.conversation_dir)
