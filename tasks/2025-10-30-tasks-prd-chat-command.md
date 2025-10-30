# Tasks: Minerva Chat Command

Generated from: `tasks/prd-chat-command.md`

## Relevant Files

### New Files to Create

- `minerva/chat/__init__.py` - [CREATED] Chat module initialization
- `minerva/chat/config.py` - [CREATED] Chat configuration schema and loading with dataclass, JSON schema validation, and env var substitution
- `minerva/chat/tools.py` - [CREATED] Tool definitions and execution wrappers for list_knowledge_bases and search_knowledge_base
- `minerva/chat/history.py` - [CREATED] Conversation persistence and management with ConversationHistory class, save/load/list functions, and auto-save support
- `minerva/chat/chat_engine.py` - [CREATED] Core chat engine with conversation state management, tool execution loop, streaming support, signal handling, and context window management with automatic summarization
- `minerva/chat/context_window.py` - [CREATED] Token estimation and context management with model limits, warning system, and summarization support
- `minerva/commands/chat.py` - [CREATED] CLI command implementation for `minerva chat` with run_chat() function, interactive REPL, single-question mode, conversation listing/resuming, and comprehensive error handling
- `tests/test_chat_config.py` - Unit tests for chat configuration
- `tests/test_chat_tools.py` - Unit tests for tool registry
- `tests/test_chat_history.py` - [CREATED] Unit tests for history manager with 25 comprehensive test cases
- `tests/test_chat_engine.py` - Unit tests for chat engine
- `tests/test_chat_context_window.py` - [CREATED] Unit tests for context window management with 32 comprehensive test cases
- `tests/integration/test_chat_workflow.py` - Integration tests for full chat workflow
- `configs/chat-config-ollama.json` - [CREATED] Example chat config for Ollama
- `configs/chat-config-openai.json` - [CREATED] Example chat config for OpenAI
- `docs/CHAT_GUIDE.md` - User guide for chat command

### Existing Files to Modify

- `minerva/common/ai_provider.py` - [MODIFIED] Added chat completion methods with streaming and tool calling support
  - Added `chat_completion()` method for standard and streaming chat completions
  - Added `chat_completion_streaming()` generator method for real-time response streaming
  - Added `_extract_tool_calls()` helper for parsing tool call responses from LLM
  - Added error handling for rate limits, token limits, and connection failures
- `minerva/cli.py` - [MODIFIED] Added chat subcommand to main CLI parser with --config, -q, --system, --list, and --resume flags
- `requirements.txt` - Add dependencies (rich for terminal UI, if not already present)

### Notes

- Unit tests should be placed in the `tests/` directory at the project root
- Integration tests go in `tests/integration/`
- Use `pytest` to run tests: `pytest tests/` or `pytest tests/test_chat_config.py`
- Follow existing Minerva patterns: use `get_logger()`, jsonschema validation, and dataclasses

## Tasks

- [x] 1.0 Extend AI Provider for Chat Completions
  - [x] 1.1 Add `chat_completion()` method to `AIProvider` class that accepts messages list and returns AI response
  - [x] 1.2 Implement streaming support using `stream=True` parameter and yield response chunks
  - [x] 1.3 Add tool calling support by accepting `tools` parameter and handling tool call responses
  - [x] 1.4 Test chat completion with all providers (Ollama, OpenAI, Anthropic, Gemini) to ensure compatibility
  - [x] 1.5 Add error handling for chat-specific errors (rate limits, token limits, tool execution failures)
  - [x] 1.6 Add `chat_completion_streaming()` generator method that yields message chunks for real-time display

- [x] 2.0 Create Chat Configuration and Schema
  - [x] 2.1 Create `minerva/chat/config.py` with `ChatConfig` dataclass containing chromadb_path, ai_provider, and chat_settings
  - [x] 2.2 Define JSON schema `CHAT_CONFIG_SCHEMA` with required fields (chromadb_path, ai_provider) and optional chat_settings
  - [x] 2.3 Implement `load_chat_config(config_path: str) -> ChatConfig` function with schema validation
  - [x] 2.4 Add support for environment variable substitution in API keys (reuse pattern from `config_loader.py`)
  - [x] 2.5 Add default values for optional settings (conversation_dir: ~/.minerva/conversations, default_max_results: 3, enable_streaming: true)
  - [x] 2.6 Create example config files in `configs/` for Ollama and OpenAI providers

