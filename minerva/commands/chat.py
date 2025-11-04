from argparse import Namespace
from pathlib import Path
import logging

from minerva.common.logger import get_logger
from minerva.common.ai_provider import AIProvider, ProviderUnavailableError, AIProviderError
from minerva.chat.config import ChatConfig, ChatConfigError, load_chat_config_from_file
from minerva.chat.chat_engine import ChatEngine, ChatEngineError
from minerva.chat.history import list_conversations
from minerva.chat.mcp_client import MCPClient, MCPConnectionError

logger = get_logger(__name__, simple=True, mode="cli")

# Suppress INFO logs from chat and AI provider modules to keep conversation clean
logging.getLogger('minerva.chat.chat_engine').setLevel(logging.WARNING)
logging.getLogger('minerva.chat.history').setLevel(logging.WARNING)
logging.getLogger('minerva.chat.mcp_client').setLevel(logging.WARNING)
logging.getLogger('minerva.chat.context_window').setLevel(logging.WARNING)
logging.getLogger('minerva.common.ai_provider').setLevel(logging.WARNING)

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to a user's personal knowledge bases.

Your capabilities:
- Search through the user's indexed notes and knowledge bases
- Answer questions based on their personal knowledge
- Provide relevant information from their collections

When searching:
- Always call list_knowledge_bases first to see what's available
- Use search_knowledge_base to find relevant information
- Cite sources by mentioning note titles when referencing information
- If you can't find relevant information, say so clearly

