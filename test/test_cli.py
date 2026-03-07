"""
Tests for cleanupx.py CLI argument parsing and high-level command routing.

Strategy:
- Parse args without executing side-effecting functions by testing
  argparse directly and patching the processing functions.
- Verify correct argument -> function call mapping.
- Verify return code behaviour.
"""

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Import the module-level main() and helpers from cleanupx
import cleanupx


# ---------------------------------------------------------------------------
# Helpers: build a Namespace matching what argparse would produce
# ---------------------------------------------------------------------------

def _ns(**kwargs):
    """Build an argparse.Namespace from keyword arguments."""
    return argparse.Namespace(**kwargs)


# ---------------------------------------------------------------------------
# Argument parsing (via main with patched sys.argv)
# ---------------------------------------------------------------------------

class TestMainArgParsing:
    """Verify that main() routes subcommands to the correct functions."""

    def _run_main_with_argv(self, argv, patch_targets):
        """
        Patch *patch_targets* (a mapping of attr -> MagicMock) on the
        cleanupx module, then call main() with sys.argv = ['cleanupx'] + argv.
        Returns the mocks dict and the return code.
        """
        patches = {}
        with patch.object(sys, "argv", ["cleanupx"] + argv):
            for attr, mock in patch_targets.items():
                p = patch.object(cleanupx, attr, mock)
                p.start()
                patches[attr] = (p, mock)
            try:
                rc = cleanupx.main()
            finally:
                for p, _ in patches.values():
                    p.stop()
        return {attr: mock for attr, (_, mock) in patches.items()}, rc

    # --- organize ---

    def test_organize_command_calls_organize_directory(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, rc = self._run_main_with_argv(
            ["organize", "--dir", str(tmp_path)],
            {"organize_directory": mock_fn}
        )
        mock_fn.assert_called_once_with(tmp_path)
        assert rc == 0

    def test_organize_error_returns_1(self, tmp_path):
        mock_fn = MagicMock(return_value={"error": "something went wrong"})
        _, rc = self._run_main_with_argv(
            ["organize", "--dir", str(tmp_path)],
            {"organize_directory": mock_fn}
        )
        assert rc == 1

    # --- deduplicate ---

    def test_deduplicate_calls_deduplicate_directory(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, rc = self._run_main_with_argv(
            ["deduplicate", "--dir", str(tmp_path)],
            {"deduplicate_directory": mock_fn}
        )
        mock_fn.assert_called_once()
        assert rc == 0

    def test_deduplicate_with_output_passes_path(self, tmp_path):
        output = tmp_path / "out"
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, _ = self._run_main_with_argv(
            ["deduplicate", "--dir", str(tmp_path), "--output", str(output)],
            {"deduplicate_directory": mock_fn}
        )
        args, kwargs = mock_fn.call_args
        # second positional arg should be the output Path
        assert args[1] == output

    # --- extract ---

    def test_extract_calls_extract_snippets(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, rc = self._run_main_with_argv(
            ["extract", "--dir", str(tmp_path)],
            {"extract_snippets": mock_fn}
        )
        mock_fn.assert_called_once()
        assert rc == 0

    def test_extract_mode_default_is_code(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, _ = self._run_main_with_argv(
            ["extract", "--dir", str(tmp_path)],
            {"extract_snippets": mock_fn}
        )
        # main() calls extract_snippets(dir_path, output_file, mode) positionally
        args, kwargs = mock_fn.call_args
        # mode is the 3rd positional arg; output_file defaults to None
        mode = args[2] if len(args) > 2 else kwargs.get("mode", "code")
        assert mode == "code"

    def test_extract_mode_snippet(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, _ = self._run_main_with_argv(
            ["extract", "--dir", str(tmp_path), "--mode", "snippet"],
            {"extract_snippets": mock_fn}
        )
        args, kwargs = mock_fn.call_args
        mode = args[2] if len(args) > 2 else kwargs.get("mode")
        assert mode == "snippet"

    # --- all ---

    def test_all_command_calls_process_all(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, rc = self._run_main_with_argv(
            ["all", "--dir", str(tmp_path)],
            {"process_all": mock_fn}
        )
        mock_fn.assert_called_once()
        assert rc == 0

    # --- images ---

    def test_images_command_calls_process_images_only(self, tmp_path):
        mock_fn = MagicMock(return_value={"status": "success"})
        mocks, rc = self._run_main_with_argv(
            ["images", "--dir", str(tmp_path)],
            {"process_images_only": mock_fn}
        )
        mock_fn.assert_called_once()
        assert rc == 0

    def test_images_error_returns_1(self, tmp_path):
        mock_fn = MagicMock(return_value={"error": "no module"})
        _, rc = self._run_main_with_argv(
            ["images", "--dir", str(tmp_path)],
            {"process_images_only": mock_fn}
        )
        assert rc == 1

    # --- scramble ---

    def test_scramble_command_calls_scramble_filenames_only(self, tmp_path):
        mock_fn = MagicMock(return_value={"success": True})
        mocks, rc = self._run_main_with_argv(
            ["scramble", "--dir", str(tmp_path)],
            {"scramble_filenames_only": mock_fn}
        )
        mock_fn.assert_called_once_with(tmp_path)
        assert rc == 0

    # --- no command ---

    def test_no_command_returns_1(self):
        with patch.object(sys, "argv", ["cleanupx"]):
            rc = cleanupx.main()
        assert rc == 1


# ---------------------------------------------------------------------------
# Legacy high-level functions (integration-light tests using tmp_path)
# ---------------------------------------------------------------------------

class TestDedupDirectory:
    def test_invalid_path_returns_error(self, tmp_path):
        result = cleanupx.deduplicate_directory(tmp_path / "ghost")
        assert "error" in result

    def test_empty_directory_returns_no_duplicates(self, tmp_path):
        result = cleanupx.deduplicate_directory(tmp_path)
        assert result.get("status") == "success"
        assert result.get("duplicates_found") is False

    def test_creates_output_directory(self, tmp_path):
        out = tmp_path / "dedup_out"
        cleanupx.deduplicate_directory(tmp_path, out)
        assert out.is_dir()

    def test_duplicate_files_creates_report(self, tmp_path):
        content = "same content\n" * 10
        (tmp_path / "a.txt").write_text(content, encoding="utf-8")
        (tmp_path / "b.txt").write_text(content, encoding="utf-8")
        out = tmp_path / "out"
        result = cleanupx.deduplicate_directory(tmp_path, out)
        assert result.get("duplicates_found") is True
        results_file = Path(result["results_file"])
        assert results_file.exists()


class TestExtractSnippets:
    def test_invalid_path_returns_error(self, tmp_path):
        result = cleanupx.extract_snippets(tmp_path / "ghost")
        assert "error" in result

    def test_creates_output_file(self, tmp_path):
        (tmp_path / "a.py").write_text("print('hi')", encoding="utf-8")
        output = tmp_path / "out.md"
        result = cleanupx.extract_snippets(tmp_path, str(output))
        assert result.get("status") == "success"
        assert output.exists()

    def test_default_output_file_name(self, tmp_path):
        (tmp_path / "b.py").write_text("x = 1", encoding="utf-8")
        result = cleanupx.extract_snippets(tmp_path)
        # Default is <dir>/final_combined.md
        assert result.get("output_file") == str(tmp_path / "final_combined.md")


class TestFallbackHelpers:
    """Tests for the fallback_* helpers in cleanupx.py."""

    def test_fallback_find_potential_duplicates_no_dups(self, tmp_path):
        (tmp_path / "a.txt").write_text("unique A", encoding="utf-8")
        (tmp_path / "b.txt").write_text("unique B", encoding="utf-8")
        groups = cleanupx.fallback_find_potential_duplicates(tmp_path)
        assert groups == []

    def test_fallback_find_potential_duplicates_finds_same_size(self, tmp_path):
        # Files with exactly same content = same size
        content = "x" * 100
        (tmp_path / "a.txt").write_text(content, encoding="utf-8")
        (tmp_path / "b.txt").write_text(content, encoding="utf-8")
        groups = cleanupx.fallback_find_potential_duplicates(tmp_path)
        assert len(groups) >= 1

    def test_fallback_create_batches_correct_size(self):
        items = [{"key": i} for i in range(13)]
        batches = cleanupx.fallback_create_batches(items, max_batch_size=5)
        assert len(batches) == 3
        assert len(batches[0]) == 5
        assert len(batches[1]) == 5
        assert len(batches[2]) == 3

    def test_fallback_create_batches_single(self):
        items = [{"key": "x"}]
        batches = cleanupx.fallback_create_batches(items, max_batch_size=5)
        assert len(batches) == 1

    def test_fallback_process_batch_creates_output(self, tmp_path):
        content = "batch content"
        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text(content, encoding="utf-8")
        f2.write_text(content, encoding="utf-8")
        batch = [{"files": [f1, f2], "key": "k1", "similarity_type": "hash"}]
        out = tmp_path / "batch_out"
        result = cleanupx.fallback_process_batch(batch, out)
        assert result["groups_processed"] == 1
        assert result["files_processed"] == 2
        assert len(result["consolidated_files"]) == 1
        assert Path(result["consolidated_files"][0]).exists()
