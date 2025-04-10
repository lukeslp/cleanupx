#!/usr/bin/env python3
"""
Caching utilities for cleanupx.
This module provides a simple in-memory caching system for storing analysis results
and other computationally expensive data.
"""

import logging
import time
import os
import json
import glob
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
from pathlib import Path

from cleanupx.config import CACHE_FILE, RENAME_LOG_FILE

# Configure logging
logger = logging.getLogger(__name__)

# Global cache storage
_CACHE: Dict[str, Dict[str, Any]] = {}

# Simple memory cache for text extraction and document processing
_MEMORY_CACHE: Dict[str, Any] = {}

# Cache statistics
_CACHE_STATS = {
    "hits": 0,
    "misses": 0,
    "size": 0,  # Number of items in cache
    "created_at": time.time()
}

# Cache configuration
_CACHE_CONFIG = {
    "max_size": 10000,  # Maximum number of items to store
    "ttl": 3600,  # Default TTL in seconds (1 hour)
    "enabled": True  # Global cache enable/disable flag
}

# Backward compatibility storage
_LEGACY_CACHE: Dict[str, Any] = {}
_RENAME_LOGS: Dict[str, List[Dict[str, Any]]] = {}

def configure_cache(max_size: Optional[int] = None, ttl: Optional[int] = None, enabled: Optional[bool] = None) -> None:
    """
    Configure cache settings.
    
    Args:
        max_size: Maximum number of items to store in cache
        ttl: Default time-to-live for cache items in seconds
        enabled: Enable or disable caching globally
    """
    global _CACHE_CONFIG
    
    if max_size is not None:
        _CACHE_CONFIG["max_size"] = max_size
    
    if ttl is not None:
        _CACHE_CONFIG["ttl"] = ttl
    
    if enabled is not None:
        _CACHE_CONFIG["enabled"] = enabled
    
    logger.info(f"Cache configured: {_CACHE_CONFIG}")

def is_cached(key: str) -> bool:
    """
    Check if a key exists in the cache and is still valid.
    
    Args:
        key: Cache key to check
        
    Returns:
        True if the key exists and is valid, False otherwise
    """
    if not _CACHE_CONFIG["enabled"]:
        return False
    
    global _CACHE_STATS
    
    if key in _CACHE:
        item = _CACHE[key]
        current_time = time.time()
        
        # Check if the item has expired
        if "expires_at" in item and item["expires_at"] < current_time:
            # Item expired, remove it
            del _CACHE[key]
            _CACHE_STATS["misses"] += 1
            return False
        
        _CACHE_STATS["hits"] += 1
        return True
    
    _CACHE_STATS["misses"] += 1
    return False

