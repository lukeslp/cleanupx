#!/usr/bin/env python3
"""
Dedupe processor for CleanupX.

This module provides functionality to detect and remove duplicate files based on size and content.
It can identify duplicate images based on file size and resolution and other file types
based on file size and content hash.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any, Set
import gc

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL/Pillow not installed. Image resolution detection disabled.")

from cleanupx.processors.base import BaseProcessor
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path

# Configure logging
logger = logging.getLogger(__name__)

class DedupeProcessor(BaseProcessor):
    """Processor for deduplicating files."""
    
    def __init__(self):
        """Initialize the dedupe processor."""
        super().__init__()
        self.supported_extensions = set()  # Support all file types
        self.max_size_mb = 1000.0  # Allow larger files for deduplication
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process a file for deduplication.
        
        Args:
            file_path: Path to the file
            cache: Cache dictionary for storing/retrieving file hashes
            rename_log: Optional log for tracking renames
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        result = {
            'original_path': str(file_path),
            'new_path': None,
            'hash': None,
            'size': None,
            'resolution': None,
            'is_duplicate': False,
            'error': None
        }
        
        try:
            # Get file size
            file_size = file_path.stat().st_size
            result['size'] = file_size
            
            # Check if we have a cached hash
            cache_key = str(file_path)
            if cache_key in cache:
                result['hash'] = cache[cache_key].get('hash')
            
            # If no cached hash, calculate it
            if not result['hash']:
                result['hash'] = get_file_hash(file_path)
                if result['hash']:
                    cache[cache_key] = {'hash': result['hash']}
                    save_cache(cache)
            
            # For images, also get resolution
            if PIL_AVAILABLE and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}:
                try:
                    with Image.open(file_path) as img:
                        result['resolution'] = img.size
                except Exception as e:
                    logger.error(f"Error getting image resolution for {file_path}: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            result['error'] = str(e)
            return result
            
    def process_directory(self, directory: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
        """
        Process a directory to find duplicates.
        
        Args:
            directory: Directory to process
            recursive: Whether to process subdirectories
            
        Returns:
            Dictionary with deduplication results
        """
        directory = Path(directory)
        result = {
            'directory': str(directory),
            'duplicate_groups': [],
            'total_duplicates': 0,
            'total_size_saved': 0,
            'error': None
        }
        
        try:
            # Find duplicates
            duplicate_groups = detect_duplicates(directory, recursive=recursive)
            
            # Process results
            for key, files in duplicate_groups.items():
                if len(files) > 1:  # Only include actual duplicate groups
                    group_info = {
                        'key': key,
                        'files': [str(f) for f in files],
                        'size': files[0].stat().st_size,
                        'count': len(files)
                    }
                    result['duplicate_groups'].append(group_info)
                    result['total_duplicates'] += len(files) - 1
                    result['total_size_saved'] += (len(files) - 1) * files[0].stat().st_size
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
            result['error'] = str(e)
            return result
            
    def delete_duplicates(self, duplicate_groups: Dict[str, List[Path]], keep_first: bool = True) -> Dict[str, Any]:
        """
        Delete duplicate files from the provided groups.
        
        Args:
            duplicate_groups: Dictionary mapping keys to lists of duplicate files
            keep_first: Whether to keep the first file in each group
            
        Returns:
            Dictionary with deletion results
        """
        result = {
            'deleted_files': [],
            'errors': [],
            'total_deleted': 0,
            'total_size_saved': 0
        }
        
        for key, files in duplicate_groups.items():
            if len(files) <= 1:
                continue
                
            files_to_delete = files[1:] if keep_first else files
            
            for file_path in files_to_delete:
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    result['deleted_files'].append(str(file_path))
                    result['total_deleted'] += 1
                    result['total_size_saved'] += size
                except Exception as e:
                    error = {'file': str(file_path), 'error': str(e)}
                    result['errors'].append(error)
                    logger.error(f"Error deleting {file_path}: {e}")
        
        return result

# Keep existing utility functions
def get_file_hash(file_path: Path, block_size: int = 65536) -> Optional[str]:
    """Calculate the SHA-256 hash of a file."""
    try:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                hasher.update(block)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None

def detect_duplicates(directory: Path, file_types: Set[str] = None, recursive: bool = False) -> Dict[str, List[Path]]:
    """Detect duplicate files in a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        logger.error(f"{directory} is not a valid directory.")
        return {}
    
    # Collect files to process
    files = []
    if recursive:
        for path in directory.rglob('*'):
            if path.is_file() and (file_types is None or path.suffix.lower() in file_types):
                files.append(path)
    else:
        for path in directory.iterdir():
            if path.is_file() and (file_types is None or path.suffix.lower() in file_types):
                files.append(path)
    
    if not files:
        logger.info(f"No matching files found in {directory}")
        return {}
    
    # Group files by size first
    size_groups = {}
    for file_path in files:
        try:
            size = file_path.stat().st_size
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file_path)
        except Exception as e:
            logger.error(f"Error getting size for {file_path}: {e}")
    
    # For each group of same-sized files, check content
    duplicate_groups = {}
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
    
    for size, file_group in size_groups.items():
        if len(file_group) < 2:
            continue  # Need at least 2 files to have duplicates
        
        # Separate image and non-image files
        image_files = [f for f in file_group if f.suffix.lower() in image_extensions]
        other_files = [f for f in file_group if f.suffix.lower() not in image_extensions]
        
        # Process image files using resolution
        if image_files and PIL_AVAILABLE:
            image_dict = {}
            for img_path in image_files:
                _, resolution = get_image_info(img_path)
                if resolution:
                    key = f"{size}_{resolution[0]}x{resolution[1]}"
                    if key not in image_dict:
                        image_dict[key] = []
                    image_dict[key].append(img_path)
            
            # Add to duplicate groups if more than one file has the same size+resolution
            for key, paths in image_dict.items():
                if len(paths) > 1:
                    duplicate_groups[key] = paths
        
        # Process non-image files using hash
        if other_files:
            hash_dict = {}
            for file_path in other_files:
                file_hash = get_file_hash(file_path)
                if file_hash:
                    key = f"{size}_{file_hash}"
                    if key not in hash_dict:
                        hash_dict[key] = []
                    hash_dict[key].append(file_path)
            
            # Add to duplicate groups if more than one file has the same size+hash
            for key, paths in hash_dict.items():
                if len(paths) > 1:
                    duplicate_groups[key] = paths
    
    return duplicate_groups

def get_image_info(file_path: Path) -> Tuple[Optional[int], Optional[Tuple[int, int]]]:
    """Get file size and resolution for an image."""
    try:
        file_size = file_path.stat().st_size
    except Exception as e:
        logger.error(f"Error getting file size for {file_path}: {e}")
        return None, None

    if not PIL_AVAILABLE:
        return file_size, None

    try:
        with Image.open(file_path) as img:
            resolution = img.size  # (width, height)
    except Exception as e:
        logger.error(f"Error opening image {file_path}: {e}")
        resolution = None

    return file_size, resolution 