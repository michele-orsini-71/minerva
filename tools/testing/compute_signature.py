#!/usr/bin/env python3
"""
Helper script to compute HMAC-SHA256 signature for GitHub webhook payload.

Usage:
    python compute_signature.py <payload_file> <secret>

Example:
    python compute_signature.py test_webhook_payload.json "my-test-secret"
"""

import sys
import hmac
import hashlib


def compute_signature(payload_file: str, secret: str) -> str:
    """
    Compute GitHub webhook signature for a payload file.

    Args:
        payload_file: Path to JSON payload file
        secret: Webhook secret

    Returns:
        Signature in format "sha256=<hex_digest>"
    """
    with open(payload_file, 'rb') as f:
        payload_body = f.read()

    mac = hmac.new(
        secret.encode('utf-8'),
        msg=payload_body,
        digestmod=hashlib.sha256
    )

    return f"sha256={mac.hexdigest()}"


def main():
    if len(sys.argv) != 3:
        print("Usage: python compute_signature.py <payload_file> <secret>", file=sys.stderr)
        sys.exit(1)

    payload_file = sys.argv[1]
    secret = sys.argv[2]

    try:
        signature = compute_signature(payload_file, secret)
        print(signature)
    except FileNotFoundError:
        print(f"Error: Payload file not found: {payload_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
