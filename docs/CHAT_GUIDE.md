# Minerva Chat Command Guide

The `minerva chat` command provides an interactive AI-powered chat interface that can search and query your indexed knowledge bases. This guide covers installation, configuration, usage, and troubleshooting.

> **💡 Note:** This guide shows the legacy standalone chat configuration. For new projects, consider using the [Unified Configuration Guide](configuration.md) which integrates chat, indexing, and server configuration in a single file.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Modes](#usage-modes)
- [Available Tools](#available-tools)
- [Context Window Management](#context-window-management)
- [Conversation Management](#conversation-management)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

The chat command enables natural language conversations with an AI assistant that has access to your personal knowledge bases. The assistant can:

- List all available knowledge bases
- Search specific collections using semantic search
- Provide answers based on your indexed notes
- Maintain conversation history across sessions
- Automatically manage context window limits

## Quick Start

### 1. Create a Configuration File

Create `chat-config.json` with your AI provider settings:

```json
{
  "chromadb_path": "/absolute/path/to/chromadb_data",
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest"
    },
    "llm": {
      "model": "llama3.1:8b"
    }
  },
  "conversation_dir": "~/.minerva/conversations",
  "default_max_results": 3,
  "enable_streaming": true
}
```

### 2. Start a Chat Session

```bash
minerva chat --config chat-config.json
```

### 3. Ask Questions

```
You: What knowledge bases do I have?
AI: [Lists your collections]

You: Search my personal notes for information about Python
AI: [Searches and provides relevant information]
```

## Configuration

> **Recommended:** Use the [Unified Configuration](configuration.md) approach for new projects. The examples below show the legacy standalone chat configuration for backward compatibility.

### Required Fields

- **chromadb_path**: Absolute path to your ChromaDB storage directory
- **ai_provider**: AI provider configuration (type, models, credentials)

### Optional Fields

- **conversation_dir** (default: `~/.minerva/conversations`): Directory for storing conversation history
- **default_max_results** (default: 3, max: 15): Number of search results to return
- **enable_streaming** (default: true): Enable real-time streaming responses

### AI Provider Configuration

#### Ollama (Local)

```json
{
  "ai_provider": {
    "type": "ollama",
    "embedding": {
      "model": "mxbai-embed-large:latest",
      "base_url": "http://localhost:11434"
    },
    "llm": {
      "model": "llama3.1:8b",
      "base_url": "http://localhost:11434"
    }
  }
}
```

**Requirements**: Ollama must be running locally (`ollama serve`)

#### OpenAI

```json
{
  "ai_provider": {
    "type": "openai",
    "embedding": {
      "model": "text-embedding-3-small",
      "api_key": "${OPENAI_API_KEY}"
    },
    "llm": {
      "model": "gpt-4o-mini",
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

**Requirements**: Set `OPENAI_API_KEY` environment variable

#### Anthropic (Claude)

```json
{
  "ai_provider": {
    "type": "anthropic",
    "embedding": {
      "model": "voyage-2",
      "api_key": "${ANTHROPIC_API_KEY}"
    },
    "llm": {
      "model": "claude-3-5-sonnet-20241022",
      "api_key": "${ANTHROPIC_API_KEY}"
    }
  }
}
```

#### Google Gemini

```json
{
  "ai_provider": {
    "type": "gemini",
    "embedding": {
      "model": "embedding-001",
      "api_key": "${GEMINI_API_KEY}"
    },
    "llm": {
      "model": "gemini-1.5-pro",
      "api_key": "${GEMINI_API_KEY}"
    }
  }
}
```

## Usage Modes

### Interactive Mode (REPL)

Start an interactive chat session:

```bash
minerva chat --config chat-config.json
```

**Special Commands**:
- `/clear` - Start a new conversation (saves current one)
- `/help` - Show available commands
- `/exit` or `exit` or `quit` - Exit the chat
- `Ctrl+D` - Exit the chat
- `Ctrl+C` - Save and exit gracefully

### Single-Question Mode

Ask a single question and exit:

```bash
minerva chat --config chat-config.json -q "What are my Python notes about?"
```

Perfect for scripting or quick queries.

### Custom System Prompt

Override the default system prompt:

```bash
minerva chat --config chat-config.json --system "You are a Python expert assistant"
```

### List Conversations

View all past conversations:

```bash
minerva chat --config chat-config.json --list
```

Output:
```
Past conversations:

1. 20251030-143022-abc123
   Title: What are my Python notes about?
   Messages: 4
   Last modified: 2025-10-30 14:32:15

2. 20251030-120000-def456
   Title: List my knowledge bases
   Messages: 2
   Last modified: 2025-10-30 12:05:30
```

### Resume a Conversation

Continue a previous conversation:

```bash
minerva chat --config chat-config.json --resume 20251030-143022-abc123
```

## Available Tools

The AI assistant has access to the following tools:

### list_knowledge_bases

Lists all available knowledge bases in the system.

**Example**:
```
You: What knowledge bases do I have?
AI: 🔍 Listing available knowledge bases...

Found 2 knowledge base(s):

✓ personal-notes
  Description: My personal notes from Bear
  Chunks: 1,234

✓ python-books
  Description: Python programming books
  Chunks: 5,678
```

### search_knowledge_base

Searches a specific knowledge base using semantic search.

**Parameters**:
- `query`: The search query in natural language
- `collection_name`: Name of the knowledge base to search
- `max_results`: Number of results (1-15, default: 3)
- `context_mode`: Context retrieval mode
  - `chunk_only`: Just the matching chunk
  - `enhanced`: Matching chunk + surrounding context (default)
  - `full_note`: Entire note

**Example**:
```
You: Search my personal notes for information about Docker containers
AI: 🔍 Searching 'personal-notes' for: 'Docker containers' (max 3 results)...

Found 3 result(s) from 'personal-notes' for query: 'Docker containers'

1. Docker Best Practices (similarity: 95.23%)
   Modified: 2025-10-15
   Preview: Docker containers provide lightweight virtualization...
```

## Context Window Management

Minerva automatically monitors token usage and manages the context window to prevent exceeding model limits.

### Model Limits

| Model | Context Limit |
|-------|---------------|
| llama3.1:8b | 32,000 tokens |
| llama2:7b | 4,096 tokens |
| gpt-4o, gpt-4o-mini | 128,000 tokens |
| claude-3-5-sonnet | 200,000 tokens |
| gemini-1.5-pro | 1,000,000 tokens |

### Warning Threshold

When conversation reaches 85% of the model's context limit, you'll see:

```
⚠️  Context Window Warning ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current usage: 27,200 / 32,000 tokens (85.00%)

Your conversation is approaching the maximum context window.
Choose an option:

  [c] Continue - Keep going (may fail if limit exceeded)
  [s] Summarize - Compress old messages into summary
  [n] New conversation - Start fresh (saves current)

Your choice (c/s/n):
```

### Summarization

Choosing to summarize:
1. Sends old messages to the AI for summarization
2. Replaces middle messages with a concise summary
3. Keeps system prompt and last 6 messages intact
4. Frees up context window space

Example:
```
🔄 Generating conversation summary...
✓ Conversation compressed: 45 -> 12 messages
```

## Conversation Management

### Automatic Saving

Conversations are automatically saved after each message exchange to:
```
~/.minerva/conversations/
  └── 20251030-143022-abc123.json
```

### Conversation File Format

```json
{
  "conversation_id": "20251030-143022-abc123",
  "created_at": "2025-10-30T14:30:22Z",
  "last_modified": "2025-10-30T14:32:15Z",
  "message_count": 4,
  "total_tokens": 856,
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful AI assistant..."
    },
    {
      "role": "user",
      "content": "What are my Python notes about?"
    }
  ]
}
```

### Graceful Exit

Pressing `Ctrl+C` saves the conversation before exiting:
```
^C
💾 Conversation saved. Goodbye!
```

## Examples

### Example 1: Exploring Knowledge Bases

```bash
minerva chat --config chat-config.json
```

```
You: What knowledge bases are available?

🔍 Listing available knowledge bases...

I have access to 3 knowledge bases:
- personal-notes (1,234 chunks)
- python-books (5,678 chunks)
- project-docs (892 chunks)

You: Search python-books for decorators

🔍 Searching 'python-books' for: 'decorators' (max 3 results)...

I found information about Python decorators in "Python Advanced Topics":
[Detailed explanation based on search results]
```

### Example 2: Single Question

```bash
minerva chat --config chat-config.json \
  -q "Summarize what I know about machine learning"
```

```
🔍 Searching 'personal-notes' for: 'machine learning' (max 3 results)...

Based on your notes, you've been learning about:
1. Neural network architectures
2. Gradient descent optimization
3. Supervised vs unsupervised learning
[Summary continues...]
```

### Example 3: Custom Context

```bash
minerva chat --config chat-config.json \
  --system "You are a Python code reviewer. Focus on best practices."
```

```
You: Show me examples of list comprehensions in my Python notes

🔍 Searching 'python-books' for: 'list comprehensions' (max 3 results)...

I found several examples in your notes. Here's a best practice review:
[Code review with suggestions]
```

### Example 4: Resuming Conversations

```bash
# List past conversations
minerva chat --config chat-config.json --list

# Resume a specific conversation
minerva chat --config chat-config.json --resume 20251030-143022-abc123
```

```
Resumed conversation from 2025-10-30 14:30:22

You: Continue where we left off...
```

## Troubleshooting

### Configuration Errors

**Error**: `Configuration file not found`
```bash
# Verify file exists
ls -l chat-config.json

# Use absolute path
minerva chat --config /full/path/to/chat-config.json
```

**Error**: `chromadb_path must be an absolute path`
```json
{
  "chromadb_path": "/Users/you/chromadb_data"  // ✓ Absolute
  // "chromadb_path": "./chromadb_data"        // ✗ Relative
}
```

### AI Provider Errors

**Error**: `Connection refused (Ollama)`
```bash
# Start Ollama service
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

**Error**: `Invalid API key (OpenAI/Anthropic)`
```bash
# Set environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Verify it's set
echo $OPENAI_API_KEY

# Run chat
minerva chat --config chat-config.json
```

### ChromaDB Errors

**Error**: `ChromaDB path does not exist`
```bash
# Verify ChromaDB directory exists
ls -la /path/to/chromadb_data

# Check collections
minerva peek collection_name --chromadb /path/to/chromadb_data
```

**Error**: `Collection not found`
```bash
# List available collections
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='./chromadb_data')
print([c.name for c in client.list_collections()])
"
```

### Performance Issues

**Slow responses**:
- Use local Ollama instead of cloud APIs (faster, no rate limits)
- Reduce `default_max_results` to 1-2 for faster searches
- Use `context_mode: "chunk_only"` for minimal context

**Out of memory**:
- Use smaller models (e.g., llama3.1:8b instead of :70b)
- Enable summarization when warned about context limits
- Start new conversations periodically

### Search Quality Issues

**Poor search results**:
- Verify embeddings model matches indexing model
- Use more specific queries
- Try increasing `max_results` to 5-10
- Check collection has been properly indexed:
  ```bash
  minerva peek collection_name --chromadb ./chromadb_data --format table
  ```

**No results found**:
- Verify collection name is correct (case-sensitive)
- Check collection is not empty
- Try broader query terms

## Advanced Configuration

### Environment Variable Substitution

Configuration files support environment variable substitution:

```json
{
  "chromadb_path": "${HOME}/chromadb_data",
  "ai_provider": {
    "type": "openai",
    "embedding": {
      "model": "text-embedding-3-small",
      "api_key": "${OPENAI_API_KEY}"
    },
    "llm": {
      "model": "${OPENAI_MODEL:-gpt-4o-mini}"
    }
  }
}
```

Variables are resolved at runtime using `os.environ`.

### Multiple Configuration Files

Create different configs for different use cases:

```bash
# Work knowledge bases with GPT-4
minerva chat --config chat-work.json

# Personal notes with local Ollama
minerva chat --config chat-personal.json

# Research with Claude Sonnet
minerva chat --config chat-research.json
```

### Conversation Directory Organization

Organize conversations by topic:

```json
{
  "conversation_dir": "~/.minerva/conversations/work"
}
```

## Best Practices

1. **Use Local Models**: Ollama provides fast, private, and unlimited queries
2. **Start Small**: Begin with `max_results: 3`, increase if needed
3. **Enable Streaming**: Better user experience for long responses
4. **Specific Queries**: More specific questions yield better results
5. **Resume Conversations**: Context from previous messages improves responses
6. **Monitor Context**: Watch for context warnings in long conversations
7. **Regular Summaries**: Summarize before hitting context limits

## Integration Examples

### Shell Scripting

```bash
#!/bin/bash
# quick-search.sh - Quick knowledge base search

QUERY="$1"
minerva chat --config ~/.minerva/chat-config.json -q "$QUERY"
```

### Alfred Workflow

```bash
# Search notes from Alfred
minerva chat --config ~/chat-config.json -q "{query}"
```

### Cron Job Summary

```bash
# Daily summary of notes tagged with #review
0 9 * * * minerva chat --config ~/.minerva/chat.json \
  -q "Summarize notes tagged with #review from the last week"
```

## See Also

- [Note Schema Documentation](NOTE_SCHEMA.md)
- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [Extractor Guide](EXTRACTOR_GUIDE.md)
- [Main README](../README.md)
