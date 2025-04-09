#!/usr/bin/env python3
"""
Main module for CleanupX file organization tool.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.progress import Progress
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logger.warning("Rich not installed. Install with: pip install rich")

from cleanupx.utils.cache import load_cache, load_rename_log, save_rename_log
from cleanupx.processors import process_file

def process_directory(directory: Union[str, Path], recursive: bool = False, skip_renamed: bool = True, max_size_mb: float = 25.0) -> Dict[str, int]:
    """
    Process files in a directory, optionally recursively.
    
    Args:
        directory: Path to the directory to process
        recursive: Whether to process subdirectories recursively
        skip_renamed: Whether to skip previously renamed files
        max_size_mb: Maximum file size to process in MB
        
    Returns:
        Dictionary with processing statistics
    """
    directory = Path(directory)
    stats = {
        "images": 0,
        "text": 0,
        "documents": 0,
        "skipped": 0,
        "failed": 0,
        "total": 0,
        "skipped_large": 0
    }
    cache = load_cache()
    rename_log = load_rename_log()
    
    # Ensure rename_log has the required structure
    if "renames" not in rename_log:
        rename_log["renames"] = []
    if "errors" not in rename_log:
        rename_log["errors"] = []
    if "stats" not in rename_log:
        rename_log["stats"] = {
            "total_files": 0,
            "successful_renames": 0,
            "failed_renames": 0,
            "skipped_files": 0,
            "images_processed": 0,
            "text_processed": 0,
            "documents_processed": 0,
            "total_processed": 0,
            "total_skipped": 0,
            "total_failed": 0
        }
    
    from datetime import datetime
    rename_log["timestamp"] = datetime.now().isoformat()
    rename_log["directory"] = str(directory)
    rename_log["recursive"] = recursive
    rename_log["skip_renamed"] = skip_renamed
    
    renamed_paths = set()
    if skip_renamed:
        for entry in rename_log.get("renames", []):
            renamed_paths.add(entry.get("original_path"))
    
    files = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files.append(Path(root) / filename)
    else:
        files = [f for f in directory.iterdir() if f.is_file()]
    
    rename_log["stats"]["total_files"] = len(files)
    
    if RICH_AVAILABLE:
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(files))
            for file_path in files:
                progress.update(task, advance=1, description=f"Processing {file_path.name}")
                if skip_renamed and str(file_path) in renamed_paths:
                    stats["skipped"] += 1
                    rename_log["stats"]["skipped_files"] += 1
                    continue
                ext = file_path.suffix.lower()
                stats["total"] += 1
                try:
                    orig_path, new_path, description = process_file(file_path, cache, rename_log, max_size_mb)
                    
                    # Update stats based on file type
                    from cleanupx.config import IMAGE_EXTENSIONS, TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS
                    if new_path:
                        if ext in IMAGE_EXTENSIONS:
                            stats["images"] += 1
                        elif ext in TEXT_EXTENSIONS:
                            stats["text"] += 1
                        elif ext in DOCUMENT_EXTENSIONS:
                            stats["documents"] += 1
                    else:
                        # Check if it was skipped due to size
                        try:
                            if file_path.stat().st_size / (1024 * 1024) > max_size_mb:
                                stats["skipped_large"] += 1
                            else:
                                stats["failed"] += 1
                        except:
                            stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    stats["failed"] += 1
                    from cleanupx.utils.cache import add_error_to_log
                    add_error_to_log(rename_log, file_path, str(e), "processing_error")
                save_rename_log(rename_log)
    else:
        for i, file_path in enumerate(files):
            print(f"Processing {i+1}/{len(files)}: {file_path.name}")
            if skip_renamed and str(file_path) in renamed_paths:
                stats["skipped"] += 1
                rename_log["stats"]["skipped_files"] += 1
                continue
            ext = file_path.suffix.lower()
            stats["total"] += 1
            try:
                orig_path, new_path, description = process_file(file_path, cache, rename_log, max_size_mb)
                
                # Update stats based on file type
                from cleanupx.config import IMAGE_EXTENSIONS, TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS
                if new_path:
                    if ext in IMAGE_EXTENSIONS:
                        stats["images"] += 1
                    elif ext in TEXT_EXTENSIONS:
                        stats["text"] += 1
                    elif ext in DOCUMENT_EXTENSIONS:
                        stats["documents"] += 1
                else:
                    # Check if it was skipped due to size
                    try:
                        if file_path.stat().st_size / (1024 * 1024) > max_size_mb:
                            stats["skipped_large"] += 1
                        else:
                            stats["failed"] += 1
                    except:
                        stats["failed"] += 1
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["failed"] += 1
                from cleanupx.utils.cache import add_error_to_log
                add_error_to_log(rename_log, file_path, str(e), "processing_error")
            if i % 10 == 0:
                save_rename_log(rename_log)
    
    # Update final stats in the rename log
    rename_log["stats"].update({
        "images_processed": stats["images"],
        "text_processed": stats["text"],
        "documents_processed": stats["documents"],
        "total_processed": stats["total"],
        "total_skipped": stats["skipped"],
        "skipped_large_files": stats.get("skipped_large", 0),
        "total_failed": stats["failed"]
    })
    
    save_rename_log(rename_log)
    return stats

def main() -> int:
    """
    Main entry point for the CleanupX tool.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    from cleanupx.ui.cli import run_cli
    return run_cli()

if __name__ == "__main__":
    sys.exit(main())
