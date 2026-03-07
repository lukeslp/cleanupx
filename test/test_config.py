"""
Tests for cleanupx_core.processors.integrated.config

Verifies that extension sets are complete, non-overlapping in critical ways,
and that constants have the expected types.
"""

import pytest

from cleanupx_core.processors.integrated.config import (
    ARCHIVE_EXTENSIONS,
    CODE_EXTENSIONS,
    DEFAULT_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MEDIA_EXTENSIONS,
    PROTECTED_PATTERNS,
    TEXT_EXTENSIONS,
)


class TestExtensionSets:
    def test_image_extensions_are_sets(self):
        assert isinstance(IMAGE_EXTENSIONS, set)

    def test_text_extensions_are_sets(self):
        assert isinstance(TEXT_EXTENSIONS, set)

    def test_code_extensions_are_sets(self):
        assert isinstance(CODE_EXTENSIONS, set)

    def test_document_extensions_are_sets(self):
        assert isinstance(DOCUMENT_EXTENSIONS, set)

    def test_media_extensions_are_sets(self):
        assert isinstance(MEDIA_EXTENSIONS, set)

    def test_archive_extensions_are_sets(self):
        assert isinstance(ARCHIVE_EXTENSIONS, set)

    def test_all_extensions_start_with_dot(self):
        all_exts = (
            IMAGE_EXTENSIONS
            | TEXT_EXTENSIONS
            | CODE_EXTENSIONS
            | DOCUMENT_EXTENSIONS
            | MEDIA_EXTENSIONS
            | ARCHIVE_EXTENSIONS
        )
        for ext in all_exts:
            assert ext.startswith("."), f"Extension without dot: {ext!r}"

    def test_all_extensions_are_lowercase(self):
        all_exts = (
            IMAGE_EXTENSIONS
            | TEXT_EXTENSIONS
            | CODE_EXTENSIONS
            | DOCUMENT_EXTENSIONS
            | MEDIA_EXTENSIONS
            | ARCHIVE_EXTENSIONS
        )
        for ext in all_exts:
            assert ext == ext.lower(), f"Non-lowercase extension: {ext!r}"

    # Expected members
    def test_jpg_in_images(self):
        assert ".jpg" in IMAGE_EXTENSIONS

    def test_png_in_images(self):
        assert ".png" in IMAGE_EXTENSIONS

    def test_pdf_in_documents(self):
        assert ".pdf" in DOCUMENT_EXTENSIONS

    def test_zip_in_archives(self):
        assert ".zip" in ARCHIVE_EXTENSIONS

    def test_mp4_in_media(self):
        assert ".mp4" in MEDIA_EXTENSIONS

    def test_py_in_code(self):
        assert ".py" in CODE_EXTENSIONS

    def test_md_in_text(self):
        assert ".md" in TEXT_EXTENSIONS


class TestDefaultExtensions:
    def test_is_superset_of_images(self):
        assert IMAGE_EXTENSIONS.issubset(DEFAULT_EXTENSIONS)

    def test_is_superset_of_documents(self):
        assert DOCUMENT_EXTENSIONS.issubset(DEFAULT_EXTENSIONS)

    def test_is_superset_of_code(self):
        assert CODE_EXTENSIONS.issubset(DEFAULT_EXTENSIONS)

    def test_is_superset_of_media(self):
        assert MEDIA_EXTENSIONS.issubset(DEFAULT_EXTENSIONS)

    def test_is_superset_of_archives(self):
        assert ARCHIVE_EXTENSIONS.issubset(DEFAULT_EXTENSIONS)

    def test_non_empty(self):
        assert len(DEFAULT_EXTENSIONS) > 0


class TestProtectedPatterns:
    def test_is_list(self):
        assert isinstance(PROTECTED_PATTERNS, list)

    def test_non_empty(self):
        assert len(PROTECTED_PATTERNS) > 0

    def test_contains_git_pattern(self):
        assert any(".git" in p for p in PROTECTED_PATTERNS)

    def test_contains_env_pattern(self):
        assert any(".env" in p for p in PROTECTED_PATTERNS)

    def test_all_patterns_are_strings(self):
        for p in PROTECTED_PATTERNS:
            assert isinstance(p, str)
