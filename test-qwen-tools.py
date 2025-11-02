#!/usr/bin/env python3
"""
Test script for Qwen 2.5 tool calling via LM Studio

Prerequisites:
1. Download and install LM Studio: https://lmstudio.ai
2. In LM Studio, search for and download: "Qwen2.5-7B-Instruct" (GGUF format)
3. Start the local server in LM Studio (Developer tab → Start Server on port 1234)
4. Run this script: python test-qwen-tools.py

This tests whether Qwen 2.5 can reliably:
- Call tools when appropriate
- Skip tools when not needed
- Parse arguments correctly
- Handle multiple tools
"""

from openai import OpenAI
import json
import sys

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def connect_to_lm_studio():
    """Connect to LM Studio's OpenAI-compatible API"""
    print(f"{BLUE}🔌 Connecting to LM Studio on http://localhost:1234{RESET}")

    client = OpenAI(
        base_url="http://localhost:1234/v1",
        api_key="lm-studio"  # LM Studio doesn't require a real key
    )

    try:
        # Test connection by listing models
        models = client.models.list()
        model_names = [model.id for model in models.data]

        if not model_names:
            print(f"{RED}❌ No models loaded in LM Studio!{RESET}")
            print(f"{YELLOW}   → Open LM Studio and load a model (e.g., Qwen2.5-7B-Instruct){RESET}")
            sys.exit(1)

        print(f"{GREEN}✓ Connected! Available models:{RESET}")
        for name in model_names:
            print(f"  - {name}")

        # Use the first model
        return client, model_names[0]

    except Exception as e:
        print(f"{RED}❌ Failed to connect to LM Studio:{RESET}")
        print(f"{YELLOW}   {str(e)}{RESET}")
        print(f"\n{YELLOW}Troubleshooting:{RESET}")
        print(f"  1. Is LM Studio running?")
        print(f"  2. Is the local server started? (Developer tab → Start Server)")
        print(f"  3. Is it running on port 1234?")
        sys.exit(1)


# Define Minerva-like tools for testing
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search through personal notes and knowledge bases using semantic search. Use this when the user asks about information in their notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query in natural language"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "The name of the knowledge base to search (e.g., 'bear_notes', 'wiki')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-15)",
                        "default": 5
                    }
                },
                "required": ["query", "collection_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_knowledge_bases",
            "description": "List all available knowledge bases (collections) in the system. Use this when the user wants to know what knowledge bases are available.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def test_query(client, model_name, query, expected_tool=None, description=""):
    """Test a single query and check if the expected tool is called"""
    print(f"\n{'='*70}")
    print(f"{BLUE}📝 Test: {description}{RESET}")
    print(f"Query: \"{query}\"")
    print(f"Expected: {expected_tool if expected_tool else 'No tool (direct response)'}")
    print(f"{'-'*70}")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant with access to the user's personal knowledge bases. Use the available tools when appropriate to search their notes."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            tools=TOOLS,
            temperature=0.1,  # Lower temperature for more predictable behavior
            max_tokens=500
        )

        message = response.choices[0].message

        # Check if tools were called
        if message.tool_calls:
            success = True
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = tool_call.function.arguments

                # Parse arguments
                try:
                    args_dict = json.loads(func_args)
                    args_str = json.dumps(args_dict, indent=2)
                except json.JSONDecodeError:
                    args_str = func_args
                    success = False

                # Check if correct tool was called
                if expected_tool and func_name == expected_tool:
                    print(f"{GREEN}✅ PASS: Correctly called '{func_name}'{RESET}")
                    print(f"{GREEN}   Arguments:{RESET}")
                    for line in args_str.split('\n'):
                        print(f"{GREEN}   {line}{RESET}")
                elif expected_tool and func_name != expected_tool:
                    print(f"{RED}❌ FAIL: Called '{func_name}' but expected '{expected_tool}'{RESET}")
                    print(f"   Arguments: {args_str}")
                    success = False
                else:
                    print(f"{YELLOW}⚠️  Called '{func_name}' (expected no tool){RESET}")
                    print(f"   Arguments: {args_str}")
                    success = False

            return success

        else:
            # No tool was called - direct response
            content = message.content or "(empty response)"

            if expected_tool:
                print(f"{RED}❌ FAIL: No tool called (expected '{expected_tool}'){RESET}")
                print(f"{RED}   Got direct response: {content[:100]}...{RESET}")
                return False
            else:
                print(f"{GREEN}✅ PASS: Direct response (no tool needed){RESET}")
                print(f"{GREEN}   Response: {content[:100]}...{RESET}")
                return True

    except Exception as e:
        print(f"{RED}❌ ERROR: {str(e)}{RESET}")
        return False


def main():
    print(f"\n{BLUE}{'='*70}")
    print(f"🧪 Qwen 2.5 Tool Calling Test Suite")
    print(f"{'='*70}{RESET}\n")

    # Connect to LM Studio
    client, model_name = connect_to_lm_studio()

    print(f"\n{BLUE}Using model: {model_name}{RESET}")
    print(f"{BLUE}Starting tests...{RESET}")

    # Define test cases
    test_cases = [
        # Should call search_knowledge_base
        {
            "query": "What are my notes about Python programming?",
            "expected_tool": "search_knowledge_base",
            "description": "Information-seeking query about notes"
        },
        {
            "query": "Show me everything I wrote about machine learning",
            "expected_tool": "search_knowledge_base",
            "description": "Request to search notes"
        },
        {
            "query": "Do I have any notes on Docker?",
            "expected_tool": "search_knowledge_base",
            "description": "Question about note existence"
        },

        # Should call list_knowledge_bases
        {
            "query": "What knowledge bases do you have access to?",
            "expected_tool": "list_knowledge_bases",
            "description": "Asking about available collections"
        },
        {
            "query": "List all my knowledge bases",
            "expected_tool": "list_knowledge_bases",
            "description": "Direct request to list collections"
        },

        # Should NOT call any tools
        {
            "query": "Hello! How are you today?",
            "expected_tool": None,
            "description": "Greeting (no tool needed)"
        },
        {
            "query": "Thanks for your help!",
            "expected_tool": None,
            "description": "Gratitude (no tool needed)"
        },
        {
            "query": "What is Python?",
            "expected_tool": None,
            "description": "General knowledge question (no personal notes needed)"
        },
    ]

    # Run tests
    results = []
    for test_case in test_cases:
        success = test_query(
            client,
            model_name,
            query=test_case["query"],
            expected_tool=test_case["expected_tool"],
            description=test_case["description"]
        )
        results.append(success)

    # Summary
    print(f"\n{BLUE}{'='*70}")
    print(f"📊 Test Results Summary")
    print(f"{'='*70}{RESET}")

    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"\nPassed: {passed}/{total} ({percentage:.1f}%)")

    if passed == total:
        print(f"{GREEN}✅ All tests passed! Qwen 2.5 handles tool calling reliably.{RESET}")
        print(f"{GREEN}   → Ready to integrate with Minerva chat!{RESET}")
    elif passed >= total * 0.7:
        print(f"{YELLOW}⚠️  Most tests passed. Qwen 2.5 is decent at tool calling.{RESET}")
        print(f"{YELLOW}   → May work with some fine-tuning of prompts/temperature{RESET}")
    else:
        print(f"{RED}❌ Many tests failed. Tool calling may not be reliable.{RESET}")
        print(f"{RED}   → Consider trying a different model or approach{RESET}")

    print(f"\n{BLUE}{'='*70}{RESET}\n")


if __name__ == "__main__":
    main()
