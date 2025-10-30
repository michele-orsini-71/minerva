from typing import Dict, Any, Optional
from minerva.common.logger import get_logger

logger = get_logger(__name__)

MODEL_CONTEXT_LIMITS = {
    'llama3.1:8b': 32_000,
    'llama3.1:70b': 32_000,
    'llama3.2:1b': 32_000,
    'llama3.2:3b': 32_000,
    'llama3:8b': 8_000,
    'llama3:70b': 8_000,
    'llama2:7b': 4_096,
    'llama2:13b': 4_096,
    'llama2:70b': 4_096,
    'mistral:7b': 8_000,
    'mixtral:8x7b': 32_000,
    'gemma:2b': 8_192,
    'gemma:7b': 8_192,
    'gpt-4o': 128_000,
    'gpt-4o-mini': 128_000,
    'gpt-4-turbo': 128_000,
    'gpt-4': 8_192,
    'gpt-3.5-turbo': 16_385,
    'claude-3-5-sonnet': 200_000,
    'claude-3-opus': 200_000,
    'claude-3-sonnet': 200_000,
    'claude-3-haiku': 200_000,
    'gemini-1.5-pro': 1_000_000,
    'gemini-1.5-flash': 1_000_000,
    'gemini-pro': 32_000,
}

DEFAULT_CONTEXT_LIMIT = 8_000
WARNING_THRESHOLD = 0.85


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return len(text) // 4


def calculate_conversation_tokens(messages: list[Dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')

        total += estimate_tokens(role)
        total += estimate_tokens(content)

        if 'tool_calls' in msg:
            tool_calls = msg['tool_calls']
            for tool_call in tool_calls:
                function_info = tool_call.get('function', {})
                total += estimate_tokens(function_info.get('name', ''))
                total += estimate_tokens(function_info.get('arguments', ''))

        if msg.get('role') == 'tool':
            total += estimate_tokens(msg.get('name', ''))

    return total


def get_context_limit(model_name: str) -> int:
    for key in MODEL_CONTEXT_LIMITS:
        if key in model_name.lower():
            return MODEL_CONTEXT_LIMITS[key]

    logger.warning(f"Unknown model '{model_name}', using default context limit of {DEFAULT_CONTEXT_LIMIT}")
    return DEFAULT_CONTEXT_LIMIT


def check_context_window(
    messages: list[Dict[str, Any]],
    model_name: str
) -> tuple[int, int, float, bool]:
    current_tokens = calculate_conversation_tokens(messages)
    max_tokens = get_context_limit(model_name)
    usage_ratio = current_tokens / max_tokens if max_tokens > 0 else 0
    should_warn = usage_ratio >= WARNING_THRESHOLD

    return current_tokens, max_tokens, usage_ratio, should_warn


def format_context_warning(current_tokens: int, max_tokens: int, usage_ratio: float) -> str:
    percentage = int(usage_ratio * 100)

    bar_width = 30
    filled = int(bar_width * usage_ratio)
    bar = '█' * filled + '░' * (bar_width - filled)

    return (
        f"\n⚠️  Context window usage: {percentage}%\n"
        f"   [{bar}] {current_tokens:,} / {max_tokens:,} tokens\n"
        f"\n"
        f"   Options:\n"
        f"     [c] Continue (may fail if limit exceeded)\n"
        f"     [s] Summarize conversation (compress old messages)\n"
        f"     [n] New conversation (start fresh)\n"
    )


def get_user_choice() -> str:
    while True:
        choice = input("   Your choice: ").strip().lower()
        if choice in ['c', 's', 'n', 'continue', 'summarize', 'new']:
            return choice[0]
        print("   Invalid choice. Please enter 'c', 's', or 'n'.")


def create_summarization_prompt(messages: list[Dict[str, Any]]) -> str:
    return (
        "Please provide a concise summary of the conversation so far. "
        "Focus on key topics discussed, important questions asked, and main conclusions reached. "
        "Keep the summary under 200 words."
    )


def create_summary_messages(
    system_message: Optional[Dict[str, Any]],
    messages_to_summarize: list[Dict[str, Any]]
) -> list[Dict[str, Any]]:
    summary_request = []

    if system_message:
        summary_request.append(system_message)

    summary_request.extend(messages_to_summarize)

    summary_request.append({
        'role': 'user',
        'content': create_summarization_prompt(messages_to_summarize)
    })

    return summary_request


def extract_system_message(messages: list[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if messages and messages[0].get('role') == 'system':
        return messages[0]
    return None


def extract_recent_messages(messages: list[Dict[str, Any]], keep_count: int = 6) -> list[Dict[str, Any]]:
    return messages[-keep_count:] if len(messages) > keep_count else messages


def replace_with_summary(
    messages: list[Dict[str, Any]],
    summary_text: str,
    keep_recent_count: int = 6
) -> list[Dict[str, Any]]:
    system_message = extract_system_message(messages)
    recent_messages = extract_recent_messages(messages, keep_recent_count)

    new_messages = []

    if system_message:
        new_messages.append(system_message)

    summary_message = {
        'role': 'assistant',
        'content': f"[Summary of previous conversation]\n\n{summary_text}"
    }
    new_messages.append(summary_message)

    start_index = 1 if system_message else 0

    for msg in recent_messages:
        if msg not in messages[:start_index + 1]:
            new_messages.append(msg)

    return new_messages
