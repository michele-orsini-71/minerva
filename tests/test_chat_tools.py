import pytest
from unittest.mock import Mock, patch
from minerva.chat.tools import (
    get_tool_definitions,
    execute_tool,
    format_tool_result,
    _execute_list_knowledge_bases,
    _execute_search_knowledge_base,
    _format_list_knowledge_bases_result,
    _format_search_result,
    TOOL_LIST_KNOWLEDGE_BASES,
    TOOL_SEARCH_KNOWLEDGE_BASE
)
from minerva.server.collection_discovery import CollectionDiscoveryError
from minerva.server.search_tools import SearchError, CollectionNotFoundError


def test_get_tool_definitions_returns_list():
    tools = get_tool_definitions()

    assert isinstance(tools, list)
    assert len(tools) == 2


def test_get_tool_definitions_contains_list_knowledge_bases():
    tools = get_tool_definitions()

    tool_names = [t['function']['name'] for t in tools]
    assert 'list_knowledge_bases' in tool_names


def test_get_tool_definitions_contains_search_knowledge_base():
    tools = get_tool_definitions()

    tool_names = [t['function']['name'] for t in tools]
    assert 'search_knowledge_base' in tool_names


def test_tool_list_knowledge_bases_structure():
    assert TOOL_LIST_KNOWLEDGE_BASES['type'] == 'function'
    assert TOOL_LIST_KNOWLEDGE_BASES['function']['name'] == 'list_knowledge_bases'
    assert 'description' in TOOL_LIST_KNOWLEDGE_BASES['function']
    assert 'parameters' in TOOL_LIST_KNOWLEDGE_BASES['function']


def test_tool_search_knowledge_base_structure():
    assert TOOL_SEARCH_KNOWLEDGE_BASE['type'] == 'function'
    assert TOOL_SEARCH_KNOWLEDGE_BASE['function']['name'] == 'search_knowledge_base'
    assert 'query' in TOOL_SEARCH_KNOWLEDGE_BASE['function']['parameters']['properties']
    assert 'collection_name' in TOOL_SEARCH_KNOWLEDGE_BASE['function']['parameters']['properties']


def test_tool_search_parameters_include_optional_fields():
    params = TOOL_SEARCH_KNOWLEDGE_BASE['function']['parameters']['properties']

    assert 'max_results' in params
    assert 'context_mode' in params
    assert params['max_results']['minimum'] == 1
    assert params['max_results']['maximum'] == 15


@patch('minerva.chat.tools.list_collections')
def test_execute_list_knowledge_bases_success(mock_list_collections):
    mock_list_collections.return_value = [
        {
            'name': 'my-notes',
            'description': 'Personal notes',
            'chunk_count': 100,
            'available': True
        }
    ]

    context = {'chromadb_path': '/path/to/chromadb'}
    result = _execute_list_knowledge_bases(context)

    assert result['success'] is True
    assert result['count'] == 1
    assert len(result['collections']) == 1
    assert result['collections'][0]['name'] == 'my-notes'


@patch('minerva.chat.tools.list_collections')
def test_execute_list_knowledge_bases_empty(mock_list_collections):
    mock_list_collections.return_value = []

    context = {'chromadb_path': '/path/to/chromadb'}
    result = _execute_list_knowledge_bases(context)

    assert result['success'] is True
    assert result['count'] == 0
    assert result['collections'] == []


def test_execute_list_knowledge_bases_missing_chromadb_path():
    context = {}
    result = _execute_list_knowledge_bases(context)

    assert result['success'] is False
    assert 'chromadb_path not provided' in result['error']


@patch('minerva.chat.tools.list_collections')
def test_execute_list_knowledge_bases_discovery_error(mock_list_collections):
    mock_list_collections.side_effect = CollectionDiscoveryError('Discovery failed')

    context = {'chromadb_path': '/path/to/chromadb'}
    result = _execute_list_knowledge_bases(context)

    assert result['success'] is False
    assert 'Discovery failed' in result['error']


@patch('minerva.chat.tools.search_knowledge_base')
def test_execute_search_knowledge_base_success(mock_search):
    mock_search.return_value = [
        {
            'noteTitle': 'Test Note',
            'similarityScore': 0.95,
            'content': 'Test content',
            'modificationDate': '2025-10-30'
        }
    ]

    context = {
        'chromadb_path': '/path/to/chromadb',
        'provider': Mock()
    }
    arguments = {
        'query': 'test query',
        'collection_name': 'my-notes'
    }

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is True
    assert result['count'] == 1
    assert result['query'] == 'test query'
    assert result['collection_name'] == 'my-notes'
    assert len(result['results']) == 1


