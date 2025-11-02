#!/usr/bin/env python3
"""
Prototype: Minerva Chat with Qwen 2.5 + MCP Server

This is a throw-away prototype to test the architecture:
  Qwen 2.5 (LM Studio) → decides tools → calls Minerva MCP server

Prerequisites:
1. LM Studio running with Qwen2.5-7B-Instruct on port 1234
2. Minerva MCP server running: minerva serve-http --config server-config.json --port 8000

Usage:
  python test-qwen-mcp-chat.py

Test it with queries like:
  - "What knowledge bases are available?"
  - "What are my notes about Python?"
  - "Hello, how are you?"
"""

from openai import OpenAI
from fastmcp import Client as FastMCPClient
import asyncio
import json
import sys
from typing import Optional

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


class MCPClient:
    """MCP client wrapper using FastMCP for calling Minerva server"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.client = FastMCPClient(self.mcp_endpoint)

    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a tool on the MCP server"""
        async with self.client:
            result = await self.client.call_tool(tool_name, arguments)

            # Debug: inspect the raw result
            print(f"[DEBUG] Raw result type: {type(result)}")
            print(f"[DEBUG] Result attributes: {dir(result)}")

            # FastMCP returns a ToolResult object - extract the actual data
            if hasattr(result, 'content'):
                # result.content is a list of ContentItem objects
                content_items = result.content
                print(f"[DEBUG] Content items count: {len(content_items)}")

                if content_items and len(content_items) > 0:
                    # Parse ALL content items (MCP returns one per array element)
                    all_results = []

                    for idx, item in enumerate(content_items):
                        if hasattr(item, 'text'):
                            text = item.text
                            try:
                                # Each content item is a JSON object
                                parsed = json.loads(text)
                                all_results.append(parsed)
                            except Exception as e:
                                print(f"[DEBUG] Failed to parse content item {idx}: {e}")

                    print(f"[DEBUG] Parsed {len(all_results)} items total")

                    # Return as array if multiple items, single item if just one
                    if len(all_results) > 1:
                        return all_results
                    elif len(all_results) == 1:
                        # Check if it's already a list
                        if isinstance(all_results[0], list):
                            return all_results[0]
                        return all_results[0]
                    else:
                        return {"error": "No content items could be parsed"}

            # Fallback: try to convert to dict
            if hasattr(result, 'data'):
                data = result.data
                print(f"[DEBUG] Using result.data: {type(data)}")
                # Convert to JSON-serializable format
                return json.loads(json.dumps(data, default=str))

            return result

    async def test_connection(self) -> bool:
        """Test if MCP server is accessible"""
        try:
            async with self.client:
                # Try to list tools to verify connection
                tools = await self.client.list_tools()
                return True
        except Exception as e:
            print(f"{RED}❌ Cannot connect to MCP server: {e}{RESET}")
            return False


# Tool definitions matching Minerva MCP server
MINERVA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_knowledge_bases",
            "description": "List all available knowledge bases (collections) in the system. Returns collection names, descriptions, and chunk counts.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Perform semantic search across a knowledge base. Use this to find relevant information from the user's notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "The name of the knowledge base to search"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-15, default: 5)",
                        "default": 5
                    },
                    "context_mode": {
                        "type": "string",
                        "description": "Context retrieval mode",
                        "enum": ["chunk_only", "enhanced", "full_note"],
                        "default": "enhanced"
                    }
                },
                "required": ["query", "collection_name"]
            }
        }
    }
]


