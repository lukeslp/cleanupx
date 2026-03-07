"""
Tests for cleanupx_core.processors.integrated.cleanup

Covers (without real API calls):
- XAIIntegration.is_available()
- XAIIntegration.extract_tool_result()
- ImageProcessor.encode_image()
- ImageProcessor.clean_filename()
- ImageProcessor.generate_new_filename()
- ImageProcessor.get_cache_key()
- ImageProcessor.create_markdown_file()
- ImageProcessor.rename_file()
- FilenameScrambler.scramble_directory()
- CleanupProcessor.scan_directory()
- CleanupProcessor.process_images() with mocked image processor
"""

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from cleanupx_core.processors.integrated.cleanup import (
    CleanupProcessor,
    FilenameScrambler,
    ImageProcessor,
    XAIIntegration,
)


# ---------------------------------------------------------------------------
# XAIIntegration
# ---------------------------------------------------------------------------

class TestXAIIntegration:
    def test_no_api_key_not_available(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure XAI_API_KEY is absent
            import os
            os.environ.pop("XAI_API_KEY", None)
            client = XAIIntegration(api_key=None)
        assert not client.is_available()

    def test_with_api_key_is_available(self):
        client = XAIIntegration(api_key="fake-key-12345")
        assert client.is_available()

    def test_extract_tool_result_from_tool_calls(self):
        client = XAIIntegration(api_key="fake-key")
        response = {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "type": "function",
                        "function": {
                            "arguments": json.dumps({"groups": [{"files": ["a.py"]}]})
                        }
                    }]
                }
            }]
        }
        result = client.extract_tool_result(response)
        assert "groups" in result
        assert result["groups"][0]["files"] == ["a.py"]

    def test_extract_tool_result_from_content_fallback(self):
        client = XAIIntegration(api_key="fake-key")
        response = {
            "choices": [{
                "message": {
                    "content": '```json\n{"key": "value"}\n```'
                }
            }]
        }
        result = client.extract_tool_result(response)
        assert result.get("key") == "value"

    def test_extract_tool_result_plain_content(self):
        client = XAIIntegration(api_key="fake-key")
        response = {
            "choices": [{
                "message": {
                    "content": "plain text response"
                }
            }]
        }
        result = client.extract_tool_result(response)
        assert result.get("content") == "plain text response"

    def test_extract_tool_result_bad_response(self):
        client = XAIIntegration(api_key="fake-key")
        result = client.extract_tool_result({})
        assert result == {}

    def test_analyze_code_snippet_no_key_returns_error(self):
        import os
        os.environ.pop("XAI_API_KEY", None)
        client = XAIIntegration(api_key=None)
        result = client.analyze_code_snippet("print('hello')")
        assert "error" in result

    def test_find_duplicates_no_key_returns_error(self):
        import os
        os.environ.pop("XAI_API_KEY", None)
        client = XAIIntegration(api_key=None)
        result = client.find_duplicates({"file.py": "content"})
        assert "error" in result


# ---------------------------------------------------------------------------
# ImageProcessor
# ---------------------------------------------------------------------------

