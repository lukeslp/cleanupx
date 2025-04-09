#!/usr/bin/env python3
"""
Main module for CleanupX file organization tool.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Union, Tuple, Optional

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

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    logger.warning("Inquirer not installed. Install with: pip install inquirer")

from cleanupx.utils.cache import load_cache, load_rename_log, save_rename_log
from cleanupx.processors import process_file
from cleanupx.utils.directory_summary import update_directory_summary, get_directory_summary, suggest_reorganization
from cleanupx.processors.dedupe import dedupe_directory
from cleanupx.utils.hidden_summary import update_hidden_summary, get_reorganization_suggestions

def process_directory(directory: Union[str, Path], recursive: bool = False, skip_renamed: bool = True, 
                     max_size_mb: float = 25.0, update_summary: bool = True, 
                     include_user_prefs: bool = False, batch_size: int = 0,
                     citation_style_pdfs: bool = False) -> Dict[str, int]:
    """
    Process files in a directory, optionally recursively.
    
    Args:
        directory: Path to the directory to process
        recursive: Whether to process subdirectories recursively
        skip_renamed: Whether to skip previously renamed files
        max_size_mb: Maximum file size to process in MB
        update_summary: Whether to create/update a directory summary file
        include_user_prefs: Whether to prompt for user preferences for organization
        batch_size: Number of files to process before asking for confirmation (0 = all)
        citation_style_pdfs: Whether to use citation-style naming for PDFs
        
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
    
    # Get list of files based on recursion
    if recursive:
        files = list(directory.rglob('*'))
    else:
        files = list(directory.glob('*'))
    print(f"[DEBUG] Found {len(files)} files in directory: {directory}")
    
    rename_log["stats"]["total_files"] = len(files)
    
    if RICH_AVAILABLE:
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(files))
            
            # Process files in batches if batch_size > 0
            batch_files = files
            current_batch = 0
            
            while batch_files:
                if batch_size > 0:
                    # Get current batch
                    current_batch_files = batch_files[:batch_size]
                    batch_files = batch_files[batch_size:]
                    current_batch += 1
                    
                    if current_batch > 1:
                        # Ask for confirmation to process next batch
                        progress.stop()
                        if INQUIRER_AVAILABLE:
                            confirm = inquirer.confirm(
                                message=f"Processed batch {current_batch-1}. Continue with next batch ({len(current_batch_files)} files)?",
                                default=True
                            )
                            if not confirm:
                                logger.info("Processing stopped by user after batch %s", current_batch-1)
                                break
                        else:
                            confirm = input(f"Processed batch {current_batch-1}. Continue with next batch ({len(current_batch_files)} files)? (Y/n): ").lower().strip() != 'n'
                            if not confirm:
                                logger.info("Processing stopped by user after batch %s", current_batch-1)
                                break
                        progress.start()
                else:
                    # Process all files at once
                    current_batch_files = batch_files
                    batch_files = []
                
                for file_path in current_batch_files:
                    progress.update(task, advance=1, description=f"Processing {file_path.name}")
                    if skip_renamed and str(file_path) in renamed_paths:
                        stats["skipped"] += 1
                        rename_log["stats"]["skipped_files"] += 1
                        continue
                    ext = file_path.suffix.lower()
                    stats["total"] += 1
                    try:
                        orig_path, new_path, description = process_file(file_path, cache, rename_log, max_size_mb, citation_style_pdfs)
                        
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
        # Non-rich version with batch processing
        batch_files = files
        current_batch = 0
        
        while batch_files:
            if batch_size > 0:
                # Get current batch
                current_batch_files = batch_files[:batch_size]
                batch_files = batch_files[batch_size:]
                current_batch += 1
                
                if current_batch > 1:
                    # Ask for confirmation to process next batch
                    if INQUIRER_AVAILABLE:
                        confirm = inquirer.confirm(
                            message=f"Processed batch {current_batch-1}. Continue with next batch ({len(current_batch_files)} files)?",
                            default=True
                        )
                        if not confirm:
                            logger.info("Processing stopped by user after batch %s", current_batch-1)
                            break
                    else:
                        confirm = input(f"Processed batch {current_batch-1}. Continue with next batch ({len(current_batch_files)} files)? (Y/n): ").lower().strip() != 'n'
                        if not confirm:
                            logger.info("Processing stopped by user after batch %s", current_batch-1)
                            break
            else:
                # Process all files at once
                current_batch_files = batch_files
                batch_files = []
            
            for i, file_path in enumerate(current_batch_files):
                print(f"Processing {i+1}/{len(current_batch_files)}: {file_path.name}")
                if skip_renamed and str(file_path) in renamed_paths:
                    stats["skipped"] += 1
                    rename_log["stats"]["skipped_files"] += 1
                    continue
                ext = file_path.suffix.lower()
                stats["total"] += 1
                try:
                    orig_path, new_path, description = process_file(file_path, cache, rename_log, max_size_mb, citation_style_pdfs)
                    
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
    
    # Update directory summary if requested
    if update_summary:
        logger.info("Updating directory summary...")
        summary = update_directory_summary(directory, include_user_prefs=include_user_prefs)
        stats["summary_updated"] = True
        
        # Also update the hidden directory summary file
        try:
            logger.info("Updating hidden directory summary...")
            hidden_summary = update_hidden_summary(directory, full_analysis=True)
            stats["hidden_summary_updated"] = True
        except Exception as e:
            logger.error(f"Error updating hidden directory summary: {e}")
            stats["hidden_summary_updated"] = False
        
        # Provide organization suggestions based on the summary
        suggestions = summary.get("suggestions", [])
        if suggestions:
            logger.info(f"Organization suggestions for {directory}:")
            
            # Sort suggestions by priority if available
            try:
                suggestions.sort(key=lambda x: {
                    "high": 0,
                    "medium": 1,
                    "normal": 2,
                    "low": 3
                }.get(x.get("priority", "normal"), 2))
            except:
                pass  # If sorting fails, just use original order
                
            for suggestion in suggestions:
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                priority = suggestion.get("priority", "")
                if priority:
                    priority = f"[{priority}] "
                logger.info(f"- {suggestion_type}: {priority}{reason}")
    
    return stats

def dedupe_files(directory: Union[str, Path], recursive: bool = False, 
                auto_delete: bool = False, dry_run: bool = True) -> Dict:
    """
    Find and optionally remove duplicate files in a directory.
    
    Args:
        directory: Path to directory to scan
        recursive: Whether to process subdirectories recursively
        auto_delete: Whether to automatically delete duplicates without confirmation
        dry_run: If True, just report duplicates without deleting
        
    Returns:
        Dictionary with deduplication statistics
    """
    directory = Path(directory)
    logger.info(f"Scanning for duplicates in {directory}...")
    
    # Run the deduplication process
    result = dedupe_directory(
        directory=directory,
        recursive=recursive,
        auto_delete=auto_delete,
        dry_run=dry_run
    )
    
    # Update the directory summary after deduplication
    update_directory_summary(directory)
    
    return result

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
