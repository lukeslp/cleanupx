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
from cleanupx.processors.base import BaseProcessor
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path

# Configure logging
logger = logging.getLogger(__name__)

class MediaProcessor(BaseProcessor):
    """Processor for media files (MP3, MP4, etc.)."""
    
    def __init__(self):
        """Initialize the media processor."""
        super().__init__()
        self.supported_extensions = MEDIA_EXTENSIONS
        self.max_size_mb = 100.0  # Media files can be large
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process a media file.
        
        Args:
            file_path: Path to the media file
            cache: Cache dictionary for storing/retrieving media descriptions
            rename_log: Optional log for tracking renames
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        result = {
            'original_path': str(file_path),
            'new_path': None,
            'description': None,
            'metadata_extracted': False,
            'renamed': False,
            'error': None
        }
        
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                result['error'] = f"Unsupported file type: {file_path.suffix}"
                return result
                
            # Check file size
            if not self.check_file_size(file_path):
                result['error'] = f"File size exceeds maximum ({self.max_size_mb}MB)"
                return result
                
            # Extract metadata
            description = self._extract_metadata(file_path, cache)
            if not description:
                result['error'] = "Failed to extract metadata"
                return result
                
            result['description'] = description
            result['metadata_extracted'] = True
            
            # Generate new filename
            new_name = self._generate_media_filename(file_path, description)
            if not new_name:
                result['error'] = "Failed to generate new filename"
                return result
                
            # Rename file using inherited method
            new_path = super().rename_file(file_path, new_name, rename_log)
            if new_path:
                result['new_path'] = str(new_path)
                result['renamed'] = True
                
            # Generate markdown
            self._generate_markdown(file_path, description)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing media file {file_path}: {e}")
            result['error'] = str(e)
            return result
        finally:
            # Force garbage collection
            gc.collect()
            
    def _extract_metadata(self, file_path: Path, cache: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from a media file.
        
        Args:
            file_path: Path to the media file
            cache: Cache dictionary for storing/retrieving media descriptions
            
        Returns:
            Dictionary with media metadata or None if extraction failed
        """
        try:
            # Check if already processed
            cache_key = str(file_path)
            if cache_key in cache:
                logger.info(f"Using cached description for {file_path.name}")
                return cache[cache_key]
                
            # Extract media metadata
            dimensions = get_media_dimensions(file_path)
            duration = get_media_duration(file_path)
            file_stats = file_path.stat()
            file_size_mb = file_stats.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            data = {
                "dimensions": dimensions,
                "duration": duration,
                "format_duration": format_duration(duration),
                "type": file_path.suffix[1:].upper() if file_path.suffix else "Unknown",
                "title": strip_media_suffixes(file_path.stem),
                "file_size": f"{file_size_mb:.2f} MB",
                "modified_date": modified_time,
                "description": f"Media file with dimensions {dimensions} and duration {format_duration(duration)}"
            }
            
            # Cache the result
            cache[cache_key] = data
            save_cache(cache)
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return None
            
    def _generate_media_filename(self, file_path: Path, description: Dict[str, Any]) -> Optional[str]:
        """
        Generate a media-specific filename with dimensions and/or duration.
        
        Args:
            file_path: Path to the media file
            description: Dictionary with media metadata
            
        Returns:
            New filename with metadata (with extension) or None if generation failed
        """
        try:
            original_stem = strip_media_suffixes(file_path.stem)
            ext = file_path.suffix.lower()
            
            dimensions = description.get('dimensions')
            duration = description.get('duration')
            
            # For video files, include both dimensions and duration
            if ext.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']:
                if dimensions and dimensions != 'Unknown' and duration:
                    duration_str = format_duration(duration).replace(':', '_')
                    return f"{original_stem}_{dimensions}_{duration_str}{ext}"
                elif dimensions and dimensions != 'Unknown':
                    return f"{original_stem}_{dimensions}{ext}"
                elif duration:
                    duration_str = format_duration(duration).replace(':', '_')
                    return f"{original_stem}_{duration_str}{ext}"
                    
            # For audio files, just include duration
            elif ext.lower() in ['.mp3', '.wav', '.ogg', '.flac', '.aac']:
                if duration:
                    duration_str = format_duration(duration).replace(':', '_')
                    return f"{original_stem}_{duration_str}{ext}"
                    
            # Fallback to base filename
            return f"{original_stem}{ext}"
            
        except Exception as e:
            logger.error(f"Error generating media filename for {file_path}: {e}")
            return None
            
    def _generate_markdown(self, file_path: Path, description: Dict[str, Any]):
        """
        Generate markdown description for the media file.
        
        Args:
            file_path: Path to the media file
            description: Dictionary with media description
        """
        try:
            ensure_metadata_dir(file_path.parent)
            md_path = get_description_path(file_path)
            
            content = [
                f"# {description.get('title', file_path.stem)}",
                "",
                "## Media Information",
                f"- **Original Filename:** {file_path.name}",
                f"- **Media Type:** {description.get('type', 'Unknown')}",
                f"- **File Size:** {description.get('file_size', 'Unknown')}",
                f"- **Modified Date:** {description.get('modified_date', 'Unknown')}"
            ]
            
            if description.get('dimensions') and description.get('dimensions') != 'Unknown':
                content.append(f"- **Dimensions:** {description.get('dimensions')}")
                
            if description.get('duration'):
                content.append(f"- **Duration:** {description.get('format_duration', format_duration(description.get('duration')))}")
                
            content.extend([
                "",
                "## Description",
                description.get('description', 'No description available')
            ])
            
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
            logger.info(f"Generated markdown description: {md_path}")
        except Exception as e:
            logger.error(f"Error generating markdown for {file_path}: {e}")

# Keep for backward compatibility
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
    processor = MediaProcessor()
    result = processor.process(file_path, cache, rename_log)
    
    new_path = None
    if result.get('new_path'):
        new_path = Path(result['new_path'])
        
    return Path(file_path), new_path, result.get('description')
