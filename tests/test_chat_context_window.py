import pytest
from minerva.chat.context_window import (
    estimate_tokens,
    calculate_conversation_tokens,
    get_context_limit,
    check_context_window,
    format_context_warning,
    create_summarization_prompt,
    create_summary_messages,
    extract_system_message,
    extract_recent_messages,
    replace_with_summary,
    MODEL_CONTEXT_LIMITS,
    DEFAULT_CONTEXT_LIMIT,
    WARNING_THRESHOLD
)


def test_estimate_tokens_empty_string():
    assert estimate_tokens("") == 0


def test_estimate_tokens_simple_text():
    text = "Hello world"
    expected = len(text) // 4
    assert estimate_tokens(text) == expected


def test_estimate_tokens_long_text():
    text = "A" * 1000
    expected = 1000 // 4
    assert estimate_tokens(text) == expected


def test_calculate_conversation_tokens_empty():
    messages = []
    assert calculate_conversation_tokens(messages) == 0


def test_calculate_conversation_tokens_simple():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]

    expected = estimate_tokens("user") + estimate_tokens("Hello")
    expected += estimate_tokens("assistant") + estimate_tokens("Hi there")

    assert calculate_conversation_tokens(messages) == expected


def test_calculate_conversation_tokens_with_tool_calls():
    messages = [
        {"role": "user", "content": "Search for Python"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "search_knowledge_base",
                        "arguments": '{"query": "Python"}'
                    }
                }
            ]
        }
    ]

    result = calculate_conversation_tokens(messages)
    assert result > 0


def test_calculate_conversation_tokens_with_tool_result():
    messages = [
        {
            "role": "tool",
            "name": "search_knowledge_base",
            "content": "Found 5 results"
        }
    ]

    result = calculate_conversation_tokens(messages)
    assert result > 0


def test_get_context_limit_llama():
    assert get_context_limit("llama3.1:8b") == 32_000
    assert get_context_limit("llama3.1:70b") == 32_000


def test_get_context_limit_gpt():
    assert get_context_limit("gpt-4o") == 128_000
    assert get_context_limit("gpt-4o-mini") == 128_000


def test_get_context_limit_claude():
    assert get_context_limit("claude-3-5-sonnet") == 200_000


def test_get_context_limit_gemini():
    assert get_context_limit("gemini-1.5-pro") == 1_000_000


def test_get_context_limit_unknown_model():
    assert get_context_limit("unknown-model") == DEFAULT_CONTEXT_LIMIT


def test_get_context_limit_case_insensitive():
    assert get_context_limit("GPT-4O") == 128_000
    assert get_context_limit("Llama3.1:8B") == 32_000


def test_get_context_limit_partial_match():
    assert get_context_limit("llama3.1:8b-instruct-q4") == 32_000


def test_check_context_window_low_usage():
    messages = [
        {"role": "user", "content": "Hello"}
    ]

    current_tokens, max_tokens, usage_ratio, should_warn = check_context_window(messages, "gpt-4o")

    assert current_tokens > 0
    assert max_tokens == 128_000
    assert usage_ratio < WARNING_THRESHOLD
    assert should_warn is False


def test_check_context_window_high_usage():
    long_content = "A" * 100_000
    messages = [
        {"role": "user", "content": long_content}
    ]

    current_tokens, max_tokens, usage_ratio, should_warn = check_context_window(messages, "llama3:8b")

    assert usage_ratio > WARNING_THRESHOLD
    assert should_warn is True


def test_format_context_warning():
    warning = format_context_warning(8500, 10000, 0.85)

    assert "85%" in warning
    assert "8,500" in warning
    assert "10,000" in warning
    assert "[c]" in warning
    assert "[s]" in warning
    assert "[n]" in warning


def test_create_summarization_prompt():
    messages = [
        {"role": "user", "content": "Hello"}
    ]

    prompt = create_summarization_prompt(messages)

    assert "summary" in prompt.lower()
    assert len(prompt) > 0


