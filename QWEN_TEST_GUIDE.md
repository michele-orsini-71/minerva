# Qwen 2.5 + Minerva MCP Integration Test Guide

This guide walks you through testing whether **Qwen 2.5** (via LM Studio) can replace Ollama for reliable tool calling in Minerva Chat.

## 🎯 What We're Testing

**Current Problem**: Ollama models fail at tool calling (malformed JSON, infinite loops)
**Proposed Solution**: Use Qwen 2.5 (known for good tool calling) via LM Studio
**Architecture**: Qwen decides what to do → calls Minerva MCP server → returns results

---

## 📋 Setup Steps

### Step 1: Install LM Studio

1. Download from: https://lmstudio.ai
2. Install and launch the application
3. On first launch, you'll see the model search interface

### Step 2: Download Qwen 2.5 Model

In LM Studio:
1. Click the **search/download tab** (🔍 icon on left sidebar)
2. Search for: `Qwen2.5-7B-Instruct`
3. Look for models by `lmstudio-community` (pre-quantized GGUF format)
4. Recommended models (pick based on your RAM):
   - **8GB RAM**: `Qwen2.5-7B-Instruct-Q4_K_M.gguf` (~4.4 GB)
   - **16GB RAM**: `Qwen2.5-7B-Instruct-Q5_K_M.gguf` (~5.2 GB)
   - **32GB+ RAM**: `Qwen2.5-7B-Instruct-Q6_K.gguf` (~5.9 GB)
5. Click **Download** and wait for completion

**Alternative models to try**:
- `Qwen2.5-14B-Instruct` (if you have 16GB+ RAM) - better quality
- `Qwen2.5-3B-Instruct` (if you have limited RAM) - faster but less capable

### Step 3: Load Model and Start Server

In LM Studio:
1. Go to **Developer** tab (</> icon on left sidebar)
2. Click **Select a model to load** dropdown
3. Choose your downloaded Qwen2.5 model
4. Click **Start Server**
5. Verify it shows: `✓ Server running on http://localhost:1234`

**Keep this server running!** The test scripts will connect to it.

### Step 4: Install Python Dependencies

```bash
# In your minerva directory
pip install openai httpx
```

---

## 🧪 Test 1: Basic Tool Calling Test

This tests whether Qwen can reliably decide when to call tools.

```bash
python test-qwen-tools.py
```

**Expected output:**
```
🧪 Qwen 2.5 Tool Calling Test Suite
============================================================

🔌 Connecting to LM Studio on http://localhost:1234
✓ Connected! Available models:
  - qwen2.5-7b-instruct

Using model: qwen2.5-7b-instruct
Starting tests...

======================================================================
📝 Test: Information-seeking query about notes
Query: "What are my notes about Python programming?"
Expected: search_knowledge_base
----------------------------------------------------------------------
✅ PASS: Correctly called 'search_knowledge_base'
   Arguments:
   {
     "query": "Python programming",
     "collection_name": "bear_notes"
   }

... (more tests) ...

📊 Test Results Summary
============================================================

Passed: 8/8 (100.0%)
✅ All tests passed! Qwen 2.5 handles tool calling reliably.
   → Ready to integrate with Minerva chat!
```

**What to look for:**
- ✅ **Good**: 80%+ pass rate, correct arguments
- ⚠️ **Okay**: 60-80% pass rate (may need prompt tuning)
- ❌ **Bad**: <60% pass rate (try different model or approach)

---

## 🚀 Test 2: Full MCP Integration (If Test 1 Passes)

This tests the complete flow: Qwen → MCP Server → Search → Response

### Prerequisites

1. **Start Minerva MCP Server** (in a separate terminal):

```bash
# First, make sure you have a server config
cat > test-server-config.json << 'EOF'
{
  "chromadb_path": "./chromadb_data",
  "default_max_results": 5
}
EOF

# Start the server in HTTP mode
minerva serve-http --config test-server-config.json --port 8000
```

Keep this running!

2. **Run the integration test** (in another terminal):

```bash
python test-qwen-mcp-chat.py
```

**Expected output:**
```
🧪 Qwen 2.5 + Minerva MCP Chat Prototype
============================================================

🔌 Connecting to LM Studio...
✓ Connected to LM Studio (model: qwen2.5-7b-instruct)

🔌 Connecting to Minerva MCP server...
✓ Connected to Minerva MCP server

============================================================
💬 Chat Session Started
============================================================

Commands:
  exit, quit - Exit the chat
  /clear     - Clear conversation history

You:
```

