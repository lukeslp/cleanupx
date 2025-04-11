"""
Core module for CleanupX.
"""

from .processor import FileProcessor
from .config import DEFAULT_EXTENSIONS, PROTECTED_PATTERNS
from .utils import (
    get_file_hash,
    get_file_metadata,
    is_protected_file,
    normalize_path
)
from .organization import organize_files
from .snippets import process_snippets
from .citations import process_citations
from .cleanup import cleanup_directory

__all__ = [
    'FileProcessor',
    'DEFAULT_EXTENSIONS',
    'PROTECTED_PATTERNS',
    'get_file_hash',
    'get_file_metadata',
    'is_protected_file',
    'normalize_path',
    'organize_files',
    'process_snippets',
    'process_citations',
    'cleanup_directory'
] 