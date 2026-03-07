"""
Tests for cleanupx_core.processors.integrated.utils

Covers pure/near-pure utility functions:
- get_file_hash()
- is_protected_file()
- normalize_path()
- ensure_metadata_dir()
- get_file_metadata()
- strip_media_suffixes()
- get_description_path()
- scramble_filenames()  (the standalone utils version)
"""

import hashlib
import os
from pathlib import Path

import pytest

from cleanupx_core.processors.integrated.utils import (
    ensure_metadata_dir,
    get_description_path,
    get_file_hash,
    get_file_metadata,
    is_protected_file,
    normalize_path,
    scramble_filenames,
    strip_media_suffixes,
)


# ---------------------------------------------------------------------------
# get_file_hash
# ---------------------------------------------------------------------------

class TestGetFileHash:
    def test_sha256_matches(self, tmp_path):
        data = b"test data for hash"
        f = tmp_path / "test.bin"
        f.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        assert get_file_hash(f) == expected

    def test_returns_empty_string_on_missing_file(self, tmp_path):
        result = get_file_hash(tmp_path / "missing.bin")
        assert result == ""

    def test_same_content_same_hash(self, tmp_path):
        data = b"identical"
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(data)
        b.write_bytes(data)
        assert get_file_hash(a) == get_file_hash(b)

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(b"A content")
        b.write_bytes(b"B content")
        assert get_file_hash(a) != get_file_hash(b)

    def test_empty_file_returns_hash(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = get_file_hash(f)
        # SHA-256 of empty bytes is a valid 64-char hex string
        assert len(result) == 64


# ---------------------------------------------------------------------------
# is_protected_file
# ---------------------------------------------------------------------------

class TestIsProtectedFile:
    PATTERNS = ["*.exe", ".git*", "__pycache__*", "requirements.txt", "*.pyc"]

    def test_exe_is_protected(self, tmp_path):
        f = tmp_path / "program.exe"
        assert is_protected_file(f, self.PATTERNS)

    def test_pyc_is_protected(self, tmp_path):
        f = tmp_path / "module.pyc"
        assert is_protected_file(f, self.PATTERNS)

    def test_requirements_is_protected(self, tmp_path):
        f = tmp_path / "requirements.txt"
        assert is_protected_file(f, self.PATTERNS)

    def test_git_dir_is_protected(self, tmp_path):
        f = tmp_path / ".gitignore"
        assert is_protected_file(f, self.PATTERNS)

    def test_normal_py_file_not_protected(self, tmp_path):
        f = tmp_path / "my_module.py"
        assert not is_protected_file(f, self.PATTERNS)

    def test_txt_file_not_protected(self, tmp_path):
        f = tmp_path / "readme.txt"
        assert not is_protected_file(f, self.PATTERNS)

    def test_empty_patterns_list(self, tmp_path):
        f = tmp_path / "anything.exe"
        assert not is_protected_file(f, [])


# ---------------------------------------------------------------------------
# normalize_path
# ---------------------------------------------------------------------------

class TestNormalizePath:
    def test_returns_path_object(self, tmp_path):
        result = normalize_path(tmp_path)
        assert isinstance(result, Path)

    def test_resolves_to_absolute(self, tmp_path):
        result = normalize_path(tmp_path)
        assert result.is_absolute()

    def test_string_input_accepted(self, tmp_path):
        result = normalize_path(str(tmp_path))
        assert isinstance(result, Path)

    def test_resolves_dotdot(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        result = normalize_path(sub / ".." / "sub")
        assert result == sub.resolve()


# ---------------------------------------------------------------------------
# ensure_metadata_dir
# ---------------------------------------------------------------------------

class TestEnsureMetadataDir:
    def test_creates_cleanupx_dir(self, tmp_path):
        result = ensure_metadata_dir(tmp_path)
        assert (tmp_path / ".cleanupx").is_dir()

    def test_returns_path_object(self, tmp_path):
        result = ensure_metadata_dir(tmp_path)
        assert isinstance(result, Path)

    def test_idempotent(self, tmp_path):
        ensure_metadata_dir(tmp_path)
        result = ensure_metadata_dir(tmp_path)
        assert result.is_dir()


# ---------------------------------------------------------------------------
# get_file_metadata
# ---------------------------------------------------------------------------

class TestGetFileMetadata:
    def test_returns_name(self, tmp_path):
        f = tmp_path / "myfile.txt"
        f.write_text("hi", encoding="utf-8")
        meta = get_file_metadata(f)
        assert meta["name"] == "myfile.txt"

    def test_returns_size(self, tmp_path):
        f = tmp_path / "sized.txt"
        f.write_bytes(b"1234567890")
        meta = get_file_metadata(f)
        assert meta["size"] == 10

    def test_returns_extension_lowercased(self, tmp_path):
        f = tmp_path / "IMAGE.JPG"
        f.write_bytes(b"\xff\xd8")
        meta = get_file_metadata(f)
        assert meta["extension"] == ".jpg"

    def test_missing_file_returns_empty(self, tmp_path):
        meta = get_file_metadata(tmp_path / "ghost.txt")
        assert meta == {}

    def test_returns_modified_time(self, tmp_path):
        f = tmp_path / "timestamped.txt"
        f.write_text("ts", encoding="utf-8")
        meta = get_file_metadata(f)
        assert "modified" in meta
        assert isinstance(meta["modified"], float)


# ---------------------------------------------------------------------------
# strip_media_suffixes
# ---------------------------------------------------------------------------

class TestStripMediaSuffixes:
    def test_strips_resolution_tag(self):
        result = strip_media_suffixes("My Video [1080p].mp4")
        assert "[1080p]" not in result

    def test_strips_quality_tag(self):
        result = strip_media_suffixes("Song [HQ].mp3")
        assert "[HQ]" not in result

    def test_strips_official_video_tag(self):
        result = strip_media_suffixes("Artist - Song (Official Video).mp4")
        assert "(Official Video)" not in result

    def test_no_suffix_unchanged_base(self):
        result = strip_media_suffixes("PlainFileName")
        assert "PlainFileName" in result

    def test_returns_stripped_string(self):
        result = strip_media_suffixes("Track [MP3] [HQ]")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# get_description_path
# ---------------------------------------------------------------------------

class TestGetDescriptionPath:
    def test_returns_path_in_cleanupx_dir(self, tmp_path):
        f = tmp_path / "image.jpg"
        f.write_bytes(b"\xff\xd8")
        desc_path = get_description_path(f)
        assert ".cleanupx" in str(desc_path)

    def test_suffix_is_md(self, tmp_path):
        f = tmp_path / "photo.png"
        f.write_bytes(b"\x89PNG")
        desc_path = get_description_path(f)
        assert desc_path.suffix == ".md"

    def test_stem_based_on_original_name(self, tmp_path):
        f = tmp_path / "myimage.jpg"
        f.write_bytes(b"\xff\xd8")
        desc_path = get_description_path(f)
        assert "myimage" in desc_path.name


# ---------------------------------------------------------------------------
# scramble_filenames (utils version)
# ---------------------------------------------------------------------------

class TestScrambleFilenames:
    def test_renames_files(self, tmp_path):
        original_names = {"alpha.txt", "beta.txt", "gamma.md"}
        for name in original_names:
            (tmp_path / name).write_text("content", encoding="utf-8")

        result = scramble_filenames(str(tmp_path), recursive=False)
        current_names = {f.name for f in tmp_path.iterdir() if f.is_file()}

        assert current_names.isdisjoint(original_names), (
            "At least one original filename survived scrambling"
        )
        assert len(result["renamed"]) == 3
        assert len(result["failed"]) == 0

    def test_preserves_extensions(self, tmp_path):
        (tmp_path / "file.txt").write_text("hi", encoding="utf-8")
        scramble_filenames(str(tmp_path), recursive=False)
        # All files should still have .txt extension
        exts = [f.suffix for f in tmp_path.iterdir() if f.is_file()]
        assert all(e == ".txt" for e in exts)

    def test_returns_renamed_list(self, tmp_path):
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")
        result = scramble_filenames(str(tmp_path))
        assert isinstance(result["renamed"], list)
        assert len(result["renamed"]) >= 1

    def test_recursive_renames_nested(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "top.txt").write_text("top", encoding="utf-8")
        (sub / "nested.txt").write_text("nested", encoding="utf-8")
        result = scramble_filenames(str(tmp_path), recursive=True)
        assert len(result["renamed"]) == 2
