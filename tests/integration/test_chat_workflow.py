import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from tasks.old.chat_engine import ChatEngine, ChatEngineError
from minerva.chat.config import ChatConfig
from minerva.common.ai_config import AIProviderConfig
from minerva.common.ai_provider import AIProvider


@pytest.fixture
def temp_chromadb(tmp_path):
    chromadb_path = tmp_path / 'chromadb_data'
    chromadb_path.mkdir()
    return chromadb_path


@pytest.fixture
def temp_conversations(tmp_path):
    conv_path = tmp_path / 'conversations'
    conv_path.mkdir()
    return conv_path


@pytest.fixture
def mock_config(temp_chromadb, temp_conversations):
    ai_provider_config = AIProviderConfig(
        provider_type='ollama',
        embedding_model='test-embed',
        llm_model='test-llm',
        base_url='http://localhost:11434'
    )

    return ChatConfig(
        chromadb_path=str(temp_chromadb),
        llm_provider=ai_provider_config,
        conversation_dir=str(temp_conversations),
        enable_streaming=False,
        mcp_server_url='http://localhost:8000',
        max_tool_iterations=5,
        system_prompt_file=None
    )


@pytest.fixture
def mock_provider():
    provider = Mock(spec=AIProvider)
    provider.chat_completion = Mock()
    provider.generate_embeddings = Mock(return_value=[[0.1] * 768])
    return provider


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client that simulates successful connection"""
    with patch('minerva.chat.mcp_client.FastMCPClient') as MockClient:
        mock_instance = AsyncMock()

        # Mock tools
        tool1 = Mock()
        tool1.name = "list_knowledge_bases"
        tool1.description = "List knowledge bases"
        tool1.inputSchema = {}

        tool2 = Mock()
        tool2.name = "search_knowledge_base"
        tool2.description = "Search knowledge base"
        tool2.inputSchema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "collection_name": {"type": "string"}
            }
        }

        mock_instance.list_tools = AsyncMock(return_value=[tool1, tool2])
        mock_instance.call_tool = AsyncMock(return_value=Mock(content=[Mock(text='{"result": "ok"}')])
        )

        MockClient.return_value = mock_instance
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None

        yield MockClient


def test_chat_engine_initialization():
    engine = ChatEngine()

    assert engine.config is None
    assert engine.provider is None
    assert engine.history is None
    assert engine.running is False


def test_initialize_conversation(mock_config, mock_provider, mock_mcp_client):
    engine = ChatEngine()

    conv_id = engine.initialize_conversation(
        system_prompt='You are a helpful assistant',
        ai_provider=mock_provider,
        config=mock_config
    )

    assert conv_id is not None
    assert engine.config == mock_config
    assert engine.provider == mock_provider
    assert engine.history is not None
    assert engine.running is True


def test_initialize_conversation_creates_history_file(mock_config, mock_provider, mock_mcp_client):
    engine = ChatEngine()

    conv_id = engine.initialize_conversation(
        system_prompt='Test prompt',
        ai_provider=mock_provider,
        config=mock_config
    )

    conv_file = Path(mock_config.conversation_dir) / f"{conv_id}.json"
    assert conv_file.exists()

    with open(conv_file, 'r') as f:
        data = json.load(f)

    assert data['conversation_id'] == conv_id
    assert len(data['messages']) == 1
    assert data['messages'][0]['role'] == 'system'


def test_send_message_without_initialization(mock_config, mock_provider):
    engine = ChatEngine()

    with pytest.raises(ChatEngineError, match='not initialized'):
        engine.send_message('Hello')


@patch.object(ChatEngine, '_get_tool_definitions')
def test_send_message_simple_response(mock_get_tools, mock_config, mock_provider, mock_mcp_client):
    mock_get_tools.return_value = []

    mock_provider.chat_completion.return_value = {
        'content': 'Hello! How can I help you?',
        'tool_calls': None
    }

    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='You are a helpful assistant',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        response = engine.send_message('Hello')

    assert response == 'Hello! How can I help you?'
    assert engine.get_message_count() == 3


@patch.object(ChatEngine, '_get_tool_definitions')
@patch('minerva.chat.mcp_client.MCPClient.check_connection_sync')
@patch('minerva.chat.mcp_client.MCPClient.call_tool_sync')
def test_send_message_with_tool_call(mock_execute_tool, mock_check_connection, mock_get_tools, mock_config, mock_provider):
    mock_check_connection.return_value = True
    mock_get_tools.return_value = [
        {
            'type': 'function',
            'function': {
                'name': 'list_knowledge_bases',
                'description': 'List knowledge bases',
                'parameters': {'type': 'object', 'properties': {}}
            }
        }
    ]

    mock_execute_tool.return_value = {
        'success': True,
        'collections': [],
        'count': 0
    }

    call_count = [0]

    def chat_completion_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {
                'content': '',
                'tool_calls': [
                    {
                        'id': 'call_123',
                        'function': {
                            'name': 'list_knowledge_bases',
                            'arguments': '{}'
                        }
                    }
                ]
            }
        else:
            return {
                'content': 'I found no knowledge bases.',
                'tool_calls': None
            }

    mock_provider.chat_completion.side_effect = chat_completion_side_effect

    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='You are a helpful assistant',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        response = engine.send_message('List my knowledge bases')

    assert response == 'I found no knowledge bases.'
    assert mock_execute_tool.called
    assert engine.get_message_count() > 3


@patch.object(ChatEngine, '_get_tool_definitions')
@patch('minerva.chat.mcp_client.MCPClient.check_connection_sync')
@patch('minerva.chat.mcp_client.MCPClient.call_tool_sync')
def test_send_message_with_search_tool(mock_execute_tool, mock_check_connection, mock_get_tools, mock_config, mock_provider):
    mock_check_connection.return_value = True
    mock_get_tools.return_value = [
        {
            'type': 'function',
            'function': {
                'name': 'search_knowledge_base',
                'description': 'Search knowledge base',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string'},
                        'collection_name': {'type': 'string'}
                    }
                }
            }
        }
    ]

    mock_execute_tool.return_value = {
        'success': True,
        'results': [
            {
                'noteTitle': 'Test Note',
                'content': 'Test content',
                'similarityScore': 0.95
            }
        ],
        'count': 1,
        'query': 'test',
        'collection_name': 'my-notes'
    }

    call_count = [0]

    def chat_completion_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {
                'content': '',
                'tool_calls': [
                    {
                        'id': 'call_456',
                        'function': {
                            'name': 'search_knowledge_base',
                            'arguments': json.dumps({
                                'query': 'test',
                                'collection_name': 'my-notes'
                            })
                        }
                    }
                ]
            }
        else:
            return {
                'content': 'I found relevant information in Test Note.',
                'tool_calls': None
            }

    mock_provider.chat_completion.side_effect = chat_completion_side_effect

    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='You are a helpful assistant',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        response = engine.send_message('Search for test')

    assert 'relevant information' in response
    assert mock_execute_tool.called

    call_args = mock_execute_tool.call_args
    assert call_args[0][0] == 'search_knowledge_base'
    assert call_args[0][1]['query'] == 'test'
    assert call_args[0][1]['collection_name'] == 'my-notes'


def test_resume_conversation(mock_config, mock_provider, mock_mcp_client):
    engine1 = ChatEngine()
    conv_id = engine1.initialize_conversation(
        system_prompt='Original prompt',
        ai_provider=mock_provider,
        config=mock_config
    )

    mock_provider.chat_completion.return_value = {
        'content': 'First response',
        'tool_calls': None
    }

    with patch('builtins.print'):
        engine1.send_message('First message')

    engine2 = ChatEngine()
    engine2.resume_conversation(conv_id, mock_provider, mock_config)

    assert engine2.get_conversation_id() == conv_id
    assert engine2.get_message_count() == 3


def test_get_conversation_id_before_initialization():
    engine = ChatEngine()

    assert engine.get_conversation_id() is None


def test_get_message_count_before_initialization():
    engine = ChatEngine()

    assert engine.get_message_count() == 0


@patch.object(ChatEngine, '_get_tool_definitions')
def test_clear_conversation(mock_get_tools, mock_config, mock_provider, mock_mcp_client):
    mock_get_tools.return_value = []
    mock_provider.chat_completion.return_value = {
        'content': 'Response',
        'tool_calls': None
    }

    engine = ChatEngine()
    original_conv_id = engine.initialize_conversation(
        system_prompt='Original',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        engine.send_message('Message')

    assert engine.get_message_count() == 3

    new_conv_id = engine.clear_conversation('New prompt')

    assert new_conv_id != original_conv_id
    assert engine.get_message_count() == 1


@patch.object(ChatEngine, '_get_tool_definitions')
def test_message_history_persistence(mock_get_tools, mock_config, mock_provider, mock_mcp_client):
    mock_get_tools.return_value = []
    mock_provider.chat_completion.return_value = {
        'content': 'Test response',
        'tool_calls': None
    }

    engine = ChatEngine()
    conv_id = engine.initialize_conversation(
        system_prompt='Test',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        engine.send_message('Test message')

    conv_file = Path(mock_config.conversation_dir) / f"{conv_id}.json"
    with open(conv_file, 'r') as f:
        data = json.load(f)

    assert len(data['messages']) == 3
    assert data['messages'][1]['role'] == 'user'
    assert data['messages'][1]['content'] == 'Test message'
    assert data['messages'][2]['role'] == 'assistant'
    assert data['messages'][2]['content'] == 'Test response'


@patch.object(ChatEngine, '_get_tool_definitions')
def test_multiple_messages_conversation(mock_get_tools, mock_config, mock_provider, mock_mcp_client):
    mock_get_tools.return_value = []

    responses = [
        {'content': 'Response 1', 'tool_calls': None},
        {'content': 'Response 2', 'tool_calls': None},
        {'content': 'Response 3', 'tool_calls': None}
    ]

    mock_provider.chat_completion.side_effect = responses

    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='Test',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        engine.send_message('Message 1')
        engine.send_message('Message 2')
        engine.send_message('Message 3')

    assert engine.get_message_count() == 7


@patch.object(ChatEngine, '_get_tool_definitions')
@patch('minerva.chat.mcp_client.MCPClient.check_connection_sync')
@patch('minerva.chat.mcp_client.MCPClient.call_tool_sync')
def test_multiple_tool_calls_in_sequence(mock_execute_tool, mock_check_connection, mock_get_tools, mock_config, mock_provider):
    mock_check_connection.return_value = True
    mock_get_tools.return_value = []

    mock_execute_tool.return_value = {
        'success': True,
        'collections': [],
        'count': 0
    }

    responses = [
        {
            'content': '',
            'tool_calls': [
                {
                    'id': 'call_1',
                    'function': {'name': 'list_knowledge_bases', 'arguments': '{}'}
                }
            ]
        },
        {
            'content': '',
            'tool_calls': [
                {
                    'id': 'call_2',
                    'function': {
                        'name': 'search_knowledge_base',
                        'arguments': json.dumps({'query': 'test', 'collection_name': 'notes'})
                    }
                }
            ]
        },
        {
            'content': 'Final response',
            'tool_calls': None
        }
    ]

    mock_provider.chat_completion.side_effect = responses

    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='Test',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        response = engine.send_message('Complex query')

    assert response == 'Final response'
    assert mock_execute_tool.call_count == 2


def test_streaming_mode_disabled(mock_config, mock_provider, mock_mcp_client):
    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='Test',
        ai_provider=mock_provider,
        config=mock_config
    )

    assert engine.config.enable_streaming is False


def test_conversation_metadata_updated(mock_config, mock_provider, mock_mcp_client):
    mock_provider.chat_completion.return_value = {
        'content': 'Response',
        'tool_calls': None
    }

    engine = ChatEngine()
    conv_id = engine.initialize_conversation(
        system_prompt='Test',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        engine.send_message('Message')

    conv_file = Path(mock_config.conversation_dir) / f"{conv_id}.json"
    with open(conv_file, 'r') as f:
        data = json.load(f)

    assert 'metadata' in data
    assert 'message_count' in data['metadata']
    assert 'total_tokens' in data['metadata']
    assert data['metadata']['message_count'] == 3


@patch.object(ChatEngine, '_get_tool_definitions')
@patch('minerva.chat.mcp_client.MCPClient.check_connection_sync')
@patch('minerva.chat.mcp_client.MCPClient.call_tool_sync')
def test_max_iterations_protection(mock_execute_tool, mock_check_connection, mock_get_tools, mock_config, mock_provider):
    mock_check_connection.return_value = True
    mock_get_tools.return_value = []
    mock_execute_tool.return_value = {'success': True, 'collections': [], 'count': 0}

    mock_provider.chat_completion.return_value = {
        'content': '',
        'tool_calls': [
            {
                'id': 'call_infinite',
                'function': {'name': 'list_knowledge_bases', 'arguments': '{}'}
            }
        ]
    }

    engine = ChatEngine()
    engine.initialize_conversation(
        system_prompt='Test',
        ai_provider=mock_provider,
        config=mock_config
    )

    with patch('builtins.print'):
        engine.send_message('Message')

    assert mock_provider.chat_completion.call_count == 5
