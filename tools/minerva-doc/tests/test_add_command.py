import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from minerva_doc.commands.add import (
    validate_collection_name,
    validate_json_file,
)


class TestValidateJsonFile:
    def test_nonexistent_file(self, capsys):
        result = validate_json_file("/nonexistent/file.json")
        assert result is None

        captured = capsys.readouterr()
        assert "Error: JSON file does not exist" in captured.out
        assert "Check that the path is correct" in captured.out

    def test_directory_instead_of_file(self, tmp_path, capsys):
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        result = validate_json_file(str(dir_path))
        assert result is None

        captured = capsys.readouterr()
        assert "Error: Path is not a file" in captured.out
        assert "points to a directory" in captured.out

    def test_valid_json_file(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text("[]")

        result = validate_json_file(str(json_file))
        assert result is not None
        assert result.exists()
        assert result.is_file()

    def test_non_json_extension(self, tmp_path, capsys):
        text_file = tmp_path / "test.txt"
        text_file.write_text("[]")

        result = validate_json_file(str(text_file))
        assert result is not None

        captured = capsys.readouterr()
        assert "Warning: File does not have .json extension" in captured.out

    def test_expanduser_home_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        test_file = tmp_path / "test.json"
        test_file.write_text("[]")

        result = validate_json_file("~/test.json")
        assert result is not None
        assert result == test_file.resolve()


class TestValidateCollectionName:
    def test_empty_name(self, capsys):
        result = validate_collection_name("")
        assert result is False

        captured = capsys.readouterr()
        assert "Error: Collection name cannot be empty" in captured.out
        assert "Provide a name using --name flag" in captured.out

    def test_name_too_long(self, capsys):
        long_name = "a" * 101
        result = validate_collection_name(long_name)
        assert result is False

        captured = capsys.readouterr()
        assert "Error: Collection name too long" in captured.out
        assert "101 characters" in captured.out

    def test_invalid_characters(self, capsys):
        invalid_names = [
            "name<test",
            "name>test",
            "name:test",
            'name"test',
            "name/test",
            "name\\test",
            "name|test",
            "name?test",
            "name*test",
        ]

        for name in invalid_names:
            result = validate_collection_name(name)
            assert result is False

        captured = capsys.readouterr()
        assert "invalid characters" in captured.out.lower()
        assert "letters, numbers, hyphens, and underscores" in captured.out

    def test_valid_names(self):
        valid_names = [
            "simple",
            "with-hyphens",
            "with_underscores",
            "with123numbers",
            "MixedCase",
            "a",
            "a" * 100,
        ]

        for name in valid_names:
            result = validate_collection_name(name)
            assert result is True, f"Expected '{name}' to be valid"


class TestEdgeCases:
    def test_empty_json_array(self, tmp_path):
        json_file = tmp_path / "empty.json"
        json_file.write_text("[]")

        result = validate_json_file(str(json_file))
        assert result is not None
        assert result.exists()

    def test_malformed_json(self, tmp_path):
        json_file = tmp_path / "malformed.json"
        json_file.write_text("{invalid json")

        result = validate_json_file(str(json_file))
        assert result is not None

    def test_permission_denied_file(self, tmp_path, capsys):
        json_file = tmp_path / "no_permission.json"
        json_file.write_text("[]")
        json_file.chmod(0o000)

        try:
            result = validate_json_file(str(json_file))
            assert result is None

            captured = capsys.readouterr()
            assert "Error: Cannot resolve path" in captured.out or "Permission" in captured.out
        finally:
            json_file.chmod(0o644)

    def test_relative_path_resolution(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        json_file = tmp_path / "test.json"
        json_file.write_text("[]")

        result = validate_json_file("test.json")
        assert result is not None
        assert result.is_absolute()
        assert result == json_file.resolve()

    def test_symlink_resolution(self, tmp_path):
        json_file = tmp_path / "original.json"
        json_file.write_text("[]")

        symlink = tmp_path / "link.json"
        symlink.symlink_to(json_file)

        result = validate_json_file(str(symlink))
        assert result is not None
        assert result.resolve() == json_file.resolve()


class TestCollisionScenarios:
    @patch("minerva_doc.commands.add.check_collection_exists")
    def test_collision_with_minerva_kb(self, mock_check, capsys):
        from minerva_doc.commands.add import check_collision

        mock_check.return_value = (True, "minerva-kb")

        result = check_collision("test-collection")
        assert result is False

        captured = capsys.readouterr()
        assert "Error: Collection 'test-collection' already exists" in captured.out
        assert "Owner: minerva-kb" in captured.out
        assert "minerva-kb remove" in captured.out

    @patch("minerva_doc.commands.add.check_collection_exists")
    def test_collision_with_minerva_doc(self, mock_check, capsys):
        from minerva_doc.commands.add import check_collision

        mock_check.return_value = (True, "minerva-doc")

        result = check_collision("test-collection")
        assert result is False

        captured = capsys.readouterr()
        assert "Error: Collection 'test-collection' already exists" in captured.out
        assert "Owner: minerva-doc" in captured.out
        assert "minerva-doc update" in captured.out or "minerva-doc remove" in captured.out

    @patch("minerva_doc.commands.add.check_collection_exists")
    def test_collision_unmanaged(self, mock_check, capsys):
        from minerva_doc.commands.add import check_collision

        mock_check.return_value = (True, None)

        result = check_collision("test-collection")
        assert result is False

        captured = capsys.readouterr()
        assert "Error: Collection 'test-collection' already exists" in captured.out
        assert "Owner: unknown" in captured.out

    @patch("minerva_doc.commands.add.check_collection_exists")
    def test_no_collision(self, mock_check):
        from minerva_doc.commands.add import check_collision

        mock_check.return_value = (False, None)

        result = check_collision("test-collection")
        assert result is True
