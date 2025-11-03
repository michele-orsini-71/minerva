# PRD: Minerva Chat Command

## Introduction/Overview

The `minerva chat` command is a conversational AI client that provides CLI-based access to Minerva's indexed knowledge bases. This feature enables users to have natural language conversations with an AI assistant that can automatically search and retrieve information from their personal notes, documentation, and other indexed content.

**Problem Statement:**
Currently, users must rely on external desktop applications (Claude Desktop, ChatGPT Desktop) to query their Minerva knowledge bases. This creates dependencies on third-party software, limits automation possibilities, and doesn't provide the speed and flexibility of a native CLI tool.

**Solution:**
A standalone chat interface (`minerva chat`) that runs entirely within the terminal, uses Minerva's search functions directly (no network protocol overhead), and supports multiple AI providers (Ollama, OpenAI, Gemini, etc.). Users gain independence, faster access to their knowledge, and the ability to script AI interactions.

## Goals

1. **Independence**: Eliminate dependency on Claude Desktop or ChatGPT desktop applications
2. **Speed**: Provide fast CLI-based access to indexed knowledge bases
3. **Flexibility**: Support multiple AI providers (local and cloud-based)
4. **Automation**: Enable scriptable AI interactions for workflow integration
5. **Accessibility**: Support both technical and non-technical users with clear documentation
6. **Transparency**: Show users when and how their knowledge bases are being searched

## User Stories

1. **As a developer**, I want to quickly query my documentation notes from the terminal so that I don't need to switch to a desktop app while coding.

2. **As a researcher**, I want to have a conversation with an AI that automatically searches my research notes so that I can explore connections across my knowledge base.

3. **As a power user**, I want to save and resume conversations so that I can return to complex research sessions later.

4. **As a scripter**, I want to use `-q` for single questions so that I can integrate AI queries into my shell scripts.

5. **As a privacy-conscious user**, I want to use local AI models (Ollama) so that my data never leaves my machine.

6. **As a user with long conversations**, I want to be warned when approaching context limits so that I can decide whether to summarize, continue, or start fresh.

7. **As a knowledge worker**, I want to see which collections were searched so that I understand where the AI's information came from.

## Functional Requirements

### Core Functionality

1. **The system must provide a conversational REPL interface** where users can type messages and receive AI responses in real-time.

2. **The system must support single-question mode** via the `-q` flag (e.g., `minerva chat -q "What's in my notes about X?"`).

3. **The system must automatically search knowledge bases** when the AI determines relevant information is needed to answer the user's question.

4. **The system must display which collections were searched** during each AI response (e.g., "Searched: my-personal-notes").

5. **The system must support streaming responses** that display word-by-word as the AI generates them.

6. **The system must support multi-turn conversations** where the AI remembers previous messages in the conversation.

### Configuration

7. **The system must read configuration from a JSON file** specified via `--config` flag.

8. **The configuration must specify**:

   - ChromaDB path (where indexed collections are stored)
   - AI provider settings (type, models, API keys, base URLs)
   - Chat settings (default system prompt, conversation directory)

9. **The system must support multiple AI providers**: Ollama (local), OpenAI, Anthropic, Google Gemini, Azure OpenAI.

10. **The system must allow per-conversation system prompt override** via `--system` flag (e.g., `minerva chat --system "You are a coding expert"`).

### Conversation History

11. **The system must automatically save conversations** after each message exchange to disk.

12. **The system must store conversations** in JSON format in a user-configurable directory (default: `~/.minerva/conversations/`).

13. **The system must allow users to list past conversations** via `--list` flag.

14. **The system must allow users to resume conversations** via `--resume [conversation-id]` flag.

15. **The system must provide a `/clear` command** that starts a new conversation file while preserving the old one (no deletion).

### Tool Integration

16. **The system must provide two tools to the AI**:

    - `list_knowledge_bases`: Lists available collections with descriptions
    - `search_knowledge_base`: Searches a specific collection for relevant information

17. **The system must use Minerva's existing search functions** (`search_knowledge_base()`, `list_collections()`) directly without MCP protocol overhead.

18. **Single-question mode must have full tool access** (AI can search knowledge bases even in quick mode).

### Context Window Management

19. **The system must monitor token usage** and warn users when approaching the AI provider's context window limit.

20. **When near the context limit, the system must offer users choices**:

    - Continue (risk exceeding limit)
    - Summarize old messages (auto-compress conversation history)
    - Start fresh (save current conversation and begin new one)

21. **The warning must display** the current token count and the model's maximum context window size.

### Error Handling

22. **The system must display clear error messages** when:

    - AI provider is unavailable
    - Knowledge base search fails
    - Configuration file is invalid or missing
    - ChromaDB connection fails

