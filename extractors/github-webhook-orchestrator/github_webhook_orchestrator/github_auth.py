import hmac
import hashlib


def validate_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header:
        return False

    if not secret:
        return False

    if not signature_header.startswith('sha256='):
        return False

    provided_signature = signature_header[7:]

    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, provided_signature)
