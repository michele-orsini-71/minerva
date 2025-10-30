"""
Tests for search_tools.py to ensure noteTitle is always present in results.

These tests verify that citation information is properly included in search results
so that AI assistants can cite sources when presenting information to users.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from minerva.server.search_tools import search_knowledge_base


class TestCitationRequirement:
    """Tests to ensure noteTitle field is always present for citations."""

    @patch('minerva.server.search_tools.initialize_chromadb_client')
    def test_search_results_include_note_title(self, mock_chromadb_client):
        """Verify that every search result includes noteTitle field."""
        # Mock ChromaDB collection and results
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        mock_collection.query.return_value = {
            'ids': [['chunk1', 'chunk2', 'chunk3']],
            'distances': [[0.1, 0.2, 0.3]],
            'documents': [['Content 1', 'Content 2', 'Content 3']],
            'metadatas': [[
                {'title': 'Note Title 1', 'noteId': 'note1', 'chunkIndex': 0, 'modificationDate': '2025-01-01'},
                {'title': 'Note Title 2', 'noteId': 'note2', 'chunkIndex': 1, 'modificationDate': '2025-01-02'},
                {'title': 'Note Title 3', 'noteId': 'note3', 'chunkIndex': 2, 'modificationDate': '2025-01-03'}
            ]]
        }

        mock_client = MagicMock()
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb_client.return_value = mock_client

        # Mock AI provider
        mock_provider = MagicMock()
        mock_provider.generate_embedding.return_value = [0.1] * 1024  # Match expected dimension
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'test-model'
        }

        # Execute search
        results = search_knowledge_base(
            query="test query",
            collection_name="test_collection",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="chunk_only",
            max_results=5
        )

        # Verify all results have noteTitle
        assert len(results) == 3, "Should return 3 results"

        for i, result in enumerate(results):
            assert 'noteTitle' in result, f"Result {i} missing 'noteTitle' field"
            assert result['noteTitle'] != '', f"Result {i} has empty 'noteTitle'"
            assert result['noteTitle'] is not None, f"Result {i} has None 'noteTitle'"
            assert isinstance(result['noteTitle'], str), f"Result {i} 'noteTitle' is not a string"

    @patch('minerva.server.search_tools.initialize_chromadb_client')
    def test_search_results_handle_missing_title_metadata(self, mock_chromadb_client):
        """Verify that search handles missing title metadata gracefully with 'Unknown'."""
        # Mock ChromaDB collection with missing title metadata
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'distances': [[0.1]],
            'documents': [['Content without title']],
            'metadatas': [[
                {'noteId': 'note1', 'chunkIndex': 0}  # Missing 'title' key
            ]]
        }

        mock_client = MagicMock()
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb_client.return_value = mock_client

        # Mock AI provider
        mock_provider = MagicMock()
        mock_provider.generate_embedding.return_value = [0.1] * 1024  # Match expected dimension
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'test-model'
        }

        # Execute search
        results = search_knowledge_base(
            query="test query",
            collection_name="test_collection",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="chunk_only",
            max_results=5
        )

        # Verify noteTitle defaults to 'Unknown' when missing
        assert len(results) == 1
        assert 'noteTitle' in results[0]
        assert results[0]['noteTitle'] == 'Unknown', "Should default to 'Unknown' when title is missing"

    @patch('minerva.server.search_tools.initialize_chromadb_client')
    def test_search_with_enhanced_context_includes_note_title(self, mock_chromadb_client):
        """Verify enhanced context mode also includes noteTitle."""
        # Mock ChromaDB collection
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'distances': [[0.1]],
            'documents': [['Content 1']],
            'metadatas': [[
                {'title': 'Enhanced Note', 'noteId': 'note1', 'chunkIndex': 1, 'modificationDate': '2025-01-01'}
            ]]
        }

        # Mock get() for context retrieval
        mock_collection.get.return_value = {
            'documents': ['Previous chunk', 'Content 1', 'Next chunk'],
            'metadatas': [
                {'chunkIndex': 0},
                {'chunkIndex': 1},
                {'chunkIndex': 2}
            ]
        }

        mock_client = MagicMock()
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb_client.return_value = mock_client

        # Mock AI provider
        mock_provider = MagicMock()
        mock_provider.generate_embedding.return_value = [0.1] * 1024  # Match expected dimension
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'test-model'
        }

        # Execute search with enhanced context
        results = search_knowledge_base(
            query="test query",
            collection_name="test_collection",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="enhanced",
            max_results=5
        )

        # Verify noteTitle is present even with enhanced context
        assert len(results) == 1
        assert 'noteTitle' in results[0]
        assert results[0]['noteTitle'] == 'Enhanced Note'

    @patch('minerva.server.search_tools.initialize_chromadb_client')
    def test_empty_search_results_return_empty_list(self, mock_chromadb_client):
        """Verify empty search results don't cause citation issues."""
        # Mock ChromaDB collection with no results
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        mock_collection.query.return_value = {
            'ids': [[]],
            'distances': [[]],
            'documents': [[]],
            'metadatas': [[]]
        }

        mock_client = MagicMock()
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb_client.return_value = mock_client

        # Mock AI provider
        mock_provider = MagicMock()
        mock_provider.generate_embedding.return_value = [0.1] * 1024  # Match expected dimension
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'test-model'
        }

        # Execute search
        results = search_knowledge_base(
            query="test query",
            collection_name="test_collection",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="chunk_only",
            max_results=5
        )

        # Verify empty list is returned (no noteTitle issues)
        assert results == []
        assert isinstance(results, list)


class TestResultStructure:
    """Tests to verify complete result structure for proper citation."""

    @patch('minerva.server.search_tools.initialize_chromadb_client')
    def test_result_contains_all_citation_fields(self, mock_chromadb_client):
        """Verify results contain all fields needed for proper citation."""
        # Mock ChromaDB collection
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        mock_collection.query.return_value = {
            'ids': [['chunk1']],
            'distances': [[0.15]],
            'documents': [['Test content']],
            'metadatas': [[
                {
                    'title': 'Test Note',
                    'noteId': 'note123',
                    'chunkIndex': 5,
                    'modificationDate': '2025-01-15T10:30:00Z'
                }
            ]]
        }

        mock_client = MagicMock()
        mock_client.list_collections.return_value = [mock_collection]
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb_client.return_value = mock_client

        # Mock AI provider
        mock_provider = MagicMock()
        mock_provider.generate_embedding.return_value = [0.1] * 1024  # Match expected dimension
        mock_collection.metadata = {
            'embedding_dimension': 1024,
            'embedding_provider': 'ollama',
            'embedding_model': 'test-model'
        }

        # Execute search
        results = search_knowledge_base(
            query="test query",
            collection_name="test_collection",
            chromadb_path="/fake/path",
            provider=mock_provider,
            context_mode="chunk_only",
            max_results=5
        )

        # Verify complete result structure
        assert len(results) == 1
        result = results[0]

        # Citation fields
        assert 'noteTitle' in result
        assert 'noteId' in result
        assert 'chunkIndex' in result
        assert 'modificationDate' in result

        # Search metadata
        assert 'collectionName' in result
        assert 'similarityScore' in result
        assert 'chunkId' in result
        assert 'content' in result

        # Verify values
        assert result['noteTitle'] == 'Test Note'
        assert result['noteId'] == 'note123'
        assert result['chunkIndex'] == 5
        assert result['collectionName'] == 'test_collection'