def test_create_summary_messages_with_system():
    system_message = {"role": "system", "content": "You are a helpful assistant"}
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"}
    ]

    summary_messages = create_summary_messages(system_message, messages)

    assert summary_messages[0] == system_message
    assert summary_messages[-1]["role"] == "user"
    assert "summary" in summary_messages[-1]["content"].lower()


def test_create_summary_messages_without_system():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"}
    ]

    summary_messages = create_summary_messages(None, messages)

    assert summary_messages[0] == messages[0]
    assert summary_messages[-1]["role"] == "user"


def test_extract_system_message_present():
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Hello"}
    ]

    system_msg = extract_system_message(messages)

    assert system_msg is not None
    assert system_msg["role"] == "system"


def test_extract_system_message_absent():
    messages = [
        {"role": "user", "content": "Hello"}
    ]

    system_msg = extract_system_message(messages)

    assert system_msg is None


def test_extract_recent_messages():
    messages = []
    for i in range(10):
        messages.append({"role": "user", "content": f"Message {i}"})

    recent = extract_recent_messages(messages, keep_count=6)

    assert len(recent) == 6
    assert recent[0]["content"] == "Message 4"
    assert recent[-1]["content"] == "Message 9"


def test_extract_recent_messages_fewer_than_keep_count():
    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "user", "content": "Message 2"}
    ]

    recent = extract_recent_messages(messages, keep_count=6)

    assert len(recent) == 2
    assert recent == messages


def test_replace_with_summary_with_system():
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Response 2"},
        {"role": "user", "content": "Message 3"},
        {"role": "assistant", "content": "Response 3"},
        {"role": "user", "content": "Message 4"}
    ]

    summary_text = "This is a summary of the conversation"

    new_messages = replace_with_summary(messages, summary_text, keep_recent_count=4)

    assert new_messages[0]["role"] == "system"
    assert new_messages[1]["role"] == "assistant"
    assert "summary" in new_messages[1]["content"].lower()
    assert summary_text in new_messages[1]["content"]
    assert len(new_messages) < len(messages)


def test_replace_with_summary_without_system():
    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Response 2"},
        {"role": "user", "content": "Message 3"},
        {"role": "assistant", "content": "Response 3"},
        {"role": "user", "content": "Message 4"}
    ]

    summary_text = "Summary without system"

    new_messages = replace_with_summary(messages, summary_text, keep_recent_count=4)

    assert new_messages[0]["role"] == "assistant"
    assert "summary" in new_messages[0]["content"].lower()
    assert len(new_messages) < len(messages)


def test_model_context_limits_contains_common_models():
    assert "llama3.1:8b" in MODEL_CONTEXT_LIMITS
    assert "gpt-4o" in MODEL_CONTEXT_LIMITS
    assert "claude-3-5-sonnet" in MODEL_CONTEXT_LIMITS
    assert "gemini-1.5-pro" in MODEL_CONTEXT_LIMITS


def test_warning_threshold_is_85_percent():
    assert WARNING_THRESHOLD == 0.85


def test_context_window_exact_threshold():
    messages = [{"role": "user", "content": "A" * 108_800}]

    current_tokens, max_tokens, usage_ratio, should_warn = check_context_window(messages, "llama3.1:8b")

    assert usage_ratio >= WARNING_THRESHOLD
    assert should_warn is True


def test_context_window_multiple_messages():
    messages = []
    for i in range(20):
        messages.append({"role": "user", "content": "Hello world " * 100})
        messages.append({"role": "assistant", "content": "Response " * 100})

    current_tokens, max_tokens, usage_ratio, should_warn = check_context_window(messages, "llama2:7b")

    assert current_tokens > 0
    assert max_tokens == 4_096


def test_calculate_tokens_with_missing_content():
    messages = [
        {"role": "user"},
        {"role": "assistant", "content": "Hello"}
    ]

    result = calculate_conversation_tokens(messages)
    assert result > 0


def test_calculate_tokens_with_empty_tool_calls():
    messages = [
        {
            "role": "assistant",
            "content": "Let me search",
            "tool_calls": []
        }
    ]

    result = calculate_conversation_tokens(messages)
    assert result > 0
