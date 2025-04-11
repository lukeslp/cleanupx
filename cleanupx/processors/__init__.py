#!/usr/bin/env python3
"""
File processors for CleanupX.

This module contains processors for different file types:
- BaseProcessor: Common base functionality for all processors
- ImageProcessor: For image files (JPG, PNG, etc.)
- DocumentProcessor: For document files (PDF, DOCX, etc.)
- ArchiveProcessor: For archive files (ZIP, TAR, etc.)
- TextProcessor: For text files (TXT, MD, etc.)
- MediaProcessor: For media files (MP3, MP4, etc.)
- DedupeProcessor: For file deduplication
- TextDedupeProcessor: For text file deduplication and merging
"""

import logging
import gc
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Type, Tuple
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
from cleanupx.processors.base import BaseProcessor
from cleanupx.processors.image import ImageProcessor
from cleanupx.processors.document import DocumentProcessor
from cleanupx.processors.archive import ArchiveProcessor
from cleanupx.processors.text import TextProcessor
from cleanupx.processors.media import MediaProcessor
from cleanupx.processors.dedupe import DedupeProcessor
from cleanupx.processors.text_dedupe import TextDedupeProcessor
from cleanupx.processors.citation import process_file_for_citations
from cleanupx.utils.common import get_file_size_mb

# Configure logging
logger = logging.getLogger(__name__)

try:
    from cleanupx.processors.smart_merge import (
        merge_code_snippets,
        find_similar_snippets,
        merge_snippet_group
    )
except ImportError as e:
    logger.warning(f"Could not import smart_merge processor: {e}")

# For backwards compatibility - these are now methods within the processor classes
process_image_file = ImageProcessor().process
process_document_file = DocumentProcessor().process
process_archive_file = ArchiveProcessor().process
process_text_file = TextProcessor().process
process_media_file = MediaProcessor().process

__all__ = [
    'BaseProcessor',
    'ImageProcessor', 
    'DocumentProcessor',
    'ArchiveProcessor',
    'TextProcessor',
    'MediaProcessor',
    'DedupeProcessor',
    'TextDedupeProcessor',
    'process_file',
    'get_processor_for_file',
    'get_file_type',
    'process_image_file',
    'process_document_file',
    'process_archive_file',
    'process_text_file',
    'process_media_file'
]

def get_processor_for_file(file_path: Union[str, Path]) -> Optional[BaseProcessor]:
    """
    Get the appropriate processor for a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Processor instance or None if no appropriate processor found
    """
    file_path = Path(file_path)
    file_ext = file_path.suffix.lower()
    
    # Try each processor in order
    processors = [
        ImageProcessor(),
        DocumentProcessor(),
        ArchiveProcessor(),
        TextProcessor(),
        MediaProcessor()
    ]
    
    for processor in processors:
        if processor.can_process(file_path):
            return processor
            
    return None

def get_file_type(file_path: Union[str, Path]) -> str:
    """
    Determine the file type based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File type as a string ("image", "document", "archive", "text", "media", or "other")
    """
    processor = get_processor_for_file(file_path)
    if processor:
        if isinstance(processor, ImageProcessor):
            return "image"
        elif isinstance(processor, DocumentProcessor):
            return "document"
        elif isinstance(processor, ArchiveProcessor):
            return "archive"
        elif isinstance(processor, TextProcessor):
            return "text"
        elif isinstance(processor, MediaProcessor):
            return "media"
    
    return "other"

def process_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None,
                max_size_mb: float = 25.0, skip_images: bool = False, skip_documents: bool = False,
                skip_archives: bool = False, skip_text: bool = False, skip_media: bool = False,
                citation_styles: Optional[List[str]] = None, generate_dash: bool = False) -> Dict[str, Any]:
    """
    Process a file based on its type.
    
    Args:
        file_path: Path to the file
        cache: Cache dictionary for storing/retrieving file descriptions
        rename_log: Optional log for tracking renames
        max_size_mb: Maximum file size in megabytes
        skip_images: Whether to skip image files
        skip_documents: Whether to skip document files
        skip_archives: Whether to skip archive files
        skip_text: Whether to skip text files
        skip_media: Whether to skip media files
        citation_styles: Optional list of citation styles to extract
        generate_dash: Whether to generate a dashboard
        
    Returns:
        Dictionary with processing results
    """
    file_path = Path(file_path)
    
    result = {
        'original_path': str(file_path),
        'new_path': None,
        'processed': False,
        'file_type': get_file_type(file_path),
        'error': None
    }
    
    # Check if we should skip this file type
    if (result['file_type'] == 'image' and skip_images) or \
       (result['file_type'] == 'document' and skip_documents) or \
       (result['file_type'] == 'archive' and skip_archives) or \
       (result['file_type'] == 'text' and skip_text) or \
       (result['file_type'] == 'media' and skip_media):
        result['error'] = f"Skipping {result['file_type']} file as requested"
        return result
        
    # Get processor for this file
    processor = get_processor_for_file(file_path)
    if not processor:
        result['error'] = f"No processor found for file type: {file_path.suffix}"
        return result
        
    # Set maximum file size
    processor.max_size_mb = max_size_mb
    
    # Process the file
    try:
        process_result = processor.process(file_path, cache, rename_log)
        
        # Update result with process_result
        result.update(process_result)
        
        if 'error' not in process_result or not process_result['error']:
            result['processed'] = True
            
        return result
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        result['error'] = str(e)
        return result
