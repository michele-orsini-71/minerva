from contextlib import ExitStack
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minerva.common.exceptions import GracefulExit
from minerva.indexing.storage import ChromaDBConnectionError, StorageError
from minerva.commands import remove as remove_cmd


class TestRunRemove:
    def setup_method(self):
        self.args = Namespace(chromadb=Path('./chromadb_data'), collection_name='test_collection')

    def _patch_common(self, collections=None):
        stack = ExitStack()
        mock_validate = stack.enter_context(
            patch.object(remove_cmd, '_validate_chromadb_path', return_value=Path('/abs/path'))
        )

        mock_client = MagicMock()
        mock_client.list_collections.return_value = collections or []
        mock_init = stack.enter_context(
            patch.object(remove_cmd, 'initialize_chromadb_client', return_value=mock_client)
        )

        mock_remove = stack.enter_context(patch.object(remove_cmd, 'remove_collection'))
        stack.enter_context(patch.object(remove_cmd, '_require_yes_confirmation'))
        stack.enter_context(patch.object(remove_cmd, '_require_collection_name_confirmation'))
        stack.enter_context(
            patch.object(remove_cmd, 'get_collection_info', return_value={'name': 'test', 'count': 0, 'metadata': {}})
        )
        stack.enter_context(patch.object(remove_cmd, 'format_collection_info_text', return_value='info text'))

        return stack, mock_client, mock_remove, mock_validate, mock_init

    def test_run_remove_successful_flow(self):
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        stack, mock_client, mock_remove, _, _ = self._patch_common(collections=[mock_collection])

        with stack:
            result = remove_cmd.run_remove(self.args)

        assert result == 0
        mock_remove.assert_called_once_with(mock_client, 'test_collection')

    def test_run_remove_handles_missing_collection(self):
        mock_collection = MagicMock()
        mock_collection.name = 'other_collection'
        stack, _, mock_remove, _, _ = self._patch_common(collections=[mock_collection])

        with stack:
            result = remove_cmd.run_remove(self.args)

        assert result == 1
        mock_remove.assert_not_called()

    def test_run_remove_handles_empty_database(self):
        stack, _, mock_remove, _, _ = self._patch_common(collections=[])

        with stack:
            result = remove_cmd.run_remove(self.args)

        assert result == 1
        mock_remove.assert_not_called()

    def test_run_remove_propagates_graceful_exit_on_confirmation(self):
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        stack, _, _, _, _ = self._patch_common(collections=[mock_collection])
        stack.enter_context(
            patch.object(remove_cmd, '_require_yes_confirmation', side_effect=GracefulExit('cancelled', exit_code=0))
        )

        with stack, pytest.raises(GracefulExit):
            remove_cmd.run_remove(self.args)

    def test_run_remove_handles_storage_error(self):
        mock_collection = MagicMock()
        mock_collection.name = 'test_collection'
        stack, _, mock_remove, _, _ = self._patch_common(collections=[mock_collection])
        mock_remove.side_effect = StorageError('boom')

        with stack:
            result = remove_cmd.run_remove(self.args)

        assert result == 1

    def test_run_remove_handles_connection_errors(self):
        stack = ExitStack()
        stack.enter_context(
            patch.object(remove_cmd, '_validate_chromadb_path', return_value=Path('/abs/path'))
        )
        stack.enter_context(
            patch.object(remove_cmd, 'initialize_chromadb_client', side_effect=ChromaDBConnectionError('down'))
        )

        with stack:
            result = remove_cmd.run_remove(self.args)

        assert result == 1


class TestConfirmationHelpers:
    def test_require_yes_confirmation_accepts_yes(self):
        with patch.object(remove_cmd, '_read_input', return_value='YES'):
            remove_cmd._require_yes_confirmation('collection', Path('/abs/path'))

    def test_require_yes_confirmation_rejects_other_values(self):
        with patch.object(remove_cmd, '_read_input', return_value='nope'):
            with pytest.raises(GracefulExit):
                remove_cmd._require_yes_confirmation('collection', Path('/abs/path'))

    def test_require_collection_name_confirmation_accepts_exact_match(self):
        with patch.object(remove_cmd, '_read_input', return_value='collection'):
            remove_cmd._require_collection_name_confirmation('collection')

    def test_require_collection_name_confirmation_rejects_mismatch(self):
        with patch.object(remove_cmd, '_read_input', return_value='other'):
            with pytest.raises(GracefulExit):
                remove_cmd._require_collection_name_confirmation('collection')
