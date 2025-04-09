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

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL/Pillow not installed. Image resolution detection disabled.")

# Configure logging
logger = logging.getLogger(__name__)

def get_image_info(file_path: Path) -> Tuple[Optional[int], Optional[Tuple[int, int]]]:
    """
    Return the file size (in bytes) and resolution (width, height) for an image.

    Args:
        file_path (Path): Path to the image file.

    Returns:
        tuple: (file_size, (width, height)) if successful; otherwise (file_size, None).
    """
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

def get_file_hash(file_path: Path, block_size: int = 65536) -> Optional[str]:
    """
    Calculate the SHA-256 hash of a file.

    Args:
        file_path (Path): Path to the file.
        block_size (int): Size of blocks to read from file.

    Returns:
        str: Hash of the file or None if failed.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                hasher.update(block)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None

def detect_duplicates(directory: Path, 
                     file_types: Set[str] = None, 
                     recursive: bool = False) -> Dict[str, List[Path]]:
    """
    Detect duplicate files in a directory.
    
    Args:
        directory (Path): Directory to scan for duplicates.
        file_types (Set[str]): Set of file extensions to process (e.g., {'.jpg', '.png'}).
                              If None, process all files.
        recursive (bool): Whether to scan subdirectories.
        
    Returns:
        Dict: Dictionary mapping a key (size+hash or size+resolution) to a list of duplicate files.
    """
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
    
    # Group files by size first (files with different sizes cannot be duplicates)
    size_groups = {}
    for file_path in files:
        try:
            size = file_path.stat().st_size
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file_path)
        except Exception as e:
            logger.error(f"Error getting size for {file_path}: {e}")
    
    # For each group of same-sized files, check content (hash or resolution)
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

def delete_duplicates(duplicate_groups: Dict[str, List[Path]], 
                     keep_first: bool = True,
                     dry_run: bool = False) -> Tuple[int, int]:
    """
    Delete duplicate files, keeping either the first file in each group or asking the user.
    
    Args:
        duplicate_groups (Dict): Dictionary mapping a key to a list of duplicate files.
        keep_first (bool): If True, automatically keep the first file in each group.
                          If False, interactively ask the user which files to keep.
        dry_run (bool): If True, don't actually delete files, just report what would be deleted.
        
    Returns:
        Tuple: (number of duplicate groups, number of files deleted)
    """
    if not duplicate_groups:
        logger.info("No duplicates found.")
        return 0, 0
    
    total_deleted = 0
    total_groups = len(duplicate_groups)
    
    for key, file_list in duplicate_groups.items():
        if len(file_list) <= 1:
            continue
        
        # Display information about the duplicate group
        original = file_list[0]
        duplicates = file_list[1:] if keep_first else file_list
        
        logger.info(f"\nFound duplicates for key {key}:")
        logger.info(f"  - Original: {original}")
        for dup in duplicates:
            logger.info(f"  - Duplicate: {dup}")
        
        # Delete duplicates
        files_to_delete = duplicates if keep_first else file_list[1:]
        for file_path in files_to_delete:
            try:
                if not dry_run:
                    file_path.unlink()
                    logger.info(f"Deleted: {file_path}")
                else:
                    logger.info(f"Would delete: {file_path}")
                total_deleted += 1
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
    
    return total_groups, total_deleted

def dedupe_directory(directory: Path,
                    file_types: Set[str] = None,
                    recursive: bool = False,
                    auto_delete: bool = False,
                    dry_run: bool = False) -> Dict:
    """
    Scan a directory for duplicates and optionally delete them.
    
    Args:
        directory (Path): Directory to scan
        file_types (Set[str]): File extensions to process
        recursive (bool): Whether to scan subdirectories
        auto_delete (bool): Whether to automatically delete duplicates
        dry_run (bool): If True, don't actually delete files
        
    Returns:
        Dict: Results dictionary with statistics
    """
    logger.info(f"Scanning for duplicates in {directory}")
    if recursive:
        logger.info("Scanning subdirectories recursively")
    
    result = {
        "directory": str(directory),
        "recursive": recursive,
        "duplicate_groups": 0,
        "total_duplicates": 0,
        "deleted": 0,
        "errors": 0
    }
    
    try:
        duplicate_groups = detect_duplicates(directory, file_types, recursive)
        
        if not duplicate_groups:
            logger.info("No duplicates found.")
            return result
        
        # Count total duplicates (excluding the first file in each group)
        total_dups = sum(len(files) - 1 for files in duplicate_groups.values())
        result["duplicate_groups"] = len(duplicate_groups)
        result["total_duplicates"] = total_dups
        
        logger.info(f"Found {total_dups} duplicate files in {len(duplicate_groups)} groups")
        
        if auto_delete or dry_run:
            groups, deleted = delete_duplicates(duplicate_groups, keep_first=True, dry_run=dry_run)
            result["deleted"] = deleted
        else:
            # In a CLI environment, we could ask the user for confirmation here
            logger.info("Run with --auto-delete to remove duplicate files")
    
    except Exception as e:
        logger.error(f"Error during deduplication: {e}")
        result["errors"] += 1
    
    return result 