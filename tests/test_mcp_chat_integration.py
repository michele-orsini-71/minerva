import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from minerva.chat.mcp_client import MCPClient, MCPToolDefinition, MCPConnectionError, MCPToolExecutionError
from minerva.chat.chat_engine import ChatEngine
from minerva.chat.config import ChatConfig
from minerva.common.ai_config import AIProviderConfig
from minerva.common.ai_provider import AIProvider


class MockFastMCPClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint
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

        self.tools = [tool1, tool2]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def list_tools(self):
        return self.tools

    async def call_tool(self, tool_name, arguments):
        result = Mock()
        if tool_name == "list_knowledge_bases":
            content_item = Mock()
            content_item.text = json.dumps([
                {"name": "test_collection", "description": "Test collection", "chunk_count": 10}
            ])
            result.content = [content_item]
        elif tool_name == "search_knowledge_base":
            content_item = Mock()
            content_item.text = json.dumps([
                {
                    "noteTitle": "Test Note",
                    "content": "Test content",
                    "similarityScore": 0.95,
                    "modificationDate": "2025-01-01"
                }
            ])
            result.content = [content_item]
        return result


@pytest.fixture
def mock_mcp_client():
    with patch('minerva.chat.mcp_client.FastMCPClient', MockFastMCPClient):
        yield


@pytest.fixture
def temp_conversation_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def chat_config(temp_conversation_dir):
    ai_config = AIProviderConfig(
        provider_type="ollama",
        embedding_model="test-embed",
        llm_model="test-llm",
        base_url="http://localhost:11434"
    )

    return ChatConfig(
        ai_provider=ai_config,
        conversation_dir=temp_conversation_dir,
        chromadb_path="/tmp/test_chromadb",
        enable_streaming=False,
        mcp_server_url="http://localhost:8000",
        max_tool_iterations=5,
        system_prompt_file=None
    )


@pytest.fixture
def mock_ai_provider():
    provider = Mock(spec=AIProvider)
    provider.chat_completion = Mock(return_value={
        'content': 'Test response',
        'tool_calls': None
    })
    return provider