### Test Queries

Try these queries to verify functionality:

```
You: What knowledge bases are available?
→ Should call list_knowledge_bases via MCP

You: What are my notes about Python?
→ Should call search_knowledge_base via MCP

You: Hello, how are you?
→ Should respond directly (no tool call)

You: Tell me more about the first result
→ Should use context from previous search
```

**What to look for:**
- ✅ Qwen decides when to search vs. respond directly
- ✅ Tool calls go through MCP server successfully
- ✅ Results are incorporated into responses
- ✅ Citations include note titles
- ✅ No infinite loops

---

## 🐛 Troubleshooting

### LM Studio Connection Error

**Error**: `Failed to connect to LM Studio`

**Fix**:
1. Is LM Studio running?
2. Go to Developer tab
3. Is server started? (should show green checkmark)
4. Check port is 1234 (default)

### MCP Server Connection Error

**Error**: `Minerva MCP server not accessible`

**Fix**:
1. Check if server is running: `ps aux | grep "minerva serve"`
2. Start it: `minerva serve --config test-server-config.json --http --port 8000`
3. Verify endpoint: `curl http://localhost:8000/mcp/`

### Model Loading Issues

**Error**: Model loads but responses are slow/bad

**Fix**:
1. Try a smaller quantization (Q4 instead of Q6)
2. Check system resources (RAM, CPU usage)
3. In LM Studio settings, try adjusting:
   - Context length (reduce to 4096)
   - GPU offload (if available)

### Tool Calling Not Working

**Symptoms**: Qwen never calls tools, or always calls wrong tools

**Try**:
1. Lower temperature in script (already at 0.1-0.3)
2. Try a different model size (14B might be better)
3. Update LM Studio to latest version
4. Check model is actually Qwen2.5-Instruct (not base model)

---

## 📊 Evaluation Criteria

### ✅ SUCCESS (Ready for Production)
- Test 1: 90%+ pass rate
- Test 2: Reliable tool calling, no loops
- Natural conversation flow
- Proper result integration

→ **Next step**: Replace Ollama with Qwen in Minerva Chat

### ⚠️ PARTIAL SUCCESS (Needs Tuning)
- Test 1: 70-90% pass rate
- Test 2: Works but occasional errors
- Some hallucinations

→ **Next step**: Fine-tune prompts, try larger model

### ❌ FAILURE (Try Different Approach)
- Test 1: <70% pass rate
- Test 2: Infinite loops, wrong tools
- Unusable

→ **Next step**: Consider rule-based intent detection or Claude/GPT orchestration

---

## 🎯 Next Steps After Successful Test

If tests pass well:

1. **Update `minerva/common/ai_provider.py`**:
   - Add LM Studio as a provider option
   - OpenAI-compatible API makes this easy

2. **Update chat engine**:
   - Replace Ollama client with OpenAI client pointing to LM Studio
   - Keep tool definitions the same
   - MCP integration works as-is

3. **Update documentation**:
   - Add LM Studio setup guide
   - Recommend Qwen 2.5 for chat
   - Note Ollama limitations

4. **Test with real knowledge bases**:
   - Index your actual notes
   - Test complex queries
   - Verify quality of responses

---

## 💡 Tips

- **Model Selection**: Start with Qwen2.5-7B, upgrade to 14B if quality issues
- **Quantization**: Q5_K_M is good balance of speed/quality
- **RAM**: Reserve at least model size + 2GB for overhead
- **GPU**: LM Studio can use GPU (Metal on Mac, CUDA on Nvidia) for huge speedups
- **Temperature**: Lower = more predictable, higher = more creative
- **Context Length**: 4K tokens usually enough for chat, can increase if needed

---

## 📚 Resources

- **LM Studio Docs**: https://lmstudio.ai/docs
- **Qwen Documentation**: https://qwen.readthedocs.io
- **Qwen Models on HuggingFace**: https://huggingface.co/Qwen
- **MCP Protocol**: https://spec.modelcontextprotocol.io

---

**Good luck with testing!** 🚀

Report your results and we can decide the next steps for integrating into Minerva.