def save_to_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Save a value to the cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time-to-live in seconds, or None to use default
        
    Returns:
        True if the value was cached, False otherwise
    """
    if not _CACHE_CONFIG["enabled"]:
        return False
    
    global _CACHE, _CACHE_STATS
    
    # Check if we need to enforce max size
    if len(_CACHE) >= _CACHE_CONFIG["max_size"]:
        # Implement a simple LRU-like eviction strategy
        # We'll remove the 10% oldest items
        items_to_remove = int(len(_CACHE) * 0.1) or 1
        to_remove = sorted(_CACHE.items(), key=lambda x: x[1].get("last_accessed", 0))[:items_to_remove]
        for k, _ in to_remove:
            del _CACHE[k]
        
        logger.info(f"Evicted {items_to_remove} items from cache due to size limit")
    
    # Calculate expiration time
    ttl = ttl if ttl is not None else _CACHE_CONFIG["ttl"]
    expires_at = time.time() + ttl
    
    # Save to cache
    _CACHE[key] = {
        "value": value,
        "created_at": time.time(),
        "last_accessed": time.time(),
        "expires_at": expires_at
    }
    
    _CACHE_STATS["size"] = len(_CACHE)
    
    return True

def get_from_cache(key: str) -> Any:
    """
    Get a value from the cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found/expired
    """
    if not _CACHE_CONFIG["enabled"] or key not in _CACHE:
        return None
    
    item = _CACHE[key]
    current_time = time.time()
    
    # Check if the item has expired
    if "expires_at" in item and item["expires_at"] < current_time:
        # Item expired, remove it
        del _CACHE[key]
        return None
    
    # Update last accessed time
    item["last_accessed"] = current_time
    
    return item["value"]

def remove_from_cache(key: str) -> bool:
    """
    Remove a specific key from the cache.
    
    Args:
        key: Cache key to remove
        
    Returns:
        True if the key was removed, False if it didn't exist
    """
    global _CACHE, _CACHE_STATS
    
    if key in _CACHE:
        del _CACHE[key]
        _CACHE_STATS["size"] = len(_CACHE)
        return True
    
    return False

def clear_cache(directory: Optional[Path] = None) -> Dict[str, int]:
    """
    Clear cache files from the system.
    
    Args:
        directory: If provided, only clear text cache files in this directory.
                  If None, clear global cache and rename log.
    
    Returns:
        Stats dictionary with count of files cleared
    """
    global _MEMORY_CACHE
    
    stats = {
        "global_cache": 0,
        "rename_log": 0,
        "text_cache": 0,
        "memory_cache": 0
    }
    
    # Clear global cache files if no specific directory
    if directory is None:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            stats["global_cache"] = 1
            logger.info(f"Cleared global cache file: {CACHE_FILE}")
            
        if os.path.exists(RENAME_LOG_FILE):
            os.remove(RENAME_LOG_FILE)
            stats["rename_log"] = 1
            logger.info(f"Cleared rename log file: {RENAME_LOG_FILE}")
        
        # Clear the in-memory cache
        cache_items = len(_MEMORY_CACHE)
        _MEMORY_CACHE.clear()
        stats["memory_cache"] = cache_items
        logger.info(f"Cleared {cache_items} items from memory cache")
    
    # Find and clear text cache files
    text_cache_pattern = "text_cache*.txt"
    if directory:
        # Find all text cache files in the given directory recursively
        pattern = os.path.join(str(directory), "**", text_cache_pattern)
        text_cache_files = glob.glob(pattern, recursive=True)
        
        # If clearing directory-specific cache, also clear related memory cache entries
        if directory:
            dir_str = str(directory)
            cache_keys_to_remove = [k for k in list(_MEMORY_CACHE.keys()) if dir_str in k]
            removed_count = len(cache_keys_to_remove)
            for key in cache_keys_to_remove:
                del _MEMORY_CACHE[key]
            stats["memory_cache"] = removed_count
            logger.info(f"Cleared {removed_count} directory-specific items from memory cache")
    else:
        # Find all text cache files in the system
        pattern = os.path.join("**", text_cache_pattern)
        text_cache_files = glob.glob(pattern, recursive=True)
    
    # Delete each text cache file
    for cache_file in text_cache_files:
        try:
            os.remove(cache_file)
            stats["text_cache"] += 1
            logger.debug(f"Cleared text cache file: {cache_file}")
        except Exception as e:
            logger.error(f"Failed to remove text cache file {cache_file}: {e}")
    
    logger.info(f"Cache cleanup: {stats['global_cache']} global cache, "
              f"{stats['rename_log']} rename log, "
              f"{stats['text_cache']} text cache files, "
              f"{stats['memory_cache']} memory cache items")
              
    return stats

def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    global _CACHE_STATS, _CACHE
    
    hit_ratio = 0
    if _CACHE_STATS["hits"] + _CACHE_STATS["misses"] > 0:
        hit_ratio = _CACHE_STATS["hits"] / (_CACHE_STATS["hits"] + _CACHE_STATS["misses"])
    
    # Calculate memory usage (rough estimate)
    import sys
    memory_usage = sys.getsizeof(_CACHE)
    
    # Add a sample of a few items to estimate total size
    if _CACHE:
        sample_size = min(10, len(_CACHE))
        sample_keys = list(_CACHE.keys())[:sample_size]
        sample_memory = sum(sys.getsizeof(_CACHE[k]) + sys.getsizeof(k) for k in sample_keys)
        estimated_memory = sample_memory / sample_size * len(_CACHE)
        memory_usage += estimated_memory
    
    stats = {
        "hits": _CACHE_STATS["hits"],
        "misses": _CACHE_STATS["misses"],
        "hit_ratio": hit_ratio,
        "size": len(_CACHE),
        "memory_usage_bytes": memory_usage,
        "created_at": _CACHE_STATS["created_at"],
        "uptime_seconds": time.time() - _CACHE_STATS["created_at"],
        "config": _CACHE_CONFIG
    }
    
    return stats

def get_cache_keys(prefix: Optional[str] = None) -> List[str]:
    """
    Get all cache keys or keys with a specific prefix.
    
    Args:
        prefix: If provided, only return keys starting with this prefix
        
    Returns:
        List of cache keys
    """
    if prefix:
        return [k for k in _CACHE.keys() if k.startswith(prefix)]
    else:
        return list(_CACHE.keys())

def invalidate_stale_cache() -> int:
    """
    Invalidate all expired cache entries.
    
    Returns:
        Number of entries invalidated
    """
    global _CACHE
    
    current_time = time.time()
    stale_keys = [
        k for k, v in _CACHE.items()
        if "expires_at" in v and v["expires_at"] < current_time
    ]
    
    for k in stale_keys:
        del _CACHE[k]
    
    _CACHE_STATS["size"] = len(_CACHE)
    logger.info(f"Invalidated {len(stale_keys)} stale cache entries")
    
    return len(stale_keys)

# Backward compatibility functions for old API
def load_cache() -> Dict[str, Any]:
    """
    Backward compatibility function to load cache from previous API.
    
    Returns:
        The legacy cache dictionary
    """
    global _LEGACY_CACHE
    logger.info("Using backward compatibility load_cache() function")
    return _LEGACY_CACHE

def save_cache(cache_data: Dict[str, Any]) -> None:
    """
    Backward compatibility function to save cache from previous API.
    
    Args:
        cache_data: The cache data to save
    """
    global _LEGACY_CACHE
    logger.info("Using backward compatibility save_cache() function")
    _LEGACY_CACHE = cache_data

def save_rename_log(rename_log: List[Dict], log_file: Optional[Union[str, Any]] = None) -> None:
    """
    Backward compatibility function for saving rename logs.
    Now stores logs in memory instead of writing to disk.
    
    Args:
        rename_log: List of rename operations
        log_file: Identifier for the log (previously a file path)
    """
    global _RENAME_LOGS
    log_key = str(log_file) if log_file else "default_rename_log"
    _RENAME_LOGS[log_key] = rename_log
    logger.info(f"Saved rename log to in-memory cache with key: {log_key}")

def load_rename_log(log_file: Optional[Union[str, Any]] = None) -> List[Dict]:
    """
    Backward compatibility function for loading rename logs.
    Now retrieves logs from memory instead of reading from disk.
    
    Args:
        log_file: Identifier for the log (previously a file path)
        
    Returns:
        List of rename operations
    """
    log_key = str(log_file) if log_file else "default_rename_log"
    result = _RENAME_LOGS.get(log_key, [])
    logger.info(f"Loaded rename log from in-memory cache with key: {log_key}")
    return result

def load_cache() -> Dict[str, Any]:
    """Load the cache file if it exists, otherwise return an empty dictionary."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
    return {}

