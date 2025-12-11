import pytest

from minerva_kb.utils.collection_naming import (
    sanitize_collection_name,
    validate_collection_name_format,
)


def test_sanitize_lowercases_and_replaces_spaces():
    assert sanitize_collection_name("/tmp/My Repo") == "my-repo-kb"


def test_sanitize_replaces_underscores():
    assert sanitize_collection_name("project_name") == "project-name-kb"


def test_sanitize_removes_special_characters():
    assert sanitize_collection_name("Repo!@#Name$") == "reponame-kb"


def test_sanitize_collapses_hyphens_and_trims():
    assert sanitize_collection_name("---Fancy___Repo---") == "fancy-repo-kb"


def test_sanitize_accepts_short_names_with_kb_suffix():
    # Short names now work because -kb suffix guarantees 3+ characters
    assert sanitize_collection_name("ab") == "ab-kb"
    assert sanitize_collection_name("x") == "x-kb"


def test_sanitize_rejects_too_long_names():
    long_name = "a" * 513
    with pytest.raises(ValueError):
        sanitize_collection_name(long_name)


def test_sanitize_rejects_all_special_characters():
    with pytest.raises(ValueError):
        sanitize_collection_name("!!!")


def test_sanitize_accepts_path_objects(tmp_path):
    repo_dir = tmp_path / "Sample Repo"
    assert sanitize_collection_name(repo_dir) == "sample-repo-kb"


def test_sanitize_handles_folders_already_ending_with_kb():
    # Edge case: folder already ends with -kb gets double suffix
    assert sanitize_collection_name("myproject-kb") == "myproject-kb-kb"
    assert sanitize_collection_name("docs-kb") == "docs-kb-kb"


def test_validate_collection_name_format_accepts_valid_name():
    validate_collection_name_format("valid-name")
    validate_collection_name_format("valid-name-kb")


def test_validate_collection_name_format_rejects_invalid_characters():
    with pytest.raises(ValueError):
        validate_collection_name_format("Invalid_Name")
