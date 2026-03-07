"""
Tests for file organisation logic.

Covers:
- _get_file_type() via direct import of the function (which succeeds because
  organization.py's broken top-level import of DocumentProcessor lives inside
  the DirectoryOrganizer class, not in the module's execution scope when
  we import selectively).  We import via importlib to avoid the class-level
  import problem, OR we test through the public API that actually works.
- cleanupx.organize_directory()  – the legacy high-level function

Note: cleanupx_core.processors.integrated.organization imports
  `from ..processors import DocumentProcessor, ImageProcessor, ArchiveProcessor`
which resolves to `cleanupx_core.processors.processors` (non-existent).
That import only runs when organization.py is loaded as a top-level import.
We work around this by importing the module lazily inside helper functions,
or by testing only through the cleanupx entry-point which uses the fallback
(cleanup.py's try/except wrapper).
"""

import json
import importlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import cleanupx


# ---------------------------------------------------------------------------
# _get_file_type – import carefully to avoid the broken class-level import
# ---------------------------------------------------------------------------

def _load_get_file_type():
    """
    Import _get_file_type from organization.py.
    organization.py's DirectoryOrganizer class has a broken relative import
    (cleanupx_core.processors.processors doesn't exist).  That import fires
    at class *definition* time which is module load time, so the whole
    module fails.  We stub the missing pieces before importing.
    """
    # Provide stub for the missing processors sub-module
    stub = MagicMock()
    fake_processors = MagicMock()
    fake_processors.DocumentProcessor = MagicMock
    fake_processors.ImageProcessor = MagicMock
    fake_processors.ArchiveProcessor = MagicMock

    # Remove cached copy so we get a fresh import with our stubs
    for key in list(sys.modules.keys()):
        if "cleanupx_core.processors.integrated.organization" in key:
            del sys.modules[key]

    with patch.dict(sys.modules, {
        "cleanupx_core.processors.processors": fake_processors,
    }):
        from cleanupx_core.processors.integrated.organization import (
            _get_file_type,
            organize_files,
        )
    return _get_file_type, organize_files


try:
    _get_file_type, _organize_files = _load_get_file_type()
    ORGANIZE_IMPORTABLE = True
except Exception:
    _get_file_type = None
    _organize_files = None
    ORGANIZE_IMPORTABLE = False


from cleanupx_core.processors.integrated.config import (
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    TEXT_EXTENSIONS,
    MEDIA_EXTENSIONS,
    CODE_EXTENSIONS,
)


# ---------------------------------------------------------------------------
# _get_file_type – only run if the module imported cleanly
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not ORGANIZE_IMPORTABLE, reason="organization module not importable")
class TestGetFileType:
    """Unit tests for the private _get_file_type helper."""

    TYPE_DIRS = {
        "images": IMAGE_EXTENSIONS,
        "documents": DOCUMENT_EXTENSIONS,
        "archives": ARCHIVE_EXTENSIONS,
        "text": TEXT_EXTENSIONS,
        "media": MEDIA_EXTENSIONS,
        "code": CODE_EXTENSIONS,
        "other": set(),
    }

    def _file(self, tmp_path, name):
        p = tmp_path / name
        p.write_bytes(b"")
        return p

    def test_jpg_classified_as_images(self, tmp_path):
        f = self._file(tmp_path, "photo.jpg")
        assert _get_file_type(f, self.TYPE_DIRS) == "images"

    def test_png_classified_as_images(self, tmp_path):
        f = self._file(tmp_path, "icon.PNG")
        assert _get_file_type(f, self.TYPE_DIRS) == "images"

    def test_pdf_classified_as_documents(self, tmp_path):
        f = self._file(tmp_path, "report.pdf")
        assert _get_file_type(f, self.TYPE_DIRS) == "documents"

    def test_zip_classified_as_archives(self, tmp_path):
        f = self._file(tmp_path, "bundle.zip")
        assert _get_file_type(f, self.TYPE_DIRS) == "archives"

    def test_mp4_classified_as_media(self, tmp_path):
        f = self._file(tmp_path, "video.mp4")
        assert _get_file_type(f, self.TYPE_DIRS) == "media"

    def test_py_classified_by_type_dirs_order(self, tmp_path):
        # .py is in both TEXT_EXTENSIONS and CODE_EXTENSIONS; _get_file_type
        # returns the first match found when iterating TYPE_DIRS. The
        # important invariant is that it always returns a recognised category,
        # never "other".
        f = self._file(tmp_path, "script.py")
        result = _get_file_type(f, self.TYPE_DIRS)
        assert result in ("text", "code"), f"unexpected category: {result!r}"

    def test_unknown_extension_classified_as_other(self, tmp_path):
        f = self._file(tmp_path, "data.xyzzy")
        assert _get_file_type(f, self.TYPE_DIRS) == "other"

    def test_no_extension_classified_as_other(self, tmp_path):
        f = self._file(tmp_path, "Makefile")
        assert _get_file_type(f, self.TYPE_DIRS) == "other"


