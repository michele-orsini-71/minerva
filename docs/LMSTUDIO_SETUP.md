# LM Studio Setup Guide

LM Studio is a desktop application for running large language models locally on your machine. This guide covers installing LM Studio, configuring it with Minerva, selecting appropriate models, and managing rate limits.

## Table of Contents

- [What is LM Studio?](#what-is-lm-studio)
- [Installation](#installation)
- [Model Selection](#model-selection)
- [Server Configuration](#server-configuration)
- [Minerva Configuration](#minerva-configuration)
- [Rate Limiting](#rate-limiting)
- [Troubleshooting](#troubleshooting)
- [Performance Tips](#performance-tips)

## What is LM Studio?

LM Studio is a user-friendly application that allows you to:

- Download and run large language models locally
- Serve models through an OpenAI-compatible API
- Run models without requiring API keys or internet connection
- Keep your data private (everything runs on your machine)

**Key Benefits for Minerva:**

- **Privacy**: All processing happens locally
- **No API costs**: Free to use once downloaded
- **Offline operation**: Works without internet
- **OpenAI compatibility**: Drop-in replacement for OpenAI API

## Installation

### Step 1: Download LM Studio

Visit [lmstudio.ai](https://lmstudio.ai) and download the installer for your platform:

- **macOS**: Apple Silicon (M1/M2/M3) or Intel
- **Windows**: Windows 10/11 (64-bit)
- **Linux**: Ubuntu 20.04+ or compatible

### Step 2: Install and Launch

**macOS:**
```bash
# Open the downloaded .dmg file
# Drag LM Studio to Applications folder
# Launch from Applications

# First launch may require security approval:
# System Settings → Privacy & Security → Allow LM Studio
```

**Windows:**
```powershell
# Run the installer executable
# Follow installation wizard
# Launch LM Studio from Start Menu
```

**Linux:**
```bash
# Extract the AppImage
chmod +x LM_Studio-*.AppImage
./LM_Studio-*.AppImage
```

### Step 3: Verify Installation

Launch LM Studio and you should see the main interface with:
- **Discover** tab: Browse available models
- **Chat** tab: Interactive testing
- **Local Server** tab: API server controls

## Model Selection

### Recommended Models for Minerva

LM Studio supports thousands of models. For Minerva, you need models that support:
- **Embeddings**: Text-to-vector conversion for semantic search
- **Chat**: Natural language interaction

#### For All-in-One Usage (Embeddings + Chat)

These models work for both embeddings and chat:

| Model | Size | VRAM Required | Best For |
|-------|------|---------------|----------|
| `qwen2.5-7b-instruct` | 7B | 8GB | Embeddings, small chat |
| `qwen2.5-14b-instruct` | 14B | 16GB | Better chat quality |
| `llama-3.1-8b-instruct` | 8B | 10GB | Good all-rounder |
| `mistral-7b-instruct-v0.2` | 7B | 8GB | Fast, efficient |

#### For Specialized Usage

**Best for Embeddings:**
- `nomic-embed-text-v1.5` - Specialized embedding model (335M parameters)
- `bge-large-en-v1.5` - High-quality embeddings (335M parameters)

**Best for Chat:**
- `qwen2.5-14b-instruct` - Excellent reasoning and instruction following
- `llama-3.1-70b-instruct` - Top quality (requires 40GB+ VRAM)
- `mixtral-8x7b-instruct` - Good balance (requires 32GB VRAM)

### Downloading Models

**Using LM Studio UI:**

1. Open LM Studio
2. Click **Discover** tab
3. Search for your model (e.g., "qwen2.5-7b-instruct")
4. Click **Download**
5. Select quantization level:
   - **Q4_K_M**: Good balance (recommended)
   - **Q5_K_M**: Better quality, larger size
   - **Q8_0**: Highest quality, largest size
   - **Q2_K**: Smallest, lower quality

**Recommended quantization:** Q4_K_M for most users

**Download location:**
- macOS: `~/.cache/lm-studio/models/`
- Windows: `C:\Users\YourName\.cache\lm-studio\models\`
- Linux: `~/.cache/lm-studio/models/`

### Model Size Guidelines

| Available VRAM | Recommended Model Size | Example Models |
|----------------|------------------------|----------------|
| 8GB | 7B models (Q4) | qwen2.5-7b, mistral-7b |
| 16GB | 7-14B models (Q4-Q5) | qwen2.5-14b, llama-3.1-8b |
| 24GB | 14-34B models (Q4) | mixtral-8x7b, yi-34b |
| 32GB+ | 34-70B models (Q4) | llama-3.1-70b, qwen2.5-72b |

## Server Configuration

### Starting the LM Studio Server

LM Studio provides an OpenAI-compatible API server that Minerva uses.

**Step 1: Load a Model**

1. Open LM Studio
2. Go to **Local Server** tab
3. Click **Select a model to load**
4. Choose your downloaded model
5. Click **Load model**

Wait for the model to load (you'll see "Model loaded" status).

**Step 2: Configure Server Settings**

In the Local Server tab:

- **Server port**: Default `1234` (recommended)
- **CORS enabled**: Enable if accessing from web apps
- **API Key**: Leave empty for local use (Minerva doesn't require it)

**Step 3: Start the Server**

Click **Start Server**

You should see:
```
Server started on http://localhost:1234
```

**Step 4: Verify Server is Running**

```bash
# Test the server
curl http://localhost:1234/v1/models

# Expected output: JSON with list of loaded models
```

### Server Endpoint

When the server is running, Minerva connects to:
```
http://localhost:1234/v1
```

This endpoint provides OpenAI-compatible routes:
- `/v1/embeddings` - Generate embeddings
- `/v1/chat/completions` - Chat completions
- `/v1/models` - List loaded models

## Minerva Configuration

### Unified Configuration File

Create a configuration file with LM Studio provider:

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
    "chromadb_path": "/absolute/path/to/chromadb_data",
    "collections": [
      {
        "collection_name": "my-notes",
        "description": "Personal notes indexed with LM Studio",
        "json_file": "./notes.json",
        "ai_provider_id": "lmstudio-local"
      }
    ]
  },
  "chat": {
    "chat_provider_id": "lmstudio-local",
    "mcp_server_url": "http://localhost:8000/mcp",
    "conversation_dir": "~/.minerva/conversations",
    "enable_streaming": false
  },
  "server": {
    "chromadb_path": "/absolute/path/to/chromadb_data",
    "default_max_results": 5
  }
}
```

### Configuration Fields

**Provider Section:**

- `id`: Unique identifier for this provider
- `provider_type`: Must be `"lmstudio"`
- `base_url`: LM Studio API endpoint (usually `http://localhost:1234/v1`)
- `embedding_model`: Model name for generating embeddings
- `llm_model`: Model name for chat/completions
- `rate_limit`: Optional rate limiting (see below)

**Model Names:**

Use the exact model name as shown in LM Studio's "Local Server" tab. Common patterns:
- `qwen2.5-7b-instruct`
- `llama-3.1-8b-instruct`
- `mistral-7b-instruct-v0.2`

### Using the Same Model for Both

You can use one model for both embeddings and chat:

```json
{
  "id": "lmstudio-unified",
  "provider_type": "lmstudio",
  "base_url": "http://localhost:1234/v1",
  "embedding_model": "qwen2.5-7b-instruct",
  "llm_model": "qwen2.5-7b-instruct"
}
```

**Tradeoff:** Faster (one model loaded) but may impact quality for specialized tasks.

### Using Different Models

For better quality, use specialized models:

```json
{
  "id": "lmstudio-specialized",
  "provider_type": "lmstudio",
  "base_url": "http://localhost:1234/v1",
  "embedding_model": "nomic-embed-text-v1.5",
  "llm_model": "qwen2.5-14b-instruct"
}
```

**Note:** LM Studio can only load one model at a time. You'll need to switch models when using different operations (indexing vs. chat).

## Rate Limiting

Rate limiting prevents overwhelming your system when processing large datasets.

### Why Rate Limit?

LM Studio runs locally and consumes:
- **CPU/GPU**: Model inference
- **Memory**: Model weights + processing
- **Disk I/O**: Model loading

Without rate limiting, processing thousands of notes simultaneously could:
- Freeze your system
- Cause out-of-memory errors
- Overheat hardware

### Configuration

```json
{
  "rate_limit": {
    "requests_per_minute": 60,
    "concurrency": 1
  }
}
```

**Fields:**

- `requests_per_minute`: Maximum API calls per minute (null = unlimited)
- `concurrency`: Maximum simultaneous requests (null = unlimited)

### Recommended Settings

**For Indexing Large Collections:**

```json
{
  "rate_limit": {
    "requests_per_minute": 30,
    "concurrency": 1
  }
}
```

- Prevents system overload
- Allows background processing
- Sustainable for hours of indexing

**For Chat (Interactive Use):**

```json
{
  "rate_limit": {
    "requests_per_minute": 60,
    "concurrency": 1
  }
}
```

- Faster response for interactive queries
- Concurrency=1 prevents model conflicts

**For Maximum Speed (Powerful Hardware):**

```json
{
  "rate_limit": null
}
```

- No artificial limits
- Only for high-end GPUs (RTX 4090, M2 Ultra, etc.)
- Monitor system resources

### Hardware-Specific Recommendations

| Hardware | Requests/Min | Concurrency |
|----------|--------------|-------------|
| MacBook Air M1 | 30 | 1 |
| MacBook Pro M1/M2 | 45 | 1 |
| Mac Studio M2 Ultra | 60 | 1-2 |
| RTX 3060 (12GB) | 30 | 1 |
| RTX 4070 (12GB) | 45 | 1 |
| RTX 4090 (24GB) | 60 | 1-2 |
| Server (A100/H100) | 120 | 2-4 |

## Troubleshooting

### Server Won't Start

**Error:** "Failed to load model"

**Solutions:**
1. Check available VRAM:
   ```bash
   # macOS
   system_profiler SPDisplaysDataType | grep VRAM

   # Linux (NVIDIA)
   nvidia-smi

   # Windows
   dxdiag
   ```

2. Try smaller quantization (Q4 instead of Q8)
3. Close other GPU-intensive applications
4. Try a smaller model (7B instead of 14B)

**Error:** "Port 1234 already in use"

**Solutions:**
```bash
# Find what's using the port
lsof -i :1234  # macOS/Linux
netstat -ano | findstr :1234  # Windows

# Either stop that process or change LM Studio port
# In LM Studio: Settings → Server Port → 1235
```

### Connection Errors

**Error:** "Connection refused to http://localhost:1234"

**Check:**
1. LM Studio server is running (green indicator in UI)
2. Model is loaded
3. Firewall isn't blocking local connections
4. Correct base_url in config (`http://localhost:1234/v1`)

**Verify:**
```bash
curl http://localhost:1234/v1/models
```

### Model Loading Issues

**Error:** "Model not found"

**Solutions:**
1. Check model name matches exactly (case-sensitive)
2. Verify model is downloaded in LM Studio
3. Reload model in LM Studio UI
4. Check LM Studio logs (View → Developer → Toggle Developer Tools)

### Slow Performance

**Symptom:** Very slow embedding/chat generation

**Solutions:**

1. **Reduce model size:**
   - Use 7B model instead of 14B+
   - Use Q4 quantization instead of Q8

2. **Check GPU usage:**
   ```bash
   # macOS - Activity Monitor → GPU tab
   # Linux
   nvidia-smi -l 1
   ```

3. **Optimize rate limits:**
   ```json
   {
     "rate_limit": {
       "requests_per_minute": 20,
       "concurrency": 1
     }
   }
   ```

4. **Close other applications:**
   - Chrome/browsers (VRAM hog)
   - Other AI tools
   - Games

5. **Use GPU acceleration:**
   - LM Studio Settings → Enable GPU acceleration
   - Update GPU drivers

### Out of Memory

**Error:** "CUDA out of memory" or system freeze

**Solutions:**

1. **Reduce batch size** (Minerva processes in batches automatically)

2. **Use smaller model:**
   - 7B instead of 14B
   - Q4 instead of Q5/Q8

3. **Increase system RAM:**
   - Close unused applications
   - Restart LM Studio

4. **Process in smaller chunks:**
   - Split large note collections
   - Index in multiple sessions

## Performance Tips

### Optimizing Indexing Speed

**For Maximum Speed:**

1. **Use Q4 quantization** (fastest while maintaining quality)
2. **Load model once** (avoid switching between models)
3. **Use same model for embeddings and chat** during initial setup
4. **Batch processing** (Minerva does this automatically)
5. **Close other apps** using GPU/RAM

**Expected Performance:**

| Hardware | Model | Embeddings/sec | Notes/hour |
|----------|-------|----------------|------------|
| M1 MacBook | qwen2.5-7b Q4 | 5-10 | 300-600 |
| M2 Pro | qwen2.5-7b Q4 | 10-15 | 600-900 |
| RTX 3060 | qwen2.5-7b Q4 | 8-12 | 500-700 |
| RTX 4090 | qwen2.5-14b Q4 | 20-30 | 1200-1800 |

### Optimizing Chat Response Time

1. **Load model before starting chat:**
   - Pre-load in LM Studio before running `minerva chat`

2. **Use smaller models for faster responses:**
   - 7B models: 1-3 seconds per response
   - 14B models: 3-5 seconds per response
   - 70B models: 10-20 seconds per response

3. **Disable streaming for consistency:**
   ```json
   {
     "enable_streaming": false
   }
   ```

4. **Reduce context window:**
   - Shorter system prompts
   - Fewer search results
   - Regular conversation summarization

### Hardware Acceleration

**NVIDIA GPUs (Linux/Windows):**
- Install CUDA toolkit
- Update NVIDIA drivers
- LM Studio auto-detects GPU

**Apple Silicon (M1/M2/M3):**
- Metal acceleration enabled by default
- No additional setup needed
- Unified memory architecture (RAM = VRAM)

**AMD GPUs:**
- Limited support in LM Studio
- May fall back to CPU
- Check LM Studio docs for ROCm support

### Model Caching

LM Studio keeps models in memory:
- First load: 10-30 seconds
- Subsequent uses: Instant
- Keep LM Studio running for best performance

### Monitoring Performance

**LM Studio Built-in Monitor:**
- Local Server tab → Performance metrics
- Shows tokens/second, memory usage

**System Monitoring:**
```bash
# macOS
Activity Monitor → GPU, Memory tabs

# Linux (NVIDIA)
watch -n 1 nvidia-smi

# Windows
Task Manager → Performance → GPU
```

## Best Practices

### Development Workflow

1. **Start LM Studio first**
   ```bash
   # Launch LM Studio
   # Load your model
   # Start server
   ```

2. **Verify connection**
   ```bash
   curl http://localhost:1234/v1/models
   ```

3. **Run Minerva commands**
   ```bash
   minerva index --config config.json
   ```

### Production Deployment

**For 24/7 Server:**
- Use dedicated GPU machine
- Auto-start LM Studio on boot
- Monitor model crashes
- Set conservative rate limits
- Regular restarts (weekly)

**For Personal Desktop:**
- Start LM Studio when needed
- Stop server when not in use
- Use aggressive rate limits
- Close when system resources needed

### Multiple Models Strategy

**Option 1: Single Model (Simple)**
```json
{
  "embedding_model": "qwen2.5-7b-instruct",
  "llm_model": "qwen2.5-7b-instruct"
}
```
- Load once, use for everything
- Faster setup
- Good enough for most uses

**Option 2: Specialized Models (Quality)**
```json
{
  "embedding_model": "nomic-embed-text-v1.5",
  "llm_model": "qwen2.5-14b-instruct"
}
```
- Better quality
- Switch models for different operations
- More VRAM required

### Backup Strategy

**Model files:**
- Already cached in `~/.cache/lm-studio/models/`
- Large files (4-40GB each)
- No need to back up (can re-download)

**Configuration:**
```bash
# Back up your Minerva configs
cp config.json config.json.backup

# Version control is better
git add configs/*.json
git commit -m "feat: update LM Studio config"
```

## See Also

- [Unified Configuration Guide](configuration.md) - Full config schema
- [Chat Guide](CHAT_GUIDE.md) - Using LM Studio for chat
- [Main README](../README.md) - General Minerva documentation
- [LM Studio Official Docs](https://lmstudio.ai/docs) - LM Studio documentation
