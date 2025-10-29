import hashlib
import pytest

from minerva.indexing.chunking import compute_content_hash


class TestComputeContentHash:
    def test_returns_sha256_hash(self):
        title = "Test Note"
        markdown = "# Content"
        result = compute_content_hash(title, markdown)

        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_deterministic_same_input_produces_same_hash(self):
        title = "Consistent Title"
        markdown = "Consistent content here"

        hash1 = compute_content_hash(title, markdown)
        hash2 = compute_content_hash(title, markdown)
        hash3 = compute_content_hash(title, markdown)

        assert hash1 == hash2 == hash3

    def test_different_titles_produce_different_hashes(self):
        markdown = "Same content"

        hash1 = compute_content_hash("Title A", markdown)
        hash2 = compute_content_hash("Title B", markdown)

        assert hash1 != hash2

    def test_different_markdown_produces_different_hashes(self):
        title = "Same Title"

        hash1 = compute_content_hash(title, "Content A")
        hash2 = compute_content_hash(title, "Content B")

        assert hash1 != hash2

    def test_empty_strings(self):
        hash_empty_both = compute_content_hash("", "")
        hash_empty_title = compute_content_hash("", "content")
        hash_empty_markdown = compute_content_hash("title", "")

        assert len(hash_empty_both) == 64
        assert len(hash_empty_title) == 64
        assert len(hash_empty_markdown) == 64
        assert hash_empty_both != hash_empty_title
        assert hash_empty_both != hash_empty_markdown
        assert hash_empty_title != hash_empty_markdown

    def test_unicode_content(self):
        title = "Unicode Title 你好 🎉"
        markdown = "Content with émojis 🚀 and spëcial çhars"

        hash_result = compute_content_hash(title, markdown)

        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result)

    def test_special_characters(self):
        title = "Title with\nnewlines\tand\ttabs"
        markdown = "Markdown with | pipes and $ symbols"

        hash_result = compute_content_hash(title, markdown)

        assert len(hash_result) == 64

    def test_very_long_content(self):
        title = "A" * 10000
        markdown = "B" * 100000

        hash_result = compute_content_hash(title, markdown)

        assert len(hash_result) == 64

    def test_matches_manual_sha256_computation(self):
        title = "Test"
        markdown = "Content"

        expected_content = f"{title}|{markdown}"
        expected_hash = hashlib.sha256(expected_content.encode('utf-8')).hexdigest()

        actual_hash = compute_content_hash(title, markdown)

        assert actual_hash == expected_hash

    def test_whitespace_sensitivity(self):
        hash1 = compute_content_hash("Title", "Content")
        hash2 = compute_content_hash("Title ", "Content")
        hash3 = compute_content_hash("Title", " Content")
        hash4 = compute_content_hash("Title", "Content ")

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash1 != hash4
        assert hash2 != hash3
        assert hash3 != hash4

    def test_case_sensitivity(self):
        hash1 = compute_content_hash("Title", "Content")
        hash2 = compute_content_hash("title", "content")
        hash3 = compute_content_hash("TITLE", "CONTENT")

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3


class TestContentHashIntegration:
    def test_hash_identifies_content_changes(self):
        original_title = "My Note"
        original_markdown = "Original content"
        original_hash = compute_content_hash(original_title, original_markdown)

        modified_markdown = "Modified content"
        modified_hash = compute_content_hash(original_title, modified_markdown)

        assert original_hash != modified_hash

    def test_hash_identifies_title_changes(self):
        original_title = "Original Title"
        markdown = "Content stays same"
        original_hash = compute_content_hash(original_title, markdown)

        modified_title = "Modified Title"
        modified_hash = compute_content_hash(modified_title, markdown)

        assert original_hash != modified_hash

    def test_unchanged_note_has_same_hash(self):
        title = "Unchanged Note"
        markdown = "This content never changes"

        hash_t0 = compute_content_hash(title, markdown)
        hash_t1 = compute_content_hash(title, markdown)
        hash_t2 = compute_content_hash(title, markdown)

        assert hash_t0 == hash_t1 == hash_t2

    def test_collision_resistance_similar_content(self):
        hashes = set()

        for i in range(100):
            title = f"Note {i}"
            markdown = f"Content for note number {i}"
            hash_val = compute_content_hash(title, markdown)
            hashes.add(hash_val)

        assert len(hashes) == 100
