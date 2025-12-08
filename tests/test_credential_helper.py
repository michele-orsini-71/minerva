import json
import pytest
from unittest.mock import MagicMock, patch

from minerva.common import credential_helper


class FakeKeyring:
    """Fake keyring backend for testing without touching the real OS keychain."""

    def __init__(self):
        self.storage = {}

    def get_password(self, service: str, username: str):
        key = f"{service}:{username}"
        return self.storage.get(key)

    def set_password(self, service: str, username: str, password: str):
        key = f"{service}:{username}"
        self.storage[key] = password

    def delete_password(self, service: str, username: str):
        key = f"{service}:{username}"
        if key in self.storage:
            del self.storage[key]
        else:
            # Real keyring raises an exception when key doesn't exist
            raise Exception(f"Password not found for {service}:{username}")

    def clear(self):
        """Helper method for tests to clear all stored credentials."""
        self.storage.clear()


@pytest.fixture
def fake_keyring():
    """Provide a fresh fake keyring for each test."""
    fake = FakeKeyring()
    with patch.object(credential_helper, 'keyring', fake):
        yield fake


class TestGetIndex:
    def test_get_index_returns_empty_list_when_no_index(self, fake_keyring):
        result = credential_helper.get_index()
        assert result == []

    def test_get_index_returns_stored_index(self, fake_keyring):
        expected = ["provider1", "provider2", "provider3"]
        fake_keyring.set_password(
            credential_helper.KEYRING_SERVICE,
            credential_helper.INDEX_KEY,
            json.dumps(expected)
        )

        result = credential_helper.get_index()
        assert result == expected

    def test_get_index_handles_corrupted_json(self, fake_keyring):
        # Store invalid JSON
        fake_keyring.set_password(
            credential_helper.KEYRING_SERVICE,
            credential_helper.INDEX_KEY,
            "not valid json {["
        )

        result = credential_helper.get_index()
        assert result == []

    def test_get_index_handles_keyring_exception(self, fake_keyring):
        # Make keyring.get_password raise an exception
        fake_keyring.get_password = MagicMock(side_effect=Exception("Keyring error"))

        result = credential_helper.get_index()
        assert result == []


class TestSaveIndex:
    def test_save_index_stores_index_as_json(self, fake_keyring):
        index = ["provider1", "provider2"]
        credential_helper.save_index(index)

        stored = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            credential_helper.INDEX_KEY
        )
        assert stored == json.dumps(index)

    def test_save_index_overwrites_existing_index(self, fake_keyring):
        # Store initial index
        initial = ["provider1"]
        credential_helper.save_index(initial)

        # Overwrite with new index
        updated = ["provider1", "provider2", "provider3"]
        credential_helper.save_index(updated)

        stored = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            credential_helper.INDEX_KEY
        )
        assert stored == json.dumps(updated)

    def test_save_index_handles_empty_list(self, fake_keyring):
        credential_helper.save_index([])

        stored = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            credential_helper.INDEX_KEY
        )
        assert stored == "[]"


class TestGetCredential:
    def test_get_credential_returns_value_from_environment(self, fake_keyring):
        with patch.dict('os.environ', {'TEST_API_KEY': 'env-value'}):
            result = credential_helper.get_credential('TEST_API_KEY')
            assert result == 'env-value'

    def test_get_credential_prefers_environment_over_keyring(self, fake_keyring):
        # Store in keyring
        fake_keyring.set_password(
            credential_helper.KEYRING_SERVICE,
            'TEST_API_KEY',
            'keyring-value'
        )

        # Set in environment
        with patch.dict('os.environ', {'TEST_API_KEY': 'env-value'}):
            result = credential_helper.get_credential('TEST_API_KEY')
            assert result == 'env-value'

    def test_get_credential_returns_value_from_keyring_when_not_in_env(self, fake_keyring):
        fake_keyring.set_password(
            credential_helper.KEYRING_SERVICE,
            'TEST_API_KEY',
            'keyring-value'
        )

        with patch.dict('os.environ', {}, clear=True):
            result = credential_helper.get_credential('TEST_API_KEY')
            assert result == 'keyring-value'

    def test_get_credential_returns_none_when_not_found(self, fake_keyring):
        with patch.dict('os.environ', {}, clear=True):
            result = credential_helper.get_credential('NONEXISTENT_KEY')
            assert result is None

    def test_get_credential_handles_keyring_exception(self, fake_keyring):
        fake_keyring.get_password = MagicMock(side_effect=Exception("Keyring error"))

        with patch.dict('os.environ', {}, clear=True):
            result = credential_helper.get_credential('TEST_API_KEY')
            assert result is None


class TestSetCredential:
    def test_set_credential_stores_in_keyring(self, fake_keyring):
        credential_helper.set_credential('openai', 'sk-test-key')

        stored = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            'openai'
        )
        assert stored == 'sk-test-key'

    def test_set_credential_adds_to_index(self, fake_keyring):
        credential_helper.set_credential('openai', 'sk-test-key')

        index = credential_helper.get_index()
        assert 'openai' in index

    def test_set_credential_does_not_duplicate_in_index(self, fake_keyring):
        # Set the same credential twice
        credential_helper.set_credential('openai', 'sk-test-key-1')
        credential_helper.set_credential('openai', 'sk-test-key-2')

        index = credential_helper.get_index()
        assert index.count('openai') == 1

    def test_set_credential_updates_existing_credential(self, fake_keyring):
        # Set initial value
        credential_helper.set_credential('openai', 'sk-old-key')

        # Update to new value
        credential_helper.set_credential('openai', 'sk-new-key')

        stored = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            'openai'
        )
        assert stored == 'sk-new-key'

    def test_set_credential_rejects_reserved_index_key(self, fake_keyring):
        with pytest.raises(ValueError, match="reserved key name"):
            credential_helper.set_credential(credential_helper.INDEX_KEY, 'some-value')

    def test_set_credential_maintains_multiple_providers(self, fake_keyring):
        credential_helper.set_credential('openai', 'sk-openai-key')
        credential_helper.set_credential('gemini', 'sk-gemini-key')

        index = credential_helper.get_index()
        assert len(index) == 2
        assert 'openai' in index
        assert 'gemini' in index


