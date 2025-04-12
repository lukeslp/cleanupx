#!/usr/bin/env python3
"""
String utility functions for the CleanupX file organization tool.
"""

import logging
import re
from typing import Optional, Union, List

# Configure logging
logger = logging.getLogger(__name__)

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncates a string to a maximum length, adding a suffix if truncated.
    
    Args:
        text: The string to truncate
        max_length: Maximum length of the string (default: 50)
        suffix: Suffix to add if string is truncated (default: "...")
        
    Returns:
        Truncated string with suffix if needed
    """
    try:
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    except Exception as e:
        logger.error(f"Error truncating string: {e}")
        return text

def clean_filename(text: str, max_length: int = 50) -> str:
    """
    Cleans text to create a valid filename.
    
    Args:
        text: Text to clean
        max_length: Maximum length of filename (default: 50)
        
    Returns:
        Cleaned filename string
    """
    try:
        # Remove invalid characters
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', text)
        # Replace multiple spaces with single underscore
        cleaned = re.sub(r'\s+', '_', cleaned)
        # Remove leading/trailing spaces and underscores
        cleaned = cleaned.strip('_')
        # Truncate if needed
        return truncate_string(cleaned, max_length, '')
    except Exception as e:
        logger.error(f"Error cleaning filename: {e}")
        return text

def strip_media_suffixes(stem: str) -> str:
    """
    Removes duplicate appended resolution and duration patterns from a filename stem.
    
    Args:
        stem: Filename stem to clean
        
    Returns:
        Cleaned filename stem
    """
    try:
        # Remove common media suffixes
        patterns = [
            r'_\d+x\d+',  # Resolution (e.g., _1920x1080)
            r'_\d+p',     # Resolution (e.g., _1080p)
            r'_\d+k',     # Resolution (e.g., _4k)
            r'_\d+\.\d+s', # Duration (e.g., _1.5s)
            r'_\d+s',     # Duration (e.g., _1s)
            r'_\d+ms',    # Duration (e.g., _100ms)
        ]
        
        cleaned = stem
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned)
            
        return cleaned
    except Exception as e:
        logger.error(f"Error stripping media suffixes: {e}")
        return stem

def normalize_whitespace(text: str) -> str:
    """
    Normalizes whitespace in a string.
    
    Args:
        text: Text to normalize
        
    Returns:
        Text with normalized whitespace
    """
    try:
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        return text.strip()
    except Exception as e:
        logger.error(f"Error normalizing whitespace: {e}")
        return text

def split_camel_case(text: str) -> str:
    """
    Splits camelCase or PascalCase text into words.
    
    Args:
        text: Text to split
        
    Returns:
        Text with spaces between words
    """
    try:
        # Split on camelCase or PascalCase
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    except Exception as e:
        logger.error(f"Error splitting camel case: {e}")
        return text 