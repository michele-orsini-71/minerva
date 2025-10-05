import pytest
from pathlib import Path
from unittest.mock import Mock
import sys

# Add parent directory to path to import context_retrieval module
sys.path.insert(0, str(Path(__file__).parent.parent))

from context_retrieval import (
    get_chunk_only_content,
    get_enhanced_content,
    get_full_note_content,
    apply_context_mode,
    ContextRetrievalError
)


class TestGetChunkOnlyContent:
    """Test chunk_only context mode."""

    def test_chunk_only_basic(self):
        """Test chunk_only returns just the matched chunk."""
        mock_collection = Mock()

        result = {
            'noteId': 'note123',
            'chunkIndex': 2,
            'content': 'This is the matched chunk',
            'totalChunks': 1
        }

        enhanced = get_chunk_only_content(mock_collection, result)

        assert enhanced['content'] == 'This is the matched chunk'
        assert enhanced['totalChunks'] == 1
        assert enhanced['noteId'] == 'note123'


class TestGetEnhancedContent:
    """Test enhanced context mode with surrounding chunks."""

    def test_enhanced_with_surrounding_chunks(self):
        """Test enhanced mode retrieves surrounding chunks with markers."""
        mock_collection = Mock()

        # Mock the get() call to return surrounding chunks
        mock_collection.get.return_value = {
            'ids': ['chunk1', 'chunk2', 'chunk3', 'chunk4', 'chunk5'],
            'documents': [
                'Chunk 0 content',
                'Chunk 1 content',
                'Chunk 2 content',
                'Chunk 3 content',
                'Chunk 4 content'
            ],
            'metadatas': [
                {'chunkIndex': 0},
                {'chunkIndex': 1},
                {'chunkIndex': 2},
                {'chunkIndex': 3},
                {'chunkIndex': 4}
            ]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 2,  # Matched chunk
            'content': 'Original content'
        }

        enhanced = get_enhanced_content(mock_collection, result)

        # Verify markers are present
        assert '[MATCH START]' in enhanced['content']
        assert '[MATCH END]' in enhanced['content']

        # Verify surrounding chunks are included
        assert 'Chunk 0 content' in enhanced['content']
        assert 'Chunk 1 content' in enhanced['content']
        assert 'Chunk 2 content' in enhanced['content']
        assert 'Chunk 3 content' in enhanced['content']
        assert 'Chunk 4 content' in enhanced['content']

        # Verify totalChunks is updated
        assert enhanced['totalChunks'] == 5

    def test_enhanced_first_chunk(self):
        """Test enhanced mode when matched chunk is first (no predecessors)."""
        mock_collection = Mock()

        # Mock returns chunks 0, 1, 2 (matched is 0)
        mock_collection.get.return_value = {
            'ids': ['chunk0', 'chunk1', 'chunk2'],
            'documents': [
                'First chunk',
                'Second chunk',
                'Third chunk'
            ],
            'metadatas': [
                {'chunkIndex': 0},
                {'chunkIndex': 1},
                {'chunkIndex': 2}
            ]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 0,  # First chunk
            'content': 'First chunk'
        }

        enhanced = get_enhanced_content(mock_collection, result)

        assert '[MATCH START]' in enhanced['content']
        assert 'First chunk' in enhanced['content']
        assert 'Second chunk' in enhanced['content']

    def test_enhanced_last_chunk(self):
        """Test enhanced mode when matched chunk is last (no successors)."""
        mock_collection = Mock()

        # Note has chunks 0-4, matched is 4, should get 2-4
        mock_collection.get.return_value = {
            'ids': ['chunk2', 'chunk3', 'chunk4'],
            'documents': [
                'Third chunk',
                'Fourth chunk',
                'Fifth chunk'
            ],
            'metadatas': [
                {'chunkIndex': 2},
                {'chunkIndex': 3},
                {'chunkIndex': 4}
            ]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 4,  # Last chunk
            'content': 'Fifth chunk'
        }

        enhanced = get_enhanced_content(mock_collection, result)

        assert '[MATCH END]' in enhanced['content']
        assert 'Fifth chunk' in enhanced['content']
        assert enhanced['totalChunks'] == 3

    def test_enhanced_single_chunk_note(self):
        """Test enhanced mode with single-chunk note."""
        mock_collection = Mock()

        mock_collection.get.return_value = {
            'ids': ['chunk0'],
            'documents': ['Only chunk'],
            'metadatas': [{'chunkIndex': 0}]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 0,
            'content': 'Only chunk'
        }

        enhanced = get_enhanced_content(mock_collection, result)

        assert '[MATCH START]' in enhanced['content']
        assert '[MATCH END]' in enhanced['content']
        assert 'Only chunk' in enhanced['content']
        assert enhanced['totalChunks'] == 1

    def test_enhanced_fallback_on_error(self):
        """Test enhanced mode falls back to chunk_only on error."""
        mock_collection = Mock()

        # Simulate error during get()
        mock_collection.get.side_effect = Exception("Database error")

        result = {
            'noteId': 'note123',
            'chunkIndex': 2,
            'content': 'Original content'
        }

        enhanced = get_enhanced_content(mock_collection, result)

        # Should fallback to chunk_only
        assert enhanced['content'] == 'Original content'
        assert enhanced['totalChunks'] == 1

    def test_enhanced_chunks_sorted_by_index(self):
        """Test enhanced mode sorts chunks by index."""
        mock_collection = Mock()

        # Return chunks in unsorted order
        mock_collection.get.return_value = {
            'ids': ['chunk2', 'chunk0', 'chunk1'],
            'documents': [
                'Third chunk',
                'First chunk',
                'Second chunk'
            ],
            'metadatas': [
                {'chunkIndex': 2},
                {'chunkIndex': 0},
                {'chunkIndex': 1}
            ]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 1,
            'content': 'Second chunk'
        }

        enhanced = get_enhanced_content(mock_collection, result)

        # Verify chunks are in correct order
        content_parts = enhanced['content'].split('\n\n')
        assert 'First chunk' in content_parts[0]
        assert '[MATCH START]' in content_parts[1]


