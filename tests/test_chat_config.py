import json
from pathlib import Path

import pytest

from minerva.chat.config import ChatConfig, ChatConfigError, load_chat_config_from_file
from tests.helpers.config_builders import make_chat_config


def test_load_chat_config_success(tmp_path: Path):
    config_dir = tmp_path / "chat"
    chat_config, config_path = make_chat_config(config_dir)

    loaded = load_chat_config_from_file(str(config_path))

    assert isinstance(loaded, ChatConfig)
    assert loaded == chat_config
    assert Path(loaded.conversation_dir).exists()
    assert Path(loaded.chromadb_path).is_absolute()


def test_load_chat_config_with_system_prompt(tmp_path: Path):
    config_dir = tmp_path / "chat"
    prompt_file = config_dir / "prompt.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("Prompt", encoding="utf-8")

    _, config_path = make_chat_config(
        config_dir,
        overrides={"system_prompt_file": "prompt.txt"},
    )

    loaded = load_chat_config_from_file(str(config_path))

    assert loaded.system_prompt_file == str(prompt_file.resolve())


def test_load_chat_config_invalid_iteration_count(tmp_path: Path):
    config_dir = tmp_path / "chat"
    _, config_path = make_chat_config(config_dir)

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["max_tool_iterations"] = 0
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(ChatConfigError):
        load_chat_config_from_file(str(config_path))


def test_load_chat_config_invalid_mcp_url(tmp_path: Path):
    config_dir = tmp_path / "chat"
    _, config_path = make_chat_config(config_dir)

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["mcp_server_url"] = "not-a-valid-url"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(ChatConfigError):
        load_chat_config_from_file(str(config_path))


def test_load_chat_config_unwritable_conversation_dir(tmp_path: Path):
    config_dir = tmp_path / "chat"
    _, config_path = make_chat_config(config_dir)

    existing_file = config_dir / "conversations"
    existing_file.rmdir()
    existing_file.write_text("placeholder", encoding="utf-8")

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["conversation_dir"] = str(existing_file)
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(ChatConfigError):
        load_chat_config_from_file(str(config_path))
