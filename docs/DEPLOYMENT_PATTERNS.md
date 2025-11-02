# Deployment Patterns

This guide covers common deployment patterns for Minerva, from simple desktop setups to complex server deployments. Each pattern includes complete configuration examples and deployment instructions.

## Table of Contents

- [Pattern 1: All LM Studio (Desktop)](#pattern-1-all-lm-studio-desktop)
- [Pattern 2: Hybrid Ollama + LM Studio](#pattern-2-hybrid-ollama--lm-studio)
- [Pattern 3: All Cloud (OpenAI)](#pattern-3-all-cloud-openai)
- [Pattern 4: Server Deployment (Ollama)](#pattern-4-server-deployment-ollama)
- [Pattern 5: Multi-User Server](#pattern-5-multi-user-server)
- [Pattern 6: Development + Production](#pattern-6-development--production)
- [Comparison Matrix](#comparison-matrix)

## Pattern 1: All LM Studio (Desktop)

**Use case:** Desktop user who wants everything running locally with a user-friendly GUI

**Pros:**
- User-friendly interface for model management
- No API costs
- Completely offline after models downloaded
- Privacy (all processing local)

**Cons:**
- Requires powerful hardware (8GB+ VRAM recommended)
- Manual model switching for different operations
- LM Studio must be running

### Hardware Requirements

- **Minimum:** 16GB RAM, 8GB VRAM (M1/M2 Mac or RTX 3060+)
- **Recommended:** 32GB RAM, 12GB+ VRAM (M2 Pro/Max or RTX 4070+)
- **Optimal:** 64GB RAM, 24GB+ VRAM (Mac Studio or RTX 4090)

### Setup Steps

**1. Install LM Studio**

Download and install from [lmstudio.ai](https://lmstudio.ai)

**2. Download Models**

In LM Studio:
- Download `qwen2.5-7b-instruct` (Q4_K_M) for embeddings
- Download `qwen2.5-14b-instruct` (Q4_K_M) for chat

**3. Start LM Studio Server**

- Load `qwen2.5-7b-instruct` initially
- Go to "Local Server" tab
- Click "Start Server" (default port: 1234)

**4. Create Configuration**

`config-lmstudio-desktop.json`:

```json
{
  "ai_providers": [
    {
      "id": "lmstudio-local",
      "provider_type": "lmstudio",
      "base_url": "http://localhost:1234/v1",
      "embedding_model": "qwen2.5-7b-instruct",
      "llm_model": "qwen2.5-14b-instruct",
      "rate_limit": {
        "requests_per_minute": 60,
        "concurrency": 1
      }
    }
  ],
  "indexing": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "collections": [
      {
        "collection_name": "personal-notes",
        "description": "Personal notes from Bear app covering software development, research, and project documentation",
        "json_file": "./notes.json",
        "chunk_size": 1200,
        "force_recreate": false,
        "skip_ai_validation": false,
        "ai_provider_id": "lmstudio-local"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "lmstudio-local",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

**5. Index Notes**

```bash
# Load qwen2.5-7b-instruct in LM Studio
minerva index --config config-lmstudio-desktop.json --verbose
```

**6. Start MCP Server**

```bash
# Start MCP server (keeps running in background)
minerva serve --config config-lmstudio-desktop.json &
```

**7. Chat**

```bash
# Switch to qwen2.5-14b-instruct in LM Studio for better chat quality
minerva chat --config config-lmstudio-desktop.json
```

### Daily Workflow

```bash
# Morning: Start LM Studio
# 1. Launch LM Studio
# 2. Load model (qwen2.5-14b-instruct)
# 3. Start server

# Start services
minerva serve --config config-lmstudio-desktop.json &

# Use chat throughout the day
minerva chat --config config-lmstudio-desktop.json

# Evening: Stop services
# Close Minerva, stop LM Studio
```

## Pattern 2: Hybrid Ollama + LM Studio

**Use case:** Desktop user who wants fast indexing (Ollama) and high-quality chat (LM Studio)

**Pros:**
- Fast indexing with Ollama (optimized for embeddings)
- Better chat quality with LM Studio
- Flexible: can use either independently
- Best of both worlds

**Cons:**
- Requires both Ollama and LM Studio running
- More complex setup
- Higher resource usage

### Hardware Requirements

- **Minimum:** 24GB RAM, 8GB VRAM
- **Recommended:** 32GB RAM, 12GB+ VRAM

### Setup Steps

**1. Install Both Tools**

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Ollama models
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b

# Install LM Studio and download qwen2.5-14b-instruct
```

**2. Create Configuration**

`config-hybrid.json`:

```json
{
  "ai_providers": [
    {
      "id": "ollama-indexing",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434",
      "embedding": {
        "model": "mxbai-embed-large:latest"
      },
      "llm": {
        "model": "llama3.1:8b"
      }
    },
    {
      "id": "lmstudio-chat",
      "provider_type": "lmstudio",
      "base_url": "http://localhost:1234/v1",
      "embedding_model": "qwen2.5-7b-instruct",
      "llm_model": "qwen2.5-14b-instruct",
      "rate_limit": {
        "requests_per_minute": 45,
        "concurrency": 1
      }
    }
  ],
  "indexing": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "collections": [
      {
        "collection_name": "engineering-journal",
        "description": "Engineering journal entries and technical documentation",
        "json_file": "./notes.json",
        "chunk_size": 1400,
        "force_recreate": false,
        "skip_ai_validation": false,
        "ai_provider_id": "ollama-indexing"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "lmstudio-chat",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

**3. Index with Ollama (Fast)**

```bash
# Start Ollama
ollama serve &

# Index (uses Ollama for fast embedding generation)
minerva index --config config-hybrid.json --verbose
```

**4. Chat with LM Studio (Quality)**

```bash
# Start LM Studio server with qwen2.5-14b-instruct loaded

# Start MCP server
minerva serve --config config-hybrid.json &

# Chat (uses LM Studio for high-quality responses)
minerva chat --config config-hybrid.json
```

### Why This Works

- **Indexing:** Ollama's `mxbai-embed-large` is optimized for embeddings (fast, efficient)
- **Chat:** LM Studio's `qwen2.5-14b` provides better reasoning and conversation quality
- **Separation:** Indexing and chat use different providers, no model switching needed

## Pattern 3: All Cloud (OpenAI)

**Use case:** User willing to pay for API access, wants highest quality

**Pros:**
- Highest quality embeddings and chat
- No local hardware requirements
- Always latest models
- No setup or maintenance

**Cons:**
- Ongoing API costs
- Requires internet connection
- Privacy concerns (data sent to OpenAI)
- Rate limits

### Cost Estimates

**Indexing 1000 notes (avg 500 tokens each):**
- Embeddings: ~$0.01 (text-embedding-3-small)
- Total: < $0.10

**Chat usage (typical):**
- ~100 messages/day
- ~50,000 tokens/day
- Cost: ~$0.75/day with gpt-4o-mini

**Monthly total:** ~$25-30 for active use

### Setup Steps

**1. Get API Key**

```bash
# Sign up at platform.openai.com
# Create API key
export OPENAI_API_KEY="sk-proj-..."

# Add to shell profile for persistence
echo 'export OPENAI_API_KEY="sk-proj-..."' >> ~/.zshrc
```

**2. Create Configuration**

`config-openai.json`:

```json
{
  "ai_providers": [
    {
      "id": "openai-cloud",
      "provider_type": "openai",
      "api_key": "${OPENAI_API_KEY}",
      "embedding": {
        "model": "text-embedding-3-small"
      },
      "llm": {
        "model": "gpt-4o-mini"
      }
    }
  ],
  "indexing": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "collections": [
      {
        "collection_name": "research-papers",
        "description": "Academic research papers and technical documentation on AI, ML, and computer science",
        "json_file": "./papers.json",
        "chunk_size": 1200,
        "ai_provider_id": "openai-cloud"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "openai-cloud",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": true,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "${HOME}/minerva/chromadb_data",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8000
  }
}
```

**3. Usage**

```bash
# Verify API key
echo $OPENAI_API_KEY

# Index (charged per token)
minerva index --config config-openai.json --verbose

# Start server
minerva serve --config config-openai.json &

# Chat (streaming enabled for better UX)
minerva chat --config config-openai.json
```

## Pattern 4: Server Deployment (Ollama)

**Use case:** Shared server for team access, all local processing

**Pros:**
- Centralized knowledge base
- No individual hardware requirements
- Team collaboration
- No API costs
- Private (all data on server)

**Cons:**
- Requires server setup
- Network dependency
- Single point of failure

### Server Requirements

- **CPU:** 8+ cores
- **RAM:** 32GB+ (64GB recommended)
- **GPU:** NVIDIA with 24GB+ VRAM (optional but recommended)
- **Storage:** 500GB+ SSD
- **OS:** Ubuntu 22.04 LTS or similar

### Setup Steps

**1. Install Ollama on Server**

```bash
# SSH to server
ssh user@server.example.com

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull mxbai-embed-large:latest
ollama pull llama3.1:8b

# Start Ollama as service
sudo systemctl enable ollama
sudo systemctl start ollama
```

**2. Install Minerva**

```bash
# Install pipx
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install Minerva
git clone https://github.com/yourusername/minerva.git
cd minerva
pipx install .

# Verify
minerva --version
```

**3. Create Server Configuration**

`/srv/minerva/config.json`:

```json
{
  "ai_providers": [
    {
      "id": "ollama-server",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434",
      "embedding": {
        "model": "mxbai-embed-large:latest"
      },
      "llm": {
        "model": "llama3.1:8b"
      }
    }
  ],
  "indexing": {
    "chromadb_path": "/srv/minerva/chromadb_data",
    "collections": [
      {
        "collection_name": "team-knowledge-base",
        "description": "Shared engineering knowledge base maintained on the central server",
        "json_file": "/srv/minerva/data/team-knowledge.json",
        "chunk_size": 1200,
        "force_recreate": false,
        "skip_ai_validation": false,
        "ai_provider_id": "ollama-server"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "ollama-server",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "/var/minerva/conversations",
    "enable_streaming": false,
    "max_tool_iterations": 5
  },
  "server": {
    "chromadb_path": "/srv/minerva/chromadb_data",
    "default_max_results": 5,
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**4. Create Systemd Service**

`/etc/systemd/system/minerva-mcp.service`:

```ini
[Unit]
Description=Minerva MCP Server
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=minerva
Group=minerva
WorkingDirectory=/srv/minerva
ExecStart=/home/minerva/.local/bin/minerva serve --config /srv/minerva/config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**5. Start Service**

```bash
# Create minerva user
sudo useradd -r -s /bin/bash -d /srv/minerva minerva
sudo mkdir -p /srv/minerva/{chromadb_data,data}
sudo chown -R minerva:minerva /srv/minerva

# Index initial data
sudo -u minerva minerva index --config /srv/minerva/config.json --verbose

# Enable and start service
sudo systemctl enable minerva-mcp
sudo systemctl start minerva-mcp

# Check status
sudo systemctl status minerva-mcp
```

**6. Access from Clients**

Clients configure MCP to point to server:

```json
{
  "chat": {
    "mcp_server_url": "http://server.example.com:8000/mcp"
  }
}
```

### Security Considerations

**Firewall:**
```bash
# Allow only internal network
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

**Reverse Proxy (Nginx):**
```nginx
server {
    listen 443 ssl;
    server_name minerva.example.com;

    ssl_certificate /etc/ssl/certs/minerva.crt;
    ssl_certificate_key /etc/ssl/private/minerva.key;

    location /mcp {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Pattern 5: Multi-User Server

**Use case:** Multiple team members with individual conversations but shared knowledge base

**Architecture:**

```
┌─────────────────────────────────────────┐
│         Shared MCP Server               │
│  (Team Knowledge Base - Read Only)      │
│         Port: 8000                      │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────┐
│ User A │  │ User B │  │ User C │
│ Local  │  │ Local  │  │ Local  │
│ Chat   │  │ Chat   │  │ Chat   │
└────────┘  └────────┘  └────────┘
```

**Server Config:**

Same as Pattern 4, but with read-only access enforcement.

**Client Config:**

Each user has local config pointing to shared server:

`config-client.json`:

```json
{
  "ai_providers": [
    {
      "id": "ollama-local",
      "provider_type": "ollama",
      "base_url": "http://localhost:11434",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "chat": {
    "chat_provider_id": "ollama-local",
    "mcp_server_url": "http://minerva-server.company.com:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false
  }
}
```

**Usage:**

```bash
# Each user runs locally
minerva chat --config config-client.json

# Conversations stored locally (~/.minerva/conversations)
# Search queries go to shared server
```

## Pattern 6: Development + Production

**Use case:** Separate environments for testing and production

**Development (Local):**

`config-dev.json`:

```json
{
  "ai_providers": [
    {
      "id": "ollama-dev",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "./chromadb_dev",
    "collections": [
      {
        "collection_name": "test-notes",
        "description": "Test collection with sample data",
        "json_file": "./test-data/sample-100-notes.json",
        "ai_provider_id": "ollama-dev"
      }
    ]
  },
  "server": {
    "chromadb_path": "./chromadb_dev",
    "default_max_results": 5,
    "host": "127.0.0.1",
    "port": 8001
  }
}
```

**Production (Server):**

`config-prod.json`:

```json
{
  "ai_providers": [
    {
      "id": "ollama-prod",
      "provider_type": "ollama",
      "embedding": {"model": "mxbai-embed-large:latest"},
      "llm": {"model": "llama3.1:8b"}
    }
  ],
  "indexing": {
    "chromadb_path": "/srv/minerva/chromadb_prod",
    "collections": [
      {
        "collection_name": "production-kb",
        "description": "Production knowledge base",
        "json_file": "/srv/minerva/data/prod-notes.json",
        "ai_provider_id": "ollama-prod"
      }
    ]
  },
  "server": {
    "chromadb_path": "/srv/minerva/chromadb_prod",
    "default_max_results": 5,
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**Workflow:**

```bash
# Development: Test locally
minerva index --config config-dev.json --verbose
minerva serve --config config-dev.json &
minerva chat --config config-dev.json

# Production: Deploy to server
scp notes.json server:/srv/minerva/data/prod-notes.json
ssh server "minerva index --config /srv/minerva/config-prod.json --verbose"
ssh server "sudo systemctl restart minerva-mcp"
```

## Comparison Matrix

| Pattern | Hardware | Cost | Quality | Privacy | Complexity | Best For |
|---------|----------|------|---------|---------|------------|----------|
| All LM Studio | High | None | Good | High | Medium | Desktop users, privacy-focused |
| Hybrid Ollama+LM | High | None | Very Good | High | Medium | Power users, best quality local |
| All Cloud | Low | Medium | Excellent | Low | Low | Users prioritizing quality |
| Server (Ollama) | Server | None | Good | High | High | Teams, shared knowledge |
| Multi-User | Server | None | Good | High | High | Teams, individual conversations |
| Dev+Prod | Both | None/Low | Good | High | High | Development workflows |

## Choosing a Pattern

**Choose Pattern 1 (All LM Studio) if:**
- You have powerful desktop hardware
- You want a GUI for model management
- Privacy is important
- You're comfortable with local-only setup

**Choose Pattern 2 (Hybrid) if:**
- You want the best local quality
- You have resources for both Ollama and LM Studio
- You index frequently but chat occasionally
- You want flexibility

**Choose Pattern 3 (All Cloud) if:**
- You have budget for API costs
- You prioritize quality over cost
- You have reliable internet
- You need minimal local setup

**Choose Pattern 4 (Server) if:**
- You're deploying for a team
- You have server infrastructure
- You want centralized knowledge
- Privacy is important

**Choose Pattern 5 (Multi-User) if:**
- Multiple users need access
- Each user needs private conversations
- You want shared knowledge base
- You have server infrastructure

**Choose Pattern 6 (Dev+Prod) if:**
- You're developing/testing Minerva
- You need separate environments
- You want to test before deploying
- You have both local and server resources

## See Also

- [Unified Configuration Guide](configuration.md) - Complete config reference
- [LM Studio Setup Guide](LMSTUDIO_SETUP.md) - LM Studio installation
- [Chat Guide](CHAT_GUIDE.md) - Chat command usage
- [Main README](../README.md) - General documentation
