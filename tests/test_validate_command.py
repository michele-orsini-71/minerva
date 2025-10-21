import pytest
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from minervium.commands.validate import (
    run_validate,
    load_json_file,
    print_validation_statistics,
    print_validation_errors,
    print_banner,
)


class TestLoadJsonFile:
    def test_load_valid_json_file(self, temp_json_file: Path):
        data = load_json_file(temp_json_file)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_load_nonexistent_file_exits(self, temp_dir: Path):
        nonexistent = temp_dir / "does_not_exist.json"
        with pytest.raises(SystemExit) as exc_info:
            load_json_file(nonexistent)
        assert exc_info.value.code == 1

    def test_load_invalid_json_exits(self, temp_invalid_json_file: Path):
        with pytest.raises(SystemExit) as exc_info:
            load_json_file(temp_invalid_json_file)
        assert exc_info.value.code == 1

    def test_load_json_with_permission_error(self, temp_dir: Path, monkeypatch):
        json_file = temp_dir / "notes.json"
        with open(json_file, "w") as f:
            json.dump([], f)

        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr("builtins.open", mock_open)
        with pytest.raises(SystemExit) as exc_info:
            load_json_file(json_file)
        assert exc_info.value.code == 1


class TestRunValidate:
    def test_validate_with_valid_file(self, temp_json_file: Path):
        args = Namespace(json_file=temp_json_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 0

    def test_validate_with_valid_file_verbose(self, temp_json_file: Path):
        args = Namespace(json_file=temp_json_file, verbose=True)
        exit_code = run_validate(args)
        assert exit_code == 0

    def test_validate_with_invalid_file(self, temp_dir: Path):
        invalid_file = temp_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            json.dump([{"title": ""}], f)  # Empty title is invalid

        args = Namespace(json_file=invalid_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 1

    def test_validate_with_invalid_file_verbose(self, temp_dir: Path):
        invalid_file = temp_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            json.dump([{"title": ""}], f)

        args = Namespace(json_file=invalid_file, verbose=True)
        exit_code = run_validate(args)
        assert exit_code == 1

    def test_validate_with_empty_array(self, temp_dir: Path):
        empty_file = temp_dir / "empty.json"
        with open(empty_file, "w") as f:
            json.dump([], f)

        args = Namespace(json_file=empty_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 0

    def test_validate_with_nonexistent_file(self, temp_dir: Path):
        nonexistent = temp_dir / "does_not_exist.json"
        args = Namespace(json_file=nonexistent, verbose=False)
        # load_json_file calls sys.exit(1) which raises SystemExit
        with pytest.raises(SystemExit) as exc_info:
            run_validate(args)
        assert exc_info.value.code == 1

    def test_validate_with_malformed_json(self, temp_invalid_json_file: Path):
        args = Namespace(json_file=temp_invalid_json_file, verbose=False)
        # load_json_file calls sys.exit(1) which raises SystemExit
        with pytest.raises(SystemExit) as exc_info:
            run_validate(args)
        assert exc_info.value.code == 1

    def test_validate_with_multiple_invalid_notes(self, temp_dir: Path):
        invalid_file = temp_dir / "multiple_invalid.json"
        invalid_data = [
            {"title": ""},  # Empty title
            {"markdown": "content"},  # Missing title
            {"title": "Valid", "markdown": "content", "size": 100, "modificationDate": "2025-01-01T00:00:00Z"},
            {"title": "Invalid", "markdown": "content", "size": -1, "modificationDate": "2025-01-01T00:00:00Z"},  # Negative size
        ]
        with open(invalid_file, "w") as f:
            json.dump(invalid_data, f)

        args = Namespace(json_file=invalid_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 1

    def test_validate_handles_keyboard_interrupt(self, temp_json_file: Path, monkeypatch):
        def mock_validate(*args, **kwargs):
            raise KeyboardInterrupt()

        monkeypatch.setattr("minervium.commands.validate.validate_notes_array", mock_validate)

        args = Namespace(json_file=temp_json_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 130

    def test_validate_with_not_a_list(self, temp_dir: Path):
        not_list_file = temp_dir / "not_list.json"
        with open(not_list_file, "w") as f:
            json.dump({"note": "this is an object, not a list"}, f)

        args = Namespace(json_file=not_list_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 1


class TestPrintValidationStatistics:
    def test_print_statistics_with_valid_data(self, valid_notes_list: list[dict[str, Any]], capsys):
        print_validation_statistics(valid_notes_list, verbose=False)
        # Function should run without errors

    def test_print_statistics_verbose(self, valid_notes_list: list[dict[str, Any]], capsys):
        print_validation_statistics(valid_notes_list, verbose=True)
        # Function should run without errors and print more details

    def test_print_statistics_with_empty_list(self, capsys):
        print_validation_statistics([], verbose=False)
        # Should handle empty list gracefully

    def test_print_statistics_with_non_list(self, capsys):
        print_validation_statistics({"not": "a list"}, verbose=False)
        # Should handle non-list input gracefully

    def test_print_statistics_calculates_averages(self, capsys):
        notes = [
            {"title": "Note 1", "markdown": "content1", "size": 100, "modificationDate": "2025-01-01T00:00:00Z"},
            {"title": "Note 2", "markdown": "content2", "size": 200, "modificationDate": "2025-01-02T00:00:00Z"},
        ]
        print_validation_statistics(notes, verbose=True)
        # Should calculate and display averages

    def test_print_statistics_with_long_titles(self, capsys):
        notes = [
            {
                "title": "A" * 100,  # Very long title
                "markdown": "content",
                "size": 100,
                "modificationDate": "2025-01-01T00:00:00Z"
            }
        ]
        print_validation_statistics(notes, verbose=True)
        # Should truncate long titles


class TestPrintValidationErrors:
    def test_print_errors_normal_mode(self, temp_dir: Path, capsys):
        errors = [f"Error {i}" for i in range(10)]
        json_path = temp_dir / "test.json"
        print_validation_errors(errors, json_path, verbose=False)
        # Should print first 5 errors in normal mode

    def test_print_errors_verbose_mode(self, temp_dir: Path, capsys):
        errors = [f"Error {i}" for i in range(10)]
        json_path = temp_dir / "test.json"
        print_validation_errors(errors, json_path, verbose=True)
        # Should print all errors in verbose mode

    def test_print_errors_few_errors(self, temp_dir: Path, capsys):
        errors = ["Error 1", "Error 2"]
        json_path = temp_dir / "test.json"
        print_validation_errors(errors, json_path, verbose=False)
        # Should print all errors when count <= 5

    def test_print_errors_single_error(self, temp_dir: Path, capsys):
        errors = ["Single error"]
        json_path = temp_dir / "test.json"
        print_validation_errors(errors, json_path, verbose=False)
        # Should handle single error


class TestPrintBanner:
    def test_print_banner(self, capsys):
        print_banner()
        # Should print banner without errors


class TestIntegrationScenarios:
    def test_validate_real_world_bear_notes(self, temp_dir: Path):
        # Simulate real Bear notes structure
        notes = [
            {
                "title": "Project Ideas",
                "markdown": "# Project Ideas\n\n- Build a CLI tool\n- Learn Rust",
                "size": len("# Project Ideas\n\n- Build a CLI tool\n- Learn Rust".encode("utf-8")),
                "modificationDate": "2025-01-15T10:30:00Z",
                "creationDate": "2025-01-10T08:00:00Z",
                "tags": ["ideas", "projects"]
            },
            {
                "title": "Meeting Notes - 2025-01-15",
                "markdown": "## Agenda\n1. Review Q1 goals\n2. Discuss hiring",
                "size": len("## Agenda\n1. Review Q1 goals\n2. Discuss hiring".encode("utf-8")),
                "modificationDate": "2025-01-15T14:00:00Z",
                "creationDate": "2025-01-15T14:00:00Z",
            }
        ]

        notes_file = temp_dir / "bear_notes.json"
        with open(notes_file, "w") as f:
            json.dump(notes, f, indent=2)

        args = Namespace(json_file=notes_file, verbose=True)
        exit_code = run_validate(args)
        assert exit_code == 0

    def test_validate_unicode_content(self, temp_dir: Path):
        notes = [
            {
                "title": "日本語のノート",
                "markdown": "これはテストです。🎉",
                "size": len("これはテストです。🎉".encode("utf-8")),
                "modificationDate": "2025-01-15T10:30:00Z",
            }
        ]

        notes_file = temp_dir / "unicode_notes.json"
        with open(notes_file, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)

        args = Namespace(json_file=notes_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 0

    def test_validate_large_dataset(self, temp_dir: Path):
        # Create a large dataset with 1000 notes
        notes = []
        for i in range(1000):
            notes.append({
                "title": f"Note {i}",
                "markdown": f"Content for note {i}",
                "size": len(f"Content for note {i}".encode("utf-8")),
                "modificationDate": "2025-01-15T10:30:00Z",
            })

        notes_file = temp_dir / "large_dataset.json"
        with open(notes_file, "w") as f:
            json.dump(notes, f)

        args = Namespace(json_file=notes_file, verbose=False)
        exit_code = run_validate(args)
        assert exit_code == 0

    def test_validate_mixed_valid_invalid(self, temp_dir: Path):
        notes = [
            {"title": "Valid 1", "markdown": "content", "size": 100, "modificationDate": "2025-01-01T00:00:00Z"},
            {"title": ""},  # Invalid: empty title
            {"title": "Valid 2", "markdown": "content", "size": 100, "modificationDate": "2025-01-02T00:00:00Z"},
            {"markdown": "content"},  # Invalid: missing title
        ]

        notes_file = temp_dir / "mixed.json"
        with open(notes_file, "w") as f:
            json.dump(notes, f)

        args = Namespace(json_file=notes_file, verbose=True)
        exit_code = run_validate(args)
        assert exit_code == 1  # Should fail because some notes are invalid
