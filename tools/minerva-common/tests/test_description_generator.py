import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minerva_common.description_generator import (
    build_description_prompt,
    extract_content_from_response,
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


def test_build_description_prompt():
    titles = ["Title 1", "Title 2", "Title 3"]
    content_previews = ["Content preview 1", "Content preview 2"]
    total_count = 10

    prompt = build_description_prompt(titles, content_previews, total_count)

    assert "10 documents" in prompt
    assert "Title 1" in prompt
    assert "Title 2" in prompt
    assert "Content preview 1" in prompt
    assert "Requirements:" in prompt


def test_build_description_prompt_many_titles():
    titles = [f"Title {i}" for i in range(20)]
    content_previews = []
    total_count = 20

    prompt = build_description_prompt(titles, content_previews, total_count)

    assert "Title 0" in prompt
    assert "Title 4" in prompt
    assert "Title 5" not in prompt


def test_build_description_prompt_many_previews():
    titles = ["Title"]
    content_previews = [f"Preview {i}" for i in range(10)]
    total_count = 1

    prompt = build_description_prompt(titles, content_previews, total_count)

    assert "Preview 0" in prompt
    assert "Preview 2" in prompt
    assert "Preview 3" not in prompt


def test_extract_content_from_response():
    response = {"choices": [{"message": {"content": "Generated description"}}]}

    content = extract_content_from_response(response)

    assert content == "Generated description"


def test_extract_content_from_response_missing_choices():
    response = {}

    with pytest.raises(ValueError, match="No choices"):
        extract_content_from_response(response)


def test_extract_content_from_response_empty_choices():
    response = {"choices": []}

    with pytest.raises(ValueError, match="No choices"):
        extract_content_from_response(response)


def test_extract_content_from_response_missing_message():
    response = {"choices": [{}]}

    with pytest.raises(ValueError, match="No content"):
        extract_content_from_response(response)


def test_extract_content_from_response_missing_content():
    response = {"choices": [{"message": {}}]}

    with pytest.raises(ValueError, match="No content"):
        extract_content_from_response(response)


def test_generate_description_from_records(sample_json_file, provider_config):
    with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
        mock_provider = MagicMock()
        mock_ai_provider.return_value = mock_provider
        mock_provider.chat_completion.return_value = {
            "choices": [{"message": {"content": "A collection of Python programming tutorials and guides."}}]
        }

        description = generate_description_from_records(sample_json_file, provider_config)

        assert description == "A collection of Python programming tutorials and guides."
        mock_ai_provider.assert_called_once()
        mock_provider.chat_completion.assert_called_once()


def test_generate_description_from_records_with_max_samples(sample_json_file, provider_config):
    with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
        mock_provider = MagicMock()
        mock_ai_provider.return_value = mock_provider
        mock_provider.chat_completion.return_value = {
            "choices": [{"message": {"content": "Test description"}}]
        }

        generate_description_from_records(sample_json_file, provider_config, max_samples=2)

        call_args = mock_provider.chat_completion.call_args
        messages = call_args[0][0]
        prompt = messages[0]["content"]

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
    with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
        mock_provider = MagicMock()
        mock_ai_provider.return_value = mock_provider
        mock_provider.chat_completion.return_value = {
            "choices": [{"message": {"content": "  Description with whitespace  \n"}}]
        }

        description = generate_description_from_records(sample_json_file, provider_config)

        assert description == "Description with whitespace"


def test_prompt_for_description_user_input(sample_json_file, provider_config):
    with patch("builtins.input", return_value="My custom description"):
        description = prompt_for_description(sample_json_file, provider_config)

        assert description == "My custom description"


def test_prompt_for_description_auto_generate(sample_json_file, provider_config):
    with patch("builtins.input", side_effect=["", ""]):
        with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
            mock_provider = MagicMock()
            mock_ai_provider.return_value = mock_provider
            mock_provider.chat_completion.return_value = {
                "choices": [{"message": {"content": "AI generated description"}}]
            }

            description = prompt_for_description(sample_json_file, provider_config)

            assert description == "AI generated description"


def test_prompt_for_description_accept_generated(sample_json_file, provider_config):
    with patch("builtins.input", side_effect=["", "y"]):
        with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
            mock_provider = MagicMock()
            mock_ai_provider.return_value = mock_provider
            mock_provider.chat_completion.return_value = {
                "choices": [{"message": {"content": "AI description"}}]
            }

            description = prompt_for_description(sample_json_file, provider_config)

            assert description == "AI description"


def test_prompt_for_description_reject_generated(sample_json_file, provider_config):
    with patch("builtins.input", side_effect=["", "n", "Manual description"]):
        with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
            mock_provider = MagicMock()
            mock_ai_provider.return_value = mock_provider
            mock_provider.chat_completion.return_value = {
                "choices": [{"message": {"content": "AI description"}}]
            }

            description = prompt_for_description(sample_json_file, provider_config)

            assert description == "Manual description"


def test_prompt_for_description_generation_failure(sample_json_file, provider_config):
    with patch("builtins.input", side_effect=["", "Fallback description"]):
        with patch("minerva_common.description_generator.AIProvider") as mock_ai_provider:
            mock_ai_provider.side_effect = Exception("AI service unavailable")

            description = prompt_for_description(sample_json_file, provider_config)

            assert description == "Fallback description"


def test_prompt_for_description_no_auto_generate(sample_json_file, provider_config):
    with patch("builtins.input", return_value=""):
        description = prompt_for_description(sample_json_file, provider_config, auto_generate=False)

        assert description == ""
