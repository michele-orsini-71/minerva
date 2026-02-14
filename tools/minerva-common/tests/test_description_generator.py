import json
from unittest.mock import patch

import pytest

from minerva_common.description_generator import (
    _build_description_prompt,
    _extract_openai_response,
    _extract_ollama_response,
    _extract_gemini_response,
    _normalize_base_url,
    _sanitize_description,
    generate_description_from_records,
    prompt_for_description,
)


@pytest.fixture
def sample_json_file(tmp_path):
    records = [
        {
            "title": "Python Programming Basics",
            "markdown": "# Python Basics\n\nPython is a high-level programming language...",
            "size": 1000,
            "modificationDate": "2024-01-01T00:00:00Z",
        },
        {
            "title": "Advanced Python Concepts",
            "markdown": "# Advanced Topics\n\nObject-oriented programming in Python...",
            "size": 1500,
            "modificationDate": "2024-01-02T00:00:00Z",
        },
        {
            "title": "Python Data Science",
            "markdown": "# Data Science\n\nUsing pandas and numpy for data analysis...",
            "size": 2000,
            "modificationDate": "2024-01-03T00:00:00Z",
        },
    ]

    json_file = tmp_path / "records.json"
    with open(json_file, "w") as f:
        json.dump(records, f)

    return json_file


@pytest.fixture
def provider_config():
    return {
        "provider_type": "ollama",
        "embedding_model": "mxbai-embed-large:latest",
        "llm_model": "llama3.1:8b",
        "base_url": "http://localhost:11434",
    }


# --- _build_description_prompt ---


def test_build_description_prompt():
    titles = ["Title 1", "Title 2", "Title 3"]
    content_previews = ["Content preview 1", "Content preview 2"]
    total_count = 10

    prompt = _build_description_prompt(titles, content_previews, total_count)

    assert "10 documents" in prompt
    assert "Title 1" in prompt
    assert "Title 2" in prompt
    assert "Content preview 1" in prompt
    assert "Requirements:" in prompt


def test_build_description_prompt_many_titles():
    titles = [f"Title {i}" for i in range(20)]
    total_count = 20

    prompt = _build_description_prompt(titles, [], total_count)

    assert "Title 0" in prompt
    assert "Title 4" in prompt
    assert "Title 5" not in prompt


def test_build_description_prompt_many_previews():
    titles = ["Title"]
    content_previews = [f"Preview {i}" for i in range(10)]

    prompt = _build_description_prompt(titles, content_previews, 1)

    assert "Preview 0" in prompt
    assert "Preview 2" in prompt
    assert "Preview 3" not in prompt


# --- Response extractors ---


def test_extract_openai_response():
    data = {"choices": [{"message": {"content": "Generated description"}}]}
    assert _extract_openai_response(data) == "Generated description"


def test_extract_openai_response_missing_choices():
    with pytest.raises(RuntimeError, match="no choices"):
        _extract_openai_response({})


def test_extract_openai_response_empty_choices():
    with pytest.raises(RuntimeError, match="no choices"):
        _extract_openai_response({"choices": []})


def test_extract_openai_response_missing_content():
    with pytest.raises(RuntimeError, match="empty description"):
        _extract_openai_response({"choices": [{"message": {}}]})


def test_extract_ollama_response():
    data = {"message": {"content": "Ollama description"}}
    assert _extract_ollama_response(data) == "Ollama description"


def test_extract_ollama_response_empty():
    with pytest.raises(RuntimeError, match="empty description"):
        _extract_ollama_response({"message": {}})


def test_extract_gemini_response():
    data = {"candidates": [{"content": {"parts": [{"text": "Gemini description"}]}}]}
    assert _extract_gemini_response(data) == "Gemini description"


def test_extract_gemini_response_no_candidates():
    with pytest.raises(RuntimeError, match="no candidates"):
        _extract_gemini_response({})


# --- _normalize_base_url ---


def test_normalize_base_url_strips_v1():
    assert _normalize_base_url("http://localhost:1234/v1") == "http://localhost:1234"


def test_normalize_base_url_strips_v1_and_trailing_slash():
    assert _normalize_base_url("http://localhost:1234/v1/") == "http://localhost:1234"


def test_normalize_base_url_no_v1():
    assert _normalize_base_url("http://localhost:1234") == "http://localhost:1234"


def test_normalize_base_url_strips_trailing_slash():
    assert _normalize_base_url("http://localhost:1234/") == "http://localhost:1234"


# --- _sanitize_description ---


def test_sanitize_description_strips_quotes():
    assert _sanitize_description('"quoted"') == "quoted"
    assert _sanitize_description("'quoted'") == "quoted"
    assert _sanitize_description("  spaced  ") == "spaced"


# --- generate_description_from_records ---