def save_cache(cache: Dict[str, Any]) -> None:
    """Save the cache dictionary to the cache file."""
    # Skip saving if NO_CACHE is set
    if os.environ.get('CLEANUPX_NO_CACHE'):
        logger.debug("Skipping cache save due to CLEANUPX_NO_CACHE environment variable")
        return
    
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def load_rename_log() -> Dict:
    """Load the rename log file if it exists, otherwise return an empty log."""
    try:
        if os.path.exists(RENAME_LOG_FILE):
            with open(RENAME_LOG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading rename log: {e}")
    return {
        "renames": [],
        "errors": [],
        "timestamp": "",
        "stats": {
            "total_files": 0,
            "successful_renames": 0,
            "failed_renames": 0,
            "skipped_files": 0
        }
    }

def save_rename_log(log: Dict) -> None:
    """Save the rename log to the log file."""
    # Skip saving if NO_CACHE is set
    if os.environ.get('CLEANUPX_NO_CACHE'):
        logger.debug("Skipping rename log save due to CLEANUPX_NO_CACHE environment variable")
        return
    
    try:
        with open(RENAME_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving rename log: {e}")

def add_error_to_log(rename_log: Dict, file_path: Path, error: str, error_type: str = "rename_error") -> None:
    """Add an error entry to the rename log."""
    error_entry = {
        "file_path": str(file_path),
        "error": error,
        "error_type": error_type,
        "timestamp": datetime.now().isoformat()
    }
    rename_log["errors"].append(error_entry)
    rename_log["stats"]["failed_renames"] += 1
    # Only save the log if NO_CACHE is not set
    if not os.environ.get('CLEANUPX_NO_CACHE'):
        save_rename_log(rename_log)
