#!/usr/bin/env python3
"""
Base processor for handling file operations.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from datetime import datetime
from abc import ABC, abstractmethod

from cleanupx.utils.common import strip_media_suffixes
from cleanupx.utils.cache import save_rename_log, add_error_to_log

from ..core.config import (
    IMAGE_EXTENSIONS,
    MEDIA_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    TEXT_EXTENSIONS,
    CODE_EXTENSIONS
)

# Configure logging
logger = logging.getLogger(__name__)

def clean_filename(filename: str) -> str:
    """
    Clean a filename by removing invalid characters and controlling spaces.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Replace invalid characters with underscores
    invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
    filename = re.sub(invalid_chars, '_', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Replace multiple underscores with a single one
    while '__' in filename:
        filename = filename.replace('__', '_')
        
    # Remove leading/trailing underscores, dots, commas
    chars_to_strip = ['_', '.', ',', '-']
    base_name, ext = os.path.splitext(filename)
    
    for char in chars_to_strip:
        while base_name.startswith(char):
            base_name = base_name[1:]
        while base_name.endswith(char):
            base_name = base_name[:-1]
            
    # Limit filename length (Windows max path is 260 chars, leave room for path)
    if len(base_name) > 200:
        base_name = base_name[:200]
        
    # If base name is empty, use a timestamp
    if not base_name:
        base_name = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    return base_name + ext

class BaseProcessor(ABC):
    """Base class for all file processors."""
    
    def __init__(self):
        """Initialize the processor."""
        self.supported_extensions = set()
        self.max_size_mb = 25.0
        
    @abstractmethod
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process a file.
        
        Args:
            file_path: Path to the file
            cache: Cache dictionary for storing/retrieving file descriptions
            rename_log: Optional log for tracking renames
            
        Returns:
            Dictionary with processing results
        """
        pass
        
    def can_process(self, file_path: Union[str, Path]) -> bool:
        """
        Check if the processor can handle the file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the processor can handle the file, False otherwise
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() in self.supported_extensions
        
    def check_file_size(self, file_path: Union[str, Path]) -> bool:
        """
        Check if the file size is within limits.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file size is acceptable, False otherwise
        """
        try:
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            return file_size_mb <= self.max_size_mb
        except Exception as e:
            logger.error(f"Error checking file size: {e}")
            return False
            
    def generate_new_filename(
        self,
        file_path: Union[str, Path],
        description: Union[str, Dict],
        file_type: str = None
    ) -> str:
        """Generate a descriptive filename based on file description."""
        file_path = Path(file_path)
        extension = file_path.suffix
        
        # If description is a dict, try to extract suggested_filename
        if isinstance(description, dict):
            if 'suggested_filename' in description:
                suggested_name = description['suggested_filename']
            elif 'filename' in description:
                suggested_name = description['filename']
            else:
                # Use description text if available, otherwise default
                suggested_name = description.get('description', file_path.stem)
        else:
            # Try to extract JSON data from the description string
            import json
            import re
            
            json_match = re.search(r'\{.*"suggested_filename":\s*"([^"]+)".*\}', description)
            if json_match:
                try:
                    # Try to parse the JSON
                    json_str = re.search(r'\{.*\}', description, re.DOTALL).group(0)
                    json_data = json.loads(json_str)
                    suggested_name = json_data.get('suggested_filename', file_path.stem)
                except (json.JSONDecodeError, AttributeError):
                    # Fall back to simple text processing
                    suggested_name = self.clean_filename(description[:100])
            else:
                # Just use the description text directly
                suggested_name = self.clean_filename(description[:100])
        
        # Clean up suggested name
        suggested_name = self.sanitize_filename(suggested_name)
        
        # Add prefix based on file type if not already present
        file_type_prefix = ""
        if file_type:
            if file_type == "document":
                file_type_prefix = "doc_"
            elif file_type == "image":
                file_type_prefix = "img_"
            elif file_type == "audio":
                file_type_prefix = "audio_"
            elif file_type == "video":
                file_type_prefix = "video_"
            elif file_type == "archive":
                file_type_prefix = "archive_"
        
        # Only add prefix if it's not already at the start of the name
        if file_type_prefix and not suggested_name.startswith(file_type_prefix):
            final_name = f"{file_type_prefix}{suggested_name}"
        else:
            final_name = suggested_name
        
        # Ensure file has extension
        if not "." in final_name:
            final_name = f"{final_name}{extension}"
            
        # Limit to a reasonable length
        if len(final_name) > 255:
            name_part, ext_part = os.path.splitext(final_name)
            final_name = f"{name_part[:250]}{ext_part}"
            
        return final_name
        
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to remove invalid characters."""
        # Remove invalid characters for filenames
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Ensure the filename is not too long (max 255 characters)
        if len(sanitized) > 255:
            name_part, ext_part = os.path.splitext(sanitized)
            sanitized = f"{name_part[:250]}{ext_part}"
            
        return sanitized
        
    def rename_file(self, original_path: Path, new_name: str, rename_log: Optional[Dict] = None) -> Optional[Path]:
        """
        Rename a file, forcing a new name if the generated name equals the original.
        
        Args:
            original_path: Path to the original file
            new_name: New filename (with extension)
            rename_log: Optional rename log to update
            
        Returns:
            Path to the renamed file or None if rename failed
        """
        try:
            if not os.path.splitext(new_name)[1]:
                new_name = f"{new_name}{original_path.suffix}"
            new_path = original_path.parent / new_name
            counter = 1
            base_name, ext = os.path.splitext(new_name)
            
            while new_path.exists() and new_path != original_path:
                new_name = f"{base_name}_{counter}{ext}"
                new_path = original_path.parent / new_name
                counter += 1
                
            if new_path == original_path:
                logger.info(f"New filename matches original, skipping rename for {original_path}")
                if rename_log is not None:
                    rename_log["stats"]["skipped_files"] += 1
                    root = original_path.parent
                    save_rename_log(rename_log, root)
                return original_path
                
            try:
                os.replace(str(original_path), str(new_path))
                logger.info(f"Renamed: {original_path} -> {new_path}")
                if rename_log is not None:
                    rename_log["stats"]["successful_renames"] += 1
            except OSError as e:
                logger.warning(f"Atomic rename failed, falling back to copy + delete for {original_path}")
                try:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(str(original_path), str(new_path))
                    if new_path.exists() and new_path.stat().st_size == original_path.stat().st_size:
                        original_path.unlink()
                        logger.info(f"Completed copy + delete rename from {original_path} to {new_path}")
                        if rename_log is not None:
                            rename_log["stats"]["successful_renames"] += 1
                    else:
                        raise OSError("File copy verification failed")
                except Exception as e:
                    logger.error(f"Copy + delete rename failed: {e}")
                    if new_path.exists():
                        try:
                            new_path.unlink()
                        except:
                            pass
                    if rename_log is not None:
                        add_error_to_log(rename_log, original_path, str(e), "copy_delete_error")
                    return None
                    
            if rename_log is not None:
                rename_entry = {
                    "original_path": str(original_path),
                    "new_path": str(new_path),
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                }
                rename_log["renames"].append(rename_entry)
                root = original_path.parent
                save_rename_log(rename_log, root)
            return new_path
        except Exception as e:
            logger.error(f"Error renaming file {original_path}: {e}")
            if rename_log is not None:
                add_error_to_log(rename_log, original_path, str(e), "rename_error")
            return None
