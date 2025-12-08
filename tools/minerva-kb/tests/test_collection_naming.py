import pytest

from minerva_kb.utils.collection_naming import (
    sanitize_collection_name,
    validate_collection_name_format,
)


def test_sanitize_lowercases_and_replaces_spaces():
    assert sanitize_collection_name("/tmp/My Repo") == "my-repo"


def test_sanitize_replaces_underscores():
    assert sanitize_collection_name("project_name") == "project-name"


def test_sanitize_removes_special_characters():
    assert sanitize_collection_name("Repo!@#Name$") == "reponame"


def test_sanitize_collapses_hyphens_and_trims():
    assert sanitize_collection_name("---Fancy___Repo---") == "fancy-repo"


def test_sanitize_rejects_too_short_names():
    with pytest.raises(ValueError):
        sanitize_collection_name("ab")


def test_sanitize_rejects_too_long_names():
    long_name = "a" * 513
    with pytest.raises(ValueError):
        sanitize_collection_name(long_name)


def test_sanitize_rejects_all_special_characters():
    with pytest.raises(ValueError):
        sanitize_collection_name("!!!")


def test_sanitize_accepts_path_objects(tmp_path):
    repo_dir = tmp_path / "Sample Repo"
    assert sanitize_collection_name(repo_dir) == "sample-repo"


def test_validate_collection_name_format_accepts_valid_name():
    validate_collection_name_format("valid-name")


def test_validate_collection_name_format_rejects_invalid_characters():
    with pytest.raises(ValueError):
        validate_collection_name_format("Invalid_Name")
