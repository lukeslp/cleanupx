"""
Tests for cleanupx_core.processors.legacy.deduper

Covers:
- get_file_hash()          – pure hashing logic
- detect_duplicates()      – core deduplication algorithm
- DedupeProcessor.process() / process_directory()
- DedupeProcessor.delete_duplicates()
- TextDedupeProcessor internals (_split_into_paragraphs, _calculate_hash,
  _calculate_similarity, process, process_directory)
"""

import hashlib
from pathlib import Path

import pytest

from cleanupx_core.processors.legacy.deduper import (
    DedupeProcessor,
    TextDedupeProcessor,
    detect_duplicates,
    get_file_hash,
)


# ---------------------------------------------------------------------------
# get_file_hash
# ---------------------------------------------------------------------------

class TestGetFileHash:
    def test_returns_sha256_hex(self, tmp_path):
        content = b"hello cleanupx"
        f = tmp_path / "test.bin"
        f.write_bytes(content)
        result = get_file_hash(f)
        expected = hashlib.sha256(content).hexdigest()
        assert result == expected

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(b"content A")
        b.write_bytes(b"content B")
        assert get_file_hash(a) != get_file_hash(b)

    def test_identical_content_same_hash(self, tmp_path):
        data = b"same data everywhere"
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(data)
        b.write_bytes(data)
        assert get_file_hash(a) == get_file_hash(b)

    def test_returns_none_for_missing_file(self, tmp_path):
        result = get_file_hash(tmp_path / "nonexistent.bin")
        assert result is None

    def test_empty_file_returns_hash(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = get_file_hash(f)
        assert isinstance(result, str) and len(result) == 64


# ---------------------------------------------------------------------------
# detect_duplicates
# ---------------------------------------------------------------------------

class TestDetectDuplicates:
    def test_empty_directory_returns_empty(self, tmp_path):
        result = detect_duplicates(tmp_path)
        assert result == {}

    def test_no_duplicates_returns_empty(self, tmp_path):
        (tmp_path / "a.txt").write_text("AAA", encoding="utf-8")
        (tmp_path / "b.txt").write_text("BBB", encoding="utf-8")
        result = detect_duplicates(tmp_path)
        assert result == {}

    def test_detects_exact_duplicates(self, tmp_path):
        content = "duplicate content\n" * 10
        (tmp_path / "dup1.txt").write_text(content, encoding="utf-8")
        (tmp_path / "dup2.txt").write_text(content, encoding="utf-8")
        result = detect_duplicates(tmp_path)
        # Exactly one group with two files
        assert len(result) == 1
        group = list(result.values())[0]
        assert len(group) == 2

    def test_three_way_duplicate(self, tmp_path):
        content = "triplicate\n" * 5
        for name in ["x.txt", "y.txt", "z.txt"]:
            (tmp_path / name).write_text(content, encoding="utf-8")
        result = detect_duplicates(tmp_path)
        assert len(result) == 1
        assert len(list(result.values())[0]) == 3

    def test_invalid_directory_returns_empty(self, tmp_path):
        result = detect_duplicates(tmp_path / "nonexistent")
        assert result == {}

    def test_recursive_flag_finds_nested_duplicates(self, tmp_path):
        content = "nested dup\n" * 5
        (tmp_path / "top.txt").write_text(content, encoding="utf-8")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.txt").write_text(content, encoding="utf-8")

        # non-recursive should miss the nested file
        non_recursive = detect_duplicates(tmp_path, recursive=False)
        assert non_recursive == {}

        # recursive should find both
        recursive = detect_duplicates(tmp_path, recursive=True)
        assert len(recursive) == 1
        assert len(list(recursive.values())[0]) == 2

    def test_file_type_filter(self, tmp_path):
        content = "same\n" * 5
        (tmp_path / "a.txt").write_text(content, encoding="utf-8")
        (tmp_path / "b.txt").write_text(content, encoding="utf-8")
        (tmp_path / "a.py").write_text(content, encoding="utf-8")
        (tmp_path / "b.py").write_text(content, encoding="utf-8")

        txt_only = detect_duplicates(tmp_path, file_types={".txt"})
        assert len(txt_only) == 1
        group = list(txt_only.values())[0]
        assert all(str(p).endswith(".txt") for p in group)


# ---------------------------------------------------------------------------
# DedupeProcessor
# ---------------------------------------------------------------------------

class TestDedupeProcessor:
    def test_process_returns_hash(self, tmp_path):
        content = b"processor content"
        f = tmp_path / "file.bin"
        f.write_bytes(content)
        processor = DedupeProcessor()
        cache = {}
        result = processor.process(f, cache)
        expected_hash = hashlib.sha256(content).hexdigest()
        assert result["hash"] == expected_hash
        assert result["size"] == len(content)
        assert result["error"] is None

    def test_process_uses_cache(self, tmp_path):
        f = tmp_path / "cached.txt"
        f.write_text("cached content", encoding="utf-8")
        processor = DedupeProcessor()
        fake_hash = "a" * 64
        cache = {str(f): {"hash": fake_hash}}
        result = processor.process(f, cache)
        assert result["hash"] == fake_hash

    def test_process_missing_file_returns_error(self, tmp_path):
        processor = DedupeProcessor()
        result = processor.process(tmp_path / "gone.txt", {})
        assert result["error"] is not None

    def test_process_directory_no_duplicates(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa", encoding="utf-8")
        (tmp_path / "b.txt").write_text("bbb", encoding="utf-8")
        processor = DedupeProcessor()
        result = processor.process_directory(tmp_path)
        assert result["duplicate_groups"] == []
        assert result["total_duplicates"] == 0

    def test_process_directory_finds_duplicates(self, tmp_path):
        content = "identical\n" * 20
        (tmp_path / "d1.txt").write_text(content, encoding="utf-8")
        (tmp_path / "d2.txt").write_text(content, encoding="utf-8")
        processor = DedupeProcessor()
        result = processor.process_directory(tmp_path)
        assert result["total_duplicates"] == 1
        assert len(result["duplicate_groups"]) == 1
        group = result["duplicate_groups"][0]
        assert group["count"] == 2

    def test_delete_duplicates_removes_files(self, tmp_path):
        content = "delete me\n" * 5
        a = tmp_path / "keep.txt"
        b = tmp_path / "remove.txt"
        a.write_text(content, encoding="utf-8")
        b.write_text(content, encoding="utf-8")

        processor = DedupeProcessor()
        duplicate_groups = {"key": [a, b]}
        result = processor.delete_duplicates(duplicate_groups, keep_first=True)

        assert a.exists()
        assert not b.exists()
        assert result["total_deleted"] == 1
        assert result["total_size_saved"] > 0

    def test_delete_duplicates_keep_first_false(self, tmp_path):
        content = "all gone\n"
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text(content, encoding="utf-8")
        b.write_text(content, encoding="utf-8")
        processor = DedupeProcessor()
        processor.delete_duplicates({"k": [a, b]}, keep_first=False)
        # Both deleted
        assert not a.exists()
        assert not b.exists()


# ---------------------------------------------------------------------------
# TextDedupeProcessor internals
# ---------------------------------------------------------------------------

class TestTextDedupeProcessor:
    def setup_method(self):
        self.proc = TextDedupeProcessor()

    # _split_into_paragraphs
    def test_split_single_paragraph(self):
        text = "Just one paragraph here."
        result = self.proc._split_into_paragraphs(text)
        assert result == ["Just one paragraph here."]

    def test_split_multiple_paragraphs(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        result = self.proc._split_into_paragraphs(text)
        assert len(result) == 3

    def test_split_empty_string(self):
        result = self.proc._split_into_paragraphs("")
        assert result == []

    def test_split_strips_whitespace(self):
        text = "  Leading whitespace.\n\n  Also leading."
        result = self.proc._split_into_paragraphs(text)
        assert all(not r.startswith(" ") for r in result)

    # _calculate_hash
    def test_calculate_hash_normalises_whitespace(self):
        # Multiple spaces -> single space, case lowered
        h1 = self.proc._calculate_hash("Hello   World")
        h2 = self.proc._calculate_hash("hello world")
        assert h1 == h2

    def test_calculate_hash_strips_markdown(self):
        # The implementation strips #, *, _ etc. but does NOT call .strip()
        # afterwards, so a leading "#" leaves a leading space. The key
        # property we test is that multiple equivalent whitespace-and-
        # markdown variants produce the *same* hash as each other.
        h1 = self.proc._calculate_hash("**Hello** _world_")
        h2 = self.proc._calculate_hash("Hello world")
        assert h1 == h2

    def test_calculate_hash_different_content(self):
        h1 = self.proc._calculate_hash("content A")
        h2 = self.proc._calculate_hash("content B")
        assert h1 != h2

    # _calculate_similarity
    def test_similarity_identical_content(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        content = "shared content here\n\nmore shared content"
        a.write_text(content, encoding="utf-8")
        b.write_text(content, encoding="utf-8")
        f1 = self.proc.process(a, {})
        f2 = self.proc.process(b, {})
        sim = self.proc._calculate_similarity(f1, f2)
        assert sim == pytest.approx(1.0)

    def test_similarity_totally_different(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("aardvark apple avenue asterisk", encoding="utf-8")
        b.write_text("zebra zipcode zeppelin zoology", encoding="utf-8")
        f1 = self.proc.process(a, {})
        f2 = self.proc.process(b, {})
        sim = self.proc._calculate_similarity(f1, f2)
        assert sim < 0.5

    # process (single file)
    def test_process_reads_content(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("Hello cleanupx", encoding="utf-8")
        result = self.proc.process(f, {})
        assert result["content"] == "Hello cleanupx"
        assert result["hash"] is not None
        assert result["error"] is None

    def test_process_unsupported_extension_returns_error(self, tmp_path):
        f = tmp_path / "binary.exe"
        f.write_bytes(b"\x00\x01\x02")
        result = self.proc.process(f, {})
        assert result["error"] is not None

    def test_process_missing_file_returns_error(self, tmp_path):
        result = self.proc.process(tmp_path / "missing.md", {})
        assert result["error"] is not None

    # process_directory
    def test_process_directory_exact_duplicates(self, tmp_path):
        content = "Duplicate markdown content\n\nMore content here.\n"
        (tmp_path / "d1.md").write_text(content, encoding="utf-8")
        (tmp_path / "d2.md").write_text(content, encoding="utf-8")
        result = self.proc.process_directory(tmp_path)
        assert result["total_duplicates"] >= 1
        assert len(result["exact_duplicates"]) >= 1

    def test_process_directory_no_duplicates(self, tmp_path):
        (tmp_path / "a.txt").write_text("unique A", encoding="utf-8")
        (tmp_path / "b.txt").write_text("unique B", encoding="utf-8")
        result = self.proc.process_directory(tmp_path)
        assert result["total_duplicates"] == 0
        assert result["exact_duplicates"] == []

    def test_process_directory_invalid_path(self, tmp_path):
        result = self.proc.process_directory(tmp_path / "nonexistent")
        assert result["error"] is not None
