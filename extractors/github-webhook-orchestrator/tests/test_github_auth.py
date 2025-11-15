import hmac
import hashlib
import pytest
from github_webhook_orchestrator.github_auth import validate_signature


class TestValidateSignature:
    def test_valid_signature(self):
        payload = b'{"test": "data"}'
        secret = "my-secret-key"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_sig}"

        assert validate_signature(payload, signature_header, secret) is True

    def test_invalid_signature(self):
        payload = b'{"test": "data"}'
        secret = "my-secret-key"
        wrong_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

        assert validate_signature(payload, wrong_signature, secret) is False

    def test_missing_signature_header(self):
        payload = b'{"test": "data"}'
        secret = "my-secret-key"

        assert validate_signature(payload, "", secret) is False
        assert validate_signature(payload, None, secret) is False

    def test_empty_secret(self):
        payload = b'{"test": "data"}'
        signature_header = "sha256=abc123"

        assert validate_signature(payload, signature_header, "") is False
        assert validate_signature(payload, signature_header, None) is False

    def test_invalid_signature_format(self):
        payload = b'{"test": "data"}'
        secret = "my-secret-key"

        assert validate_signature(payload, "invalid-format", secret) is False
        assert validate_signature(payload, "sha1=abc123", secret) is False
        assert validate_signature(payload, "abc123", secret) is False

    def test_signature_with_different_payload(self):
        payload1 = b'{"test": "data1"}'
        payload2 = b'{"test": "data2"}'
        secret = "my-secret-key"

        sig1 = hmac.new(secret.encode('utf-8'), payload1, hashlib.sha256).hexdigest()
        signature_header = f"sha256={sig1}"

        assert validate_signature(payload1, signature_header, secret) is True
        assert validate_signature(payload2, signature_header, secret) is False

    def test_signature_with_different_secret(self):
        payload = b'{"test": "data"}'
        secret1 = "secret1"
        secret2 = "secret2"

        sig = hmac.new(secret1.encode('utf-8'), payload, hashlib.sha256).hexdigest()
        signature_header = f"sha256={sig}"

        assert validate_signature(payload, signature_header, secret1) is True
        assert validate_signature(payload, signature_header, secret2) is False

    def test_empty_payload(self):
        payload = b''
        secret = "my-secret-key"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_sig}"

        assert validate_signature(payload, signature_header, secret) is True

    def test_large_payload(self):
        payload = b'x' * 10000
        secret = "my-secret-key"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_sig}"

        assert validate_signature(payload, signature_header, secret) is True

    def test_special_characters_in_secret(self):
        payload = b'{"test": "data"}'
        secret = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_sig}"

        assert validate_signature(payload, signature_header, secret) is True

    def test_unicode_in_payload(self):
        payload = '{"test": "こんにちは"}'.encode('utf-8')
        secret = "my-secret-key"
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_sig}"

        assert validate_signature(payload, signature_header, secret) is True