class TestMCPClient:
    def test_mcp_client_initialization(self, mock_mcp_client):
        client = MCPClient("http://localhost:8000")
        assert client.server_url == "http://localhost:8000"
        assert client.mcp_endpoint == "http://localhost:8000/mcp"

    def test_check_connection_sync(self, mock_mcp_client):
        client = MCPClient("http://localhost:8000")
        result = client.check_connection_sync()
        assert result is True

    def test_get_tool_definitions_sync(self, mock_mcp_client):
        client = MCPClient("http://localhost:8000")
        tools = client.get_tool_definitions_sync()

        assert len(tools) == 2
        assert all(isinstance(tool, MCPToolDefinition) for tool in tools)
        assert tools[0].name == "list_knowledge_bases"
        assert tools[1].name == "search_knowledge_base"

    def test_tool_definition_to_openai_format(self, mock_mcp_client):
        client = MCPClient("http://localhost:8000")
        tools = client.get_tool_definitions_sync()

        openai_format = tools[0].to_openai_format()
        assert openai_format['type'] == 'function'
        assert 'function' in openai_format
        assert openai_format['function']['name'] == 'list_knowledge_bases'

    def test_call_tool_sync_list_knowledge_bases(self, mock_mcp_client):
        client = MCPClient("http://localhost:8000")
        result = client.call_tool_sync("list_knowledge_bases", {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['name'] == 'test_collection'

    def test_call_tool_sync_search_knowledge_base(self, mock_mcp_client):
        client = MCPClient("http://localhost:8000")
        result = client.call_tool_sync("search_knowledge_base", {
            "query": "test query",
            "collection_name": "test_collection"
        })

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['noteTitle'] == 'Test Note'


class TestMCPConnectionError:
    def test_connection_error_raised_on_failure(self):
        with patch('minerva.chat.mcp_client.FastMCPClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.side_effect = Exception("Connection failed")
            MockClient.return_value = mock_instance

            client = MCPClient("http://localhost:8000")

            with pytest.raises(MCPConnectionError):
                client.get_tool_definitions_sync()


class TestChatEngineWithMCP:
    def test_chat_engine_initializes_mcp_client(self, chat_config, mock_ai_provider, mock_mcp_client):
        engine = ChatEngine()

        conversation_id = engine.initialize_conversation(
            system_prompt="Test prompt",
            ai_provider=mock_ai_provider,
            config=chat_config
        )

        assert engine.mcp_client is not None
        assert engine._mcp_available is True
        assert conversation_id is not None

    def test_chat_engine_handles_mcp_unavailable(self, chat_config, mock_ai_provider):
        with patch('minerva.chat.mcp_client.FastMCPClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.side_effect = Exception("Connection failed")
            MockClient.return_value = mock_instance

            engine = ChatEngine()

            conversation_id = engine.initialize_conversation(
                system_prompt="Test prompt",
                ai_provider=mock_ai_provider,
                config=chat_config
            )

            assert engine.mcp_client is not None
            assert engine._mcp_available is False
            assert conversation_id is not None

    def test_chat_engine_fetches_tool_definitions_from_mcp(self, chat_config, mock_ai_provider, mock_mcp_client):
        engine = ChatEngine()

        engine.initialize_conversation(
            system_prompt="Test prompt",
            ai_provider=mock_ai_provider,
            config=chat_config
        )

        tool_defs = engine._get_tool_definitions()

        assert len(tool_defs) == 2
        assert tool_defs[0]['type'] == 'function'
        assert tool_defs[0]['function']['name'] == 'list_knowledge_bases'

    def test_chat_engine_returns_empty_tools_when_mcp_unavailable(self, chat_config, mock_ai_provider):
        with patch('minerva.chat.mcp_client.FastMCPClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.side_effect = Exception("Connection failed")
            MockClient.return_value = mock_instance

            engine = ChatEngine()

            engine.initialize_conversation(
                system_prompt="Test prompt",
                ai_provider=mock_ai_provider,
                config=chat_config
            )

            tool_defs = engine._get_tool_definitions()
            assert tool_defs == []

    def test_streaming_fallback_on_error(self, chat_config, mock_ai_provider, mock_mcp_client):
        chat_config_with_streaming = ChatConfig(
            ai_provider=chat_config.ai_provider,
            conversation_dir=chat_config.conversation_dir,
            chromadb_path=chat_config.chromadb_path,
            enable_streaming=True,
            mcp_server_url=chat_config.mcp_server_url,
            max_tool_iterations=chat_config.max_tool_iterations,
            system_prompt_file=None
        )

        mock_ai_provider.chat_completion_streaming = Mock(side_effect=Exception("Streaming not supported"))
        mock_ai_provider.chat_completion = Mock(return_value={
            'content': 'Non-streaming response',
            'tool_calls': None
        })

        engine = ChatEngine()
        engine.initialize_conversation(
            system_prompt="Test prompt",
            ai_provider=mock_ai_provider,
            config=chat_config_with_streaming
        )

        response = engine.send_message("Test message")

        assert response == 'Non-streaming response'
        assert engine._streaming_enabled is False
        assert engine._streaming_fallback_triggered is True

    def test_max_tool_iterations_respected(self, chat_config, mock_ai_provider, mock_mcp_client):
        mock_ai_provider.chat_completion = Mock(return_value={
            'content': 'Response with tool call',
            'tool_calls': [{
                'id': 'call_1',
                'function': {
                    'name': 'list_knowledge_bases',
                    'arguments': '{}'
                }
            }]
        })

        config_with_low_max = ChatConfig(
            ai_provider=chat_config.ai_provider,
            conversation_dir=chat_config.conversation_dir,
            chromadb_path=chat_config.chromadb_path,
            enable_streaming=False,
            mcp_server_url=chat_config.mcp_server_url,
            max_tool_iterations=2,
            system_prompt_file=None
        )

        engine = ChatEngine()
        engine.initialize_conversation(
            system_prompt="Test prompt",
            ai_provider=mock_ai_provider,
            config=config_with_low_max
        )

        response = engine.send_message("Test message")

        assert mock_ai_provider.chat_completion.call_count <= 2 + 1
