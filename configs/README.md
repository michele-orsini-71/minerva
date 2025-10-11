# Configuration Files

This directory contains example configuration files for the AI-powered notes pipeline. These configurations define how your notes are processed, embedded, and stored using different AI providers.

## Available Examples

### `example-ollama.json`
**Local AI Provider (No API Keys Required)**

Uses Ollama for completely offline, local processing. Perfect for:
- Privacy-sensitive notes
- Offline work
- Development and testing
- No API costs

**Requirements:**
- Ollama service running locally (`ollama serve`)
- Models pulled: `mxbai-embed-large:latest` and `llama3.1:8b`

### `example-openai.json`
**OpenAI API Provider**

Uses OpenAI's embeddings and language models for high-quality semantic search.

**Requirements:**
- OpenAI API key set as environment variable: `export OPENAI_API_KEY=sk-...`
- Active OpenAI account with API access

**Models:**
- Embeddings: `text-embedding-3-small` (1536 dimensions)
- LLM: `gpt-4o-mini` (for description validation)

### `example-gemini.json`
**Google Gemini API Provider**

Uses Google's Gemini AI for embeddings and language understanding.

**Requirements:**
- Google AI API key set as environment variable: `export GEMINI_API_KEY=...`
- Active Google Cloud account with Gemini API enabled

**Models:**
- Embeddings: `text-embedding-004` (768 dimensions)
- LLM: `gemini-1.5-flash` (for description validation)

## Configuration Fields

### Required Fields

#### `collection_name` (string)
Unique identifier for the ChromaDB collection.
- Must start with alphanumeric character
- Can contain letters, numbers, underscores, hyphens
- Length: 1-63 characters
- Example: `bear_notes`, `project-docs`, `team_knowledge`

#### `description` (string)
Detailed description of the collection's content and purpose.
- Used by AI to determine when to use this collection
- Should explain what content is stored and when to search it
- Length: 10-1000 characters
- Example: "Personal notes covering software development, meetings, and research"

#### `chromadb_path` (string)
Path to ChromaDB storage directory.
- Relative or absolute path
- Will be created if it doesn't exist
- Example: `./chromadb_data` or `/path/to/chromadb`

#### `json_file` (string)
Path to the JSON file containing parsed notes.
- Relative or absolute path
- Must be output from the Bear notes parser
- Example: `./test-data/sample.json`

#### `ai_provider` (object)
AI provider configuration for embeddings and LLM.

**Sub-fields:**

##### `ai_provider.type` (string)
Provider type. Must be one of:
- `ollama` - Local Ollama service
- `openai` - OpenAI API
- `gemini` - Google Gemini API
- `azure` - Azure OpenAI
- `anthropic` - Anthropic API

##### `ai_provider.embedding` (object)
Embedding model configuration.

**Required:**
- `model` (string): Model name/identifier
  - Ollama: `mxbai-embed-large:latest`
  - OpenAI: `text-embedding-3-small`, `text-embedding-3-large`
  - Gemini: `text-embedding-004`

**Optional:**
- `base_url` (string or null): Custom API endpoint URL
  - Ollama: `http://localhost:11434`
  - Cloud providers: usually `null`
- `api_key` (string or null): API key as environment variable template
  - Format: `${ENV_VAR_NAME}` (e.g., `${OPENAI_API_KEY}`)
  - **Never store actual API keys in config files**
  - Ollama: `null` (no authentication required)

##### `ai_provider.llm` (object)
Language model configuration for description validation.

**Required:**
- `model` (string): Model name/identifier
  - Ollama: `llama3.1:8b`, `gemma3:12b-it-qat`
  - OpenAI: `gpt-4o-mini`, `gpt-4o`
  - Gemini: `gemini-1.5-flash`, `gemini-1.5-pro`

**Optional:**
- `base_url` (string or null): Custom API endpoint URL
- `api_key` (string or null): API key as environment variable template

### Optional Fields

#### `chunk_size` (number)
Target size for text chunks in characters.
- Default: `1200`
- Range: 300-20000
- Affects granularity of search results
- Smaller: more precise but more chunks
- Larger: more context but less precise

#### `forceRecreate` (boolean)
Whether to recreate the collection if it already exists.
- Default: `false`
- `true`: Delete and recreate collection (loses all data)
- `false`: Error if collection already exists

