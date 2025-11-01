import json
import signal
from pathlib import Path
from typing import Optional, Dict, Any

from minerva.common.ai_provider import AIProvider, AIProviderError, ProviderUnavailableError
from minerva.common.exceptions import ChatEngineError
from minerva.common.logger import get_logger
from minerva.chat.config import ChatConfig
from minerva.chat.history import ConversationHistory
from minerva.chat.tools import get_tool_definitions, execute_tool, format_tool_result
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
        self.running = False
        self._original_sigint_handler = None

    def initialize_conversation(
        self,
        system_prompt: str,
        ai_provider: AIProvider,
        config: ChatConfig
    ) -> str:
        self.config = config
        self.provider = ai_provider

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
        max_iterations = 10
        iteration = 0
        full_response = ""

        while iteration < max_iterations:
            iteration += 1

            tool_definitions = get_tool_definitions()

            try:
                if self.config.enable_streaming:
                    response_content, tool_calls = self._get_streaming_response(messages, tool_definitions)
                else:
                    response_content, tool_calls = self._get_standard_response(messages, tool_definitions)

                if response_content:
                    full_response = response_content

                if not tool_calls:
                    if response_content:
                        self.history.add_message(role='assistant', content=response_content)
                    break

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

        if iteration >= max_iterations:
            logger.warning("Maximum conversation iterations reached")
            print("\n⚠️  Maximum tool execution iterations reached.")

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
            temperature=self.config.temperature,
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
        accumulated_content = []
        final_tool_calls = None

        print()

        for chunk in self.provider.chat_completion_streaming(
            messages=messages,
            tools=tool_definitions,
            temperature=self.config.temperature
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

    def _execute_tool_calls(self, tool_calls: list[Dict], messages: list[Dict[str, Any]]):
        for tool_call in tool_calls:
            tool_call_id = tool_call.get('id')
            function_info = tool_call.get('function', {})
            tool_name = function_info.get('name')
            arguments_str = function_info.get('arguments', '{}')

            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}

            print(f"🔍 {self._format_tool_execution_message(tool_name, arguments)}")

            context = {
                'chromadb_path': self.config.chromadb_path,
                'provider': self.provider
            }

            result = execute_tool(tool_name, arguments, context)

            formatted_result = format_tool_result(tool_name, result)

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