23. **The system must gracefully handle interruptions** (Ctrl+C) and save conversation state before exiting.

### User Experience

24. **The system must provide visual feedback** for:

    - AI thinking/processing (spinner or progress indicator)
    - Tool calls being executed (e.g., "🔍 Searching my-personal-notes...")
    - Streaming responses (word-by-word display)

25. **The system must display a welcome message** showing:

    - Number of available collections
    - Current AI provider and model
    - Available commands (e.g., `/clear`, `/help`)

26. **The system must support graceful exit** via typing "exit", "quit", or pressing Ctrl+D.

## Non-Goals (Out of Scope)

The following features are **explicitly excluded** from the initial version:

1. **Multimodal support**: No image uploads, image analysis, or file attachments in conversations.

2. **Web UI/GUI interface**: This is a CLI-only tool. No graphical interface, web dashboard, or browser-based UI.

3. **Real-time collaboration**: No shared conversations, multi-user support, or collaborative editing.

4. **Voice input/output**: Text-only interface. No speech recognition or text-to-speech.

5. **Conversation search**: No ability to search across past conversations (may be added in future).

6. **Custom tool creation**: Users cannot define custom tools beyond the built-in search tools.

7. **Conversation branching**: No support for creating multiple branches from a single conversation point.

8. **Export to other formats**: Conversations are saved as JSON only (no PDF, HTML, or Markdown export).

## Design Considerations

### CLI Interface Design

**Interactive Mode:**

```bash
$ minerva chat --config ~/.minerva/chat-config.json

Welcome to Minerva Chat!
📚 5 knowledge bases available
🤖 Using ollama/llama3.1:8b

Commands: /clear /help /exit
Type your message or 'exit' to quit.

You: What does my documentation say about indexing?

🔍 Searching: my-personal-notes (3 results)
AI: According to your documentation in "my-personal-notes", indexing in Minerva involves...
[rest of streaming response]

```

**Single Question Mode:**

```bash
$ minerva chat --config ~/.minerva/chat-config.json -q "How do I index notes?"

🔍 Searching: my-personal-notes (3 results)

Answer: To index notes in Minerva, you need to...
```

**Context Window Warning:**

```bash
⚠️  Context Window Warning
Current: 28,450 tokens
Limit: 32,768 tokens

Options:
  [c] Continue (may exceed limit)
  [s] Summarize old messages
  [n] Start fresh conversation

Your choice:
```

### Configuration Schema

```json
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "ai_provider": {
    "provider_type": "ollama",
    "embedding_model": "mxbai-embed-large:latest",
    "llm_model": "llama3.1:8b",
    "base_url": "http://localhost:11434"
  },
  "chat_settings": {
    "default_system_prompt": "You are a helpful AI assistant with access to the user's personal knowledge bases. When answering questions, search relevant collections and cite your sources.",
    "conversation_dir": "~/.minerva/conversations",
    "default_max_results": 3,
    "context_mode": "enhanced",
    "enable_streaming": true,
    "save_conversations": true
  }
}
```

**Alternative providers:**

**OpenAI:**