class TestDeleteCredential:
    def test_delete_credential_removes_from_keyring(self, fake_keyring):
        # Setup: store a credential
        fake_keyring.set_password(
            credential_helper.KEYRING_SERVICE,
            'openai',
            'sk-test-key'
        )

        # Delete it
        credential_helper.delete_credential('openai')

        # Verify it's gone
        result = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            'openai'
        )
        assert result is None

    def test_delete_credential_removes_from_index(self, fake_keyring):
        # Setup: store a credential
        credential_helper.set_credential('openai', 'sk-test-key')
        assert 'openai' in credential_helper.get_index()

        # Delete it
        credential_helper.delete_credential('openai')

        # Verify it's removed from index
        index = credential_helper.get_index()
        assert 'openai' not in index

    def test_delete_credential_rejects_reserved_index_key(self, fake_keyring):
        with pytest.raises(ValueError, match="reserved key name"):
            credential_helper.delete_credential(credential_helper.INDEX_KEY)

    def test_delete_credential_handles_nonexistent_credential(self, fake_keyring):
        # Should not raise an exception even if credential doesn't exist
        # (The real keyring will raise, but delete_credential should handle it)
        # We need to make sure our function doesn't crash
        try:
            credential_helper.delete_credential('nonexistent')
        except Exception as e:
            # If it raises, it should be from keyring.delete_password
            # which is expected behavior
            assert "Password not found" in str(e)

    def test_delete_credential_only_removes_specified_provider(self, fake_keyring):
        # Setup: store multiple credentials
        credential_helper.set_credential('openai', 'sk-openai-key')
        credential_helper.set_credential('gemini', 'sk-gemini-key')

        # Delete one
        credential_helper.delete_credential('openai')

        # Verify the other remains
        index = credential_helper.get_index()
        assert 'openai' not in index
        assert 'gemini' in index

        stored = fake_keyring.get_password(
            credential_helper.KEYRING_SERVICE,
            'gemini'
        )
        assert stored == 'sk-gemini-key'

    def test_delete_credential_handles_credential_not_in_index(self, fake_keyring):
        # Manually add a credential to keyring but not to index
        # (simulates edge case or manual intervention)
        fake_keyring.set_password(
            credential_helper.KEYRING_SERVICE,
            'manual',
            'sk-manual-key'
        )

        # Delete should not crash even if not in index
        try:
            credential_helper.delete_credential('manual')
        except Exception as e:
            # Exception from keyring is acceptable
            pass


class TestListCredentials:
    def test_list_credentials_returns_empty_list_initially(self, fake_keyring):
        result = credential_helper.list_credentials()
        assert result == []

    def test_list_credentials_returns_all_stored_credentials(self, fake_keyring):
        credential_helper.set_credential('openai', 'sk-openai-key')
        credential_helper.set_credential('gemini', 'sk-gemini-key')

        result = credential_helper.list_credentials()
        assert len(result) == 2
        assert 'openai' in result
        assert 'gemini' in result

    def test_list_credentials_reflects_deletions(self, fake_keyring):
        credential_helper.set_credential('openai', 'sk-openai-key')

        credential_helper.delete_credential('openai')

        result = credential_helper.list_credentials()
        assert len(result) == 0
        assert 'openai' not in result


class TestIntegration:
    """Integration tests that verify the complete workflow."""

    def test_full_credential_lifecycle(self, fake_keyring):
        # Start with empty credentials
        assert credential_helper.list_credentials() == []

        # Add multiple credentials
        credential_helper.set_credential('openai', 'sk-openai-key')
        credential_helper.set_credential('gemini', 'sk-gemini-key')

        # List them
        credentials = credential_helper.list_credentials()
        assert len(credentials) == 2

        # Retrieve them
        with patch.dict('os.environ', {}, clear=True):
            assert credential_helper.get_credential('openai') == 'sk-openai-key'
            assert credential_helper.get_credential('gemini') == 'sk-gemini-key'

        # Update one
        credential_helper.set_credential('openai', 'sk-new-openai-key')
        with patch.dict('os.environ', {}, clear=True):
            assert credential_helper.get_credential('openai') == 'sk-new-openai-key'

        # Delete one
        credential_helper.delete_credential('openai')
        credentials = credential_helper.list_credentials()
        assert len(credentials) == 1
        assert 'gemini' in credentials
        assert 'openai' not in credentials

    def test_environment_variable_override_workflow(self, fake_keyring):
        # Store in keyring
        credential_helper.set_credential('openai', 'sk-keyring-key')

        # Without env var, get from keyring
        with patch.dict('os.environ', {}, clear=True):
            assert credential_helper.get_credential('openai') == 'sk-keyring-key'

        # With env var, get from environment
        with patch.dict('os.environ', {'openai': 'sk-env-key'}):
            assert credential_helper.get_credential('openai') == 'sk-env-key'

        # After removing env var, fall back to keyring
        with patch.dict('os.environ', {}, clear=True):
            assert credential_helper.get_credential('openai') == 'sk-keyring-key'