- [x] 3.0 Build Tool Registry and Definitions
  - [x] 3.1 Create `minerva/chat/tools.py` module with tool definitions in OpenAI function calling format
  - [x] 3.2 Define `list_knowledge_bases` tool that wraps `minerva.server.collection_discovery.list_collections()`
  - [x] 3.3 Define `search_knowledge_base` tool that wraps `minerva.server.search_tools.search_knowledge_base()`
  - [x] 3.4 Create `get_tool_definitions() -> List[Dict]` function that returns tool schemas for AI
  - [x] 3.5 Create `execute_tool(tool_name: str, arguments: Dict, context: Dict) -> Dict` function to dispatch tool calls
  - [x] 3.6 Format tool results into AI-friendly text summaries (e.g., "Found 3 results from 'my-notes'...")

- [x] 4.0 Implement Conversation History Manager
  - [x] 4.1 Create `minerva/chat/history.py` module with `ConversationHistory` class
  - [x] 4.2 Implement `generate_conversation_id()` function using timestamp format: YYYYMMDD-HHMMSS-{random}
  - [x] 4.3 Implement `save_conversation(conversation: Dict, conversation_dir: Path) -> str` to write JSON file
  - [x] 4.4 Implement `load_conversation(conversation_id: str, conversation_dir: Path) -> Dict` to read JSON file
  - [x] 4.5 Implement `list_conversations(conversation_dir: Path) -> List[Dict]` to show past conversations with metadata
  - [x] 4.6 Create conversation directory if it doesn't exist (handle ~/.minerva/conversations expansion)
  - [x] 4.7 Add auto-save after each message exchange to prevent data loss

- [x] 5.0 Build Chat Engine with REPL Interface
  - [x] 5.1 Create `minerva/chat/chat_engine.py` with `ChatEngine` class that manages conversation state
  - [x] 5.2 Implement `initialize_conversation(system_prompt: str, ai_provider: AIProvider, config: ChatConfig)` method
  - [x] 5.3 Implement `send_message(user_message: str)` method that coordinates AI response and tool execution
  - [x] 5.4 Add tool call detection and execution loop (AI can make multiple tool calls before responding)
  - [x] 5.5 Implement streaming response display with word-by-word output using rich or simple print statements
  - [x] 5.6 Add visual feedback for tool executions (e.g., "🔍 Searching my-personal-notes...")
  - [x] 5.7 Handle Ctrl+C interruption gracefully by saving conversation state before exit
  - [x] 5.8 Track message history and update conversation metadata (token count, message count)

- [x] 6.0 Create Chat CLI Command
  - [x] 6.1 Create `minerva/commands/chat.py` with `run_chat(args)` function
  - [x] 6.2 Add argument parser in `minerva/cli.py` for chat subcommand with flags: --config, -q, --system, --list, --resume
  - [x] 6.3 Implement single-question mode (`-q` flag) that runs one query and exits
  - [x] 6.4 Implement interactive REPL loop with input prompt "You: " and exit on "exit", "quit", or Ctrl+D
  - [x] 6.5 Add special commands: `/clear` (start new conversation), `/help` (show commands), `/exit` (quit)
  - [x] 6.6 Display welcome message showing available collections count, AI provider/model, and available commands
  - [x] 6.7 Implement `--list` flag to show past conversations from history
  - [x] 6.8 Implement `--resume` flag to continue a previous conversation by ID
  - [x] 6.9 Add error handling for missing config, ChromaDB connection failures, and AI provider unavailable

- [x] 7.0 Add Context Window Management
  - [x] 7.1 Create `minerva/chat/context_window.py` with `estimate_tokens(text: str) -> int` function using `len(text) / 4`
  - [x] 7.2 Implement `calculate_conversation_tokens(messages: List[Dict]) -> int` to sum up all message tokens
  - [x] 7.3 Add context window limits map for common models (llama3.1:8b: 32K, gpt-4o-mini: 128K, claude-3-5-sonnet: 200K)
  - [x] 7.4 Implement warning at 85% of context limit with display showing current/max tokens
  - [x] 7.5 Create user prompt for choices: [c]ontinue, [s]ummarize, [n]ew conversation
  - [x] 7.6 Implement summarization flow that sends old messages to LLM with summarization prompt
  - [x] 7.7 Replace middle messages with summary while keeping system prompt and last 3-4 exchanges
  - [x] 7.8 Test context management with long conversations approaching token limits

- [ ] 8.0 Testing and Documentation
  - [ ] 8.1 Write unit tests for `ChatConfig` loading and validation (test invalid configs, missing fields)
  - [ ] 8.2 Write unit tests for tool definitions and execution (mock search results)
  - [ ] 8.3 Write unit tests for conversation history save/load/list operations
  - [ ] 8.4 Write unit tests for token estimation and context window warnings
  - [ ] 8.5 Write integration test for full chat workflow (single question mode with mock AI provider)
  - [ ] 8.6 Create `docs/CHAT_GUIDE.md` with usage examples, configuration options, and troubleshooting
  - [ ] 8.7 Add chat command examples to main README.md
  - [ ] 8.8 Test with real Ollama instance for end-to-end validation

