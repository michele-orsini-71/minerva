# AI Provider Usage Examples

This document shows how to use the refactored AI provider abstraction with separated concerns.

## Architecture Overview

- `ai_config.py` - Configuration management and environment variable resolution
- `ai_provider.py` - AI provider operations (embeddings, LLM calls)

## Key Principle: RAII (Resource Acquisition Is Initialization)

The `AIProvider` class follows RAII pattern:
- Resources (API keys) are acquired during `__init__`
- Provider is fully configured and ready to use after construction
- No separate setup or initialization step needed

## Example 1: Local Ollama (No API Keys)

```python
from ai_config import AIProviderConfig
from ai_provider import AIProvider

# Create configuration (base_url is plain text, not secret)
config = AIProviderConfig(
    provider_type='ollama',
    embedding_model='mxbai-embed-large:latest',
    llm_model='llama3.1:8b',
    base_url='http://localhost:11434'  # Plain URL, stored in config
)

# Create provider (RAII: fully initialized and ready to use)
provider = AIProvider(config)

# Generate embeddings
embedding = provider.generate_embedding("test text")
print(f"Embedding dimension: {len(embedding)}")

# Check availability
status = provider.check_availability()
print(f"Available: {status['available']}")
```

## Example 2: OpenAI with Environment Variable

```python
import os
from ai_config import AIProviderConfig
from ai_provider import AIProvider

# Set API key in environment (or use .env file)
os.environ['OPENAI_API_KEY'] = 'sk-...'

# Create configuration with template
config = AIProviderConfig(
    provider_type='openai',
    embedding_model='text-embedding-3-small',
    llm_model='gpt-4o-mini',
    api_key='${OPENAI_API_KEY}'  # Template, not actual key
)

# Create provider (RAII: API key resolved automatically during __init__)
provider = AIProvider(config)

# Generate batch embeddings
texts = ["hello", "world", "test"]
embeddings = provider.generate_embeddings_batch(texts)
print(f"Generated {len(embeddings)} embeddings")
```

## Example 3: Error Handling for Missing API Keys

```python
from ai_config import AIProviderConfig, APIKeyMissingError
from ai_provider import AIProvider

config = AIProviderConfig(
    provider_type='openai',
    embedding_model='text-embedding-3-small',
    llm_model='gpt-4o-mini',
    api_key='${MISSING_KEY}'  # Key not in environment
)

try:
    # Error occurs during AIProvider.__init__ (RAII)
    provider = AIProvider(config)
except APIKeyMissingError as e:
    print(f"API key error: {e}")
    # Output shows actionable guidance:
    # Environment variable 'MISSING_KEY' is not set.
    #   Required for: ${MISSING_KEY}
    #   Suggestion: Set the environment variable before running:
    #     export MISSING_KEY='your-api-key-here'
```

## Example 4: Validate Collection Description

```python
from ai_config import AIProviderConfig
from ai_provider import AIProvider

config = AIProviderConfig(
    provider_type='ollama',
    embedding_model='mxbai-embed-large:latest',
    llm_model='llama3.1:8b'
)

provider = AIProvider(config)

# Validate a collection description
description = "My personal notes about Python programming and data science"
result = provider.validate_description(description)

print(f"Score: {result['score']}/10")
print(f"Valid: {result['valid']}")  # True if score >= 7
print(f"Feedback: {result['feedback']}")
```

## Example 5: Get Embedding Metadata (for ChromaDB storage)

```python
import os
from ai_config import AIProviderConfig
from ai_provider import AIProvider

os.environ['OPENAI_API_KEY'] = 'sk-...'

config = AIProviderConfig(
    provider_type='openai',
    embedding_model='text-embedding-3-small',
    llm_model='gpt-4o-mini',
    api_key='${OPENAI_API_KEY}'
)

provider = AIProvider(config)

# Get metadata for storage
metadata = provider.get_embedding_metadata()

# Metadata includes:
# - embedding_provider: 'openai'
# - embedding_model: 'text-embedding-3-small'
# - llm_model: 'gpt-4o-mini'
# - embedding_dimension: 1536 (actual dimension)
# - embedding_base_url: None
# - embedding_api_key_ref: '${OPENAI_API_KEY}' (template, NOT resolved key!)

# Safe to store in ChromaDB - no secrets exposed!
print(f"Provider: {metadata['embedding_provider']}")
print(f"Model: {metadata['embedding_model']}")
print(f"Dimension: {metadata['embedding_dimension']}")
print(f"API Key Ref: {metadata['embedding_api_key_ref']}")  # Template only
```

## Why This Design?

### 1. Security: API Keys Never Leaked

```python
# BAD: Old design mixed concerns
provider.get_embedding_metadata()
# Could accidentally expose: {'api_key': 'sk-actual-secret-key'}

# GOOD: New design separates resolution from storage
metadata = provider.get_embedding_metadata()
# Always safe: {'embedding_api_key_ref': '${OPENAI_API_KEY}'}
```

### 2. Clarity: base_url is Not Secret

```python
# GOOD: base_url is plain text, stored directly in config
config = AIProviderConfig(
    provider_type='ollama',
    base_url='http://localhost:11434'  # Just a URL
)

# No need for: base_url='${OLLAMA_BASE_URL}'
```

### 3. Testability: Easy to Mock

```python
# Tests can inject resolved values directly
provider = AIProvider(config, resolved_api_key='test-key-123')

# No need to manipulate environment variables
```

### 4. RAII: Fully Initialized Objects

```python
# GOOD: RAII pattern - one step, fully initialized
config = AIProviderConfig(...)
provider = AIProvider(config)  # Ready to use!

# No separate setup needed, no half-initialized state
# Provider is guaranteed to be valid or construction fails
```