class TestGetFullNoteContent:
    """Test full_note context mode."""

    def test_full_note_basic(self):
        """Test full_note retrieves all chunks with match marker."""
        mock_collection = Mock()

        mock_collection.get.return_value = {
            'ids': ['chunk0', 'chunk1', 'chunk2', 'chunk3'],
            'documents': [
                'Introduction',
                'Main point 1',
                'Main point 2',
                'Conclusion'
            ],
            'metadatas': [
                {'chunkIndex': 0},
                {'chunkIndex': 1},
                {'chunkIndex': 2},
                {'chunkIndex': 3}
            ]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 1,  # Matched chunk
            'content': 'Main point 1'
        }

        full_note = get_full_note_content(mock_collection, result)

        # Verify match marker
        assert '[MATCH AT CHUNK 1]' in full_note['content']

        # Verify all chunks are included
        assert 'Introduction' in full_note['content']
        assert 'Main point 1' in full_note['content']
        assert 'Main point 2' in full_note['content']
        assert 'Conclusion' in full_note['content']

        assert full_note['totalChunks'] == 4

    def test_full_note_single_chunk(self):
        """Test full_note with single-chunk note."""
        mock_collection = Mock()

        mock_collection.get.return_value = {
            'ids': ['chunk0'],
            'documents': ['Complete note'],
            'metadatas': [{'chunkIndex': 0}]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 0,
            'content': 'Complete note'
        }

        full_note = get_full_note_content(mock_collection, result)

        assert '[MATCH AT CHUNK 0]' in full_note['content']
        assert 'Complete note' in full_note['content']
        assert full_note['totalChunks'] == 1

    def test_full_note_chunks_sorted(self):
        """Test full_note sorts chunks by index."""
        mock_collection = Mock()

        # Return chunks in random order
        mock_collection.get.return_value = {
            'ids': ['chunk3', 'chunk1', 'chunk0', 'chunk2'],
            'documents': [
                'Fourth',
                'Second',
                'First',
                'Third'
            ],
            'metadatas': [
                {'chunkIndex': 3},
                {'chunkIndex': 1},
                {'chunkIndex': 0},
                {'chunkIndex': 2}
            ]
        }

        result = {
            'noteId': 'note123',
            'chunkIndex': 2,
            'content': 'Third'
        }

        full_note = get_full_note_content(mock_collection, result)

        # Verify order
        content_parts = full_note['content'].split('\n\n')
        assert 'First' in content_parts[0]
        assert 'Second' in content_parts[1]
        assert '[MATCH AT CHUNK 2]' in content_parts[2]
        assert 'Third' in content_parts[3]
        assert 'Fourth' in content_parts[4]

    def test_full_note_fallback_on_error(self):
        """Test full_note falls back to chunk_only on error."""
        mock_collection = Mock()

        mock_collection.get.side_effect = Exception("Database error")

        result = {
            'noteId': 'note123',
            'chunkIndex': 1,
            'content': 'Original content'
        }

        full_note = get_full_note_content(mock_collection, result)

        # Should fallback to chunk_only
        assert full_note['content'] == 'Original content'
        assert full_note['totalChunks'] == 1