```json
{
  "ai_provider": {
    "provider_type": "openai",
    "embedding_model": "text-embedding-3-small",
    "llm_model": "gpt-4o-mini",
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

**Anthropic:**

```json
{
  "ai_provider": {
    "provider_type": "anthropic",
    "llm_model": "claude-3-5-sonnet-20241022",
    "api_key": "${ANTHROPIC_API_KEY}"
  }
}
```

### Conversation History Format

```json
{
  "conversation_id": "20251030-152341-a3b2c1",
  "created_at": "2025-10-30T15:23:41Z",
  "last_updated": "2025-10-30T15:45:12Z",
  "system_prompt": "You are a helpful AI assistant...",
  "ai_provider": {
    "provider_type": "ollama",
    "llm_model": "llama3.1:8b"
  },
  "messages": [
    {
      "role": "user",
      "content": "What does my documentation say about indexing?",
      "timestamp": "2025-10-30T15:23:45Z"
    },
    {
      "role": "assistant",
      "content": "According to your documentation...",
      "timestamp": "2025-10-30T15:23:52Z",
      "tool_calls": [
        {
          "tool": "search_knowledge_base",
          "arguments": {
            "query": "indexing documentation",
            "collection_name": "my-personal-notes",
            "max_results": 3
          },
          "results_count": 3
        }
      ]
    }
  ],
  "metadata": {
    "total_tokens": 1250,
    "message_count": 6
  }
}
```

## Technical Considerations

### Architecture Components

1. **Chat Engine** (`minerva/chat/chat_engine.py`):

   - Manages conversation state and history
   - Coordinates between AI provider and tool execution
   - Handles streaming responses
   - Monitors token usage

2. **Tool Registry** (`minerva/chat/tools.py`):

   - Defines tool schemas for AI (JSON format compatible with function calling)
   - Wraps Minerva's search functions (`search_knowledge_base`, `list_collections`)
   - Converts tool results to AI-friendly format

3. **History Manager** (`minerva/chat/history.py`):

   - Loads/saves conversations to disk
   - Lists past conversations
   - Manages conversation IDs and metadata

4. **Configuration** (`minerva/chat/config.py`):

   - Parses and validates chat configuration JSON
   - Handles environment variable substitution
   - Provides defaults for optional settings

5. **CLI Command** (`minerva/commands/chat.py`):
   - Argument parsing and validation
   - REPL loop implementation
   - Special command handling (`/clear`, `/help`, `/exit`)
   - User interaction (prompts, confirmations)

### Dependencies

**Existing Minerva modules:**

- `minerva.common.ai_provider` - AI provider abstraction (already supports LLMs and embeddings)
- `minerva.server.search_tools` - Search function implementation
- `minerva.server.collection_discovery` - Collection listing and provider discovery
- `minerva.indexing.storage` - ChromaDB client initialization
- `minerva.common.logger` - Logging system

**New dependencies** (may need to add to `requirements.txt`):

- `rich` or `prompt_toolkit` - Enhanced terminal UI (spinners, colors, formatting)
- `tiktoken` - Accurate token counting for context window management

### Tool Calling Implementation

The AI provider's `chat_completion()` method must support function/tool calling. Most modern LLM providers support this:

- **Ollama**: Supports function calling with llama3.1:8b and newer models
- **OpenAI**: Native function calling support
- **Anthropic**: Tool use via the API
- **Gemini**: Function calling supported

**Tool definition format** (OpenAI-compatible):

```python
tools = [
    {
        "provider_type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search indexed knowledge bases for relevant information...",
            "parameters": {
                "provider_type": "object",
                "properties": {
                    "query": {"provider_type": "string", "description": "Search query"},
                    "collection_name": {"provider_type": "string", "description": "Collection to search"},
                    "max_results": {"provider_type": "integer", "default": 3}
                },
                "required": ["query", "collection_name"]
            }
        }
    }
]
```

### Context Window Management Strategy

1. **Track tokens**: Use `tiktoken` to count tokens in conversation history
2. **Warning threshold**: Warn at 85% of model's context window
3. **Summarization**: When user chooses to summarize:
   - Keep first message (system prompt)
   - Keep last 3-4 exchanges
   - Summarize middle messages into a single "conversation summary" message
4. **Model context windows** (common values to handle):
   - llama3.1:8b (Ollama): 32K tokens
   - gpt-4o-mini (OpenAI): 128K tokens
   - claude-3-5-sonnet (Anthropic): 200K tokens

### Error Handling Strategy

**Provider unavailable:**

```
❌ Error: Cannot connect to Ollama at http://localhost:11434

   Troubleshooting:
   - Is Ollama running? Try: ollama serve
   - Check base_url in config file
   - Verify model is pulled: ollama list
```

**Search fails:**

```
⚠️  Search failed: Collection 'my-notes' not found

Available collections:
  - my-personal-notes
  - b4-repository
  - wikipedia-history

Continuing without search results...
```

**Config invalid:**

```
❌ Configuration Error: /Users/you/.minerva/chat-config.json

   Missing required field: chromadb_path

   Example:
   {
     "chromadb_path": "./chromadb_data",
     "ai_provider": { ... }
   }
