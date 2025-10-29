import pytest
from unittest.mock import Mock, MagicMock

from minerva.indexing.updater import (
    UpdateStats,
    ExistingState,
    ConfigChange,
    ChangeDetectionResult,
    is_v1_collection,
    detect_config_changes,
    format_v1_collection_error,
    format_config_change_error,
    fetch_existing_state,
    detect_changes,
    delete_note_chunks,
    update_collection_timestamp,
    update_collection_description,
)


class TestUpdateStats:
    def test_initialization_defaults_to_zero(self):
        stats = UpdateStats()

        assert stats.added == 0
        assert stats.updated == 0
        assert stats.deleted == 0
        assert stats.unchanged == 0

    def test_total_changes_counts_added_updated_deleted(self):
        stats = UpdateStats(added=5, updated=3, deleted=2, unchanged=10)

        assert stats.total_changes() == 10

    def test_total_processed_counts_all_notes(self):
        stats = UpdateStats(added=5, updated=3, deleted=2, unchanged=10)

        assert stats.total_processed() == 20

    def test_zero_stats(self):
        stats = UpdateStats()

        assert stats.total_changes() == 0
        assert stats.total_processed() == 0


class TestIsV1Collection:
    def test_returns_true_when_version_is_none(self):
        collection = Mock()
        collection.metadata = {'description': 'test'}

        result = is_v1_collection(collection)

        assert result is True

    def test_returns_true_when_version_is_empty_string(self):
        collection = Mock()
        collection.metadata = {'version': ''}

        result = is_v1_collection(collection)

        assert result is True

    def test_returns_false_when_version_is_2_0(self):
        collection = Mock()
        collection.metadata = {'version': '2.0'}

        result = is_v1_collection(collection)

        assert result is False

    def test_returns_true_when_metadata_is_none(self):
        collection = Mock()
        collection.metadata = None

        result = is_v1_collection(collection)

        assert result is True

    def test_returns_true_when_metadata_is_empty_dict(self):
        collection = Mock()
        collection.metadata = {}

        result = is_v1_collection(collection)

        assert result is True


class TestDetectConfigChanges:
    def test_no_changes_when_all_match(self):
        collection = Mock()
        collection.metadata = {
            'embedding_model': 'mxbai-embed-large:latest',
            'embedding_provider': 'ollama',
            'chunk_size': 1200
        }

        result = detect_config_changes(
            collection,
            'mxbai-embed-large:latest',
            'ollama',
            1200
        )

        assert result.has_changes is False
        assert len(result.changed_fields) == 0

    def test_detects_embedding_model_change(self):
        collection = Mock()
        collection.metadata = {
            'embedding_model': 'old-model',
            'embedding_provider': 'ollama',
            'chunk_size': 1200
        }

        result = detect_config_changes(
            collection,
            'new-model',
            'ollama',
            1200
        )

        assert result.has_changes is True
        assert 'embedding_model' in result.changed_fields
        assert result.old_values['embedding_model'] == 'old-model'
        assert result.new_values['embedding_model'] == 'new-model'

    def test_detects_embedding_provider_change(self):
        collection = Mock()
        collection.metadata = {
            'embedding_model': 'model',
            'embedding_provider': 'ollama',
            'chunk_size': 1200
        }

        result = detect_config_changes(
            collection,
            'model',
            'openai',
            1200
        )

        assert result.has_changes is True
        assert 'embedding_provider' in result.changed_fields
        assert result.old_values['embedding_provider'] == 'ollama'
        assert result.new_values['embedding_provider'] == 'openai'

    def test_detects_chunk_size_change(self):
        collection = Mock()
        collection.metadata = {
            'embedding_model': 'model',
            'embedding_provider': 'ollama',
            'chunk_size': 1200
        }

        result = detect_config_changes(
            collection,
            'model',
            'ollama',
            2000
        )

        assert result.has_changes is True
        assert 'chunk_size' in result.changed_fields
        assert result.old_values['chunk_size'] == 1200
        assert result.new_values['chunk_size'] == 2000

    def test_detects_multiple_changes(self):
        collection = Mock()
        collection.metadata = {
            'embedding_model': 'old-model',
            'embedding_provider': 'ollama',
            'chunk_size': 1200
        }

        result = detect_config_changes(
            collection,
            'new-model',
            'openai',
            2000
        )

        assert result.has_changes is True
        assert len(result.changed_fields) == 3
        assert 'embedding_model' in result.changed_fields
        assert 'embedding_provider' in result.changed_fields
        assert 'chunk_size' in result.changed_fields

    def test_ignores_missing_stored_values(self):
        collection = Mock()
        collection.metadata = {}

        result = detect_config_changes(
            collection,
            'new-model',
            'openai',
            2000
        )

        assert result.has_changes is False
        assert len(result.changed_fields) == 0


