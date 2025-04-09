#!/usr/bin/env python3
"""
Cache management utilities for CleanupX.
"""

import os
import json
import logging
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from cleanupx.config import CACHE_FILE, RENAME_LOG_FILE

# Configure logging
logger = logging.getLogger(__name__)

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
    save_rename_log(rename_log)