def test_generate_description_from_records(sample_json_file, provider_config):
    mock_response = {"message": {"content": "A collection of Python programming tutorials and guides."}}

    with patch("minerva_common.description_generator._perform_request", return_value=mock_response):
        description = generate_description_from_records(sample_json_file, provider_config)

    assert description == "A collection of Python programming tutorials and guides."


def test_generate_description_from_records_with_max_samples(sample_json_file, provider_config):
    mock_response = {"message": {"content": "Test description"}}

    with patch("minerva_common.description_generator._perform_request", return_value=mock_response) as mock_req:
        generate_description_from_records(sample_json_file, provider_config, max_samples=2)

    # Verify the request was made (prompt built from max 2 samples)
    mock_req.assert_called_once()
    request_obj = mock_req.call_args[0][0]
    body = json.loads(request_obj.data.decode("utf-8"))
    prompt = body["messages"][0]["content"]
    assert "Python Programming Basics" in prompt
    assert "Advanced Python Concepts" in prompt


def test_generate_description_from_records_invalid_json(tmp_path, provider_config):
    json_file = tmp_path / "invalid.json"
    with open(json_file, "w") as f:
        json.dump({"not": "a list"}, f)

    with pytest.raises(ValueError, match="must contain a list"):
        generate_description_from_records(json_file, provider_config)


def test_generate_description_from_records_empty_json(tmp_path, provider_config):
    json_file = tmp_path / "empty.json"
    with open(json_file, "w") as f:
        json.dump([], f)

    with pytest.raises(ValueError, match="contains no records"):
        generate_description_from_records(json_file, provider_config)


def test_generate_description_from_records_strips_whitespace(sample_json_file, provider_config):
    mock_response = {"message": {"content": "  Description with whitespace  \n"}}

    with patch("minerva_common.description_generator._perform_request", return_value=mock_response):
        description = generate_description_from_records(sample_json_file, provider_config)

    assert description == "Description with whitespace"


def test_generate_description_uses_base_url_from_config(sample_json_file):
    config = {
        "provider_type": "ollama",
        "llm_model": "llama3.1:8b",
        "base_url": "http://custom-host:9999",
    }
    mock_response = {"message": {"content": "description"}}

    with patch("minerva_common.description_generator._perform_request", return_value=mock_response) as mock_req:
        generate_description_from_records(sample_json_file, config)

    request_obj = mock_req.call_args[0][0]
    assert request_obj.full_url == "http://custom-host:9999/api/chat"


def test_generate_description_lmstudio_normalizes_base_url(sample_json_file):
    config = {
        "provider_type": "lmstudio",
        "llm_model": "gemma-3-4b",
        "base_url": "http://localhost:1234/v1",
    }
    mock_response = {"choices": [{"message": {"content": "description"}}]}

    with patch("minerva_common.description_generator._perform_request", return_value=mock_response) as mock_req:
        generate_description_from_records(sample_json_file, config)

    request_obj = mock_req.call_args[0][0]
    assert request_obj.full_url == "http://localhost:1234/v1/chat/completions"


# --- prompt_for_description ---


def test_prompt_for_description_user_input(sample_json_file, provider_config):
    with patch("builtins.input", return_value="My custom description"):
        description = prompt_for_description(sample_json_file, provider_config)

    assert description == "My custom description"


def test_prompt_for_description_auto_generate(sample_json_file, provider_config):
    mock_response = {"message": {"content": "AI generated description"}}

    with patch("builtins.input", side_effect=["", ""]):
        with patch("minerva_common.description_generator._perform_request", return_value=mock_response):
            description = prompt_for_description(sample_json_file, provider_config)

    assert description == "AI generated description"


def test_prompt_for_description_accept_generated(sample_json_file, provider_config):
    mock_response = {"message": {"content": "AI description"}}

    with patch("builtins.input", side_effect=["", "y"]):
        with patch("minerva_common.description_generator._perform_request", return_value=mock_response):
            description = prompt_for_description(sample_json_file, provider_config)

    assert description == "AI description"


def test_prompt_for_description_reject_generated(sample_json_file, provider_config):
    mock_response = {"message": {"content": "AI description"}}

    with patch("builtins.input", side_effect=["", "n", "Manual description"]):
        with patch("minerva_common.description_generator._perform_request", return_value=mock_response):
            description = prompt_for_description(sample_json_file, provider_config)

    assert description == "Manual description"


def test_prompt_for_description_generation_failure(sample_json_file, provider_config):
    with patch("builtins.input", side_effect=["", "Fallback description"]):
        with patch(
            "minerva_common.description_generator._perform_request",
            side_effect=RuntimeError("Connection error"),
        ):
            description = prompt_for_description(sample_json_file, provider_config)

    assert description == "Fallback description"


def test_prompt_for_description_no_auto_generate(sample_json_file, provider_config):
    with patch("builtins.input", return_value=""):
        description = prompt_for_description(sample_json_file, provider_config, auto_generate=False)

    assert description == ""
