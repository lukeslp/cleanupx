"""
Utility modules for cleanupx.
"""

# Re-export important cache functions and variables for easier imports
from cleanupx.utils.cache import (
    load_cache, 
    save_cache, 
    load_rename_log, 
    save_rename_log, 
    clear_cache, 
    add_error_to_log,
    _MEMORY_CACHE
)

# Re-export string utilities
from cleanupx.utils.string import (
    truncate_string,
    clean_filename,
    strip_media_suffixes,
    normalize_whitespace,
    split_camel_case
)

# Re-export file utilities
from cleanupx.utils.file import (
    get_file_metadata,
    get_file_extension,
    get_file_hash,
    is_binary_file,
    validate_file,
    create_backup,
    restore_from_backup
)