@patch('minerva.chat.tools.search_knowledge_base')
def test_execute_search_knowledge_base_with_options(mock_search):
    mock_search.return_value = []

    context = {
        'chromadb_path': '/path/to/chromadb',
        'provider': Mock()
    }
    arguments = {
        'query': 'test',
        'collection_name': 'notes',
        'max_results': 10,
        'context_mode': 'full_note'
    }

    result = _execute_search_knowledge_base(arguments, context)

    mock_search.assert_called_once_with(
        query='test',
        collection_name='notes',
        chromadb_path='/path/to/chromadb',
        provider=context['provider'],
        context_mode='full_note',
        max_results=10
    )


def test_execute_search_knowledge_base_missing_chromadb_path():
    context = {'provider': Mock()}
    arguments = {'query': 'test', 'collection_name': 'notes'}

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is False
    assert 'chromadb_path not provided' in result['error']


def test_execute_search_knowledge_base_missing_provider():
    context = {'chromadb_path': '/path'}
    arguments = {'query': 'test', 'collection_name': 'notes'}

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is False
    assert 'AI provider not provided' in result['error']


def test_execute_search_knowledge_base_missing_query():
    context = {
        'chromadb_path': '/path',
        'provider': Mock()
    }
    arguments = {'collection_name': 'notes'}

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is False
    assert 'query parameter is required' in result['error']


def test_execute_search_knowledge_base_missing_collection_name():
    context = {
        'chromadb_path': '/path',
        'provider': Mock()
    }
    arguments = {'query': 'test'}

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is False
    assert 'collection_name parameter is required' in result['error']


@patch('minerva.chat.tools.search_knowledge_base')
def test_execute_search_knowledge_base_collection_not_found(mock_search):
    mock_search.side_effect = CollectionNotFoundError('Collection not found')

    context = {
        'chromadb_path': '/path',
        'provider': Mock()
    }
    arguments = {
        'query': 'test',
        'collection_name': 'nonexistent'
    }

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is False
    assert 'Collection not found' in result['error']


@patch('minerva.chat.tools.search_knowledge_base')
def test_execute_search_knowledge_base_search_error(mock_search):
    mock_search.side_effect = SearchError('Search failed')

    context = {
        'chromadb_path': '/path',
        'provider': Mock()
    }
    arguments = {
        'query': 'test',
        'collection_name': 'notes'
    }

    result = _execute_search_knowledge_base(arguments, context)

    assert result['success'] is False
    assert 'Search failed' in result['error']


@patch('minerva.chat.tools._execute_list_knowledge_bases')
def test_execute_tool_list_knowledge_bases(mock_execute):
    mock_execute.return_value = {'success': True, 'collections': []}

    context = {'chromadb_path': '/path'}
    result = execute_tool('list_knowledge_bases', {}, context)

    assert result['success'] is True
    mock_execute.assert_called_once_with(context)


@patch('minerva.chat.tools._execute_search_knowledge_base')
def test_execute_tool_search_knowledge_base(mock_execute):
    mock_execute.return_value = {'success': True, 'results': []}

    context = {'chromadb_path': '/path', 'provider': Mock()}
    arguments = {'query': 'test', 'collection_name': 'notes'}
    result = execute_tool('search_knowledge_base', arguments, context)

    assert result['success'] is True
    mock_execute.assert_called_once_with(arguments, context)


def test_execute_tool_unknown_tool():
    result = execute_tool('unknown_tool', {}, {})

    assert result['success'] is False
    assert 'Unknown tool' in result['error']


def test_format_tool_result_failure():
    result = {'success': False, 'error': 'Something went wrong'}

    formatted = format_tool_result('any_tool', result)

    assert 'failed' in formatted.lower()
    assert 'Something went wrong' in formatted


def test_format_list_knowledge_bases_result_empty():
    result = {'success': True, 'collections': [], 'count': 0}

    formatted = _format_list_knowledge_bases_result(result)

    assert 'No knowledge bases found' in formatted


def test_format_list_knowledge_bases_result_single():
    result = {
        'success': True,
        'count': 1,
        'collections': [
            {
                'name': 'my-notes',
                'description': 'Personal notes',
                'chunk_count': 100,
                'available': True
            }
        ]
    }

    formatted = _format_list_knowledge_bases_result(result)

    assert 'Found 1 knowledge base' in formatted
    assert 'my-notes' in formatted
    assert 'Personal notes' in formatted
    assert '100' in formatted


