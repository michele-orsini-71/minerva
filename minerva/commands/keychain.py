import getpass
import sys
import keyring

from minerva.common.logger import get_logger
from minerva.common.credential_helper import (
    set_credential,
    delete_credential,
    get_credential,
    list_credentials
)

logger = get_logger(__name__, simple=True, mode="cli")


def run_keychain(args):
    action = args.keychain_action

    if action == 'set':
        return handle_set(args)
    elif action == 'get':
        return handle_get(args)
    elif action == 'delete':
        return handle_delete(args)
    elif action == 'list':
        return handle_list(args)
    else:
        logger.error(f"Unknown keychain action: {action}")
        return 1


def handle_set(args):
    provider = args.provider

    if args.key:
        api_key = args.key
    else:
        api_key = getpass.getpass(f"Enter API key for {provider}: ")

    if not api_key:
        logger.error("API key cannot be empty")
        return 1

    try:
        set_credential(provider, api_key)
        print(f"✓ API key for '{provider}' stored in OS keychain")
        return 0
    except ValueError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Failed to store API key: {e}")
        return 1


def handle_get(args):
    provider = args.provider

    try:
        credential = get_credential(provider)

        if credential is None:
            logger.error(f"No credential found for '{provider}'")
            return 1

        if len(credential) <= 8:
            masked = credential
        else:
            masked = f"{credential[:4]}...{credential[-4:]}"

        print(f"API key for '{provider}': {masked}")
        return 0

    except Exception as e:
        logger.error(f"Failed to retrieve API key: {e}")
        return 1


def handle_delete(args):
    provider = args.provider

    try:
        delete_credential(provider)
        print(f"✓ API key for '{provider}' deleted from OS keychain")
        return 0
    except ValueError as e:
        logger.error(str(e))
        return 1
    except keyring.errors.PasswordDeleteError:
        logger.error(f"No credential found for '{provider}'")
        return 1
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        return 1


def handle_list(args):
    try:
        credentials = list_credentials()

        if not credentials:
            print("No credentials stored in keychain")
            return 0

        print("Stored credentials:")
        for cred in credentials:
            print(f"  • {cred}")

        return 0

    except Exception as e:
        logger.error(f"Failed to list credentials: {e}")
        return 1
