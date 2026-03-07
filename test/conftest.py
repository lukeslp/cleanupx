"""
Shared fixtures for cleanupx test suite.

Provides reusable tmp_path fixtures, sample file factories, and
mock helpers so tests stay isolated and do not touch a real filesystem
beyond pytest's own tmp_path.
"""

import hashlib
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Basic directory/file factories
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_dir(tmp_path):
    """Return an empty temporary directory."""
    return tmp_path


@pytest.fixture
def dir_with_text_files(tmp_path):
    """
    Directory containing a handful of plain text files.
    Returns the directory Path.
    """
    files = {
        "alpha.txt": "Hello world\nThis is file alpha.\n",
        "beta.txt": "Different content entirely.\nLine two of beta.\n",
        "gamma.md": "# Gamma\n\nA markdown file.\n",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def dir_with_duplicate_files(tmp_path):
    """
    Directory that contains exact duplicate files.
    Returns (directory_path, {filename: content}) mapping.
    """
    content = "Exactly the same content in every file.\n" * 5
    names = ["dup_a.txt", "dup_b.txt", "dup_c.txt"]
    for name in names:
        (tmp_path / name).write_text(content, encoding="utf-8")
    # Add a unique file so we can verify it is NOT flagged as duplicate
    (tmp_path / "unique.txt").write_text("I am unique.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def dir_with_mixed_types(tmp_path):
    """
    Directory containing files of multiple types.
    Returns the directory Path.
    """
    files = {
        "photo.jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00",
        "image.png": b"\x89PNG\r\n\x1a\n",
        "readme.md": "# Readme\nThis is a readme.\n",
        "script.py": "print('hello')\n",
        "data.json": '{"key": "value"}\n',
        "archive.zip": b"PK\x03\x04",
        "video.mp4": b"\x00\x00\x00\x18ftypmp42",
    }
    for name, content in files.items():
        path = tmp_path / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def dir_with_nested(tmp_path):
    """
    Directory with a single level of subdirectories.
    Returns the top-level directory.
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "top.txt").write_text("top level\n", encoding="utf-8")
    (tmp_path / "sub" / "deep.txt").write_text("nested file\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Helper: write a file with known SHA-256 hash
# ---------------------------------------------------------------------------

def make_file_with_content(directory: Path, filename: str, content: str) -> Path:
    """Write *content* to directory/filename and return the Path."""
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def sha256_of(content: str) -> str:
    """Return hex SHA-256 of a string (utf-8 encoded)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
