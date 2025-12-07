import os
import json
import keyring
from typing import Optional

from minerva.common.logger import get_logger

logger = get_logger(__name__)
KEYRING_SERVICE = "minerva"
INDEX_KEY = "_index"


def get_index() -> list[str]:
    try:
        index_json = keyring.get_password(KEYRING_SERVICE, INDEX_KEY)
        if index_json:
            return json.loads(index_json)
    except Exception:
        pass
    return []


def save_index(index: list[str]) -> None:
    keyring.set_password(KEYRING_SERVICE, INDEX_KEY, json.dumps(index))


def get_credential(credential_name: str) -> Optional[str]:
    value = os.environ.get(credential_name)
    if value:
        return value

    try:
        value = keyring.get_password(KEYRING_SERVICE, credential_name)
        if value:
            return value
    except Exception:
        pass

    return None


def set_credential(provider_name: str, api_key: str) -> None:
    if provider_name == INDEX_KEY:
        raise ValueError(f"'{INDEX_KEY}' is a reserved key name and cannot be used")

    keyring.set_password(KEYRING_SERVICE, provider_name, api_key)

    index = get_index()
    if provider_name not in index:
        index.append(provider_name)
        save_index(index)

    logger.info(f"✓ Stored '{provider_name}' in OS keychain")


def delete_credential(provider_name: str) -> None:
    if provider_name == INDEX_KEY:
        raise ValueError(f"'{INDEX_KEY}' is a reserved key name and cannot be deleted")

    keyring.delete_password(KEYRING_SERVICE, provider_name)

    index = get_index()
    if provider_name in index:
        index.remove(provider_name)
        save_index(index)


def list_credentials() -> list[str]:
    return get_index()
