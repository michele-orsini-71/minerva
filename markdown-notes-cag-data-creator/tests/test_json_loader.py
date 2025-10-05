import json
from pathlib import Path

import pytest

import json_loader


def create_notes_payload():
    return [
        {
            "title": "Note",
            "markdown": "content",
            "size": 12,
            "modificationDate": "2024-01-01",
        }
    ]


def test_load_json_notes_success(tmp_path: Path):
    json_file = tmp_path / "notes.json"
    json_file.write_text(json.dumps(create_notes_payload()), encoding="utf-8")

    notes = json_loader.load_json_notes(str(json_file))
    assert notes == create_notes_payload()


def test_load_json_notes_file_not_found(tmp_path: Path):
    with pytest.raises(SystemExit) as exit_info:
        json_loader.load_json_notes(str(tmp_path / "missing.json"))

    assert exit_info.value.code == 1


def test_load_json_notes_invalid_json(tmp_path: Path):
    json_file = tmp_path / "notes.json"
    json_file.write_text("not-json", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        json_loader.load_json_notes(str(json_file))

    assert exit_info.value.code == 1


def test_load_json_notes_wrong_type(tmp_path: Path):
    json_file = tmp_path / "notes.json"
    json_file.write_text(json.dumps({"note": "value"}), encoding="utf-8")

    with pytest.raises(SystemExit):
        json_loader.load_json_notes(str(json_file))


def test_load_json_notes_missing_required_fields(tmp_path: Path):
    json_file = tmp_path / "notes.json"
    payload = [
        {
            "title": "Note",
            "markdown": "text",
            "size": 10,
            # modificationDate missing
        }
    ]
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit):
        json_loader.load_json_notes(str(json_file))


def test_load_json_notes_empty_list(tmp_path: Path):
    json_file = tmp_path / "notes.json"
    json_file.write_text("[]", encoding="utf-8")

    notes = json_loader.load_json_notes(str(json_file))
    assert notes == []
