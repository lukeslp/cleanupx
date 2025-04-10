#!/usr/bin/env python3
"""
Caching utilities for cleanupx.
This module provides a simple in-memory and disk-based caching system for storing analysis results
and other computationally expensive data.
"""

import logging
import time
import os
import json
import glob
import hashlib
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
from pathlib import Path

from cleanupx.config import CACHE_FILE, RENAME_LOG_FILE

# Configure logging
logger = logging.getLogger(__name__)

# Constants for cache locations
DEFAULT_CACHE_DIR = os.path.expanduser("~/.cleanupx")
METADATA_DIR = lambda root: Path(root) / ".cleanupx"
CACHE_FILE = lambda root: METADATA_DIR(root) / "global_cache.json"
RENAME_LOG_FILE = lambda root: METADATA_DIR(root) / "rename_log.json"
CITATIONS_FILE = lambda root: METADATA_DIR(root) / "citations.json"
SUMMARY_FILE = lambda root: METADATA_DIR(root) / "directory_summary.json"
HIDDEN_SUMMARY_FILE = lambda root: METADATA_DIR(root) / "hidden_summary.json"

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
    "enabled": True,  # Global cache enable/disable flag
    "cache_dir": DEFAULT_CACHE_DIR,  # Cache directory
    "cleanup_interval": 86400,  # Cleanup interval in seconds (24 hours)
    "last_cleanup": time.time()  # Last cleanup timestamp
}

# Backward compatibility storage
_LEGACY_CACHE: Dict[str, Any] = {}
_RENAME_LOGS: Dict[str, List[Dict[str, Any]]] = {}

def ensure_metadata_dir(root: Union[str, Path]) -> Path:
    """
    Ensure the .cleanupx metadata directory exists in the given root.
    
    Args:
        root: Root directory path
        
    Returns:
        Path to the metadata directory
    """
    metadata_dir = METADATA_DIR(root)
    
    # Don't automatically create the directory, just return the path
    # Directories will be created only when files are explicitly saved
    
    return metadata_dir

def create_metadata_dir(root: Union[str, Path], create_subdirs: bool = True) -> Path:
    """
    Create the .cleanupx metadata directory in the given root.
    This is only called when we explicitly need to save metadata.
    
    Args:
        root: Root directory path
        create_subdirs: Whether to create subdirectories
        
    Returns:
        Path to the created metadata directory
    """
    metadata_dir = METADATA_DIR(root)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for different types of metadata if requested
    if create_subdirs:
        (metadata_dir / "cache").mkdir(exist_ok=True)
        (metadata_dir / "descriptions").mkdir(exist_ok=True)
        (metadata_dir / "summaries").mkdir(exist_ok=True)
    
    return metadata_dir

def get_description_path(file_path: Path) -> Path:
    """
    Get the path for a file's description markdown file.
    
    Args:
        file_path: Path to the source file
        
    Returns:
        Path to the description markdown file
    """
    metadata_dir = ensure_metadata_dir(file_path.parent)
    return metadata_dir / "descriptions" / f"{file_path.stem}.md"

