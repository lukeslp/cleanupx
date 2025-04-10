#!/usr/bin/env python3
"""
File processors for CleanupX.

This package contains specialized file processors for different file types:
- text: Text file processor
- image: Image file processor
- document: Document file processor (PDF, DOCX, etc.)
- media: Media file processor (audio, video)
- archive: Archive file processor (ZIP, TAR, etc.)
- dedupe: Deduplication processor
- smart_merge: Intelligent document merging and deduplication
"""

import logging
import gc
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
import fnmatch
import mimetypes
import magic

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
from cleanupx.utils.common import get_file_size_mb

# Configure logging
logger = logging.getLogger(__name__)

try:
    from cleanupx.processors.smart_merge import (
        smart_merge_documents,
        find_similar_documents,
        merge_document_group
    )
except ImportError as e:
    logger.warning(f"Could not import smart_merge processor: {e}")

def process_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict, 
                max_size_mb: float = 25.0, citation_style_pdfs: bool = False, 
                generate_dashboard: bool = False) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a file based on its type.
    
    Args:
        file_path: Path to the file
        cache: Cache dictionary for storing/retrieving file descriptions
        rename_log: Log dictionary for tracking file renames
        max_size_mb: Maximum file size to process (in MB)
        citation_style_pdfs: Whether to use citation-style naming for PDFs (e.g., Author_Year_Title.pdf)
        generate_dashboard: Whether to generate an HTML dashboard after processing
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    try:
        file_path = Path(file_path)
        full_name = file_path.name
        ext = file_path.suffix.lower()
        
        # Check file size
        size_mb = get_file_size_mb(file_path)
        if size_mb > max_size_mb:
            logger.warning(f"File {file_path} exceeds maximum size ({size_mb:.2f} MB > {max_size_mb} MB). Skipping.")
            return file_path, None, None
        
        # Skip files that should be protected
        for pattern in PROTECTED_PATTERNS:
            if fnmatch.fnmatch(file_path.name.lower(), pattern.lower()):
                logger.info(f"Skipping protected file: {file_path}")
                return file_path, None, None
        
        # Handle files without extension by detecting file type and adding extension
        if not ext:
            logger.info(f"Processing file without extension: {file_path}")
            
            # Try to determine file type using magic
            try:
                mime_type = magic.from_file(str(file_path), mime=True)
                logger.info(f"Detected MIME type for {file_path}: {mime_type}")
                
                # Map MIME type to extension
                if mime_type:
                    guessed_extension = mimetypes.guess_extension(mime_type)
                    
                    if guessed_extension:
                        new_path = file_path.with_suffix(guessed_extension)
                        
                        # Rename the file to add the extension
                        try:
                            os.rename(file_path, new_path)
                            logger.info(f"Added extension to file: {file_path} -> {new_path}")
                            
                            # Update file_path for further processing
                            file_path = new_path
                            ext = guessed_extension
                            
                            # Update rename log
                            if str(file_path) not in rename_log:
                                rename_log[str(file_path)] = {
                                    "original_path": str(file_path),
                                    "new_path": str(new_path),
                                    "timestamp": str(Path(file_path).stat().st_mtime),
                                    "status": "success (extension added)"
                                }
                        except Exception as e:
                            logger.error(f"Error adding extension to {file_path}: {e}")
            except Exception as e:
                logger.error(f"Error determining file type for {file_path}: {e}")
                # Continue with processing as text file if we couldn't determine the type
        
        # Wrap each processor call in its own try/except block to prevent one failure
        # from affecting the entire process
        result = None
        try:
            # Process file based on extension
            if ext in DOCUMENT_EXTENSIONS:
                result = process_document_file(file_path, cache, rename_log, citation_style_pdfs)
            elif ext in TEXT_EXTENSIONS:
                result = process_text_file(file_path, cache, rename_log)
            elif ext in IMAGE_EXTENSIONS:
                result = process_image_file(file_path, cache, rename_log)
            elif ext in MEDIA_EXTENSIONS:
                result = process_media_file(file_path, cache, rename_log)
            # Handle special case for .tar.gz files
            elif full_name.endswith('.tar.gz') or ext == '.tgz':
                result = process_archive_file(file_path, cache, rename_log)
            elif ext in ARCHIVE_EXTENSIONS:
                result = process_archive_file(file_path, cache, rename_log)
            else:
                # For unknown file types, default to text processing
                logger.info(f"Unknown file type: {file_path}, processing as text")
                result = process_text_file(file_path, cache, rename_log)
            
            # Force garbage collection after processing each file
            gc.collect()
            
            return result
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            # Force garbage collection after errors
            gc.collect()
            return file_path, None, None
            
    except Exception as e:
        logger.error(f"Error in file processing pipeline for {file_path}: {e}")
        # Force garbage collection after errors
        gc.collect()
        return file_path, None, None
