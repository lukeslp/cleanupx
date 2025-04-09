#!/usr/bin/env python3
"""
Archive file processor for CleanupX (ZIP, TAR, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

from cleanupx.config import ARCHIVE_FUNCTION_SCHEMA, ARCHIVE_EXTENSIONS, XAI_MODEL_TEXT
from cleanupx.utils.cache import save_cache
from cleanupx.api import call_xai_api
from cleanupx.processors.base import rename_file
from cleanupx.utils.common import clean_filename, strip_media_suffixes

# Configure logging
logger = logging.getLogger(__name__)

def process_archive_file(file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Dict) -> Tuple[Path, Optional[Path], Optional[Dict]]:
    """
    Process archive files (.zip, .tar, etc.) to:
    1. Analyze contents to suggest a new filename
    2. Generate a markdown (.md) summary of the archive contents
    
    Args:
        file_path: Path to the archive file
        cache: Cache dictionary for storing/retrieving archive descriptions
        rename_log: Log for tracking renames
        
    Returns:
        Tuple of (original_path, new_path, description)
    """
    file_path = Path(file_path)
    cache_key = str(file_path)
    
    # Check if we have a cached result
    cached_result = cache.get(cache_key)
    result = None
    
    if cached_result:
        try:
            if isinstance(cached_result, str):
                result = json.loads(cached_result)
            else:
                result = cached_result
            logger.info(f"Using cached description for {file_path}")
        except json.JSONDecodeError:
            result = None
    
    # If no cached result, analyze the archive contents
    if not result:
        try:
            content_summary = []
            if file_path.suffix.lower() == '.zip':
                try:
                    import zipfile
                    with zipfile.ZipFile(file_path, 'r') as zipf:
                        file_list = zipf.namelist()
                        content_summary.append(f"Archive contains {len(file_list)} files/directories")
                        for i, name in enumerate(file_list[:20]):  # Limit to first 20 items
                            content_summary.append(f"- {name}")
                        if len(file_list) > 20:
                            content_summary.append(f"... and {len(file_list) - 20} more items")
                except Exception as e:
                    content_summary.append(f"Error reading zip: {e}")
            elif file_path.suffix.lower() in {'.tar', '.tgz', '.tar.gz'}:
                try:
                    import tarfile
                    with tarfile.open(file_path, 'r') as tar:
                        file_list = tar.getnames()
                        content_summary.append(f"Archive contains {len(file_list)} files/directories")
                        for i, name in enumerate(file_list[:20]):  # Limit to first 20 items
                            content_summary.append(f"- {name}")
                        if len(file_list) > 20:
                            content_summary.append(f"... and {len(file_list) - 20} more items")
                except Exception as e:
                    content_summary.append(f"Error reading tar archive: {e}")
            elif file_path.suffix.lower() == '.rar':
                try:
                    import rarfile
                    with rarfile.RarFile(file_path, 'r') as rf:
                        file_list = rf.namelist()
                        content_summary.append(f"Archive contains {len(file_list)} files/directories")
                        for i, name in enumerate(file_list[:20]):
                            content_summary.append(f"- {name}")
                        if len(file_list) > 20:
                            content_summary.append(f"... and {len(file_list) - 20} more items")
                except Exception as e:
                    content_summary.append(f"Error reading rar: {e}")
            elif file_path.suffix.lower() == '.gz' and not file_path.name.endswith('.tar.gz'):
                try:
                    import gzip
                    with gzip.open(file_path, 'rb') as gz:
                        preview = gz.read(1024)  # read first 1KB for preview
                    content_summary.append(f"Gzip file with size: {file_path.stat().st_size} bytes")
                    content_summary.append("Preview (first 1024 bytes):")
                    content_summary.append(preview.decode('utf-8', errors='replace'))
                except Exception as e:
                    content_summary.append(f"Error reading gzip file: {e}")
            else:
                content_summary.append(f"Unsupported archive type: {file_path.suffix}")
            
            # Build the prompt for the AI
            archive_prompt = f"""Analyze this archive file and provide structured information.
File name: {file_path.name}
File type: {file_path.suffix}

Archive Contents:
{chr(10).join(content_summary)}

Provide:
1. A suggested filename (5-7 words, lowercase with underscores, no extension).
2. A markdown (.md) summary of the archive contents."""
            
            result = call_xai_api(XAI_MODEL_TEXT, archive_prompt, ARCHIVE_FUNCTION_SCHEMA)
            
            if result:
                cache[cache_key] = result
                save_cache(cache)
        except Exception as e:
            logger.error(f"Error analyzing archive {file_path}: {e}")
            return file_path, None, None
    
    # If we have a result, process the file renaming and create markdown summary
    if result:
        new_name = None
        if "suggested_filename" in result:
            suggested_name = result["suggested_filename"]
            if suggested_name:
                clean_name = clean_filename(suggested_name)
                new_name = f"{clean_name}{file_path.suffix}"
        
        # If no suggested filename, use the original name
        if not new_name:
            clean_stem = strip_media_suffixes(file_path.stem)
            new_name = f"{clean_stem}{file_path.suffix}"
        
        # Rename the file
        new_path = rename_file(file_path, new_name, rename_log)
        
        # Create a markdown summary file
        if "summary_md" in result and new_path:
            try:
                summary_content = result["summary_md"]
                md_path = new_path.with_suffix(".md")
                
                with open(md_path, "w", encoding="utf-8") as md_file:
                    md_file.write(f"# Archive Summary: {new_path.name}\n\n")
                    md_file.write(summary_content)
                
                logger.info(f"Created archive summary: {md_path}")
            except Exception as e:
                logger.error(f"Error creating archive summary: {e}")
        
        # Update cache if renamed
        if new_path and new_path != file_path and cache_key in cache:
            cache[str(new_path)] = cache[cache_key]
            del cache[cache_key]
            save_cache(cache)
        
        return file_path, new_path, result
    
    return file_path, None, None
