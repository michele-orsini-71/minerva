# Task: Implement OS Keychain Integration for Minerva

## Overview

Implement Phase 1 (Core Keychain Integration) from the pipx-based deployment plan. This adds secure OS keychain storage for API keys with fallback to environment variables.

**Source Plan:** `tasks/2025-11-29-local-mcp-deploy.md`

## Status: IN PROGRESS

## Tasks

### Phase 1: Core Keychain Integration

- [x] **1. Add keyring dependency to setup.py**
  - [x] Add `"keyring>=24.0.0"` to `install_requires` list in setup.py
  - [x] Verify installation works with `pip install -e .`

- [x] **2. Create credential_helper.py module**
  - [x] Create file: `minerva/common/credential_helper.py`
  - [x] Implement `get_credential(credential_name: str) -> Optional[str]`
    - [x] Check environment variable first (priority)
    - [x] Fallback to OS keychain (using keyring library)
    - [x] Return None if not found
    - [x] Add debug logging for credential source
  - [x] Implement `set_credential(provider_name: str, api_key: str) -> None`
    - [x] Store in OS keychain using keyring
    - [x] Log success message
  - [x] Implement `delete_credential(provider_name: str) -> None`
    - [x] Delete from OS keychain
    - [x] Handle PasswordDeleteError gracefully
  - [x] Define `KEYRING_SERVICE = "minerva"` constant

- [x] **3. Integrate credential helper into ai_config.py**
  - [x] Import `get_credential` from credential_helper
  - [x] Modify `resolve_env_variable()` function
    - [x] Replace `os.environ.get(var_name)` with `get_credential(var_name)`
    - [x] Update error message in APIKeyMissingError to suggest both options:
      - [x] Keychain: `minerva keychain set <provider>`
      - [x] Environment: `export VAR_NAME='key'`
      - [x] Shell profile: Add export to ~/.zshrc

- [x] **4. Add keychain subcommand to CLI**
  - [x] Edit `minerva/cli.py`
  - [x] Import keychain command runner
  - [x] Add keychain subparser after existing commands
    - [x] Add `keychain set <provider> [--key KEY]` subcommand
    - [x] Add `keychain get <provider>` subcommand
    - [x] Add `keychain delete <provider>` subcommand
    - [x] Add `keychain list` subcommand

- [x] **5. Create keychain command implementation**
  - [x] Create file: `minerva/commands/keychain.py`
  - [x] Implement `run_keychain(args)` dispatcher function
  - [x] Implement `handle_set(args)`
    - [x] Prompt for API key if not provided via --key flag
    - [x] Use getpass for secure input (no echo)
    - [x] Call `set_credential(provider, key)`
    - [x] Display success message
  - [x] Implement `handle_get(args)`
    - [x] Retrieve credential using `get_credential(provider)`
    - [x] Display masked version (show first/last 4 chars only)
    - [x] Handle not-found case
  - [x] Implement `handle_delete(args)`
    - [x] Call `delete_credential(provider)`
    - [x] Display confirmation
  - [x] Implement `handle_list(args)`
    - [x] Query keyring for all minerva service entries
    - [x] Display list of stored providers
    - [x] Handle empty case

### Phase 2: Update Setup Script

- [x] **6. Fix apps/local-repo-kb/setup.py**
  - [x] Update keychain command calls to work with new CLI
  - [x] Test OpenAI provider flow end-to-end
  - [x] Test Gemini provider flow end-to-end
  - [x] Verify Ollama and LM Studio still work (no API key needed)

### Phase 3: Documentation

- [x] **7. Create SECURITY.md**
  - [x] Create file: `apps/local-repo-kb/SECURITY.md`
  - [x] Document how keychain encryption works per OS
    - [x] macOS: Keychain Access with Touch ID
    - [x] Linux: Secret Service (GNOME Keyring, KWallet)
    - [x] Windows: Credential Manager with Windows Hello
  - [x] Document priority system (env vars override keychain)
  - [x] Document best practices (dedicated keys, rotation, rate limits)
  - [x] Document CI/CD usage (environment variables)
  - [x] Document advanced options (envchain, 1Password CLI)

