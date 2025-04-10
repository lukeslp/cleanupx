#!/usr/bin/env python3
"""
Base processor for handling file operations.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any
from datetime import datetime

from cleanupx.utils.common import clean_filename, strip_media_suffixes
from cleanupx.utils.cache import save_rename_log, add_error_to_log

# Configure logging
logger = logging.getLogger(__name__)

def generate_new_filename(file_path: Union[str, Path], description: Optional[Dict[str, Any]] = None, 
                         use_extensions_from: Optional[set] = None) -> Optional[str]:
    """
    Generate a new filename based on file type and description.
    
    Args:
        file_path: Path to the file
        description: Dictionary with file description from AI analysis
        use_extensions_from: Optional set of extensions to check file against
        
    Returns:
        New filename (with extension) or None if generation failed
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    
    # For non-image files, use the previous logic
    if description and isinstance(description, dict):
        suggested_name = description.get("suggested_filename")
        if suggested_name and isinstance(suggested_name, str):
            clean_name = clean_filename(suggested_name)
            return f"{clean_name}{ext}"
    
    clean_stem = strip_media_suffixes(file_path.stem)
    fallback_name = clean_filename(clean_stem)
    return f"{fallback_name}{ext}"

def rename_file(original_path: Path, new_name: str, rename_log: Optional[Dict] = None) -> Optional[Path]:
    """
    Rename a file, forcing a new name if the generated name equals the original.
    The rename log is updated if provided.
    
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

        # If the new path is the same as the original, don't rename
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
        
def process_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict, 
                max_size_mb: float = 25.0, generate_image_md: bool = True, generate_archive_md: bool = True) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Base function to process a file. This will be overridden by specific processors.
    
    Args:
        file_path: Path to the file to process
        cache: Cache dictionary for storing/retrieving file descriptions
        rename_log: Log for tracking renames
        max_size_mb: Maximum file size to process (in MB)
        generate_image_md: Flag to indicate if image markdown should be generated
        generate_archive_md: Flag to indicate if archive markdown should be generated
        
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
    
    # This is a base implementation that should be overridden by subclasses
    logger.info(f"Base implementation - not processing {file_path}")
    return file_path, None, None