#### `skipAiValidation` (boolean)
Whether to skip AI validation of collection description.
- Default: `false`
- `true`: Skip LLM-based quality check
- `false`: Validate description quality (requires LLM)

## Usage Examples

### Using Ollama (Local)

```bash
# Start Ollama service
ollama serve

# Pull required models
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b

# Run pipeline with Ollama config
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-ollama.json
```

### Using OpenAI

```bash
# Set API key environment variable
export OPENAI_API_KEY=sk-your-key-here

# Run pipeline with OpenAI config
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-openai.json
```

### Using Google Gemini

```bash
# Set API key environment variable
export GEMINI_API_KEY=your-key-here

# Run pipeline with Gemini config
cd markdown-notes-cag-data-creator
python full_pipeline.py --config ../configs/example-gemini.json
```

## Creating Custom Configurations

1. Copy one of the example files
2. Modify `collection_name` to be unique
3. Update `description` to match your content
4. Adjust `chromadb_path` and `json_file` paths
5. Choose appropriate AI provider and models
6. Set environment variables for API keys (if needed)
7. Validate configuration:

```bash
cd markdown-notes-cag-data-creator
python -c "from config_loader import load_collection_config; config = load_collection_config('../configs/your-config.json'); print('✓ Valid configuration')"
```

## Security Best Practices

### API Key Management

**✓ DO:**
- Store API keys in environment variables
- Use `${VAR_NAME}` template syntax in configs
- Add `.env` files to `.gitignore`
- Rotate keys regularly

**✗ DON'T:**
- Store actual API keys in JSON files
- Commit API keys to version control
- Share configs with embedded keys
- Use hardcoded key values

### Example Environment Setup

Create a `.env` file (add to `.gitignore`):

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Google Gemini
export GEMINI_API_KEY=...

# Azure (if using)
export AZURE_API_KEY=...
```

Load environment variables:

```bash
source .env
```

## Troubleshooting

### "Configuration file not found"
- Check the path to the config file
- Use absolute paths or correct relative paths
- Verify file has `.json` extension

### "Invalid JSON syntax"
- Validate JSON at https://jsonlint.com
- Check for missing commas, quotes, or brackets
- Ensure no trailing commas in objects/arrays

### "Missing required field: ai_provider"
- All configs must include `ai_provider` section
- See examples above for correct structure
- Verify `type`, `embedding`, and `llm` are all present

### "API key format invalid"
- API keys must use template format: `${VAR_NAME}`
- Never use raw key values like `sk-abc123...`
- Use `null` for providers that don't need keys (Ollama)

### "Embedding dimension mismatch"
- Different models produce different embedding dimensions
- Can't query collection with different model than used for indexing
- Must recreate collection if changing embedding model

### "Provider unavailable"
- Ollama: Check `ollama serve` is running
- OpenAI/Gemini: Verify API key is set and valid
- Check `base_url` if using custom endpoints
- Test provider availability separately

## Model Selection Guide

### Embedding Models

**Ollama (Local)**
- `mxbai-embed-large:latest`: 1024 dimensions, excellent quality, no API costs
- `nomic-embed-text`: 768 dimensions, faster, good for large datasets

**OpenAI**
- `text-embedding-3-small`: 1536 dimensions, cost-effective, good quality
- `text-embedding-3-large`: 3072 dimensions, highest quality, higher cost

**Google Gemini**
- `text-embedding-004`: 768 dimensions, good quality, competitive pricing

### LLM Models (for Description Validation)

**Ollama (Local)**
- `llama3.1:8b`: Fast, good reasoning, 8B parameters
- `gemma3:12b-it-qat`: Larger model, better quality, slower

**OpenAI**
- `gpt-4o-mini`: Cost-effective, fast, good quality
- `gpt-4o`: Highest quality, more expensive

**Google Gemini**
- `gemini-1.5-flash`: Fast, efficient, good for validation
- `gemini-1.5-pro`: Highest quality, more expensive

## Additional Resources

- [LiteLLM Documentation](https://docs.litellm.ai/) - Multi-provider AI library
- [ChromaDB Documentation](https://docs.trychroma.com/) - Vector database
- [Ollama Models](https://ollama.ai/library) - Local model library
- [OpenAI API](https://platform.openai.com/docs/) - OpenAI documentation
- [Google AI](https://ai.google.dev/) - Gemini API documentation