class TestFormatV1CollectionError:
    def test_includes_collection_name(self):
        error_msg = format_v1_collection_error('my_collection', '/path/to/db')

        assert 'my_collection' in error_msg

    def test_includes_chromadb_path(self):
        error_msg = format_v1_collection_error('my_collection', '/path/to/db')

        assert '/path/to/db' in error_msg

    def test_includes_force_recreate_instruction(self):
        error_msg = format_v1_collection_error('my_collection', '/path/to/db')

        assert 'forceRecreate' in error_msg
        assert 'true' in error_msg

    def test_includes_v1_0_mention(self):
        error_msg = format_v1_collection_error('my_collection', '/path/to/db')

        assert 'v1.0' in error_msg


class TestFormatConfigChangeError:
    def test_includes_collection_name(self):
        config_change = ConfigChange(
            has_changes=True,
            changed_fields=['embedding_model'],
            old_values={'embedding_model': 'old'},
            new_values={'embedding_model': 'new'}
        )

        error_msg = format_config_change_error('my_collection', config_change)

        assert 'my_collection' in error_msg

    def test_includes_embedding_model_change_details(self):
        config_change = ConfigChange(
            has_changes=True,
            changed_fields=['embedding_model'],
            old_values={'embedding_model': 'old-model'},
            new_values={'embedding_model': 'new-model'}
        )

        error_msg = format_config_change_error('my_collection', config_change)

        assert 'old-model' in error_msg
        assert 'new-model' in error_msg

    def test_includes_provider_change_details(self):
        config_change = ConfigChange(
            has_changes=True,
            changed_fields=['embedding_provider'],
            old_values={'embedding_provider': 'ollama'},
            new_values={'embedding_provider': 'openai'}
        )

        error_msg = format_config_change_error('my_collection', config_change)

        assert 'ollama' in error_msg
        assert 'openai' in error_msg

    def test_includes_chunk_size_change_details(self):
        config_change = ConfigChange(
            has_changes=True,
            changed_fields=['chunk_size'],
            old_values={'chunk_size': 1200},
            new_values={'chunk_size': 2000}
        )

        error_msg = format_config_change_error('my_collection', config_change)

        assert '1200' in error_msg
        assert '2000' in error_msg

    def test_includes_force_recreate_instruction(self):
        config_change = ConfigChange(
            has_changes=True,
            changed_fields=['embedding_model'],
            old_values={'embedding_model': 'old'},
            new_values={'embedding_model': 'new'}
        )

        error_msg = format_config_change_error('my_collection', config_change)

        assert 'forceRecreate' in error_msg