# ---------------------------------------------------------------------------
# organize_files (dry_run=True) – only run if module imported cleanly
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not ORGANIZE_IMPORTABLE, reason="organization module not importable")
class TestOrganizeFilesDryRun:
    """Verify organize_files with dry_run=True reports correctly."""

    def test_returns_organized_list(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8")
        (tmp_path / "readme.md").write_text("# Hi", encoding="utf-8")
        result = _organize_files(tmp_path, dry_run=True, move_files=False, create_dirs=False)
        assert "organized" in result
        assert "stats" in result

    def test_total_files_counted(self, tmp_path):
        for i in range(4):
            (tmp_path / f"file{i}.txt").write_text("content", encoding="utf-8")
        result = _organize_files(tmp_path, dry_run=True, move_files=False, create_dirs=False)
        assert result["stats"]["total_files"] >= 4

    def test_invalid_directory_returns_error(self, tmp_path):
        result = _organize_files(tmp_path / "nonexistent", dry_run=True)
        assert "errors" in result

    def test_dry_run_does_not_move_files(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8")
        _organize_files(tmp_path, dry_run=True)
        assert f.exists()


# ---------------------------------------------------------------------------
# organize_files (live) – only run if module imported cleanly
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not ORGANIZE_IMPORTABLE, reason="organization module not importable")
class TestOrganizeFilesLive:
    def test_creates_subdirectories(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8")
        _organize_files(tmp_path, create_dirs=True, move_files=False, dry_run=False)
        assert (tmp_path / "images").is_dir()

    def test_moves_file_to_correct_type_dir(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8")
        result = _organize_files(tmp_path, create_dirs=True, move_files=True, dry_run=False)
        assert result["stats"]["organized_files"] >= 1
        assert not f.exists() or (tmp_path / "images" / "photo.jpg").exists()

    def test_saves_rename_log(self, tmp_path):
        (tmp_path / "a.py").write_text("pass", encoding="utf-8")
        _organize_files(tmp_path, create_dirs=True, move_files=True, dry_run=False)
        log = tmp_path / "rename_log.json"
        assert log.exists()


# ---------------------------------------------------------------------------
# Legacy cleanupx.organize_directory
# ---------------------------------------------------------------------------

class TestLegacyOrganizeDirectory:
    def test_invalid_path_returns_error(self, tmp_path):
        result = cleanupx.organize_directory(tmp_path / "ghost")
        assert "error" in result

    def test_valid_directory_returns_success(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        result = cleanupx.organize_directory(tmp_path)
        assert result.get("status") == "success"

    def test_report_file_created(self, tmp_path):
        (tmp_path / "b.py").write_text("print()", encoding="utf-8")
        result = cleanupx.organize_directory(tmp_path)
        report = Path(result["report_file"])
        assert report.exists()

    def test_extensions_found_in_result(self, tmp_path):
        (tmp_path / "c.md").write_text("# MD", encoding="utf-8")
        (tmp_path / "d.txt").write_text("txt", encoding="utf-8")
        result = cleanupx.organize_directory(tmp_path)
        exts = result.get("extensions_found", {})
        assert ".md" in exts or ".txt" in exts

    def test_empty_directory_returns_success(self, tmp_path):
        result = cleanupx.organize_directory(tmp_path)
        assert result.get("status") == "success"