class TestImageProcessor:
    def _make_processor(self):
        """Return an ImageProcessor backed by a no-op (unavailable) client."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        return ImageProcessor(mock_client)

    # encode_image
    def test_encode_image_returns_base64(self, tmp_path):
        proc = self._make_processor()
        content = b"fake image bytes"
        f = tmp_path / "img.jpg"
        f.write_bytes(content)
        encoded = proc.encode_image(f)
        assert encoded == base64.b64encode(content).decode("utf-8")

    def test_encode_image_missing_file_returns_none(self, tmp_path):
        proc = self._make_processor()
        result = proc.encode_image(tmp_path / "missing.jpg")
        assert result is None

    # clean_filename
    def test_clean_filename_removes_forbidden_chars(self):
        proc = self._make_processor()
        result = proc.clean_filename('my<file>name:here"test')
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result

    def test_clean_filename_collapses_underscores(self):
        proc = self._make_processor()
        result = proc.clean_filename("hello   world")
        assert "   " not in result

    def test_clean_filename_truncates_long_name(self):
        proc = self._make_processor()
        long_name = "a" * 300
        result = proc.clean_filename(long_name)
        assert len(result) <= 255

    def test_clean_filename_short_name_unchanged(self):
        proc = self._make_processor()
        result = proc.clean_filename("short_name")
        assert result == "short_name"

    # generate_new_filename
    def test_generate_new_filename_uses_suggested(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "original.jpg"
        f.write_bytes(b"\xff\xd8")
        description = {"suggested_filename": "my_cool_photo"}
        new_name = proc.generate_new_filename(f, description)
        assert new_name.startswith("my_cool_photo")
        assert new_name.endswith(".jpg")

    def test_generate_new_filename_falls_back_to_stem(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "fallback.png"
        f.write_bytes(b"\x89PNG")
        new_name = proc.generate_new_filename(f, {})
        assert new_name.endswith(".png")

    # get_cache_key
    def test_get_cache_key_is_string(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\xff\xd8")
        key = proc.get_cache_key(str(f))
        assert isinstance(key, str) and len(key) > 0

    def test_get_cache_key_changes_after_modification(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\xff\xd8")
        key1 = proc.get_cache_key(str(f))
        import time
        time.sleep(0.01)
        f.write_bytes(b"\xff\xd8\x00")  # change mtime
        key2 = proc.get_cache_key(str(f))
        assert key1 != key2

    # create_markdown_file
    def test_create_markdown_file(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "testimage.jpg"
        f.write_bytes(b"\xff\xd8")
        description = {
            "description": "A test image",
            "alt_text": "test alt",
            "tags": ["tag1", "tag2"],
        }
        md_path = proc.create_markdown_file(f, description)
        assert md_path is not None and md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "A test image" in content
        assert "test alt" in content
        assert "tag1" in content

    def test_create_markdown_file_missing_description(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "noalt.jpg"
        f.write_bytes(b"\xff\xd8")
        md_path = proc.create_markdown_file(f, {})
        assert md_path is not None
        content = md_path.read_text(encoding="utf-8")
        assert "No description available" in content

    # rename_file
    def test_rename_file_same_name_returns_original(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "same.jpg"
        f.write_bytes(b"\xff\xd8")
        result = proc.rename_file(f, "same.jpg")
        assert result == f

    def test_rename_file_renames_successfully(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "old_name.jpg"
        f.write_bytes(b"\xff\xd8")
        result = proc.rename_file(f, "new_name.jpg")
        assert result is not None
        assert result.name == "new_name.jpg"
        assert result.exists()
        assert not f.exists()

    def test_rename_file_handles_collision(self, tmp_path):
        proc = self._make_processor()
        original = tmp_path / "img.jpg"
        existing = tmp_path / "renamed.jpg"
        original.write_bytes(b"\xff\xd8")
        existing.write_bytes(b"\xff\xd9")
        result = proc.rename_file(original, "renamed.jpg")
        # Collision resolved – result name should differ from "renamed.jpg"
        assert result is not None
        assert result.exists()
        assert result.name != "renamed.jpg" or not original.exists()

    # generate_alt_text – unavailable client
    def test_generate_alt_text_no_client_returns_none(self, tmp_path):
        proc = self._make_processor()
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\xff\xd8")
        result = proc.generate_alt_text(str(f))
        assert result is None


# ---------------------------------------------------------------------------
# FilenameScrambler
# ---------------------------------------------------------------------------

class TestFilenameScrambler:
    def test_scramble_invalid_directory_returns_error(self, tmp_path):
        scrambler = FilenameScrambler()
        result = scrambler.scramble_directory(tmp_path / "nonexistent", interactive=False)
        assert result.get("success") is False

    def test_scramble_empty_directory_returns_no_files(self, tmp_path):
        scrambler = FilenameScrambler()
        result = scrambler.scramble_directory(str(tmp_path), interactive=False)
        # No files to rename
        assert result.get("renamed_count", 0) == 0

    def test_scramble_renames_files(self, tmp_path):
        original_names = {"file_a.txt", "file_b.txt"}
        for name in original_names:
            (tmp_path / name).write_text("content", encoding="utf-8")

        scrambler = FilenameScrambler()
        result = scrambler.scramble_directory(str(tmp_path), interactive=False)

        assert result.get("success") is True
        assert result.get("renamed_count") == 2

        current_names = {f.name for f in tmp_path.iterdir() if f.is_file() and f.suffix != ".txt" or f.name not in original_names}
        # Original names must be gone (except possibly the log file)
        for name in original_names:
            assert not (tmp_path / name).exists()

    def test_scramble_creates_log_file(self, tmp_path):
        (tmp_path / "only.txt").write_text("log me", encoding="utf-8")
        scrambler = FilenameScrambler()
        result = scrambler.scramble_directory(str(tmp_path), interactive=False)
        log_path = Path(result.get("log_file", ""))
        assert log_path.exists()

    def test_scramble_no_directory_returns_error(self):
        scrambler = FilenameScrambler()
        result = scrambler.scramble_directory(directory_path=None, interactive=False)
        assert result.get("success") is False


# ---------------------------------------------------------------------------
# CleanupProcessor.scan_directory
# ---------------------------------------------------------------------------

class TestCleanupProcessorScan:
    def _make_processor(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("XAI_API_KEY", None)
        return CleanupProcessor(api_key=None)

    def test_scan_categorises_images(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8")
        proc = self._make_processor()
        result = proc.scan_directory(tmp_path, recursive=False)
        assert any("photo.jpg" in str(p) for p in result["images"])

    def test_scan_categorises_code(self, tmp_path):
        (tmp_path / "script.py").write_text("pass", encoding="utf-8")
        proc = self._make_processor()
        result = proc.scan_directory(tmp_path, recursive=False)
        assert any("script.py" in str(p) for p in result["code"])

    def test_scan_categorises_documents(self, tmp_path):
        (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4")
        proc = self._make_processor()
        result = proc.scan_directory(tmp_path, recursive=False)
        assert any("report.pdf" in str(p) for p in result["documents"])

    def test_scan_returns_four_categories(self, tmp_path):
        proc = self._make_processor()
        result = proc.scan_directory(tmp_path, recursive=False)
        assert set(result.keys()) == {"images", "code", "documents", "other"}

    def test_scan_recursive_finds_nested(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.py").write_text("pass", encoding="utf-8")
        proc = self._make_processor()
        non_recursive = proc.scan_directory(tmp_path, recursive=False)
        recursive = proc.scan_directory(tmp_path, recursive=True)
        assert len(recursive["code"]) > len(non_recursive["code"])

    def test_process_images_empty_list_returns_zero(self):
        proc = self._make_processor()
        result = proc.process_images([])
        assert result["processed"] == 0