class TestFetchExistingState:
    def test_returns_empty_state_when_collection_is_empty(self):
        collection = Mock()
        collection.count.return_value = 0

        result = fetch_existing_state(collection)

        assert isinstance(result, ExistingState)
        assert len(result.noteId_to_chunks) == 0
        assert len(result.noteId_to_hash) == 0

    def test_builds_note_to_chunks_mapping(self):
        collection = Mock()
        collection.count.return_value = 3
        collection.get.return_value = {
            'ids': ['chunk1', 'chunk2', 'chunk3'],
            'metadatas': [
                {'noteId': 'note1', 'chunkIndex': 0, 'content_hash': 'hash1'},
                {'noteId': 'note1', 'chunkIndex': 1},
                {'noteId': 'note2', 'chunkIndex': 0, 'content_hash': 'hash2'}
            ]
        }

        result = fetch_existing_state(collection)

        assert 'note1' in result.noteId_to_chunks
        assert 'note2' in result.noteId_to_chunks
        assert len(result.noteId_to_chunks['note1']) == 2
        assert len(result.noteId_to_chunks['note2']) == 1

    def test_extracts_content_hashes_from_first_chunks(self):
        collection = Mock()
        collection.count.return_value = 3
        collection.get.return_value = {
            'ids': ['chunk1', 'chunk2', 'chunk3'],
            'metadatas': [
                {'noteId': 'note1', 'chunkIndex': 0, 'content_hash': 'hash1'},
                {'noteId': 'note1', 'chunkIndex': 1},
                {'noteId': 'note2', 'chunkIndex': 0, 'content_hash': 'hash2'}
            ]
        }

        result = fetch_existing_state(collection)

        assert result.noteId_to_hash['note1'] == 'hash1'
        assert result.noteId_to_hash['note2'] == 'hash2'

    def test_skips_chunks_without_note_id(self):
        collection = Mock()
        collection.count.return_value = 2
        collection.get.return_value = {
            'ids': ['chunk1', 'chunk2'],
            'metadatas': [
                {'noteId': 'note1', 'chunkIndex': 0, 'content_hash': 'hash1'},
                {'chunkIndex': 0}
            ]
        }

        result = fetch_existing_state(collection)

        assert len(result.noteId_to_chunks) == 1
        assert 'note1' in result.noteId_to_chunks

    def test_handles_empty_get_results(self):
        collection = Mock()
        collection.count.return_value = 10
        collection.get.return_value = {'ids': None}

        result = fetch_existing_state(collection)

        assert len(result.noteId_to_chunks) == 0
        assert len(result.noteId_to_hash) == 0


class TestDetectChanges:
    def test_detects_added_notes(self):
        new_notes = [
            {
                'title': 'New Note',
                'markdown': 'Content',
                'modificationDate': '2025-01-01T00:00:00Z'
            }
        ]
        existing_state = ExistingState(
            noteId_to_chunks={},
            noteId_to_hash={}
        )

        result = detect_changes(new_notes, existing_state, 'desc', 'desc')

        assert len(result.added_notes) == 1
        assert result.added_notes[0]['title'] == 'New Note'
        assert len(result.updated_notes) == 0
        assert len(result.deleted_note_ids) == 0

    def test_detects_deleted_notes(self):
        new_notes = []
        existing_state = ExistingState(
            noteId_to_chunks={'note1': []},
            noteId_to_hash={'note1': 'hash1'}
        )

        result = detect_changes(new_notes, existing_state, 'desc', 'desc')

        assert len(result.added_notes) == 0
        assert len(result.updated_notes) == 0
        assert len(result.deleted_note_ids) == 1
        assert 'note1' in result.deleted_note_ids

    def test_detects_unchanged_notes_with_same_hash(self):
        from minerva.indexing.chunking import generate_note_id, compute_content_hash

        note = {
            'title': 'Unchanged Note',
            'markdown': 'Same content',
            'modificationDate': '2025-01-01T00:00:00Z'
        }
        note_id = generate_note_id(note['title'], note.get('creationDate'))
        content_hash = compute_content_hash(note['title'], note['markdown'])

        new_notes = [note]
        existing_state = ExistingState(
            noteId_to_chunks={note_id: []},
            noteId_to_hash={note_id: content_hash}
        )

        result = detect_changes(new_notes, existing_state, 'desc', 'desc')

        assert len(result.added_notes) == 0
        assert len(result.updated_notes) == 0
        assert len(result.unchanged_note_ids) == 1

    def test_detects_updated_notes_with_different_hash(self):
        from minerva.indexing.chunking import generate_note_id

        note = {
            'title': 'Modified Note',
            'markdown': 'New content',
            'modificationDate': '2025-01-01T00:00:00Z'
        }
        note_id = generate_note_id(note['title'], note.get('creationDate'))

        new_notes = [note]
        existing_state = ExistingState(
            noteId_to_chunks={note_id: []},
            noteId_to_hash={note_id: 'old_hash_different'}
        )

        result = detect_changes(new_notes, existing_state, 'desc', 'desc')

        assert len(result.added_notes) == 0
        assert len(result.updated_notes) == 1
        assert result.updated_notes[0]['title'] == 'Modified Note'

    def test_treats_note_without_hash_as_updated(self):
        from minerva.indexing.chunking import generate_note_id

        note = {
            'title': 'Note Missing Hash',
            'markdown': 'Content',
            'modificationDate': '2025-01-01T00:00:00Z'
        }
        note_id = generate_note_id(note['title'], note.get('creationDate'))

        new_notes = [note]
        existing_state = ExistingState(
            noteId_to_chunks={note_id: []},
            noteId_to_hash={}
        )

        result = detect_changes(new_notes, existing_state, 'desc', 'desc')

        assert len(result.updated_notes) == 1 or len(result.added_notes) == 1

    def test_detects_description_change(self):
        result = detect_changes([], ExistingState({}, {}), 'old desc', 'new desc')

        assert result.description_changed is True

    def test_detects_no_description_change(self):
        result = detect_changes([], ExistingState({}, {}), 'same desc', 'same desc')

        assert result.description_changed is False


