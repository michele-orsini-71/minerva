# Qwen 2.5 Testing - Quick Start

## ✅ You're Ready to Test!

All Python dependencies are already installed:
- ✅ `openai` (1.101.0)
- ✅ `httpx` (0.28.1)

## 🚀 Quick Steps

### 1. Download & Setup LM Studio (do this now)
1. Go to https://lmstudio.ai and download
2. Install and launch
3. Search for `Qwen2.5-7B-Instruct`
4. Download a GGUF model (recommend Q5_K_M, ~5.2GB)
5. Go to Developer tab → Load model → Start Server

### 2. Run Basic Test (after LM Studio is ready)
```bash
python test-qwen-tools.py
```

This tests if Qwen can decide when to use tools correctly.

**Goal**: 80%+ pass rate

### 3. Run Full Integration Test (if test 1 passes)

Start Minerva MCP server:
```bash
minerva serve-http --config configs/server-config.json --port 8000
```

In another terminal:
```bash
python test-qwen-mcp-chat.py
```

This tests the full chat flow with MCP integration.

---

## 📖 Detailed Guide

See [QWEN_TEST_GUIDE.md](./QWEN_TEST_GUIDE.md) for:
- Complete setup instructions
- Troubleshooting tips
- What to look for in results
- Next steps based on outcomes

---

## 🎯 What We're Testing

**Question**: Can Qwen 2.5 reliably replace Ollama for tool calling?

**Test Files**:
- `test-qwen-tools.py` - Tests tool calling accuracy
- `test-qwen-mcp-chat.py` - Tests full chat integration with MCP
- `QWEN_TEST_GUIDE.md` - Detailed documentation

**If successful**: We'll integrate this into Minerva Chat permanently!

---

## 📝 Quick Notes

**Recommended Model**: `lmstudio-community/Qwen2.5-7B-Instruct-Q5_K_M-GGUF`
- Good balance of speed and quality
- Runs on 8GB+ RAM
- Known for excellent tool calling

**LM Studio Server**: Must be running on `http://localhost:1234`
**Minerva MCP Server**: Must be running on `http://localhost:8000` (for test 2)

---

**Questions?** Check the full guide or just run the tests and see what happens! 🚀
