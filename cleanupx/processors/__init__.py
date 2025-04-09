#!/usr/bin/env python3
"""
File processors for CleanupX.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

from cleanupx.config import (
    IMAGE_EXTENSIONS, 
    TEXT_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, 
    ARCHIVE_EXTENSIONS,
    MEDIA_EXTENSIONS
)
from cleanupx.processors.image import process_image_file
from cleanupx.processors.text import process_text_file
from cleanupx.processors.document import process_document_file
from cleanupx.processors.archive import process_archive_file
from cleanupx.processors.media import process_media_file

# Configure logging
logger = logging.getLogger(__name__)

def process_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict, 
                max_size_mb: float = 25.0) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a file based on its extension, routing to the appropriate processor.
    
    Args:
        file_path: Path to the file to process
        cache: Cache dictionary for storing/retrieving file descriptions
        rename_log: Log for tracking renames
        max_size_mb: Maximum file size to process (in MB)
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    
    # Check file size first
    try:
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            logger.warning(f"Skipping file {file_path.name} - size {file_size_mb:.1f}MB exceeds maximum {max_size_mb}MB")
            rename_log["stats"]["skipped_files"] += 1
            return file_path, None, None
    except Exception as e:
        logger.error(f"Error checking file size: {e}")
    
    ext = file_path.suffix.lower()
    full_name = file_path.name.lower()
    
    try:
        # Handle special case for .tar.gz files
        if full_name.endswith('.tar.gz') or ext == '.tgz':
            return process_archive_file(file_path, cache, rename_log)
            
        # Route file to appropriate processor based on extension
        if ext in MEDIA_EXTENSIONS:
            return process_media_file(file_path, cache, rename_log)
        elif ext in IMAGE_EXTENSIONS:
            return process_image_file(file_path, cache, rename_log)
        elif ext in TEXT_EXTENSIONS:
            return process_text_file(file_path, cache, rename_log)
        elif ext in DOCUMENT_EXTENSIONS:
            return process_document_file(file_path, cache, rename_log)
        elif ext in ARCHIVE_EXTENSIONS:
            return process_archive_file(file_path, cache, rename_log)
        else:
            logger.info(f"Skipping unsupported file type: {file_path}")
            return file_path, None, None
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        # Add error to log
        from cleanupx.utils.cache import add_error_to_log
        add_error_to_log(rename_log, file_path, str(e), "processing_error")
        return file_path, None, None
