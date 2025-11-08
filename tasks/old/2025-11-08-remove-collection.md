# Remove collection

- CLI surface: Add a remove subparser to minerva/cli.py (create_parser() around lines 152-225) matching minerva remove CHROMADB_PATH COLLECTION_NAME. No --force flag—interactive confirmations are mandatory. Update main() to dispatch via a new run_remove.
  - Command module: Create minerva/commands/remove.py patterned after commands/peek.py. Workflow:
    1. Validate Chroma path exists and is a directory (reuse the checks from run_peek).
    2. Initialize the client with initialize_chromadb_client.
    3. Retrieve the target collection and hydrate a full info payload via get_collection_info. Reuse the formatting helpers from peek so the user sees every available detail (metadata, counts, samples, warnings) before confirming.
    4. Show a first confirmation prompt (“Type YES to continue deleting COLLECTION_NAME from /path/to/chromadb_data”). Require exact YES.
    5. Show a second prompt asking the user to retype the collection name verbatim. Abort on mismatch, raising GracefulExit("Deletion cancelled", exit_code=0) so the CLI exits cleanly.
    6. On success, call storage helper (see below), log concise success, and remind how to rebuild via minerva index.
    7. Catch StorageError/ChromaDBConnectionError to present actionable guidance; let other exceptions bubble for the CLI to handle.
  - Storage helper: Introduce remove_collection(client, collection_name) inside minerva/indexing/storage.py right next to delete_existing_collection. This function should:
    - Check existence, raising StorageError if the collection doesn’t exist (preventing ambiguous states).
    - Call client.delete_collection and return once complete.
    - Keep delete_existing_collection but have it delegate to remove_collection so indexing code stays consistent.
  - User prompts: Implement prompt helpers in the new command (e.g., _confirm_yes(prompt: str) and _confirm_collection_name(expected: str)). Keep them pure so we can monkeypatch them in tests. Prompts should clearly explain that deletion is irreversible and mention both the collection name and absolute path.
  - Testing:
    - Extend tests/test_cli_parsing.py to cover the new positional arguments, help text, and required inputs.
    - Create tests/test_remove_command.py with pytest + mocks:
          1. Happy path where the collection exists, confirmations succeed, and remove_collection is called once.
          2. Abort scenarios: missing Chroma path, user answers “no”, user types wrong collection name, collection missing, storage errors.
          3. Ensure the rich info output leverages the same formatting functions (can assert log calls or returned strings).
  - Documentation:
    - Update README (CLI usage/examples section) and any relevant docs under docs/ to describe why/when to use minerva remove, emphasizing that it’s an exceptional, destructive tool intended for cleanup or owner-level testing.
    - If there’s a CHANGELOG or release notes (e.g., docs/RELEASE_NOTES_v2.0.md), add an entry mentioning the new command and its guardrails.

  This plan keeps the destructive workflow highly intentional (no automation flag) while giving the operator all existing context before committing to deletion, aligning with the clean architecture approach already used for other commands.
