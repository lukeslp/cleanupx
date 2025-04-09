#!/usr/bin/env python3
"""
Media file processor for CleanupX (MP3, MP4, etc.).
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

from cleanupx.config import MEDIA_EXTENSIONS
from cleanupx.utils.common import get_media_dimensions, get_media_duration, format_duration, strip_media_suffixes
from cleanupx.processors.base import rename_file

# Configure logging
logger = logging.getLogger(__name__)

def process_media_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process a media file - extract metadata and rename with dimension/duration info.
    
    Args:
        file_path: Path to the media file
        cache: Cache dictionary (not used for media files but kept for API consistency)
        rename_log: Log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    duration = get_media_duration(file_path)
    dimensions = get_media_dimensions(file_path)
    
    # Clean the stem to remove any existing resolution/duration tokens
    clean_stem = strip_media_suffixes(file_path.stem)
    
    if dimensions:
        resolution = f"{dimensions[0]}x{dimensions[1]}"
    else:
        resolution = "unknown"
    if duration:
        duration_str = format_duration(duration)
    else:
        duration_str = "unknown"
    
    if file_path.suffix.lower() in {'.mp3', '.wav', '.ogg', '.flac', '.mp4', '.avi', '.mov', '.mkv'}:
        new_name = f"{clean_stem}_{resolution}_{duration_str}{file_path.suffix}"
    elif file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
        new_name = f"{clean_stem}_{resolution}{file_path.suffix}"
    else:
        return file_path, None, None
        
    new_path = rename_file(file_path, new_name, rename_log)
    return file_path, new_path, None
