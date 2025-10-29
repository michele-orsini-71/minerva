import pytest
from unittest.mock import Mock, patch, MagicMock
from minerva.indexing.updater import run_incremental_update, UpdateStats
from minerva.common.models import Chunk, ChunkWithEmbedding


@pytest.fixture
def mock_provider():
    provider = Mock()
    provider.generate_embeddings = Mock(return_value=[[0.1, 0.2, 0.3]])
    return provider


@pytest.fixture
def mock_collection():
    collection = Mock()
    collection.name = 'test_collection'
    collection.metadata = {
        'version': '2.0',
        'description': 'Test collection',
        'embedding_model': 'test-model',
        'embedding_provider': 'test-provider',
        'chunk_size': 1200
    }
    collection.count = Mock(return_value=0)
    collection.get = Mock(return_value={'ids': [], 'metadatas': []})
    collection.modify = Mock()
    return collection


class TestIncrementalUpdateIntegration:
    def test_empty_collection_adds_all_notes(self, mock_collection, mock_provider):
        new_notes = [
            {
                'title': 'Note 1',
                'markdown': 'Content 1',
                'modificationDate': '2025-01-01T00:00:00Z'
            },
            {
                'title': 'Note 2',
                'markdown': 'Content 2',
                'modificationDate': '2025-01-02T00:00:00Z'
            }
        ]

        mock_collection.count.return_value = 0
        mock_collection.add = Mock()

        with patch('minerva.indexing.updater.generate_embeddings') as mock_gen_emb:
            mock_gen_emb.return_value = [
                ChunkWithEmbedding(
                    chunk=Chunk(
                        id='chunk1',
                        content='Content 1',
                        noteId='note1',
                        title='Note 1',
                        modificationDate='2025-01-01T00:00:00Z',
                        creationDate='',
                        size=10,
                        chunkIndex=0,
                        content_hash='hash1'
                    ),
                    embedding=[0.1, 0.2]
                ),
                ChunkWithEmbedding(
                    chunk=Chunk(
                        id='chunk2',
                        content='Content 2',
                        noteId='note2',
                        title='Note 2',
                        modificationDate='2025-01-02T00:00:00Z',
                        creationDate='',
                        size=10,
                        chunkIndex=0,
                        content_hash='hash2'
                    ),
                    embedding=[0.1, 0.2]
                )
            ]

            stats = run_incremental_update(
                mock_collection,
                new_notes,
                mock_provider,
                'Test description'
            )

        assert stats.added == 2
        assert stats.updated == 0
        assert stats.deleted == 0
        assert stats.unchanged == 0

    def test_no_changes_updates_only_timestamp(self, mock_collection, mock_provider):
        from minerva.indexing.chunking import generate_note_id, compute_content_hash

        note = {
            'title': 'Unchanged Note',
            'markdown': 'Same content',
            'modificationDate': '2025-01-01T00:00:00Z'
        }
        note_id = generate_note_id(note['title'], note.get('creationDate'))
        content_hash = compute_content_hash(note['title'], note['markdown'])

        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {
            'ids': ['chunk1'],
            'metadatas': [{
                'noteId': note_id,
                'chunkIndex': 0,
                'content_hash': content_hash
            }]
        }

        stats = run_incremental_update(
            mock_collection,
            [note],
            mock_provider,
            'Test description'
        )

        assert stats.added == 0
        assert stats.updated == 0
        assert stats.deleted == 0
        assert stats.unchanged == 1
        mock_collection.modify.assert_called()

    def test_deleted_notes_removed_from_collection(self, mock_collection, mock_provider):
        mock_collection.count.return_value = 2
        mock_collection.get.return_value = {
            'ids': ['chunk1', 'chunk2'],
            'metadatas': [
                {'noteId': 'note1', 'chunkIndex': 0, 'content_hash': 'hash1'},
                {'noteId': 'note2', 'chunkIndex': 0, 'content_hash': 'hash2'}
            ]
        }
        mock_collection.delete = Mock()

        stats = run_incremental_update(
            mock_collection,
            [],
            mock_provider,
            'Test description'
        )

        assert stats.deleted == 2
        assert stats.added == 0
        assert stats.updated == 0
        mock_collection.delete.assert_called_once()

    def test_updated_notes_replaced_in_collection(self, mock_collection, mock_provider):
        from minerva.indexing.chunking import generate_note_id

        note = {
            'title': 'Modified Note',
            'markdown': 'New content here',
            'modificationDate': '2025-01-02T00:00:00Z'
        }
        note_id = generate_note_id(note['title'], note.get('creationDate'))

        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {
            'ids': ['old_chunk1'],
            'metadatas': [{
                'noteId': note_id,
                'chunkIndex': 0,
                'content_hash': 'old_hash_different'
            }]
        }
        mock_collection.delete = Mock()
        mock_collection.add = Mock()

        with patch('minerva.indexing.updater.generate_embeddings') as mock_gen_emb:
            mock_gen_emb.return_value = [
                ChunkWithEmbedding(
                    chunk=Chunk(
                        id='new_chunk1',
                        content='New content here',
                        noteId=note_id,
                        title='Modified Note',
                        modificationDate='2025-01-02T00:00:00Z',
                        creationDate='',
                        size=16,
                        chunkIndex=0,
                        content_hash='new_hash'
                    ),
                    embedding=[0.1, 0.2]
                )
            ]

            stats = run_incremental_update(
                mock_collection,
                [note],
                mock_provider,
                'Test description'
            )

        assert stats.updated == 1
        assert stats.added == 0
        assert stats.deleted == 0
        mock_collection.delete.assert_called_once()
        mock_collection.add.assert_called()

    def test_mixed_operations_all_handled(self, mock_collection, mock_provider):
        from minerva.indexing.chunking import generate_note_id, compute_content_hash

        existing_note_unchanged = {
            'title': 'Unchanged',
            'markdown': 'Same',
            'modificationDate': '2025-01-01T00:00:00Z'
        }
        existing_note_modified = {
            'title': 'Modified',
            'markdown': 'New content',
            'modificationDate': '2025-01-02T00:00:00Z'
        }
        new_note = {
            'title': 'Brand New',
            'markdown': 'Fresh content',
            'modificationDate': '2025-01-03T00:00:00Z'
        }

        unchanged_id = generate_note_id(existing_note_unchanged['title'], existing_note_unchanged.get('creationDate'))
        unchanged_hash = compute_content_hash(existing_note_unchanged['title'], existing_note_unchanged['markdown'])
        modified_id = generate_note_id(existing_note_modified['title'], existing_note_modified.get('creationDate'))
        deleted_id = 'deleted_note_id'

        mock_collection.count.return_value = 3
        mock_collection.get.return_value = {
            'ids': ['chunk1', 'chunk2', 'chunk3'],
            'metadatas': [
                {'noteId': unchanged_id, 'chunkIndex': 0, 'content_hash': unchanged_hash},
                {'noteId': modified_id, 'chunkIndex': 0, 'content_hash': 'old_hash'},
                {'noteId': deleted_id, 'chunkIndex': 0, 'content_hash': 'deleted_hash'}
            ]
        }
        mock_collection.delete = Mock()
        mock_collection.add = Mock()

        with patch('minerva.indexing.updater.generate_embeddings') as mock_gen_emb:
            mock_gen_emb.return_value = [
                ChunkWithEmbedding(
                    chunk=Chunk(
                        id='new_chunk',
                        content='content',
                        noteId='note_id',
                        title='Title',
                        modificationDate='2025-01-01T00:00:00Z',
                        creationDate='',
                        size=10,
                        chunkIndex=0,
                        content_hash='hash'
                    ),
                    embedding=[0.1, 0.2]
                )
            ]

            stats = run_incremental_update(
                mock_collection,
                [existing_note_unchanged, existing_note_modified, new_note],
                mock_provider,
                'Test description'
            )

        assert stats.unchanged == 1
        assert stats.updated == 1
        assert stats.added == 1
        assert stats.deleted == 1
        assert stats.total_changes() == 3
        assert stats.total_processed() == 4

    def test_description_change_triggers_metadata_update(self, mock_collection, mock_provider):
        mock_collection.metadata['description'] = 'Old description'

        stats = run_incremental_update(
            mock_collection,
            [],
            mock_provider,
            'New description'
        )

        mock_collection.modify.assert_called()
        call_args = mock_collection.modify.call_args
        assert call_args.kwargs['metadata']['description'] == 'New description'

    def test_handles_notes_with_creation_date(self, mock_collection, mock_provider):
        note = {
            'title': 'Note with Creation Date',
            'markdown': 'Content',
            'modificationDate': '2025-01-02T00:00:00Z',
            'creationDate': '2025-01-01T00:00:00Z'
        }

        mock_collection.add = Mock()

        with patch('minerva.indexing.updater.generate_embeddings') as mock_gen_emb:
            mock_gen_emb.return_value = [
                ChunkWithEmbedding(
                    chunk=Chunk(
                        id='chunk1',
                        content='Content',
                        noteId='note1',
                        title='Note with Creation Date',
                        modificationDate='2025-01-02T00:00:00Z',
                        creationDate='2025-01-01T00:00:00Z',
                        size=7,
                        chunkIndex=0,
                        content_hash='hash1'
                    ),
                    embedding=[0.1, 0.2]
                )
            ]

            stats = run_incremental_update(
                mock_collection,
                [note],
                mock_provider,
                'Test description'
            )

        assert stats.added == 1

    def test_handles_notes_with_multiple_chunks(self, mock_collection, mock_provider):
        long_note = {
            'title': 'Long Note',
            'markdown': 'A' * 5000,
            'modificationDate': '2025-01-01T00:00:00Z'
        }

        mock_collection.add = Mock()

        with patch('minerva.indexing.updater.build_chunks_from_note') as mock_build_chunks:
            mock_build_chunks.return_value = [
                Chunk(
                    id='chunk1',
                    content='A' * 1200,
                    noteId='note1',
                    title='Long Note',
                    modificationDate='2025-01-01T00:00:00Z',
                    creationDate='',
                    size=1200,
                    chunkIndex=0,
                    content_hash='hash1'
                ),
                Chunk(
                    id='chunk2',
                    content='A' * 1200,
                    noteId='note1',
                    title='Long Note',
                    modificationDate='2025-01-01T00:00:00Z',
                    creationDate='',
                    size=1200,
                    chunkIndex=1,
                    content_hash=None
                ),
                Chunk(
                    id='chunk3',
                    content='A' * 1200,
                    noteId='note1',
                    title='Long Note',
                    modificationDate='2025-01-01T00:00:00Z',
                    creationDate='',
                    size=1200,
                    chunkIndex=2,
                    content_hash=None
                )
            ]

            with patch('minerva.indexing.updater.generate_embeddings') as mock_gen_emb:
                mock_gen_emb.return_value = [
                    ChunkWithEmbedding(
                        chunk=Chunk(
                            id='chunk1',
                            content='A' * 1200,
                            noteId='note1',
                            title='Long Note',
                            modificationDate='2025-01-01T00:00:00Z',
                            creationDate='',
                            size=1200,
                            chunkIndex=0,
                            content_hash='hash1'
                        ),
                        embedding=[0.1, 0.2]
                    ),
                    ChunkWithEmbedding(
                        chunk=Chunk(
                            id='chunk2',
                            content='A' * 1200,
                            noteId='note1',
                            title='Long Note',
                            modificationDate='2025-01-01T00:00:00Z',
                            creationDate='',
                            size=1200,
                            chunkIndex=1,
                            content_hash=None
                        ),
                        embedding=[0.1, 0.2]
                    ),
                    ChunkWithEmbedding(
                        chunk=Chunk(
                            id='chunk3',
                            content='A' * 1200,
                            noteId='note1',
                            title='Long Note',
                            modificationDate='2025-01-01T00:00:00Z',
                            creationDate='',
                            size=1200,
                            chunkIndex=2,
                            content_hash=None
                        ),
                        embedding=[0.1, 0.2]
                    )
                ]

                stats = run_incremental_update(
                    mock_collection,
                    [long_note],
                    mock_provider,
                    'Test description'
                )

        assert stats.added == 1

    def test_returns_update_stats_with_correct_counts(self, mock_collection, mock_provider):
        stats = run_incremental_update(
            mock_collection,
            [],
            mock_provider,
            'Test description'
        )

        assert isinstance(stats, UpdateStats)
        assert hasattr(stats, 'added')
        assert hasattr(stats, 'updated')
        assert hasattr(stats, 'deleted')
        assert hasattr(stats, 'unchanged')

    def test_updates_collection_timestamp(self, mock_collection, mock_provider):
        stats = run_incremental_update(
            mock_collection,
            [],
            mock_provider,
            'Test description'
        )

        mock_collection.modify.assert_called()
        call_args = mock_collection.modify.call_args
        assert 'last_updated' in call_args.kwargs['metadata']