def save_description(file_path: Path, description: str) -> bool:
    """
    Save a file description to its markdown file.
    
    Args:
        file_path: Path to the source file
        description: The description text
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Only create directories when actually saving a file
        metadata_dir = create_metadata_dir(file_path.parent)
        desc_path = metadata_dir / "descriptions" / f"{file_path.stem}.md"
        desc_path.parent.mkdir(exist_ok=True)
        
        with open(desc_path, 'w', encoding='utf-8') as f:
            f.write(description)
        return True
    except Exception as e:
        logger.error(f"Error saving description for {file_path}: {e}")
        return False

def get_cache_path(file_path: Union[str, Path], cache_type: str = "text") -> Path:
    """
    Get the cache path for a given file.
    
    Args:
        file_path: Path to the source file
        cache_type: Type of cache (text, images, documents)
        
    Returns:
        Path to the cache file
    """
    file_path = Path(file_path)
    
    # Use the central cache directory instead of creating .cleanupx directories everywhere
    cache_dir = Path(_CACHE_CONFIG["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a hash of the absolute path to ensure unique cache files
    file_hash = hashlib.md5(str(file_path.absolute()).encode()).hexdigest()[:8]
    
    # Create a cache filename that includes the original filename for debugging
    cache_filename = f"{file_hash}_{file_path.stem}.cache"
    
    # Ensure cache type subdirectory exists
    cache_type_dir = cache_dir / cache_type
    cache_type_dir.mkdir(exist_ok=True)
    
    return cache_type_dir / cache_filename

def configure_cache(
    max_size: Optional[int] = None,
    ttl: Optional[int] = None,
    enabled: Optional[bool] = None,
    cache_dir: Optional[str] = None,
    cleanup_interval: Optional[int] = None
) -> None:
    """
    Configure cache settings.
    
    Args:
        max_size: Maximum number of items to store in cache
        ttl: Default time-to-live for cache items in seconds
        enabled: Enable or disable caching globally
        cache_dir: Directory to store cache files
        cleanup_interval: Interval in seconds between cache cleanups
    """
    global _CACHE_CONFIG
    
    if max_size is not None:
        _CACHE_CONFIG["max_size"] = max_size
    
    if ttl is not None:
        _CACHE_CONFIG["ttl"] = ttl
    
    if enabled is not None:
        _CACHE_CONFIG["enabled"] = enabled
    
    if cache_dir is not None:
        _CACHE_CONFIG["cache_dir"] = os.path.expanduser(cache_dir)
        ensure_metadata_dir(Path(cache_dir))
    
    if cleanup_interval is not None:
        _CACHE_CONFIG["cleanup_interval"] = cleanup_interval
    
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

def clear_cache(root: Union[str, Path] = None) -> Dict[str, int]:
    """
    Clear cache files from the system.
    
    Args:
        root: Optional root directory (uses home directory if not specified)
        
    Returns:
        Stats dictionary with count of files cleared
    """
    global _MEMORY_CACHE
    
    stats = {
        "global_cache": 0,
        "rename_log": 0,
        "descriptions": 0,
        "summaries": 0
    }
    
    try:
        if root is None:
            metadata_dir = Path(DEFAULT_CACHE_DIR)
        else:
            metadata_dir = METADATA_DIR(root)
        
        if metadata_dir.exists():
            # Clear global cache
            cache_file = metadata_dir / "global_cache.json"
            if cache_file.exists():
                os.remove(cache_file)
                stats["global_cache"] = 1
            
            # Clear rename log
            log_file = metadata_dir / "rename_log.json"
            if log_file.exists():
                os.remove(log_file)
                stats["rename_log"] = 1
            
            # Clear descriptions
            desc_dir = metadata_dir / "descriptions"
            if desc_dir.exists():
                for file in desc_dir.glob("*.md"):
                    os.remove(file)
                    stats["descriptions"] += 1
            
            # Clear summaries
            sum_dir = metadata_dir / "summaries"
            if sum_dir.exists():
                for file in sum_dir.glob("*.json"):
                    os.remove(file)
                    stats["summaries"] += 1
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
    
    return stats

def cleanup_old_cache() -> None:
    """
    Clean up old cache files based on TTL and last access time.
    """
    current_time = time.time()
    
    # Check if it's time for cleanup
    if current_time - _CACHE_CONFIG["last_cleanup"] < _CACHE_CONFIG["cleanup_interval"]:
        return
    
    cache_dir = ensure_metadata_dir(Path(_CACHE_CONFIG["cache_dir"]))
    stats = {
        "text": 0,
        "images": 0,
        "documents": 0
    }
    
    for cache_type in stats.keys():
        cache_type_dir = cache_dir / cache_type
        if not cache_type_dir.exists():
            continue
            
        for cache_file in cache_type_dir.glob("*.cache"):
            try:
                # Check file modification time
                file_mtime = cache_file.stat().st_mtime
                if current_time - file_mtime > _CACHE_CONFIG["ttl"]:
                    os.remove(cache_file)
                    stats[cache_type] += 1
            except Exception as e:
                logger.error(f"Failed to remove old cache file {cache_file}: {e}")
    
    _CACHE_CONFIG["last_cleanup"] = current_time
    logger.info(f"Cleaned up old cache files: {stats}")

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

def save_cache(cache_data: Dict[str, Any], root: Union[str, Path] = None) -> None:
    """
    Save cache data to the appropriate location.
    
    Args:
        cache_data: The cache data to save
        root: Optional root directory (uses home directory if not specified)
    """
    try:
        if root is None:
            # Use the central cache directory from config
            cache_file = Path(_CACHE_CONFIG["cache_dir"]) / "global_cache.json"
        else:
            cache_file = CACHE_FILE(root)
        
        # Ensure parent directory exists
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def save_rename_log(log_data: Dict[str, Any], root: Union[str, Path]) -> None:
    """
    Save rename log data to the appropriate location.
    
    Args:
        log_data: The log data to save
        root: Root directory path
    """
    try:
        # Use the central cache directory instead of local directories
        if isinstance(root, str) and root.startswith("/"):
            # This is an absolute path, use it to create a unique filename
            import hashlib
            dir_hash = hashlib.md5(root.encode()).hexdigest()[:8]
            log_file = Path(_CACHE_CONFIG["cache_dir"]) / f"rename_log_{dir_hash}.json"
        else:
            log_file = RENAME_LOG_FILE(root)
        
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving rename log: {e}")

def load_rename_log(root: Union[str, Path]) -> Dict[str, Any]:
    """
    Load rename log data from the appropriate location.
    
    Args:
        root: Root directory path
        
    Returns:
        The loaded rename log data
    """
    try:
        log_file = RENAME_LOG_FILE(root)
        if log_file.exists():
            with open(log_file, 'r') as f:
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
        # Get the parent directory of the file as the root
        root = file_path.parent
        save_rename_log(rename_log, root)
