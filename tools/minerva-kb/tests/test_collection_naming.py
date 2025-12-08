import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from minerva_kb.utils.collection_naming import sanitize_collection_name


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