class QwenMCPChat:
    """Chat engine using Qwen 2.5 for orchestration and Minerva MCP for search"""

    def __init__(self, llm_client: OpenAI, mcp_client: MCPClient, model_name: str):
        self.llm_client = llm_client
        self.mcp_client = mcp_client
        self.model_name = model_name
        self.conversation_history = []
        self.system_prompt = """You are a helpful AI assistant with access to the user's personal knowledge bases.

Your capabilities:
- Search through the user's indexed notes and knowledge bases
- Answer questions based on their personal knowledge
- Provide relevant information from their collections

IMPORTANT - When using tools:
- When you receive a list of results, ALWAYS process and mention ALL items in the list
- Don't just focus on the first item - users need to see all available options
- Count the items and verify you're describing all of them
- When listing knowledge bases, show ALL collections, not just the first one

When searching:
- First call list_knowledge_bases to see what's available
- Use search_knowledge_base to find relevant information
- Cite sources by mentioning note titles when referencing information
- If you can't find relevant information, say so clearly

Be concise, helpful, and accurate."""

    async def send_message(self, user_message: str) -> str:
        """Send a message and handle tool calls via MCP"""
        # TEMPORARY: Disable history - start fresh each query
        # self.conversation_history.append({
        #     "role": "user",
        #     "content": user_message
        # })

        # Prepare messages for API (include system prompt, NO history)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        # messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history

        # Main conversation loop (max 5 iterations to prevent infinite loops)
        max_iterations = 5
        final_response = None

        for iteration in range(max_iterations):
            print(f"{CYAN}[Iteration {iteration + 1}]{RESET}")

            # Call Qwen to decide what to do
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=MINERVA_TOOLS,
                temperature=0.3,
                max_tokens=1000
            )

            message = response.choices[0].message

            # Check if tools were called
            if message.tool_calls:
                # TEMPORARY: Disabled history
                # self.conversation_history.append({
                #     "role": "assistant",
                #     "content": message.content or "",
                #     "tool_calls": [
                #         {
                #             "id": tc.id,
                #             "type": "function",
                #             "function": {
                #                 "name": tc.function.name,
                #                 "arguments": tc.function.arguments
                #             }
                #         } for tc in message.tool_calls
                #     ]
                # })

                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]
                })

                # Execute each tool call via MCP
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args_str = tool_call.function.arguments

                    try:
                        func_args = json.loads(func_args_str)
                    except json.JSONDecodeError:
                        func_args = {}

                    print(f"{YELLOW}🔍 Calling MCP tool: {func_name}({json.dumps(func_args, indent=2)}){RESET}")

                    # Call Minerva MCP server
                    try:
                        result = await self.mcp_client.call_tool(func_name, func_args)

                        # Debug: show what we got
                        print(f"{CYAN}[DEBUG] Result type: {type(result)}{RESET}")

                        # Convert to JSON string for LLM
                        try:
                            result_str = json.dumps(result, indent=2)
                            print(f"{GREEN}✓ Tool result received ({len(result_str)} chars){RESET}")

                            # Show first 500 chars of response for debugging
                            print(f"{CYAN}[DEBUG] Response preview:{RESET}")
                            preview = result_str[:500] + "..." if len(result_str) > 500 else result_str
                            print(f"{CYAN}{preview}{RESET}")
                        except TypeError as te:
                            # If still not serializable, force convert
                            result_str = str(result)
                            print(f"{YELLOW}⚠ Result converted to string ({len(result_str)} chars){RESET}")

                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                        print(f"{RED}✗ Tool call failed: {e}{RESET}")

                    # Add tool result to messages (but not persistent history)
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str
                    }

                    # TEMPORARY: Disabled history
                    # self.conversation_history.append(tool_message)
                    messages.append(tool_message)

                # Continue loop to get final response
                continue

            else:
                # No tools called - we have a final response
                final_response = message.content or ""
                # TEMPORARY: Disabled history
                # self.conversation_history.append({
                #     "role": "assistant",
                #     "content": final_response
                # })
                break

        if final_response is None:
            final_response = "I apologize, but I couldn't complete the request after several attempts."

        return final_response


async def main():
    print(f"\n{BLUE}{'='*70}")
    print(f"🧪 Qwen 2.5 + Minerva MCP Chat Prototype")
    print(f"{'='*70}{RESET}\n")

    # Step 1: Connect to LM Studio
    print(f"{BLUE}🔌 Connecting to LM Studio...{RESET}")
    llm_client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio"
    )

    try:
        models = llm_client.models.list()
        model_names = [m.id for m in models.data]
        if not model_names:
            print(f"{RED}❌ No models loaded in LM Studio{RESET}")
            sys.exit(1)
        model_name = model_names[0]
        print(f"{GREEN}✓ Connected to LM Studio (model: {model_name}){RESET}")
    except Exception as e:
        print(f"{RED}❌ Failed to connect to LM Studio: {e}{RESET}")
        print(f"{YELLOW}   Make sure LM Studio is running with server started on port 1234{RESET}")
        sys.exit(1)

    # Step 2: Connect to Minerva MCP server
    print(f"\n{BLUE}🔌 Connecting to Minerva MCP server...{RESET}")
    mcp_client = MCPClient("http://localhost:8000")

    if not await mcp_client.test_connection():
        print(f"{RED}❌ Minerva MCP server not accessible{RESET}")
        print(f"{YELLOW}   Start it with: minerva serve-http --config server-config.json --port 8000{RESET}")
        sys.exit(1)

    print(f"{GREEN}✓ Connected to Minerva MCP server{RESET}")

    # Step 3: Start chat loop
    print(f"\n{BLUE}{'='*70}")
    print(f"💬 Chat Session Started")
    print(f"{'='*70}{RESET}")
    print(f"\nCommands:")
    print(f"  exit, quit - Exit the chat")
    print(f"  /clear     - Clear conversation history\n")

    chat = QwenMCPChat(llm_client, mcp_client, model_name)

    while True:
        try:
            user_input = input(f"{CYAN}You: {RESET}").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit']:
                print(f"\n{GREEN}👋 Goodbye!{RESET}\n")
                break

            if user_input == '/clear':
                chat.conversation_history = []
                print(f"{GREEN}✓ Conversation history cleared{RESET}")
                continue

            if user_input == '/debug':
                print(f"\n{CYAN}=== Debug Info ==={RESET}")
                print(f"History length: {len(chat.conversation_history)} messages")
                total_chars = sum(len(str(msg)) for msg in chat.conversation_history)
                print(f"Total history size: {total_chars:,} chars")
                print(f"{CYAN}================={RESET}\n")
                continue

            print()
            response = await chat.send_message(user_input)
            print(f"\n{GREEN}🤖 Assistant:{RESET} {response}\n")

        except KeyboardInterrupt:
            print(f"\n\n{YELLOW}⚠️  Interrupted{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}❌ Error: {e}{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
