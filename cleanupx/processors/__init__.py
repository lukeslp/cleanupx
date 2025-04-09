#!/usr/bin/env python3
"""
File processors for CleanupX.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
import fnmatch

from cleanupx.config import (
    IMAGE_EXTENSIONS, 
    TEXT_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, 
    ARCHIVE_EXTENSIONS,
    MEDIA_EXTENSIONS,
    PROTECTED_PATTERNS
)
from cleanupx.processors.image import process_image_file
from cleanupx.processors.text import process_text_file
from cleanupx.processors.document import process_document_file
from cleanupx.processors.archive import process_archive_file
from cleanupx.processors.media import process_media_file
from cleanupx.processors.dedupe import dedupe_directory
from cleanupx.processors.citation import process_file_for_citations

# Configure logging
logger = logging.getLogger(__name__)

def process_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict, 
                max_size_mb: float = 25.0, citation_style_pdfs: bool = False) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a file - analyze content, generate description, and possibly rename.
    
    Args:
        file_path: Path to the file
        cache: Cache dictionary for storing/retrieving descriptions
        rename_log: Log for tracking renames
        max_size_mb: Maximum file size to process in MB
        citation_style_pdfs: Whether to use citation-style naming for PDFs
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    
    # Skip files larger than the maximum size
    try:
        if file_path.stat().st_size / (1024 * 1024) > max_size_mb:
            logger.warning(f"Skipping {file_path} - larger than {max_size_mb}MB")
            return file_path, None, None
    except Exception as e:
        logger.error(f"Error checking file size for {file_path}: {e}")
        return file_path, None, None
    
    # Skip files that should be protected
    for pattern in PROTECTED_PATTERNS:
        if fnmatch.fnmatch(file_path.name.lower(), pattern.lower()):
            logger.info(f"Skipping protected file: {file_path}")
            return file_path, None, None
    
    ext = file_path.suffix.lower()
    full_name = file_path.name.lower()
    
    try:
        # For files without extension, treat as text
        if not ext:
            logger.info(f"Processing file without extension as text: {file_path}")
            result = process_text_file(file_path, cache, rename_log)
            
            # For text files that might contain citations, also extract citations
            if ext in {'.txt', '.md', '.markdown'}:
                try:
                    process_file_for_citations(file_path)
                except Exception as e:
                    logger.error(f"Error extracting citations from {file_path}: {e}")
            
            return result
            
        # Handle special case for .tar.gz files
        if full_name.endswith('.tar.gz') or ext == '.tgz':
            return process_archive_file(file_path, cache, rename_log)
            
        # Route file to appropriate processor based on extension
        if ext in MEDIA_EXTENSIONS:
            return process_media_file(file_path, cache, rename_log)
        elif ext in IMAGE_EXTENSIONS:
            return process_image_file(file_path, cache, rename_log)
        elif ext in TEXT_EXTENSIONS:
            result = process_text_file(file_path, cache, rename_log)
            
            # For text files that might contain citations, also extract citations
            if ext in {'.txt', '.md', '.markdown'}:
                try:
                    process_file_for_citations(file_path)
                except Exception as e:
                    logger.error(f"Error extracting citations from {file_path}: {e}")
            
            return result
        elif ext in DOCUMENT_EXTENSIONS:
            result = process_document_file(file_path, cache, rename_log, citation_style_pdfs)
            
            # For document files, also extract citations
            try:
                process_file_for_citations(file_path)
            except Exception as e:
                logger.error(f"Error extracting citations from {file_path}: {e}")
            
            return result
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
