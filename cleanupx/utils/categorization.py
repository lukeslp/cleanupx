#!/usr/bin/env python3
"""
File categorization utilities for CleanupX.
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Union, Set, Optional
from collections import defaultdict

from cleanupx.config import (
    IMAGE_EXTENSIONS, 
    TEXT_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, 
    ARCHIVE_EXTENSIONS,
    MEDIA_EXTENSIONS
)
from cleanupx.utils.cache import load_cache

# Configure logging
logger = logging.getLogger(__name__)

def get_file_category(file_path: Path) -> str:
    """
    Determine the category of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Category name as string
    """
    ext = file_path.suffix.lower()
    
    # Basic categorization by extension
    if ext in IMAGE_EXTENSIONS:
        return "images"
    elif ext in DOCUMENT_EXTENSIONS:
        if ext == ".pdf":
            return "pdfs"
        elif ext in {".docx", ".doc"}:
            return "word_documents"
        elif ext in {".ppt", ".pptx"}:
            return "presentations"
        else:
            return "documents"
    elif ext in TEXT_EXTENSIONS:
        if ext in {".md", ".markdown"}:
            return "markdown"
        elif ext in {".py", ".js", ".java", ".cpp", ".c", ".php"}:
            return "code"
        elif ext in {".json", ".xml", ".yaml", ".yml"}:
            return "data"
        elif ext in {".csv", ".tsv"}:
            return "data_tables"
        else:
            return "text"
    elif ext in MEDIA_EXTENSIONS:
        if ext in {".mp4", ".avi", ".mov", ".webm", ".mkv"}:
            return "videos"
        elif ext in {".mp3", ".wav", ".ogg", ".flac", ".aac"}:
            return "audio"
        else:
            return "media"
    elif ext in ARCHIVE_EXTENSIONS:
        return "archives"
    else:
        return "other"

def get_content_based_category(file_path: Path) -> Optional[str]:
    """
    Determine the category of a file based on its analyzed content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Content-based category or None if not available
    """
    try:
        # Load the cache to check for existing descriptions
        cache = load_cache()
        
        # Check if this file has been analyzed
        file_key = str(file_path)
        
        # First check direct key for newer format
        if file_key in cache:
            description = cache[file_key]
            
            # Check if description contains document_type or content_type
            if isinstance(description, dict):
                doc_type = description.get("document_type", "").lower()
                content_type = description.get("content_type", "").lower()
                
                # Return appropriate content-based category
                if doc_type:
                    if "article" in doc_type or "paper" in doc_type:
                        return "research"
                    elif "report" in doc_type:
                        return "reports"
                    elif "book" in doc_type:
                        return "books"
                    elif "letter" in doc_type or "email" in doc_type:
                        return "correspondence"
                    elif "code" in doc_type or "script" in doc_type:
                        return "code"
                
                if content_type:
                    if "academic" in content_type:
                        return "academic"
                    elif "business" in content_type:
                        return "business"
                    elif "personal" in content_type:
                        return "personal"
        
        # Check older cache format structure
        for section in ["documents", "images", "text", "archives"]:
            if section in cache and file_key in cache[section]:
                description = cache[section][file_key]
                
                # For older format, check for common keywords
                if isinstance(description, str):
                    description = description.lower()
                    
                    # Check for common themes in the description
                    if "research" in description or "academic" in description:
                        return "research"
                    elif "personal" in description or "family" in description:
                        return "personal"
                    elif "business" in description or "work" in description:
                        return "business"
                
        return None
        
    except Exception as e:
        logger.error(f"Error determining content-based category for {file_path}: {e}")
        return None

def categorize_files(directory: Union[str, Path], recursive: bool = False) -> Dict[str, List[Path]]:
    """
    Categorize all files in a directory.
    
    Args:
        directory: Path to the directory
        recursive: Whether to process subdirectories recursively
        
    Returns:
        Dictionary mapping categories to lists of file paths
    """
    directory = Path(directory)
    categories = defaultdict(list)
    
    # Gather all files to process
    files = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files.append(Path(root) / filename)
    else:
        files = [f for f in directory.iterdir() if f.is_file()]
    
    # Categorize each file
    for file_path in files:
        # First try content-based categorization
        category = get_content_based_category(file_path)
        
        # Fall back to extension-based categorization
        if not category:
            category = get_file_category(file_path)
        
        categories[category].append(file_path)
    
    return categories

def move_to_category_folders(directory: Union[str, Path], categories: Dict[str, List[Path]]) -> Dict[str, int]:
    """
    Move files to their category folders.
    
    Args:
        directory: Base directory
        categories: Dictionary mapping categories to lists of file paths
        
    Returns:
        Dictionary with statistics on moved files
    """
    directory = Path(directory)
    stats = {"moved": 0, "failed": 0, "skipped": 0}
    
    # Process each category
    for category, files in categories.items():
        # Create category folder if it doesn't exist
        category_dir = directory / category
        category_dir.mkdir(exist_ok=True)
        
        # Move files to category folder
        for file_path in files:
            # Skip files that are already in their category folder
            if file_path.parent.name == category:
                stats["skipped"] += 1
                continue
            
            try:
                # Generate target path
                target_path = category_dir / file_path.name
                
                # Handle name collision
                counter = 1
                original_stem = file_path.stem
                while target_path.exists():
                    new_name = f"{original_stem}_{counter}{file_path.suffix}"
                    target_path = category_dir / new_name
                    counter += 1
                
                # Move the file
                shutil.move(str(file_path), str(target_path))
                logger.info(f"Moved {file_path} to {target_path}")
                stats["moved"] += 1
                
            except Exception as e:
                logger.error(f"Error moving {file_path} to {category_dir}: {e}")
                stats["failed"] += 1
    
    return stats 