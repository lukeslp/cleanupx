#!/usr/bin/env python3
"""
File utility functions for the CleanupX file organization tool.
"""

import os
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

# Configure logging
logger = logging.getLogger(__name__)

class FileProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass

def get_file_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get metadata for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file metadata
    """
    file_path = Path(file_path)
    try:
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'created': format_timestamp(stat.st_ctime),
            'modified': format_timestamp(stat.st_mtime),
            'accessed': format_timestamp(stat.st_atime),
            'is_file': file_path.is_file(),
            'is_dir': file_path.is_dir(),
            'extension': file_path.suffix.lower(),
            'name': file_path.name,
            'stem': file_path.stem,
            'parent': str(file_path.parent)
        }
    except Exception as e:
        logger.error(f"Error getting metadata for {file_path}: {e}")
        return {}

def format_timestamp(timestamp: float) -> str:
    """
    Format a Unix timestamp into a human-readable string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted date string
    """
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"Error formatting timestamp {timestamp}: {e}")
        return ""

def get_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> Optional[str]:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        Hex digest of the file hash, or None if hashing fails
    """
    file_path = Path(file_path)
    try:
        import hashlib
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None

def is_binary_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file is binary.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is binary, False otherwise
    """
    file_path = Path(file_path)
    try:
        with open(file_path, 'rb') as f:
            # Read first 1024 bytes
            chunk = f.read(1024)
            # Check for null bytes or non-printable characters
            return b'\0' in chunk or any(byte < 32 and byte not in (9, 10, 13) for byte in chunk)
    except Exception as e:
        logger.error(f"Error checking if file is binary: {e}")
        return False

def validate_file(file_path: Union[str, Path], supported_extensions: Optional[List[str]] = None) -> bool:
    """
    Validates if a file can be processed.
    
    Args:
        file_path: Path to the file to validate
        supported_extensions: Optional list of supported file extensions
        
    Returns:
        bool: Whether the file is valid for processing
    """
    file_path = Path(file_path)
    try:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False
            
        if not file_path.is_file():
            logger.warning(f"Not a file: {file_path}")
            return False
            
        if supported_extensions and file_path.suffix.lower() not in supported_extensions:
            logger.warning(f"Unsupported file type: {file_path}")
            return False
            
        # Check if file is readable
        try:
            file_path.open('rb').close()
        except Exception as e:
            logger.warning(f"File not readable: {file_path} - {str(e)}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error validating file {file_path}: {str(e)}")
        return False

def create_backup(file_path: Union[str, Path]) -> Optional[Path]:
    """
    Creates a backup of a file before processing.
    
    Args:
        file_path: Path to the file to backup
        
    Returns:
        Path to the backup file, or None if backup fails
        
    Raises:
        FileProcessingError: If backup creation fails
    """
    file_path = Path(file_path)
    try:
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        logger.info(f"Creating backup: {backup_path}")
        
        shutil.copy2(file_path, backup_path)
        return backup_path
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return None

def restore_from_backup(backup_path: Union[str, Path]) -> bool:
    """
    Restores a file from its backup.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        bool: Whether restoration was successful
    """
    backup_path = Path(backup_path)
    try:
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
            
        original_path = backup_path.with_suffix('')
        logger.info(f"Restoring from backup: {original_path}")
        
        shutil.move(backup_path, original_path)
        return True
        
    except Exception as e:
        logger.error(f"Error restoring from backup: {str(e)}")
        return False

def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    Get the extension of a file (including the dot).
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (lowercase) including the dot, or empty string if no extension
    """
    try:
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        return ext
    except Exception as e:
        logger.error(f"Error getting file extension for {file_path}: {e}")
        return "" 