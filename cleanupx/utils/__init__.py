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