- [x] **8. Update main README.md**
  - [x] Add pipx installation section with keychain setup
  - [x] Add quick start showing `minerva keychain set OPENAI_API_KEY`
  - [x] Link to apps/local-repo-kb/README.md for full guide

### Phase 4: Testing

- [ ] **9. Manual testing**
  - [x] Test `minerva keychain set OPENAI_API_KEY` with interactive prompt
  - [x] Test `minerva keychain get OPENAI_API_KEY` shows masked key
  - [x] Test `minerva index --config` works with keychain-stored key
  - [x] Test environment variable override works (export OPENAI_API_KEY=test)
  - [x] Test error message when key not found (clear, helpful)
  - [x] Test `minerva keychain delete OPENAI_API_KEY` removes key
  - [x] Test `minerva keychain list` shows stored providers
  - [x] Test apps/local-repo-kb/setup.py works end-to-end with OpenAI
  - [ ] ~~Test apps/local-repo-kb/setup.py works end-to-end with Gemini~~ not necessary

- [ ] **10. Run full test suite**
  - [x] Run `pytest` to ensure no regressions
  - [x] Fix any failing tests
  - [x] Add new tests if needed for credential_helper module

## Relevant Files

### New Files Created

- `minerva/common/credential_helper.py` - Core credential resolution with keychain support (get_credential, set_credential, delete_credential functions)
- `minerva/commands/keychain.py` - CLI command implementation for keychain management (handle_set, handle_get, handle_delete, handle_list functions)
- `apps/local-repo-kb/SECURITY.md` - Comprehensive security documentation covering OS keychain encryption, priority system, best practices, CI/CD usage, and troubleshooting

### Modified Files

- `setup.py` - Added keyring>=24.0.0 dependency to install_requires
- `minerva/common/ai_config.py` - Integrated credential_helper into resolve_env_variable function with improved error messages
- `minerva/common/credential_helper.py` - Implemented index-based listing, removed case transformations, stores exact key names as provided
  - Added `_index` tracking to enable credential listing
  - Removed `.lower()` transformations - stores exact case
  - Added `list_credentials()` function
  - Protected `_index` as reserved key name
- `minerva/commands/keychain.py` - Removed hardcoded common providers, uses index-based listing
  - Removed `.lower()` from all handlers
  - Added ValueError handling for reserved keys
  - Updated list to use `list_credentials()`
- `minerva/cli.py` - Added keychain subcommand with set/get/delete/list actions and comprehensive help text
- `apps/local-repo-kb/setup.py` - Already implemented, ready to work with new keychain commands
- `README.md` - Added "API Key Management" section with keychain usage, security best practices, and link to SECURITY.md

### Existing Files (context)

- `apps/local-repo-kb/README.md` - Already created
- `apps/local-repo-kb/configs/` - Already created
- `tools/local-repo-watcher/` - Already implemented (Python version)

## Notes

- The setup.py script in apps/local-repo-kb is already written and correctly assumes keychain functionality exists
- The Python-based local-repo-watcher is already implemented (replaces TypeScript version)
- Focus only on implementing the missing Phase 1 keychain functionality
- Follow Clean Code principles: no comments/docstrings, self-documenting function names

## Implementation Improvements

During implementation, the following improvements were made beyond the original plan:

1. **Index-based credential listing**: Added `_index` special key to track all stored credentials, enabling true listing functionality without hardcoded common providers
2. **No case transformations**: Removed `.lower()` transformations - keys are stored exactly as provided (e.g., `OPENAI_API_KEY` not `openai_api_key`)
3. **Reserved key protection**: `_index` is protected and cannot be used as a credential name
4. **Simplified credential resolution**: Direct 1:1 mapping between config variable names and keychain keys
5. **Compatible with envchain**: Uses same uppercase convention as envchain for consistency
