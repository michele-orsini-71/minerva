import pytest
from typing import Any

from minerva.common.schemas import (
    validate_note,
    validate_notes_array,
    validate_notes_file,
    get_schema_summary,
    NOTE_SCHEMA,
    NOTES_ARRAY_SCHEMA,
)


class TestValidateNote:
    def test_valid_note_with_all_fields(self, valid_note: dict[str, Any]):
        is_valid, errors = validate_note(valid_note, 0)
        assert is_valid is True
        assert len(errors) == 0

    def test_valid_note_without_optional_creation_date(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        del note["creationDate"]
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True
        assert len(errors) == 0

    def test_valid_note_with_custom_fields(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["customField"] = "custom value"
        note["customNumber"] = 42
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True
        assert len(errors) == 0

    def test_valid_note_with_empty_markdown(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["markdown"] = ""
        note["size"] = 0
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_note_not_a_dict(self):
        is_valid, errors = validate_note("not a dict", 5)
        assert is_valid is False
        assert len(errors) == 1
        assert "index 5" in errors[0]
        assert "Expected object" in errors[0]

    def test_invalid_note_missing_title(self, invalid_note_missing_title: dict[str, Any]):
        is_valid, errors = validate_note(invalid_note_missing_title, 0)
        assert is_valid is False
        assert any("Missing required fields" in error and "title" in error for error in errors)

    def test_invalid_note_empty_title(self, invalid_note_empty_title: dict[str, Any]):
        is_valid, errors = validate_note(invalid_note_empty_title, 0)
        assert is_valid is False
        assert any("cannot be empty" in error for error in errors)

    def test_invalid_note_missing_markdown(self, invalid_note_missing_markdown: dict[str, Any]):
        is_valid, errors = validate_note(invalid_note_missing_markdown, 0)
        assert is_valid is False
        assert any("Missing required fields" in error and "markdown" in error for error in errors)

    def test_invalid_note_negative_size(self, invalid_note_negative_size: dict[str, Any]):
        is_valid, errors = validate_note(invalid_note_negative_size, 0)
        assert is_valid is False
        assert any("non-negative" in error for error in errors)

    def test_invalid_note_bad_date_format(self, invalid_note_bad_date_format: dict[str, Any]):
        is_valid, errors = validate_note(invalid_note_bad_date_format, 0)
        assert is_valid is False
        assert any("ISO 8601" in error for error in errors)

    def test_invalid_note_missing_all_required_fields(self):
        note = {}
        is_valid, errors = validate_note(note, 0)
        assert is_valid is False
        assert any("Missing required fields" in error for error in errors)
        error_msg = [e for e in errors if "Missing required fields" in e][0]
        assert "title" in error_msg
        assert "markdown" in error_msg
        assert "size" in error_msg
        assert "modificationDate" in error_msg

    def test_invalid_note_wrong_title_type(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["title"] = 123
        is_valid, errors = validate_note(note, 0)
        assert is_valid is False
        assert any("title" in error and "must be a string" in error for error in errors)

    def test_invalid_note_wrong_markdown_type(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["markdown"] = ["not", "a", "string"]
        is_valid, errors = validate_note(note, 0)
        assert is_valid is False
        assert any("markdown" in error and "must be a string" in error for error in errors)

    def test_invalid_note_wrong_size_type(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["size"] = "100"
        is_valid, errors = validate_note(note, 0)
        assert is_valid is False
        assert any("size" in error and "must be an integer" in error for error in errors)

    def test_invalid_note_wrong_modification_date_type(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["modificationDate"] = 20250115
        is_valid, errors = validate_note(note, 0)
        assert is_valid is False
        assert any("modificationDate" in error and "must be a string" in error for error in errors)

    def test_invalid_note_wrong_creation_date_format(self, valid_note: dict[str, Any]):
        note = valid_note.copy()
        note["creationDate"] = "Jan 15, 2025"
        is_valid, errors = validate_note(note, 0)
        assert is_valid is False
        assert any("creationDate" in error and "ISO 8601" in error for error in errors)

    def test_note_index_in_error_messages(self):
        is_valid, errors = validate_note({}, 42)
        assert is_valid is False
        assert any("index 42" in error for error in errors)


class TestValidateNotesArray:
    def test_valid_notes_array(self, valid_notes_list: list[dict[str, Any]]):
        is_valid, errors = validate_notes_array(valid_notes_list, strict=True)
        assert is_valid is True
        assert len(errors) == 0

    def test_valid_empty_array(self):
        is_valid, errors = validate_notes_array([], strict=True)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_not_an_array(self):
        is_valid, errors = validate_notes_array({"note": "value"}, strict=True)
        assert is_valid is False
        assert len(errors) == 1
        assert "Expected an array" in errors[0]

    def test_invalid_array_with_one_bad_note_strict(self, valid_notes_list: list[dict[str, Any]]):
        notes = valid_notes_list.copy()
        notes.append({"title": ""})  # Invalid: empty title and missing fields
        is_valid, errors = validate_notes_array(notes, strict=True)
        assert is_valid is False
        assert len(errors) >= 1  # Should stop at first error in strict mode

    def test_invalid_array_with_one_bad_note_non_strict(self, valid_notes_list: list[dict[str, Any]]):
        notes = valid_notes_list.copy()
        notes.append({"title": ""})  # Invalid: empty title and missing fields
        is_valid, errors = validate_notes_array(notes, strict=False)
        assert is_valid is False
        assert len(errors) > 1  # Should collect all errors in non-strict mode

    def test_invalid_array_all_bad_notes_non_strict(self):
        notes = [
            {"title": ""},  # Empty title
            {"markdown": "content"},  # Missing title
            {"title": 123, "markdown": "content", "size": 100, "modificationDate": "2025-01-01T00:00:00Z"},  # Wrong type
        ]
        is_valid, errors = validate_notes_array(notes, strict=False)
        assert is_valid is False
        assert len(errors) >= 3  # At least one error per note

    def test_invalid_array_mixed_types(self):
        notes = [
            {"title": "Valid", "markdown": "content", "size": 100, "modificationDate": "2025-01-01T00:00:00Z"},
            "not a note object",
            {"title": "Also Valid", "markdown": "content", "size": 50, "modificationDate": "2025-01-02T00:00:00Z"},
        ]
        is_valid, errors = validate_notes_array(notes, strict=False)
        assert is_valid is False
        assert any("index 1" in error and "Expected object" in error for error in errors)


class TestValidateNotesFile:
    def test_valid_file_data_returns_true(self, valid_notes_list: list[dict[str, Any]]):
        result = validate_notes_file(valid_notes_list, "test.json")
        assert result is True

    def test_invalid_file_data_returns_false(self):
        invalid_data = [{"title": ""}]  # Empty title
        result = validate_notes_file(invalid_data, "invalid.json")
        assert result is False

    def test_invalid_file_with_multiple_errors_returns_false(self):
        invalid_data = [
            {"title": ""},
            {"markdown": "content"},
        ]
        result = validate_notes_file(invalid_data, "invalid.json")
        assert result is False

    def test_empty_array_is_valid(self):
        result = validate_notes_file([], "empty.json")
        assert result is True

    def test_validates_all_notes_in_file(self):
        mixed_data = [
            {"title": "Valid", "markdown": "content", "size": 100, "modificationDate": "2025-01-01T00:00:00Z"},
            {"title": ""},  # Invalid
            {"title": "Also Valid", "markdown": "content", "size": 50, "modificationDate": "2025-01-02T00:00:00Z"},
        ]
        result = validate_notes_file(mixed_data, "mixed.json")
        assert result is False  # Should fail because one note is invalid


class TestGetSchemaSummary:
    def test_schema_summary_contains_required_fields(self):
        summary = get_schema_summary()
        assert "title" in summary
        assert "markdown" in summary
        assert "size" in summary
        assert "modificationDate" in summary

    def test_schema_summary_contains_optional_fields(self):
        summary = get_schema_summary()
        assert "creationDate" in summary
        assert "Optional" in summary or "optional" in summary

    def test_schema_summary_contains_example(self):
        summary = get_schema_summary()
        assert "Example" in summary or "example" in summary
        assert "{" in summary
        assert "}" in summary

    def test_schema_summary_is_non_empty(self):
        summary = get_schema_summary()
        assert len(summary) > 100
        assert isinstance(summary, str)


class TestSchemaConstants:
    def test_note_schema_has_required_fields(self):
        assert "required" in NOTE_SCHEMA
        assert "title" in NOTE_SCHEMA["required"]
        assert "markdown" in NOTE_SCHEMA["required"]
        assert "size" in NOTE_SCHEMA["required"]
        assert "modificationDate" in NOTE_SCHEMA["required"]

    def test_note_schema_allows_additional_properties(self):
        assert NOTE_SCHEMA.get("additionalProperties") is True

    def test_notes_array_schema_is_array_type(self):
        assert NOTES_ARRAY_SCHEMA["type"] == "array"
        assert "items" in NOTES_ARRAY_SCHEMA


class TestISODateValidation:
    def test_valid_iso_dates(self):
        valid_dates = [
            "2025-01-15T10:30:00Z",
            "2025-01-15T10:30:00",
            "2025-01-15T10:30:00+00:00",
            "2025-01-15T10:30:00-05:00",
            "2025-12-31T23:59:59Z",
        ]
        for date in valid_dates:
            note = {
                "title": "Test",
                "markdown": "content",
                "size": 10,
                "modificationDate": date,
            }
            is_valid, errors = validate_note(note, 0)
            assert is_valid is True, f"Date {date} should be valid, but got errors: {errors}"

    def test_invalid_iso_dates(self):
        invalid_dates = [
            "2025-01-15",  # Missing time
            "01/15/2025",  # Wrong format
            "Jan 15, 2025",  # Wrong format
            "2025-01-15 10:30:00",  # Space instead of T
            "15-01-2025T10:30:00",  # Wrong date order
            "",  # Empty string
        ]
        for date in invalid_dates:
            note = {
                "title": "Test",
                "markdown": "content",
                "size": 10,
                "modificationDate": date,
            }
            is_valid, errors = validate_note(note, 0)
            assert is_valid is False, f"Date {date} should be invalid"
            assert any("ISO 8601" in error for error in errors), f"Expected ISO 8601 error for date {date}"


class TestEdgeCases:
    def test_note_with_very_long_title(self):
        note = {
            "title": "A" * 10000,
            "markdown": "content",
            "size": 100,
            "modificationDate": "2025-01-15T10:30:00Z",
        }
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True

    def test_note_with_very_long_markdown(self):
        long_content = "x" * 100000
        note = {
            "title": "Test",
            "markdown": long_content,
            "size": len(long_content.encode("utf-8")),
            "modificationDate": "2025-01-15T10:30:00Z",
        }
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True

    def test_note_with_unicode_content(self):
        note = {
            "title": "Unicode Test 你好 🎉",
            "markdown": "Content with émojis 🚀 and spëcial çhars",
            "size": len("Content with émojis 🚀 and spëcial çhars".encode("utf-8")),
            "modificationDate": "2025-01-15T10:30:00Z",
        }
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True

    def test_note_with_zero_size(self):
        note = {
            "title": "Empty Note",
            "markdown": "",
            "size": 0,
            "modificationDate": "2025-01-15T10:30:00Z",
        }
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True

    def test_note_with_large_size(self):
        note = {
            "title": "Large Note",
            "markdown": "content",
            "size": 999999999,
            "modificationDate": "2025-01-15T10:30:00Z",
        }
        is_valid, errors = validate_note(note, 0)
        assert is_valid is True

    def test_array_with_many_notes(self):
        notes = []
        for i in range(1000):
            notes.append({
                "title": f"Note {i}",
                "markdown": f"Content {i}",
                "size": 10,
                "modificationDate": "2025-01-15T10:30:00Z",
            })
        is_valid, errors = validate_notes_array(notes, strict=False)
        assert is_valid is True
        assert len(errors) == 0
