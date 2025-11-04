import json
import signal
from pathlib import Path
from typing import Optional, Dict, Any

from minerva.common.ai_provider import AIProvider, AIProviderError, ProviderUnavailableError
from minerva.common.exceptions import ChatEngineError
from minerva.common.logger import get_logger
from minerva.chat.config import ChatConfig
from minerva.chat.history import ConversationHistory
from minerva.chat.mcp_client import MCPClient, MCPConnectionError, MCPToolExecutionError
from minerva.chat.context_window import (
    check_context_window,
    format_context_warning,
    get_user_choice,
    create_summary_messages,
    replace_with_summary,
    calculate_conversation_tokens
)

logger = get_logger(__name__)

class ChatEngine:
    def __init__(self):
        self.config: Optional[ChatConfig] = None
        self.provider: Optional[AIProvider] = None
        self.history: Optional[ConversationHistory] = None
        self.mcp_client: Optional[MCPClient] = None
        self.running = False
        self._original_sigint_handler = None
        self._mcp_available = False
        self._streaming_enabled = True
        self._streaming_fallback_triggered = False

    def connect_mcp_or_fail(self, mcp_server_url: str):
        self.mcp_client = MCPClient(mcp_server_url)
        self._mcp_available = self.mcp_client.check_connection_sync()
        if not self._mcp_available:
            raise ChatEngineError(
                f"MCP server is unavailable at {mcp_server_url}\n"
                f"  Chat requires MCP server (HTTP mode) to access knowledge bases.\n"
                f"  Please start the MCP server with:\n"
                f"    minerva serve-http --config configs/server/local.json"
            )

        logger.info(f"MCP server connected at {mcp_server_url}")

    def initialize_conversation(
        self,
        system_prompt: str,
        ai_provider: AIProvider,
        config: ChatConfig
    ) -> str:
        self.config = config
        self.provider = ai_provider
        self._streaming_enabled = config.enable_streaming

        self.connect_mcp_or_fail(config.mcp_server_url)

        self.history = ConversationHistory(
            conversation_dir=Path(config.conversation_dir),
            auto_save=True
        )

        conversation_id = self.history.start_new_conversation(system_prompt)

        self.running = True
        self._setup_signal_handler()

        logger.info(f"Initialized conversation {conversation_id}")
        return conversation_id

    def _setup_signal_handler(self):
        self._original_sigint_handler = signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        logger.info("Received interrupt signal, saving conversation...")
        self.running = False

        if self.history and self.history.current_conversation:
            self.history.save()
            print("\n\n💾 Conversation saved. Goodbye!")

        if self._original_sigint_handler:
            signal.signal(signal.SIGINT, self._original_sigint_handler)

        raise KeyboardInterrupt()

    def _check_and_handle_context_window(self):
        if not self.history or not self.provider or not self.config:
            return

        messages = self.history.get_messages()
        model_name = self.config.ai_provider.llm_model

        current_tokens, max_tokens, usage_ratio, should_warn = check_context_window(messages, model_name)

        if should_warn:
            warning_message = format_context_warning(current_tokens, max_tokens, usage_ratio)
            print(warning_message)

            choice = get_user_choice()

            if choice == 'c':
                logger.info("User chose to continue despite context warning")
                return
            elif choice == 's':
                logger.info("User chose to summarize conversation")
                self._summarize_conversation()
            elif choice == 'n':
                logger.info("User chose to start new conversation")
                raise KeyboardInterrupt()

    def _summarize_conversation(self):
        if not self.history or not self.provider:
            return

        messages = self.history.get_messages()

        system_message = messages[0] if messages and messages[0].get('role') == 'system' else None
        messages_to_summarize = messages[1:] if system_message else messages

        if len(messages_to_summarize) <= 6:
            logger.warning("Too few messages to summarize")
            print("\n⚠️  Not enough messages to summarize. Continuing...")
            return

        print("\n🔄 Generating conversation summary...")

        summary_request = create_summary_messages(system_message, messages_to_summarize[:-6])

        try:
            response = self.provider.chat_completion(
                messages=summary_request,
                temperature=0.5,
                stream=False
            )

            summary_text = response.get('content', 'Unable to generate summary.')

            new_messages = replace_with_summary(messages, summary_text, keep_recent_count=6)

            self.history.current_conversation['messages'] = new_messages

            self.history.save()

            logger.info(f"Conversation summarized: {len(messages)} -> {len(new_messages)} messages")
            print(f"✓ Conversation compressed: {len(messages)} -> {len(new_messages)} messages\n")

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            print(f"\n❌ Failed to generate summary: {e}")
            print("Continuing with full conversation...\n")

    def send_message(self, user_message: str) -> str:
        if not self.history or not self.provider or not self.config:
            raise ChatEngineError("Chat engine not initialized. Call initialize_conversation() first.")

        self.history.add_message(role='user', content=user_message)

        self._check_and_handle_context_window()

        messages = self._prepare_messages_for_api()

        full_response = self._execute_conversation_loop(messages)

        return full_response

    def _prepare_messages_for_api(self) -> list[Dict[str, Any]]:
        messages = []

        for msg in self.history.get_messages():
            role = msg['role']
            content = msg['content']

            api_message = {'role': role, 'content': content}

            if 'tool_calls' in msg:
                api_message['tool_calls'] = msg['tool_calls']

            if role == 'tool':
                api_message['tool_call_id'] = msg.get('tool_call_id')
                api_message['name'] = msg.get('name')

            messages.append(api_message)

        return messages

    def _execute_conversation_loop(self, messages: list[Dict[str, Any]]) -> str:
        if not self.config:
            raise ChatEngineError("Chat engine not initialized")

        max_iterations = self.config.max_tool_iterations
        iteration = 0
        full_response = ""

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Conversation iteration {iteration}/{max_iterations}")

            tool_definitions = self._get_tool_definitions()

            try:
                if self._streaming_enabled:
                    response_content, tool_calls = self._get_streaming_response(messages, tool_definitions)
                else:
                    response_content, tool_calls = self._get_standard_response(messages, tool_definitions)

                if response_content:
                    full_response = response_content

                if not tool_calls:
                    if response_content:
                        self.history.add_message(role='assistant', content=response_content)
                    break

                logger.info(f"Assistant requested {len(tool_calls)} tool call(s)")
                self.history.add_message(role='assistant', content=response_content or "", tool_calls=tool_calls)
                messages.append({
                    'role': 'assistant',
                    'content': response_content or "",
                    'tool_calls': tool_calls
                })

                self._execute_tool_calls(tool_calls, messages)

            except (AIProviderError, ProviderUnavailableError) as e:
                error_message = f"AI provider error: {e}"
                logger.error(error_message)
                print(f"\n❌ {error_message}")
                raise ChatEngineError(error_message) from e
            except (MCPConnectionError, MCPToolExecutionError) as e:
                error_message = f"MCP error: {e}"
                logger.error(error_message)
                print(f"\n❌ {error_message}")
                raise ChatEngineError(error_message) from e

        if iteration >= max_iterations:
            # User-facing message already printed below
            print(f"\n⚠️  Maximum tool execution iterations reached ({max_iterations}).")

        self._update_conversation_metadata()

        return full_response

    def _get_standard_response(
        self,
        messages: list[Dict[str, Any]],
        tool_definitions: list[Dict]
    ) -> tuple[str, Optional[list[Dict]]]:
        response = self.provider.chat_completion(
            messages=messages,
            tools=tool_definitions,
            temperature=0.7,
            stream=False
        )

        content = response.get('content') or ""
        tool_calls = response.get('tool_calls')

        if content:
            print(f"\n{content}")

        return content, tool_calls

    def _get_streaming_response(
        self,
        messages: list[Dict[str, Any]],
        tool_definitions: list[Dict]
    ) -> tuple[str, Optional[list[Dict]]]:
        try:
            accumulated_content = []
            final_tool_calls = None

            print()

            for chunk in self.provider.chat_completion_streaming(
                messages=messages,
                tools=tool_definitions,
                temperature=0.7
            ):
                if 'content' in chunk:
                    content = chunk['content']
                    accumulated_content.append(content)
                    print(content, end='', flush=True)

                if 'finish_reason' in chunk:
                    if 'full_tool_calls' in chunk:
                        final_tool_calls = chunk['full_tool_calls']
                    break

            print()

            full_content = ''.join(accumulated_content)
            return full_content, final_tool_calls

        except Exception as e:
            if not self._streaming_fallback_triggered:
                logger.warning(f"Streaming failed: {e}")
                print("\n")
                print("⚠️  Streaming mode is incompatible with this provider/model.")
                print("    Falling back to non-streaming mode for this session.")
                print()
                self._streaming_enabled = False
                self._streaming_fallback_triggered = True

            logger.info("Retrying with non-streaming mode")
            return self._get_standard_response(messages, tool_definitions)

    def _get_tool_definitions(self) -> list[Dict]:
        if not self._mcp_available or not self.mcp_client:
            logger.warning("MCP not available, returning empty tool list")
            return []

        try:
            mcp_tools = self.mcp_client.get_tool_definitions_sync()
            tool_definitions = [tool.to_openai_format() for tool in mcp_tools]
            logger.info(f"Fetched {len(tool_definitions)} tool definitions from MCP")
            return tool_definitions
        except MCPConnectionError as e:
            logger.error(f"Failed to fetch tool definitions: {e}")
            return []

    def _execute_tool_calls(self, tool_calls: list[Dict], messages: list[Dict[str, Any]]):
        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id')
            function_info = tool_call.get('function', {})
            tool_name = function_info.get('name')
            arguments_str = function_info.get('arguments', '{}')

            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool arguments: {arguments_str}")
                arguments = {}

            print(f"🔍 {self._format_tool_execution_message(tool_name, arguments)}")

            if not self._mcp_available or not self.mcp_client:
                error_result = "❌ MCP server unavailable - cannot execute tools"
                logger.error(error_result)
                self.history.add_tool_result(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    result=error_result
                )
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call_id,
                    'name': tool_name,
                    'content': error_result
                })
                continue

            try:
                logger.info(f"Executing MCP tool: {tool_name} with arguments: {arguments}")
                result = self.mcp_client.call_tool_sync(tool_name, arguments)
                formatted_result = self._format_mcp_result(tool_name, result)

                logger.info(f"Tool {tool_name} completed successfully")

                self.history.add_tool_result(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    result=formatted_result
                )

                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call_id,
                    'name': tool_name,
                    'content': formatted_result
                })

            except MCPToolExecutionError as e:
                error_result = f"❌ Tool execution failed: {e}"
                logger.error(error_result)
                self.history.add_tool_result(
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    result=error_result
                )
                messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call_id,
                    'name': tool_name,
                    'content': error_result
                })

    def _format_mcp_result(self, tool_name: str, result: Any) -> str:
        if isinstance(result, list):
            return json.dumps(result, ensure_ascii=False)
        elif isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        elif isinstance(result, str):
            return result
        else:
            return str(result)

    def _format_tool_execution_message(self, tool_name: str, arguments: Dict) -> str:
        if tool_name == 'list_knowledge_bases':
            return "Listing available knowledge bases..."
        elif tool_name == 'search_knowledge_base':
            collection = arguments.get('collection_name', 'unknown')
            query = arguments.get('query', '')
            max_results = arguments.get('max_results', 3)
            return f"Searching '{collection}' for: '{query}' (max {max_results} results)..."
        else:
            return f"Executing {tool_name}..."

    def _update_conversation_metadata(self):
        messages = self.history.get_messages()
        message_count = len(messages)

        self.history.update_metadata(
            message_count=message_count,
            total_tokens=self._estimate_total_tokens(messages)
        )

    def _estimate_total_tokens(self, messages: list[Dict]) -> int:
        return calculate_conversation_tokens(messages)

    def resume_conversation(self, conversation_id: str, ai_provider: AIProvider, config: ChatConfig):
        self.config = config
        self.provider = ai_provider
        self._streaming_enabled = config.enable_streaming

        self.connect_mcp_or_fail(config.mcp_server_url)

        self.history = ConversationHistory(
            conversation_dir=Path(config.conversation_dir),
            auto_save=True
        )

        self.history.resume_conversation(conversation_id)

        self.running = True
        self._setup_signal_handler()

        logger.info(f"Resumed conversation {conversation_id}")

    def get_conversation_id(self) -> Optional[str]:
        if self.history:
            return self.history.conversation_id
        return None

    def get_message_count(self) -> int:
        if self.history:
            return len(self.history.get_messages())
        return 0

    def clear_conversation(self, system_prompt: str) -> str:
        if not self.provider or not self.config:
            raise ChatEngineError("Chat engine not initialized")

        return self.initialize_conversation(system_prompt, self.provider, self.config)