class TestApplyContextMode:
    """Test context mode application to results."""

    def test_apply_chunk_only_mode(self):
        """Test applying chunk_only mode."""
        mock_collection = Mock()

        results = [
            {'noteId': 'note1', 'chunkIndex': 0, 'content': 'Content 1'},
            {'noteId': 'note2', 'chunkIndex': 1, 'content': 'Content 2'}
        ]

        enhanced = apply_context_mode(mock_collection, results, "chunk_only")

        assert len(enhanced) == 2
        assert enhanced[0]['content'] == 'Content 1'
        assert enhanced[1]['content'] == 'Content 2'
        assert enhanced[0]['totalChunks'] == 1

    def test_apply_enhanced_mode(self):
        """Test applying enhanced mode."""
        mock_collection = Mock()

        # Mock get() for enhanced retrieval
        mock_collection.get.return_value = {
            'ids': ['chunk0'],
            'documents': ['Enhanced content'],
            'metadatas': [{'chunkIndex': 0}]
        }

        results = [{'noteId': 'note1', 'chunkIndex': 0, 'content': 'Content'}]

        enhanced = apply_context_mode(mock_collection, results, "enhanced")

        assert len(enhanced) == 1
        # Should have called get_enhanced_content which adds markers
        assert '[MATCH START]' in enhanced[0]['content']

    def test_apply_full_note_mode(self):
        """Test applying full_note mode."""
        mock_collection = Mock()

        mock_collection.get.return_value = {
            'ids': ['chunk0', 'chunk1'],
            'documents': ['Part 1', 'Part 2'],
            'metadatas': [{'chunkIndex': 0}, {'chunkIndex': 1}]
        }

        results = [{'noteId': 'note1', 'chunkIndex': 0, 'content': 'Part 1'}]

        enhanced = apply_context_mode(mock_collection, results, "full_note")

        assert len(enhanced) == 1
        assert '[MATCH AT CHUNK 0]' in enhanced[0]['content']
        assert enhanced[0]['totalChunks'] == 2

    def test_apply_unknown_mode_defaults_to_chunk_only(self):
        """Test unknown mode defaults to chunk_only."""
        mock_collection = Mock()

        results = [{'noteId': 'note1', 'chunkIndex': 0, 'content': 'Content'}]

        enhanced = apply_context_mode(mock_collection, results, "unknown_mode")

        assert len(enhanced) == 1
        assert enhanced[0]['content'] == 'Content'
        assert enhanced[0]['totalChunks'] == 1

    def test_apply_empty_results(self):
        """Test applying context mode to empty results."""
        mock_collection = Mock()

        enhanced = apply_context_mode(mock_collection, [], "enhanced")

        assert len(enhanced) == 0
