# Code Improvements Implementation Plan

## Problem 1: Remove ChromaDB Direct Access from Chat

Files: minerva/commands/chat.py, minerva/chat/config.py

1. Add MCP endpoint to list available tools/collections
2. Update initialize_chat_system() to query MCP server instead of ChromaDB
3. Remove chromadb_path from chat config schema
4. Update chat config loading to not require chromadb_path
5. Update sample chat configs in configs/chat/*.json

## Problem 2: Fix LMStudioClient Parameters

File: minerva/common/ai_provider.py:75-80

1. Change base_url: Optional[str] → base_url: str (required)
2. Remove api_key parameter entirely from __init__
3. Remove self.api_key storage and all references
4. Update _headers() method to remove api_key logic
5. Update AIProviderConfig if it references api_key for LMStudio

## Problem 3: Empty Messages Check

File: minerva/common/ai_provider.py:610-619

✅ No changes needed - Keep defensive validation as-is

## Problem 4: Fix Redundant Role Assignment

File: minerva/common/ai_provider.py:649-669

1. Extract role from message object using same pattern as content
2. Replace result = {'role': 'assistant'} with extracted role
3. Add fallback to 'assistant' if role extraction fails

## Problem 5: Move litellm to Module-Level Import

File: minerva/common/ai_provider.py:190-204

1. Add import litellm at top of file with other imports
2. Remove dynamic import try/except block in __init__
3. Simplify initialization: self.litellm = litellm

## Problem 6: Upgrade Dependencies

File: setup.py:39-40

1. Update litellm>=1.0.0 → litellm>=1.79.0 (fixes asyncio warning)
2. Update httpx>=0.26.0 → httpx>=0.28.0 (better Python 3.13 support)
3. Run tests to verify compatibility
4. Test dry-run to confirm deprecation warnings are resolved

## Testing Plan

1. Run full test suite: pytest -v
2. Test index dry-run: minerva index --config <config> --dry-run
3. Test chat initialization without ChromaDB access
4. Verify no deprecation warnings appear
5. Test LM Studio connection without api_key parameter
