# Minerva Configuration Examples

This directory contains example configuration files for Minerva. These are templates you can copy and customize for your own use.

## Directory Structure

```
configs/
├── index/                      # Index configurations (one per collection)
│   ├── example-openai.json    # Using OpenAI embeddings (cloud)
│   └── example-ollama.json    # Using Ollama embeddings (local)
└── server/                     # Server configurations (deployment profiles)
    ├── local-stdio.json       # Local stdio mode (for Claude Desktop)
    └── remote-http.json       # Remote HTTP mode (for team deployment)
```

## Usage

### 1. Index Configuration

Create one config file per collection you want to index:

```bash
# Copy example
cp configs/index/example-openai.json configs/index/my-repo.json

# Edit to customize
# - Change collection name
# - Update description
# - Point json_file to your extracted notes
# - Adjust chunk_size if needed

# Run indexing
minerva index --config configs/index/my-repo.json
```

**Key fields to customize:**
- `collection.name` - Unique collection identifier (use `snake_case`)
- `collection.description` - What this collection contains (used by AI for relevance)
- `collection.json_file` - Path to extracted JSON notes
- `chromadb_path` - Where to store the vector database

**Provider options:**
- `openai` - Fast cloud embeddings, requires API key
- `ollama` - Free local embeddings, requires Ollama server running
- `lmstudio` - Local embeddings via LM Studio

### 2. Server Configuration

Choose based on your deployment scenario:

**Local Development (stdio mode):**
```bash
cp configs/server/local-stdio.json ~/.minerva/configs/server.json
minerva serve --config ~/.minerva/configs/server.json
```

**Remote Team Deployment (HTTP mode):**
```bash
cp configs/server/remote-http.json /data/configs/server.json
# Edit to set host and port
minerva serve-http --config /data/configs/server.json
```

## Path Resolution

All relative paths in config files are resolved **relative to the config file's location**.

**Example:**
```
project/
├── chromadb_data/              # Vector database storage
├── data/
│   └── extracted/
│       └── my-repo.json        # Extracted notes
└── configs/
    └── index/
        └── my-repo.json        # Config file
```

In `configs/index/my-repo.json`:
```json
{
  "chromadb_path": "../../chromadb_data",
  "collection": {
    "json_file": "../../data/extracted/my-repo.json"
  }
}
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your API keys
```

Config files can reference environment variables:
```json
{
  "provider": {
    "api_key": "${OPENAI_API_KEY}"
  }
}
```

## Personal Configs

**Do not commit personal configs to git!**

Create your personal configs in:
- `~/.minerva/configs/` - For personal development
- `/data/configs/` - For server deployment

The example configs in this directory are templates only.

## More Information

- Full configuration guide: `docs/configuration.md`
- Command parameters: `minerva --help`
- AI provider setup: `docs/LMSTUDIO_SETUP.md`