class TestDeleteNoteChunks:
    def test_returns_zero_when_no_notes_to_delete(self):
        collection = Mock()
        existing_state = ExistingState({}, {})

        result = delete_note_chunks(collection, [], existing_state)

        assert result == 0
        collection.delete.assert_not_called()

    def test_deletes_chunks_for_given_note_ids(self):
        collection = Mock()
        existing_state = ExistingState(
            noteId_to_chunks={
                'note1': [{'id': 'chunk1'}, {'id': 'chunk2'}],
                'note2': [{'id': 'chunk3'}]
            },
            noteId_to_hash={}
        )

        result = delete_note_chunks(collection, ['note1', 'note2'], existing_state)

        assert result == 3
        collection.delete.assert_called_once()
        call_args = collection.delete.call_args
        assert set(call_args.kwargs['ids']) == {'chunk1', 'chunk2', 'chunk3'}

    def test_returns_zero_when_no_chunks_found(self):
        collection = Mock()
        existing_state = ExistingState({}, {})

        result = delete_note_chunks(collection, ['note1'], existing_state)

        assert result == 0


class TestUpdateCollectionTimestamp:
    def test_updates_last_updated_field(self):
        collection = Mock()
        collection.metadata = {'description': 'test'}

        update_collection_timestamp(collection)

        collection.modify.assert_called_once()
        call_args = collection.modify.call_args
        assert 'last_updated' in call_args.kwargs['metadata']
        assert call_args.kwargs['metadata']['last_updated'].endswith('Z') or 'T' in call_args.kwargs['metadata']['last_updated']

    def test_preserves_existing_metadata(self):
        collection = Mock()
        collection.metadata = {'description': 'test', 'version': '2.0'}

        update_collection_timestamp(collection)

        call_args = collection.modify.call_args
        metadata = call_args.kwargs['metadata']
        assert metadata['description'] == 'test'
        assert metadata['version'] == '2.0'

    def test_handles_none_metadata(self):
        collection = Mock()
        collection.metadata = None

        update_collection_timestamp(collection)

        collection.modify.assert_called_once()


class TestUpdateCollectionDescription:
    def test_updates_description_and_timestamp(self):
        collection = Mock()
        collection.metadata = {'description': 'old'}

        update_collection_description(collection, 'new description')

        collection.modify.assert_called_once()
        call_args = collection.modify.call_args
        metadata = call_args.kwargs['metadata']
        assert metadata['description'] == 'new description'
        assert 'last_updated' in metadata
        assert 'T' in metadata['last_updated']

    def test_preserves_other_metadata(self):
        collection = Mock()
        collection.metadata = {'version': '2.0', 'other': 'value'}

        update_collection_description(collection, 'new description')

        call_args = collection.modify.call_args
        metadata = call_args.kwargs['metadata']
        assert metadata['version'] == '2.0'
        assert metadata['other'] == 'value'
