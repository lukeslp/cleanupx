#!/usr/bin/env python3
"""
Text file processor for CleanupX.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

from cleanupx.config import TEXT_EXTENSIONS, DOCUMENT_FUNCTION_SCHEMA, FILE_TEXT_PROMPT, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file
from cleanupx.utils.cache import save_cache
from cleanupx.api import call_xai_api
from cleanupx.processors.base import generate_new_filename, rename_file

# Configure logging
logger = logging.getLogger(__name__)

def analyze_text_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Analyze text file content using X.AI API.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Dictionary with text file analysis or None if analysis failed
    """
    file_path = Path(file_path)
    content = read_text_file(file_path)
    if not content.strip():
        logger.error(f"No content found in {file_path}")
        return None
    prompt = FILE_TEXT_PROMPT.format(suffix=file_path.suffix, name=file_path.name, content=content[:10000])
    result = call_xai_api(XAI_MODEL_TEXT, prompt, DOCUMENT_FUNCTION_SCHEMA)
    if result:
        logger.info(f"Successfully analyzed text file: {file_path.name}")
        return result
    logger.error(f"Failed to analyze text file: {file_path.name}")
    return None

def process_text_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a text file - analyze content and rename based on content.
    
    Args:
        file_path: Path to the text file
        cache: Cache dictionary for storing/retrieving file descriptions
        rename_log: Log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    cache_key = str(file_path)
    cached_result = cache.get(cache_key)
    description = None
    if cached_result:
        try:
            if isinstance(cached_result, str):
                description = json.loads(cached_result)
            else:
                description = cached_result
            logger.info(f"Using cached description for {file_path}")
        except json.JSONDecodeError:
            description = None
    if not description:
        description = analyze_text_file(file_path)
        if description:
            cache[cache_key] = description
            save_cache(cache)
    if not description:
        logger.warning(f"Could not analyze text file: {file_path}")
        return file_path, None, None
    new_name = generate_new_filename(file_path, description)
    new_path = None
    if new_name:
        new_path = rename_file(file_path, new_name, rename_log)
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
    return file_path, new_path, description
