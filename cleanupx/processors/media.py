#!/usr/bin/env python3
"""
Media file processor for CleanupX (MP3, MP4, etc.).
"""

import logging
import gc
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from datetime import datetime

from cleanupx.config import MEDIA_EXTENSIONS
from cleanupx.utils.common import get_media_dimensions, get_media_duration, format_duration, strip_media_suffixes
from cleanupx.processors.base import rename_file
from cleanupx.utils.cache import save_cache

# Configure logging
logger = logging.getLogger(__name__)

def process_media_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Tuple[Path, Optional[Path], Optional[Dict[str, Any]]]:
    """
    Process a media file - extract metadata and rename with dimension/duration info.
    
    Args:
        file_path: Path to the media file
        cache: Cache dictionary for storing/retrieving media descriptions
        rename_log: Optional log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description) where:
            - original_path: Original file path
            - new_path: New file path if renamed, None if not renamed
            - description: Dictionary with media metadata if available, None if not available
    """
    try:
        file_path = Path(file_path)
        
        # Check if already processed
        cache_key = str(file_path)
        if cache_key in cache:
            logger.info(f"Using cached description for {file_path.name}")
            data = cache[cache_key]
        else:
            # Extract media metadata
            dimensions = get_media_dimensions(file_path)
            duration = get_media_duration(file_path)
            
            data = {
                "dimensions": dimensions,
                "duration": duration,
                "type": file_path.suffix[1:].upper() if file_path.suffix else "Unknown",
                "title": file_path.stem,
                "description": f"Media file with dimensions {dimensions} and duration {format_duration(duration)}"
            }
            
            # Cache the result
            cache[cache_key] = data
            save_cache(cache)
        
        # Generate new filename
        new_path = generate_new_filename(file_path, data)
        if new_path:
            # Create markdown file with media description
            markdown_path = new_path.with_suffix('.md')
            try:
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Media Description\n\n")
                    f.write(f"## {data.get('title', 'Untitled Media')}\n\n")
                    f.write(f"**Type:** {data.get('type', 'Unknown')}\n\n")
                    f.write(f"**Description:** {data.get('description', 'No description available')}\n\n")
                    f.write(f"**Original Name:** {file_path.name}\n")
                    f.write(f"**Current Name:** {new_path.name}\n")
                    f.write(f"**Dimensions:** {data.get('dimensions', 'Unknown')}\n")
                    f.write(f"**Duration:** {format_duration(data.get('duration', 0))}\n")
                    f.write(f"**File Size:** {file_path.stat().st_size / 1024:.2f} KB\n")
                    f.write(f"**Last Modified:** {datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n")
                logger.info(f"Created markdown description file: {markdown_path}")
            except Exception as e:
                logger.error(f"Failed to create markdown file for {file_path}: {e}")
            
            # Rename file
            success = rename_file(file_path, new_path, rename_log)
            if success:
                logger.info(f"Renamed {file_path.name} to {new_path.name}")
                return file_path, new_path, data
            else:
                logger.error(f"Failed to rename {file_path.name}")
                return file_path, None, data
        else:
            logger.warning(f"No new filename generated for {file_path.name}")
            return file_path, None, data
            
    except Exception as e:
        logger.error(f"Error processing media file {file_path}: {e}")
        return file_path, None, None
    finally:
        # Force garbage collection
        gc.collect()
