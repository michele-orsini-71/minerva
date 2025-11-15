import pytest
from github_webhook_orchestrator.reindex import detect_markdown_changes


class TestDetectMarkdownChanges:
    def test_markdown_file_added(self):
        commits = [
            {
                'added': ['README.md'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_markdown_file_modified(self):
        commits = [
            {
                'added': [],
                'modified': ['docs/guide.md'],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_markdown_file_removed(self):
        commits = [
            {
                'added': [],
                'modified': [],
                'removed': ['old-doc.md']
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_mdx_file_added(self):
        commits = [
            {
                'added': ['component.mdx'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_mdx_file_modified(self):
        commits = [
            {
                'added': [],
                'modified': ['docs/page.mdx'],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_no_markdown_files(self):
        commits = [
            {
                'added': ['src/index.js', 'package.json'],
                'modified': ['src/App.tsx'],
                'removed': ['old-file.txt']
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_multiple_commits_with_markdown(self):
        commits = [
            {
                'added': ['src/index.js'],
                'modified': [],
                'removed': []
            },
            {
                'added': ['docs/README.md'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_multiple_commits_without_markdown(self):
        commits = [
            {
                'added': ['src/index.js'],
                'modified': [],
                'removed': []
            },
            {
                'added': ['src/App.tsx'],
                'modified': ['package.json'],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_mixed_files_with_markdown(self):
        commits = [
            {
                'added': ['src/index.js', 'README.md', 'package.json'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_empty_commits_list(self):
        commits = []
        assert detect_markdown_changes(commits) is False

    def test_commit_without_file_lists(self):
        commits = [
            {
                'author': 'Test User',
                'message': 'Test commit'
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_commit_with_empty_file_lists(self):
        commits = [
            {
                'added': [],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_nested_markdown_file(self):
        commits = [
            {
                'added': ['docs/api/endpoints/authentication.md'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_markdown_in_all_categories(self):
        commits = [
            {
                'added': ['new.md'],
                'modified': ['updated.md'],
                'removed': ['deleted.md']
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_case_sensitive_md_extension(self):
        commits = [
            {
                'added': ['README.MD', 'guide.Md'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_file_with_md_in_name_but_different_extension(self):
        commits = [
            {
                'added': ['markdown-parser.js', 'readme.txt'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_invalid_commit_structure(self):
        commits = [
            'not a dict',
            123,
            None
        ]
        assert detect_markdown_changes(commits) is False

    def test_invalid_file_list_types(self):
        commits = [
            {
                'added': 'not-a-list',
                'modified': 123,
                'removed': None
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_file_list_with_non_string_items(self):
        commits = [
            {
                'added': [123, None, {'file': 'test.md'}],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is False

    def test_markdown_file_first_in_multiple_commits(self):
        commits = [
            {
                'added': ['README.md'],
                'modified': [],
                'removed': []
            },
            {
                'added': ['src/index.js'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_markdown_file_last_in_multiple_commits(self):
        commits = [
            {
                'added': ['src/index.js'],
                'modified': [],
                'removed': []
            },
            {
                'added': ['README.md'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_real_github_webhook_structure(self):
        commits = [
            {
                'id': '1234567890abcdef',
                'message': 'Update documentation',
                'author': {'name': 'Test User', 'email': 'test@example.com'},
                'added': ['docs/getting-started.md'],
                'modified': ['README.md'],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True

    def test_hidden_markdown_file(self):
        commits = [
            {
                'added': ['.github/README.md'],
                'modified': [],
                'removed': []
            }
        ]
        assert detect_markdown_changes(commits) is True
