# FastMCP Solution for Multi-Collection MCP Server

This document addresses **OQ1** from the PRD and shows how FastMCP solves the architectural challenges outlined in `tasks/instructions.md`.

## Quick Answer to OQ1

**OQ1: Which MCP framework/SDK should we use for Python implementation?**

**Answer: FastMCP (`mcp.server.fastmcp`)**

- **Recommended by Anthropic** - Official SDK for MCP servers
- **Minimal boilerplate** - ~300 lines vs. 1000+ for custom JSON-RPC
- **Type-safe** - Automatic validation from Python type hints
- **Well-maintained** - Active development, community support

## How FastMCP Solves the Multi-Collection Problem

### Your Original Concerns (from instructions.md)

You identified three potential approaches, all with downsides:

1. **❌ Collection name as parameter** - "Will the AI be able to select the right collection?"
2. **❌ Different tools per collection** - "Manifest depends on database collections (weak point)"
3. **❌ Different MCP instances** - "Hardcoded manifest linked to dynamic source"

### The FastMCP Solution: Self-Discovery Pattern ✅

FastMCP enables a **fourth approach** that solves all these issues:

```python
@mcp.tool()
def list_knowledge_bases() -> List[Dict[str, Any]]:
    """AI discovers all collections dynamically"""
    collections = chromadb_client.list_collections()
    return [{"name": c.name, "description": c.metadata["description"], ...}]

@mcp.tool()
def search_knowledge_base(query: str, collection_name: str, ...) -> List[Dict]:
    """AI selects the right collection based on descriptions"""
    # ... search logic
```

**Why this works:**

1. **No hardcoded collections** - The manifest defines two tools, not specific collections
2. **AI-driven selection** - The AI reads collection descriptions and makes intelligent choices
3. **Zero configuration updates** - Add new collections without touching the MCP server code or manifest
4. **Type safety** - FastMCP validates `collection_name` parameter automatically

## Comparison: Custom Implementation vs. FastMCP

### Custom JSON-RPC Server (Your Option 1)

```python
# You would need to write:
import json
from typing import Any, Dict

class MCPServer:
    def __init__(self):
        self.handlers = {}

    def register_tool(self, name: str, handler, schema: Dict):
        """Manual tool registration"""
        self.handlers[name] = handler
        # Also need to build JSON schema manually

    def handle_request(self, request_str: str) -> str:
        """Parse JSON-RPC, validate, call handler, format response"""
        try:
            request = json.loads(request_str)
            method = request.get("method")
            params = request.get("params", {})

            # Validate parameters manually
            if method not in self.handlers:
                return self._error_response(request["id"], f"Unknown method: {method}")

            # Validate parameter types manually
            # ... 50+ lines of validation code ...

            # Call handler
            result = self.handlers[method](**params)

            # Format response
            return json.dumps({
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": result
            })

        except Exception as e:
            return self._error_response(request.get("id"), str(e))

    def _error_response(self, request_id, error_msg: str) -> str:
        """Format JSON-RPC error"""
        return json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": error_msg}
        })

    def generate_manifest(self) -> Dict:
        """Manually build manifest JSON"""
        return {
            "tools": [
                {
                    "name": "list_knowledge_bases",
                    "description": "...",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},  # Manual schema definition
                        "required": []
                    }
                },
                # ... more tools
            ]
        }

    def run_stdio(self):
        """Handle stdio communication loop"""
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            response = self.handle_request(line)
            sys.stdout.write(response + "\n")
            sys.stdout.flush()

# Register tools manually
server = MCPServer()
server.register_tool("list_knowledge_bases", list_knowledge_bases_handler, {
    "type": "object",
    "properties": {},
    # ... manual schema
})
# ... 200+ more lines
```

**Lines of code: ~1000+**

### FastMCP Implementation (Your New Approach)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Markdown Notes Search")

@mcp.tool()
def list_knowledge_bases() -> List[Dict[str, Any]]:
    """List all available knowledge bases."""
    collections = chromadb_client.list_collections()
    return [{"name": c.name, "description": c.metadata["description"], ...}]

@mcp.tool()
def search_knowledge_base(
    query: str,
    collection_name: str,
    context_mode: Literal["chunk_only", "enhanced", "full_note"] = "enhanced"
) -> List[Dict[str, Any]]:
    """Search a specific knowledge base."""
    # ... search logic
    return results

if __name__ == "__main__":
    mcp.run()
```

**Lines of code: ~300 (including business logic)**

### What FastMCP Handles Automatically

| Feature | Custom Implementation | FastMCP |
|---------|----------------------|---------|
| **JSON-RPC Protocol** | 200+ lines | ✅ Built-in |
| **Parameter Validation** | Manual type checking | ✅ From type hints |
| **Schema Generation** | Manual JSON schema | ✅ Automatic |
| **Error Formatting** | Custom error handlers | ✅ Standard format |
| **Stdio Communication** | Custom loop + buffering | ✅ Built-in |
| **Manifest Generation** | Manual JSON building | ✅ From decorators |
| **Type Safety** | Runtime checks only | ✅ Static + runtime |

## Real-World Usage Example

### How the AI Uses Your MCP Server

**Step 1: User asks a question**

```
User: "What did I write about Python async programming?"
```

**Step 2: AI discovers available collections**

```python
# AI calls:
list_knowledge_bases()

# Returns:
[
    {
        "name": "bear_notes_chunks",
        "description": "Personal notes from Bear app covering software development, productivity, and learning",
        "chunk_count": 1543
    },
    {
        "name": "wikipedia_history_chunks",
        "description": "Wikipedia articles on world history...",
        "chunk_count": 3201
    }
]
```

**Step 3: AI intelligently selects the right collection**

```python
# AI reasoning:
# "The user asked about 'what I wrote', so it's personal notes.
#  The description says bear_notes_chunks contains 'software development'.
#  This matches Python programming. I'll search there."

