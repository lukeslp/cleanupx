#!/usr/bin/env python3
"""
Cache management utilities for CleanupX.
"""

import os
import json
import logging
import pickle
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

from cleanupx.config import CACHE_FILE, RENAME_LOG_FILE

# Configure logging
logger = logging.getLogger(__name__)

# In-memory cache to store data
_MEMORY_CACHE: Dict[str, Any] = {}
_MEMORY_RENAME_LOG: List[Dict[str, Any]] = []

def init_cache() -> None:
    """Initialize the cache system."""
    # Clear in-memory cache
    global _MEMORY_CACHE, _MEMORY_RENAME_LOG
    _MEMORY_CACHE = {}
    _MEMORY_RENAME_LOG = []
    logger.info("Initialized in-memory cache")

def is_cached(key: str) -> bool:
    """
    Check if a key exists in the in-memory cache.
    
    Args:
        key: The cache key to check
        
    Returns:
        True if the key exists in cache, False otherwise
    """
    return key in _MEMORY_CACHE

def save_to_cache(key: str, data: Any) -> bool:
    """
    Save data to the in-memory cache.
    
    Args:
        key: The cache key
        data: Data to cache
        
    Returns:
        True if successful, False otherwise
    """
    try:
        _MEMORY_CACHE[key] = data
        return True
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")
        return False

def get_from_cache(key: str) -> Any:
    """
    Retrieve data from the in-memory cache.
    
    Args:
        key: The cache key
        
    Returns:
        The cached data or None if not found
    """
    return _MEMORY_CACHE.get(key)

def clear_cache() -> None:
    """
    Clear all items from the in-memory cache.
    """
    _MEMORY_CACHE.clear()
    logger.info("In-memory cache cleared")

def remove_from_cache(key: str) -> bool:
    """
    Remove a specific key from the in-memory cache.
    
    Args:
        key: The cache key to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if key in _MEMORY_CACHE:
            del _MEMORY_CACHE[key]
            return True
        return False
    except Exception as e:
        logger.error(f"Error removing from cache: {e}")
        return False

def log_rename_operation(
    original_path: Union[str, Path], 
    new_path: Union[str, Path], 
    operation_type: str = "rename",
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a rename operation to the rename log.
    
    Args:
        original_path: Original file path
        new_path: New file path
        operation_type: Type of operation (rename, move, etc.)
        metadata: Additional metadata to store
    """
    # Convert paths to strings
    original_path_str = str(original_path)
    new_path_str = str(new_path)
    
    # Create log entry
    log_entry = {
        "original_path": original_path_str,
        "new_path": new_path_str,
        "operation_type": operation_type,
        "timestamp": str(Path(new_path_str).stat().st_mtime if Path(new_path_str).exists() else 0)
    }
    
    # Add metadata if provided
    if metadata:
        log_entry["metadata"] = metadata
    
    global _MEMORY_RENAME_LOG
    _MEMORY_RENAME_LOG.append(log_entry)
    logger.info(f"Logged rename operation: {original_path_str} -> {new_path_str}")

def get_rename_log() -> List[Dict[str, Any]]:
    """
    Get the complete rename log.
    
    Returns:
        List of rename log entries
    """
    global _MEMORY_RENAME_LOG
    return _MEMORY_RENAME_LOG

def clear_rename_log() -> None:
    """Clear the rename log."""
    global _MEMORY_RENAME_LOG
    _MEMORY_RENAME_LOG = []
    logger.info("In-memory rename log cleared")

# For backward compatibility - file system operations

def save_rename_log(rename_log: Dict, log_file: Union[str, Path]) -> bool:
    """
    Save rename log to a file.
    This function is kept for backward compatibility.
    
    Args:
        rename_log: Dictionary containing rename operations
        log_file: Path to the log file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        log_file = Path(log_file)
        os.makedirs(log_file.parent, exist_ok=True)
        
        # Also keep a copy in memory
        save_to_cache("rename_log", rename_log)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(rename_log, f, indent=2)
        
        logger.info(f"Rename log saved to {log_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving rename log: {e}")
        return False

def load_rename_log(log_file: Union[str, Path]) -> Dict:
    """
    Load rename log from a file.
    This function is kept for backward compatibility.
    
    Args:
        log_file: Path to the log file
        
    Returns:
        Dictionary containing rename operations
    """
    try:
        log_file = Path(log_file)
        
        # Check if in memory first
        cached_log = get_from_cache("rename_log")
        if cached_log:
            return cached_log
        
        if not log_file.exists():
            logger.warning(f"Rename log file does not exist: {log_file}")
            return {}
        
        with open(log_file, 'r', encoding='utf-8') as f:
            rename_log = json.load(f)
        
        # Store in memory for future access
        save_to_cache("rename_log", rename_log)
        
        return rename_log
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in rename log: {log_file}")
        return {}
    except Exception as e:
        logger.error(f"Error loading rename log: {e}")
        return {}