Be concise, helpful, and accurate."""


def display_welcome_banner(
    collections_count: int,
    provider_type: str,
    model_name: str,
    mcp_connected: bool,
    mcp_url: str,
    streaming_enabled: bool
):
    print("\n" + "=" * 60)
    print("  Minerva Chat - Interactive Knowledge Assistant")
    print("=" * 60)

    print(f"\n🤖 AI Provider: {provider_type} ({model_name})")

    mcp_status = "✓ Connected" if mcp_connected else "✗ Disconnected"
    mcp_icon = "🔗" if mcp_connected else "⚠️"
    print(f"{mcp_icon} MCP Server: {mcp_status} ({mcp_url})")

    print(f"📚 Knowledge Bases: {collections_count} available")

    streaming_status = "enabled" if streaming_enabled else "disabled"
    print(f"⚡ Streaming: {streaming_status}")

    print("\nCommands:")
    print("  /help   - Show this help message")
    print("  /clear  - Start a new conversation")
    print("  /exit   - Exit the chat")
    print("  exit    - Exit the chat")
    print("  quit    - Exit the chat")
    print("\nType your question or command to begin.\n")


def display_help():
    print("\n📖 Available Commands:")
    print("  /help   - Show this help message")
    print("  /clear  - Start a new conversation (saves current)")
    print("  /exit   - Exit the chat (saves conversation)")
    print("  exit    - Exit the chat (saves conversation)")
    print("  quit    - Exit the chat (saves conversation)")
    print("\n💡 Tips:")
    print("  - Ask questions about your knowledge bases")
    print("  - Use Ctrl+C or Ctrl+D to exit")
    print("  - All conversations are automatically saved")
    print()


def list_past_conversations(args: Namespace) -> int:
    try:
        config = load_chat_config_from_file(str(args.config))
    except ChatConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    conversations = list_conversations(Path(config.conversation_dir))

    if not conversations:
        print("\n📭 No previous conversations found.")
        print(f"   Conversations are saved in: {config.conversation_dir}\n")
        return 0

    print(f"\n📚 Found {len(conversations)} conversation(s):\n")
    print("=" * 80)

    for conv in conversations:
        conv_id = conv.get('conversation_id', 'unknown')
        title = conv.get('title', 'Untitled')
        message_count = conv.get('message_count', 0)
        created_at = conv.get('created_at', 'Unknown')
        last_modified = conv.get('last_modified', 'Unknown')

        print(f"\nID: {conv_id}")
        print(f"   Title: {title}")
        print(f"   Messages: {message_count}")
        print(f"   Created: {created_at}")
        print(f"   Last Modified: {last_modified}")

    print("\n" + "=" * 80)
    print("\nTo resume a conversation, use:")
    print("  minerva chat --config <config> --resume <conversation_id>\n")

    return 0


def initialize_chat_system(config_path: str) -> tuple:
    try:
        config = load_chat_config_from_file(config_path)
    except ChatConfigError as e:
        logger.error("Configuration Error")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)
        return None, None, None

    # Query MCP server for available collections
    try:
        mcp_client = MCPClient(config.mcp_server_url)
        collections = mcp_client.call_tool_sync("list_knowledge_bases", {})
        collections_count = len(collections) if isinstance(collections, list) else 0
        logger.info(f"MCP server connection successful: {collections_count} collections available")
    except MCPConnectionError as e:
        logger.error("MCP Server Connection Error")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)
        logger.error("\nTroubleshooting:")
        logger.error("  1. Ensure the MCP server is running: minerva serve --config <server-config>")
        logger.error(f"  2. Check the MCP server URL is correct: {config.mcp_server_url}")
        logger.error("  3. Verify network connectivity to the MCP server")
        return None, None, None
    except Exception as e:
        logger.error("MCP Server Error")
        logger.error("=" * 60)
        logger.error(f"Failed to query MCP server: {e}")
        logger.error("=" * 60)
        return None, None, None

    try:
        llm_provider = AIProvider(config.llm_provider)

        availability = llm_provider.check_availability()
        if not availability['available']:
            error_msg = availability.get('error', 'Unknown error')
            logger.error("LLM Provider Unavailable")
            logger.error("=" * 60)
            logger.error(f"Provider: {config.llm_provider.provider_type}")
            logger.error(f"Model: {config.llm_provider.llm_model}")
            logger.error(f"Error: {error_msg}")
            logger.error("=" * 60)
            logger.error("\nTroubleshooting:")
            logger.error("  1. For Ollama: ensure 'ollama serve' is running")
            logger.error("  2. For cloud providers: check API key is set correctly")
            logger.error("  3. Verify network connectivity")
            logger.error("  4. Check provider base URL is correct")
            return None, None, None

    except (ProviderUnavailableError, AIProviderError) as e:
        logger.error("LLM Provider Error")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)
        return None, None, None

    return config, llm_provider, collections_count


def run_single_question_mode(config, provider, question: str) -> int:
    engine = ChatEngine()

    try:
        engine.initialize_conversation(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            ai_provider=provider,
            config=config
        )

        print(f"\n💬 Question: {question}\n")
        print("🤖 Response:")
        print("-" * 60)

        engine.send_message(question)

        print("-" * 60)
        print()

        return 0

    except ChatEngineError as e:
        logger.error(f"Chat engine error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


def run_interactive_mode(config, provider, collections_count: int, resume_id: str = None) -> int:
    engine = ChatEngine()

    # Load system prompt from config file or use default
    system_prompt = DEFAULT_SYSTEM_PROMPT
    if config.system_prompt_file:
        try:
            prompt_path = Path(config.system_prompt_file)
            if not prompt_path.is_absolute():
                # Resolve relative paths against config file location
                if config.source_path:
                    prompt_path = config.source_path.parent / prompt_path

            if prompt_path.exists():
                system_prompt = prompt_path.read_text().strip()
                logger.info(f"Loaded system prompt from {prompt_path}")
            else:
                logger.warning(f"System prompt file not found: {prompt_path}, using default")
        except Exception as e:
            logger.warning(f"Failed to load system prompt: {e}, using default")

    try:
        if resume_id:
            print(f"\n🔄 Resuming conversation: {resume_id}\n")
            engine.resume_conversation(resume_id, provider, config)
            print(f"💬 Conversation resumed. You have {engine.get_message_count()} messages in history.")

            mcp_status = "✓ Connected" if engine._mcp_available else "✗ Disconnected"
            mcp_icon = "🔗" if engine._mcp_available else "⚠️"
            print(f"{mcp_icon} MCP Server: {mcp_status} ({config.mcp_server_url})")
            print()
        else:
            conversation_id = engine.initialize_conversation(
                system_prompt=system_prompt,
                ai_provider=provider,
                config=config
            )

            display_welcome_banner(
                collections_count,
                config.llm_provider.provider_type,
                config.llm_provider.llm_model,
                engine._mcp_available,
                config.mcp_server_url,
                config.enable_streaming
            )

            logger.info(f"Conversation started: {conversation_id}")

        while engine.running:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 Goodbye! Conversation saved.\n")
                    break

                if user_input == '/exit':
                    print("\n👋 Goodbye! Conversation saved.\n")
                    break

                if user_input == '/help':
                    display_help()
                    continue

                if user_input == '/clear':
                    print("\n🔄 Starting new conversation...\n")
                    conversation_id = engine.clear_conversation(system_prompt)
                    logger.info(f"New conversation started: {conversation_id}")
                    print("✨ New conversation started.\n")
                    continue

                print()
                print("🤖 Assistant:")
                print("-" * 60)

                engine.send_message(user_input)

                print("-" * 60)
                print()

            except EOFError:
                print("\n\n👋 Goodbye! Conversation saved.\n")
                break

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user. Conversation saved.\n")
                break

        return 0

    except ChatEngineError as e:
        logger.error(f"Chat engine error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


def run_chat(args: Namespace) -> int:
    if args.list:
        return list_past_conversations(args)

    config_path = str(args.config)
    config, provider, collections_count = initialize_chat_system(config_path)

    if not config or not provider:
        return 1

    if args.question:
        return run_single_question_mode(config, provider, args.question)

    resume_id = args.resume if hasattr(args, 'resume') and args.resume else None

    return run_interactive_mode(config, provider, collections_count, resume_id)