```

## Success Metrics

The feature's success will be measured primarily by **user satisfaction**, indicated by:

1. **Adoption rate**: Number of users who set up and use `minerva chat` regularly
2. **Retention**: Users continue using the tool week-over-week
3. **Positive feedback**: Direct user comments, issue reports showing engagement
4. **Feature requests**: Users asking for enhancements (indicates active use)

**Secondary indicators:**

- Query success rate (AI finds relevant information from knowledge bases)
- Tool call frequency (how often search functions are invoked)
- Conversation length (users engaging in multi-turn conversations)
- Response latency (fast enough for interactive use)

## Design Decisions

These questions were resolved during the design phase:

### 1. Token Counting Strategy

**Decision:** Use universal estimation approach (character-based approximation).

**Implementation:**

- Estimate tokens as `len(text) / 4` (rough industry standard)
- Works across all AI providers (Ollama, OpenAI, Anthropic, Gemini)
- Acceptable ~10-15% margin of error for context warnings
- Can be upgraded to model-specific tokenizers in future phases

**Rationale:** Simple, provider-agnostic, and sufficient for warning users before hitting context limits. Using `tiktoken` directly would only work for OpenAI models, while other providers (Ollama's llama3.1, Anthropic's Claude, Google's Gemini) use different tokenization schemes.

### 2. Conversation Summarization

**Decision:** Use the same LLM that's handling the conversation.

**Implementation:**

- When user chooses "summarize" option, send old messages to the LLM with a summarization prompt
- Replace middle messages with a single "Conversation summary: ..." message
- Keep system prompt, last 3-4 exchanges, and add summary in between

**Rationale:** Maintains consistency with the conversation style, leverages the AI's understanding of context, and avoids implementing separate compression logic.

### 3. Collection Selection

**Decision:** Ask the user for confirmation when multiple collections might be relevant.

**Implementation:**

- AI can call `list_knowledge_bases` to see available collections
- When searching, AI must specify a single collection name
- If user's question is ambiguous, AI asks: "Should I search in 'my-personal-notes' or 'wikipedia-history'?"

**Rationale:** Prevents unexpected searches, gives users control over which knowledge bases are queried, and makes the search process transparent.

### 4. Offline Mode

**Decision:** No offline browsing mode. Issue clear error and recommend local models.

**Implementation:**

- If AI provider is unavailable, display error message
- Suggest troubleshooting steps (check if Ollama is running, verify config)
- Recommend using Ollama for fully offline operation

**Rationale:** Keeps the feature focused on conversational AI. Users wanting to browse collections without AI can use `minerva peek` command directly.

### 5. Conversation Encryption

**Decision:** Not necessary for initial version.

**Implementation:**

- Conversations stored as plain JSON files
- Users responsible for disk-level encryption (FileVault, LUKS, BitLocker)

**Rationale:** Adds complexity without clear benefit. Users already trust filesystem security for ChromaDB and indexed notes. Can be reconsidered if users request it.

### 6. Rate Limiting

**Decision:** Yes, implement rate limiting for cloud providers.

**Implementation:**

- Track API calls per minute/hour for cloud providers (OpenAI, Anthropic, Gemini)
- Warn user when approaching rate limits
- Add configurable `max_requests_per_minute` in chat settings (optional)

**Rationale:** Prevents accidental API cost spikes during long conversations or rapid-fire questions. No rate limiting needed for local Ollama.

### 7. Progress Feedback

**Decision:** Spinner only, no progress bars.

**Implementation:**

- Show spinner during AI thinking: "⏳ Thinking..."
- Show search indicator: "🔍 Searching my-personal-notes..."
- Stream responses word-by-word as they arrive

**Rationale:** Progress bars require knowing total work upfront (not available for AI generation or semantic search). Spinners provide sufficient feedback that work is happening.

### 8. Default System Prompt

**Decision:** Emphasize accuracy and source citation.

**Implementation:**

```
You are a helpful AI assistant with access to the user's personal knowledge bases.
When answering questions, search relevant collections to find accurate information.
Always cite which knowledge base your information comes from.
Prioritize accuracy over speed. If you're unsure, say so.
```

**Rationale:** Users rely on Minerva for accurate recall of their own notes. Citation is critical for trust and verification.

### 9. Session Management

**Decision:** Conversations persist indefinitely (no auto-expiration).

**Implementation:**

- Save all conversations to `~/.minerva/conversations/` by default
- Users manually delete old conversations if desired
- No automatic cleanup or expiration logic

**Rationale:** Users may return to old conversations weeks/months later for reference. Disk space is cheap; lost conversations are not recoverable.

### 10. Integration with MCP Server

**Decision:** No. Use direct function calls only.

**Implementation:**

- `minerva chat` calls search functions directly via Python imports
- Reuses `minerva.server.search_tools` module for search logic
- No HTTP requests, MCP protocol, or server communication

**Rationale:** MCP adds network serialization overhead, error surface area, and requires running a separate server process. Direct function calls are faster and simpler for a local CLI tool.

---

## Implementation Phases

### Phase 1: Core MVP

- Basic REPL interface
- Single AI provider (Ollama)
- Direct function call integration
- Simple streaming responses
- Minimal error handling

### Phase 2: History & Configuration

- Conversation history save/load
- Configuration file support
- Multiple AI provider support
- `/clear` command

### Phase 3: Advanced Features

- Context window monitoring
- Conversation summarization
- `--list` and `--resume` flags
- Enhanced error messages
- Visual feedback (spinners, colors)

### Phase 4: Polish & Documentation

- Comprehensive testing
- User documentation
- Example configurations
- Video tutorial/demo

---

**Document Status:** APPROVED (Design Phase Complete)
**Last Updated:** 2025-10-30
**Author:** Product Team
**Design Decisions:** Finalized 2025-10-30
