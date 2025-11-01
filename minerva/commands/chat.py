import sys
from argparse import Namespace
from pathlib import Path

from minerva.common.logger import get_logger
from minerva.common.ai_provider import AIProvider, ProviderUnavailableError, AIProviderError
from minerva.chat.config import load_chat_config, ChatConfigError
from minerva.chat.chat_engine import ChatEngine, ChatEngineError
from minerva.chat.history import list_conversations
from minerva.server.collection_discovery import list_collections, CollectionDiscoveryError

logger = get_logger(__name__, simple=True, mode="cli")

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


def display_welcome_banner(collections_count: int, provider_type: str, model_name: str):
    print("\n" + "=" * 60)
    print("  Minerva Chat - Interactive Knowledge Assistant")
    print("=" * 60)
    print(f"\n📚 Knowledge Bases: {collections_count} available")
    print(f"🤖 AI Provider: {provider_type} ({model_name})")
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
        config = load_chat_config(str(args.config))
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
        config = load_chat_config(config_path)
    except ChatConfigError as e:
        logger.error("Configuration Error")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)
        return None, None, None

    try:
        collections = list_collections(config.chromadb_path)
        collections_count = len(collections)
    except CollectionDiscoveryError as e:
        logger.error("ChromaDB Connection Error")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)
        return None, None, None

    try:
        provider = AIProvider(config.ai_provider)

        availability = provider.check_availability()
        if not availability['available']:
            error_msg = availability.get('error', 'Unknown error')
            logger.error("AI Provider Unavailable")
            logger.error("=" * 60)
            logger.error(f"Provider: {config.ai_provider.provider_type}")
            logger.error(f"Error: {error_msg}")
            logger.error("=" * 60)
            logger.error("\nTroubleshooting:")
            logger.error("  1. For Ollama: ensure 'ollama serve' is running")
            logger.error("  2. For cloud providers: check API key is set correctly")
            logger.error("  3. Verify network connectivity")
            logger.error("  4. Check provider base URL is correct")
            return None, None, None

    except (ProviderUnavailableError, AIProviderError) as e:
        logger.error("AI Provider Error")
        logger.error("=" * 60)
        logger.error(str(e))
        logger.error("=" * 60)
        return None, None, None

    return config, provider, collections_count


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


def run_interactive_mode(config, provider, collections_count: int, resume_id: str = None, custom_system_prompt: str = None) -> int:
    engine = ChatEngine()

    system_prompt = custom_system_prompt or DEFAULT_SYSTEM_PROMPT

    try:
        if resume_id:
            print(f"\n🔄 Resuming conversation: {resume_id}\n")
            engine.resume_conversation(resume_id, provider, config)
            print(f"💬 Conversation resumed. You have {engine.get_message_count()} messages in history.\n")
        else:
            display_welcome_banner(
                collections_count,
                config.ai_provider.provider_type,
                config.ai_provider.llm_model
            )

            conversation_id = engine.initialize_conversation(
                system_prompt=system_prompt,
                ai_provider=provider,
                config=config
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
    custom_system_prompt = args.system if hasattr(args, 'system') and args.system else None

    return run_interactive_mode(config, provider, collections_count, resume_id, custom_system_prompt)