# AI calls:
search_knowledge_base(
    query="Python async programming",
    collection_name="bear_notes_chunks",  # ✅ Correct choice!
    context_mode="enhanced"
)
```

**Step 4: AI presents results**

```
AI: "I found your note titled 'Python Concurrency Patterns' from
     September 15th. You wrote about async/await syntax and
     compared it to threading..."
```

### Why This Works

The AI can select the right collection because:

1. **Rich descriptions** - Each collection has an AI-optimized description
2. **Semantic understanding** - The AI understands "what I wrote" = personal notes
3. **Clear tool contract** - FastMCP's automatic schema tells the AI exactly what parameters to send

## Addressing Your Specific Concerns

### Concern 1: "Will the AI be able to select the right collection?"

**Answer: Yes, when collections have good descriptions.**

From the PRD (Success Metric SM1):
> AI agent correctly selects the appropriate collection based on user query intent in 95% of test cases **when collections have well-crafted descriptions**

Example descriptions that work well:

```python
# ✅ Good: Clear, AI-optimized
"Personal notes from Bear app covering software development, productivity, and learning"

# ❌ Bad: Too vague
"My notes"

# ✅ Good: Specific domain
"Wikipedia articles on world history, major events from ancient civilizations to modern times"

# ❌ Bad: No context
"Wikipedia dump"
```

### Concern 2: "Manifest depends on database collections (weak point)"

**Answer: FastMCP eliminates this dependency.**

**Before (your concern):**
```json
{
  "tools": [
    {"name": "bear_notes_search", ...},      // ❌ Hardcoded collection
    {"name": "wiki_search", ...},             // ❌ Hardcoded collection
    {"name": "docs_search", ...}              // ❌ Hardcoded collection
  ]
}
```
*Problem: Adding a 4th collection requires manifest update*

**After (FastMCP approach):**
```json
{
  "tools": [
    {"name": "list_knowledge_bases", ...},     // ✅ Dynamic discovery
    {"name": "search_knowledge_base", ...}     // ✅ Takes collection_name param
  ]
}
```
*Solution: Manifest is stable, collections are discovered at runtime*

### Concern 3: "Different MCP instances = linking hardcoded info to dynamic source"

**Answer: Single MCP instance handles all collections.**

**Before (your concern):**
```json
{
  "mcpServers": {
    "bear-notes": {"command": "mcp-server", "args": ["--collection=bear"]},    // ❌ Hardcoded
    "wiki": {"command": "mcp-server", "args": ["--collection=wiki"]},           // ❌ Hardcoded
    "docs": {"command": "mcp-server", "args": ["--collection=docs"]}            // ❌ Hardcoded
  }
}
```

**After (FastMCP approach):**
```json
{
  "mcpServers": {
    "markdown-notes": {
      "command": "python",
      "args": ["server.py"]  // ✅ Single instance, discovers all collections
    }
  }
}
```

## Performance Considerations

### FastMCP Overhead

- **Minimal:** FastMCP adds ~5ms per request (negligible)
- **Trade-off:** 5ms overhead vs. 800+ lines of code saved

### Embedding Generation

- **Dominant cost:** Ollama embedding generation (~500-1000ms)
- **FastMCP impact:** <1% of total latency

### ChromaDB Queries

- **Chunk-only:** 1 query (~50-100ms)
- **Enhanced:** N+1 queries (~150-300ms for 3 results)
- **Full note:** N+1 queries (~200-500ms for 3 results)

## Migration Path

If you later need more control, FastMCP doesn't lock you in:

1. **Start with FastMCP** - Get working quickly (recommended for v1)
2. **Profile in production** - Identify actual bottlenecks
3. **Optimize hot paths** - Replace specific slow functions
4. **Keep FastMCP for protocol** - Only customize business logic if needed

Most projects never need to migrate away from FastMCP.

## Decision Summary

### Use FastMCP if:

- ✅ You want fast development (recommended for v1)
- ✅ You value maintainability over control
- ✅ You trust Anthropic's recommended approach
- ✅ You have <10k requests/hour (covers most use cases)

### Consider Custom Implementation if:

- ⚠️ You need extreme performance optimization (unusual)
- ⚠️ You have very specific protocol requirements (rare)
- ⚠️ You enjoy writing JSON-RPC handlers (masochist mode 😄)

## Recommendation

**Start with FastMCP for the following reasons:**

1. **Faster to market** - Working prototype in 1 day vs. 1 week
2. **Less maintenance** - Protocol updates handled by `mcp` package
3. **Better testing** - Focus tests on business logic, not protocol handling
4. **Proven approach** - Recommended by Anthropic, used in production
5. **Easy to extend** - Add new tools with just a decorator

You can always optimize later if profiling shows FastMCP is a bottleneck (unlikely).

## Next Steps

1. **Install FastMCP:**
   ```bash
   pip install mcp
   ```

2. **Test the server:**
   ```bash
   python test_server.py
   ```

3. **Add to Claude Desktop:**
   - Copy `claude_desktop_config.example.json` settings
   - Update paths to absolute paths
   - Restart Claude Desktop

4. **Try it out:**
   - "List my knowledge bases"
   - "Search my notes for Python async"

## References

- **PRD:** [prd-multi-collection-mcp-server.md](tasks/prd-multi-collection-mcp-server.md)
- **FastMCP Docs:** https://pypi.org/project/mcp/
- **Original Instructions:** [tasks/instructions.md](tasks/instructions.md)