def test_format_list_knowledge_bases_result_unavailable():
    result = {
        'success': True,
        'count': 1,
        'collections': [
            {
                'name': 'broken-notes',
                'description': 'Broken collection',
                'chunk_count': 0,
                'available': False,
                'unavailable_reason': 'Empty collection'
            }
        ]
    }

    formatted = _format_list_knowledge_bases_result(result)

    assert 'broken-notes' in formatted
    assert 'Unavailable' in formatted
    assert 'Empty collection' in formatted


def test_format_search_result_empty():
    result = {
        'success': True,
        'count': 0,
        'results': [],
        'query': 'test query',
        'collection_name': 'my-notes'
    }

    formatted = _format_search_result(result)

    assert 'No results found' in formatted
    assert 'test query' in formatted
    assert 'my-notes' in formatted


def test_format_search_result_single():
    result = {
        'success': True,
        'count': 1,
        'results': [
            {
                'noteTitle': 'Test Note',
                'similarityScore': 0.95,
                'modificationDate': '2025-10-30',
                'content': 'This is test content'
            }
        ],
        'query': 'test',
        'collection_name': 'notes'
    }

    formatted = _format_search_result(result)

    assert 'Found 1 result' in formatted
    assert 'Test Note' in formatted
    assert '95.00%' in formatted
    assert 'This is test content' in formatted


def test_format_search_result_multiple():
    result = {
        'success': True,
        'count': 3,
        'results': [
            {
                'noteTitle': 'Note 1',
                'similarityScore': 0.95,
                'content': 'Content 1'
            },
            {
                'noteTitle': 'Note 2',
                'similarityScore': 0.85,
                'content': 'Content 2'
            },
            {
                'noteTitle': 'Note 3',
                'similarityScore': 0.75,
                'content': 'Content 3'
            }
        ],
        'query': 'test',
        'collection_name': 'notes'
    }

    formatted = _format_search_result(result)

    assert 'Found 3 result' in formatted
    assert 'Note 1' in formatted
    assert 'Note 2' in formatted
    assert 'Note 3' in formatted


def test_format_search_result_long_content_truncation():
    long_content = 'A' * 300
    result = {
        'success': True,
        'count': 1,
        'results': [
            {
                'noteTitle': 'Long Note',
                'similarityScore': 0.9,
                'content': long_content
            }
        ],
        'query': 'test',
        'collection_name': 'notes'
    }

    formatted = _format_search_result(result)

    assert '...' in formatted
    assert len(formatted) < len(long_content) + 500


def test_format_tool_result_list_knowledge_bases():
    result = {
        'success': True,
        'collections': [{'name': 'notes', 'description': 'My notes', 'chunk_count': 50, 'available': True}],
        'count': 1
    }

    formatted = format_tool_result('list_knowledge_bases', result)

    assert 'notes' in formatted
    assert 'My notes' in formatted


def test_format_tool_result_search_knowledge_base():
    result = {
        'success': True,
        'results': [
            {'noteTitle': 'Test', 'similarityScore': 0.9, 'content': 'Test content'}
        ],
        'count': 1,
        'query': 'test',
        'collection_name': 'notes'
    }

    formatted = format_tool_result('search_knowledge_base', result)

    assert 'Test' in formatted
    assert 'test' in formatted


def test_tool_definitions_are_valid_openai_format():
    tools = get_tool_definitions()

    for tool in tools:
        assert 'type' in tool
        assert tool['type'] == 'function'
        assert 'function' in tool
        assert 'name' in tool['function']
        assert 'description' in tool['function']
        assert 'parameters' in tool['function']
        assert 'type' in tool['function']['parameters']
        assert 'properties' in tool['function']['parameters']


@patch('minerva.chat.tools.search_knowledge_base')
def test_execute_search_uses_default_max_results(mock_search):
    mock_search.return_value = []

    context = {'chromadb_path': '/path', 'provider': Mock()}
    arguments = {'query': 'test', 'collection_name': 'notes'}

    _execute_search_knowledge_base(arguments, context)

    call_args = mock_search.call_args
    assert call_args.kwargs['max_results'] == 3


@patch('minerva.chat.tools.search_knowledge_base')
def test_execute_search_uses_default_context_mode(mock_search):
    mock_search.return_value = []

    context = {'chromadb_path': '/path', 'provider': Mock()}
    arguments = {'query': 'test', 'collection_name': 'notes'}

    _execute_search_knowledge_base(arguments, context)

    call_args = mock_search.call_args
    assert call_args.kwargs['context_mode'] == 'enhanced'
