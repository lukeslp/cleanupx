#!/usr/bin/env python3
"""
Main module for CleanupX file organization tool.
"""

import os
import sys
import logging
import json
import argparse
import concurrent.futures
from pathlib import Path
from typing import Dict, Union, Tuple, Optional, Callable, Any
import inspect
from datetime import datetime
import shutil

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
from cleanupx.utils.dashboard_generator import generate_dashboard as generate_html_dashboard
from cleanupx.config import (
    TEXT_EXTENSIONS, IMAGE_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, MEDIA_EXTENSIONS,
    ARCHIVE_EXTENSIONS, DEFAULT_EXTENSIONS,
    init_config
)
from cleanupx.processors import (
    process_text_file,
    process_image_file,
    process_document_file,
    process_media_file,
    process_archive_file
)

def process_directory(directory: Union[str, Path], recursive: bool = False, skip_renamed: bool = True, 
                     max_size_mb: float = 25.0, update_summary: bool = True, 
                     include_user_prefs: bool = False, batch_size: int = 0,
                     citation_style_pdfs: bool = False,
                     generate_image_md: bool = True,
                     generate_archive_md: bool = True,
                     generate_dashboard: bool = False,
                     progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, int]:
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
        generate_image_md: Whether to generate image metadata
        generate_archive_md: Whether to generate archive metadata
        generate_dashboard: Whether to generate a dashboard after processing
        progress_callback: Optional callback function to report progress
        
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
    rename_log = load_rename_log(Path.cwd())
    
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
    
    # Filter to only files (not directories)
    files = [f for f in files if f.is_file()]
    
    rename_log["stats"]["total_files"] = len(files)
    
    process_file_sig = inspect.signature(process_file)
    supports_new_keywords = 'generate_image_md' in process_file_sig.parameters
    
    # Process files in batches if requested
    if batch_size > 0:
        batches = [files[i:i + batch_size] for i in range(0, len(files), batch_size)]
    else:
        batches = [files]
    
    files_processed = 0
    
    for batch_num, current_batch_files in enumerate(batches, 1):
        if batch_size > 0:
            logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(current_batch_files)} files)")
        
        for file_path in current_batch_files:
            if skip_renamed and str(file_path) in renamed_paths:
                stats["skipped"] += 1
                rename_log["stats"]["skipped_files"] += 1
                continue
                
            ext = file_path.suffix.lower()
            stats["total"] += 1
            
            try:
                if supports_new_keywords:
                    orig_path, new_path, description = process_file(
                        file_path, cache, rename_log, max_size_mb, citation_style_pdfs,
                        generate_image_md=generate_image_md,
                        generate_archive_md=generate_archive_md
                    )
                else:
                    orig_path, new_path, description = process_file(
                        file_path, cache, rename_log, max_size_mb, citation_style_pdfs
                    )
                
                # Update stats based on file type
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
                
                files_processed += 1
                
                # Update progress if callback provided
                if progress_callback:
                    status = f"Processing {file_path.name}"
                    if new_path:
                        status = f"Renamed {file_path.name} → {new_path.name}"
                    progress_callback(files_processed, status)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["failed"] += 1
                rename_log["stats"]["failed_renames"] += 1
                rename_log["errors"].append({
                    "file": str(file_path),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update progress even for failures
                files_processed += 1
                if progress_callback:
                    progress_callback(files_processed, f"Failed: {file_path.name}")
    
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
        
        # Generate dashboard if requested
        if generate_dashboard:
            try:
                dashboard_path = generate_html_dashboard(directory)
                if dashboard_path:
                    logger.info(f"Dashboard generated at: {dashboard_path}")
            except Exception as e:
                logger.error(f"Error generating dashboard: {e}")
    
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

def smart_merge_files(directory: Union[str, Path], output_dir: Optional[Union[str, Path]] = None,
                     similarity_threshold: float = 0.75, archive_dir: Optional[Union[str, Path]] = None,
                     recursive: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Intelligently merge similar documents in a directory, creating definitive versions.
    
    Args:
        directory: Directory containing documents to merge
        output_dir: Directory to save merged documents (defaults to directory/merged)
        similarity_threshold: Threshold for considering documents similar (0-1)
        archive_dir: Directory to move source documents to after merging
        recursive: Whether to scan subdirectories
        dry_run: If True, just report similar documents without merging
        
    Returns:
        Dictionary with merge results
    """
    directory = Path(directory)
    logger.info(f"Starting intelligent document merging in {directory}")
    
    if dry_run:
        # Only find similar documents without merging
        logger.info("Dry run mode: Only finding similar documents without merging")
        from cleanupx.processors.smart_merge import find_similar_snippets
        similar_groups = find_similar_snippets(
            directory, similarity_threshold)
        
        results = {
            "total_groups": len(similar_groups),
            "similar_files": {}
        }
        
        # Format results for reporting
        for group_id, group in similar_groups.items():
            files = [str(f) for _, _, f in group]
            results["similar_files"][group_id] = files
            
        logger.info(f"Found {len(similar_groups)} groups of similar documents")
        return results
    else:
        # Perform the actual merging - sending to xAI API without similarity check
        from cleanupx.processors.smart_merge import merge_code_snippets
        results = merge_code_snippets(
            directory=directory,
            output_dir=output_dir,
            similarity_threshold=similarity_threshold,
            archive_dir=archive_dir
        )
        
        logger.info(f"Smart merge complete: {results['merged_groups']} groups merged, "
                   f"{len(results['merged_files'])} merged files created")
        return results

def analyze_directory(directory: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
    """
    Analyze a directory and return information about its structure and contents.
    
    Args:
        directory: Path to the directory to analyze
        recursive: Whether to include subdirectories in analysis
        
    Returns:
        Dictionary with analysis results
    """
    directory = Path(directory)
    logger.info(f"Analyzing directory: {directory}")
    
    result = {
        "path": str(directory),
        "name": directory.name,
        "file_count": 0,
        "directory_count": 0,
        "total_size_mb": 0,
        "file_types": {},
        "largest_files": [],
        "subdirectories": []
    }
    
    # Get list of files based on recursion
    files = []
    if recursive:
        # Walk through all subdirectories
        for item in directory.rglob('*'):
            if item.is_file():
                files.append(item)
                result["file_count"] += 1
            elif item.is_dir():
                result["directory_count"] += 1
                result["subdirectories"].append({
                    "name": item.name,
                    "path": str(item),
                    "file_count": len([f for f in item.glob('*') if f.is_file()]),
                    "directory_count": len([d for d in item.glob('*') if d.is_dir()])
                })
    else:
        # Only look at immediate contents
        for item in directory.glob('*'):
            if item.is_file():
                files.append(item)
                result["file_count"] += 1
            elif item.is_dir():
                result["directory_count"] += 1
                result["subdirectories"].append({
                    "name": item.name,
                    "path": str(item),
                    "file_count": len([f for f in item.glob('*') if f.is_file()]),
                    "directory_count": len([d for d in item.glob('*') if d.is_dir()])
                })
    
    # Calculate total size and collect file types
    largest_files = []
    for file_path in files:
        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            result["total_size_mb"] += size_mb
            
            # Track file types
            ext = file_path.suffix.lower()
            if ext not in result["file_types"]:
                result["file_types"][ext] = {
                    "count": 0,
                    "total_size_mb": 0
                }
            result["file_types"][ext]["count"] += 1
            result["file_types"][ext]["total_size_mb"] += size_mb
            
            # Track largest files
            largest_files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size_mb": size_mb
            })
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    # Sort and limit the largest files
    largest_files.sort(key=lambda x: x["size_mb"], reverse=True)
    result["largest_files"] = largest_files[:10]  # Keep top 10
    
    # Round the total size for cleaner output
    result["total_size_mb"] = round(result["total_size_mb"], 2)
    
    # Get summary information if available
    try:
        from cleanupx.utils.directory_summary import get_directory_summary
        summary = get_directory_summary(directory)
        if summary:
            result["summary"] = summary
    except Exception as e:
        logger.error(f"Error getting directory summary: {e}")
    
    # Get hidden summary information if available
    try:
        from cleanupx.utils.hidden_summary import get_hidden_summary
        hidden_summary = get_hidden_summary(directory)
        if hidden_summary:
            result["hidden_summary"] = hidden_summary
    except Exception as e:
        logger.error(f"Error getting hidden summary: {e}")
    
    return result

def organize_directory(directory: Union[str, Path], strategy: str = "auto", 
                      dry_run: bool = True, recursive: bool = False,
                      apply_suggestions: bool = False) -> Dict[str, Any]:
    """
    Organize a directory based on a specified strategy.
    
    Args:
        directory: Path to the directory to organize
        strategy: Organization strategy ('auto', 'by_type', 'by_date', 'by_size', 'smart')
        dry_run: If True, only show what would be done without making changes
        recursive: Whether to organize subdirectories recursively
        apply_suggestions: Whether to apply organization suggestions from analysis
        
    Returns:
        Dictionary with organization results
    """
    directory = Path(directory)
    logger.info(f"Organizing directory: {directory} (strategy: {strategy}, dry_run: {dry_run})")
    
    result = {
        "path": str(directory),
        "strategy": strategy,
        "dry_run": dry_run,
        "moves": [],
        "errors": []
    }
    
    # If applying suggestions from analysis
    if apply_suggestions:
        try:
            from cleanupx.utils.hidden_summary import get_reorganization_suggestions, apply_suggestions as apply_reorg_suggestions
            suggestions = get_reorganization_suggestions(directory)
            if suggestions:
                logger.info(f"Applying {len(suggestions)} organization suggestions")
                if not dry_run:
                    changes = apply_reorg_suggestions(directory, suggestions)
                    result["suggested_changes"] = changes
                else:
                    result["suggested_changes"] = suggestions
        except Exception as e:
            logger.error(f"Error applying suggestions: {e}")
            result["errors"].append(f"Failed to apply suggestions: {str(e)}")
    
    # Apply the selected organization strategy
    if strategy == "by_type":
        # Organize files by their type/extension
        result.update(_organize_by_type(directory, dry_run, recursive))
    elif strategy == "by_date":
        # Organize files by creation/modification date
        result.update(_organize_by_date(directory, dry_run, recursive))
    elif strategy == "by_size":
        # Organize files by size categories
        result.update(_organize_by_size(directory, dry_run, recursive))
    elif strategy == "smart":
        # Use content-aware organization
        result.update(_organize_smart(directory, dry_run, recursive))
    elif strategy == "auto":
        # Automatically choose the best strategy based on directory content
        analysis = analyze_directory(directory, recursive=False)
        strategy = _determine_best_strategy(analysis)
        logger.info(f"Auto-selected strategy: {strategy}")
        result["auto_selected_strategy"] = strategy
        
        # Call this function again with the selected strategy
        strategy_result = organize_directory(
            directory, 
            strategy=strategy, 
            dry_run=dry_run, 
            recursive=recursive, 
            apply_suggestions=False  # Don't apply suggestions again
        )
        result.update(strategy_result)
    else:
        result["errors"].append(f"Unknown organization strategy: {strategy}")
    
    return result

def _organize_by_type(directory: Path, dry_run: bool, recursive: bool) -> Dict[str, Any]:
    """Helper function to organize files by type/extension."""
    result = {"moves": [], "errors": []}
    
    # Define the category mappings
    categories = {
        "images": IMAGE_EXTENSIONS,
        "documents": DOCUMENT_EXTENSIONS,
        "text": TEXT_EXTENSIONS,
        "media": MEDIA_EXTENSIONS,
        "archives": ARCHIVE_EXTENSIONS
    }
    
    # Process files
    files = directory.glob('*') if not recursive else directory.rglob('*')
    for file_path in files:
        if not file_path.is_file():
            continue
            
        # Skip files in subdirectories if we're at the root and not recursive
        if not recursive and file_path.parent != directory:
            continue
            
        # Determine category
        category = None
        ext = file_path.suffix.lower()
        for cat_name, extensions in categories.items():
            if ext in extensions:
                category = cat_name
                break
                
        # Create target directory if it doesn't exist
        if category:
            target_dir = directory / category
            
            # Record the planned move
            target_path = target_dir / file_path.name
            result["moves"].append({
                "source": str(file_path),
                "destination": str(target_path),
                "category": category
            })
            
            # Execute the move if not a dry run
            if not dry_run:
                try:
                    if not target_dir.exists():
                        target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Handle name conflicts
                    if target_path.exists():
                        base = target_path.stem
                        ext = target_path.suffix
                        counter = 1
                        while target_path.exists():
                            new_name = f"{base}_{counter}{ext}"
                            target_path = target_dir / new_name
                            counter += 1
                    
                    # Move the file
                    shutil.move(str(file_path), str(target_path))
                except Exception as e:
                    result["errors"].append(f"Error moving {file_path}: {str(e)}")
    
    return result

def _organize_by_date(directory: Path, dry_run: bool, recursive: bool) -> Dict[str, Any]:
    """Helper function to organize files by date."""
    result = {"moves": [], "errors": []}
    
    # Process files
    files = directory.glob('*') if not recursive else directory.rglob('*')
    for file_path in files:
        if not file_path.is_file():
            continue
            
        # Skip files in subdirectories if we're at the root and not recursive
        if not recursive and file_path.parent != directory:
            continue
            
        try:
            # Get file modification time
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            year_month = mod_time.strftime("%Y-%m")
            
            # Create target directory if it doesn't exist
            target_dir = directory / year_month
            
            # Record the planned move
            target_path = target_dir / file_path.name
            result["moves"].append({
                "source": str(file_path),
                "destination": str(target_path),
                "date": year_month
            })
            
            # Execute the move if not a dry run
            if not dry_run:
                try:
                    if not target_dir.exists():
                        target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Handle name conflicts
                    if target_path.exists():
                        base = target_path.stem
                        ext = target_path.suffix
                        counter = 1
                        while target_path.exists():
                            new_name = f"{base}_{counter}{ext}"
                            target_path = target_dir / new_name
                            counter += 1
                    
                    # Move the file
                    shutil.move(str(file_path), str(target_path))
                except Exception as e:
                    result["errors"].append(f"Error moving {file_path}: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Error processing {file_path}: {str(e)}")
    
    return result

def _organize_by_size(directory: Path, dry_run: bool, recursive: bool) -> Dict[str, Any]:
    """Helper function to organize files by size."""
    result = {"moves": [], "errors": []}
    
    # Define size categories in MB
    categories = {
        "tiny": (0, 0.5),
        "small": (0.5, 5),
        "medium": (5, 50),
        "large": (50, 500),
        "huge": (500, float('inf'))
    }
    
    # Process files
    files = directory.glob('*') if not recursive else directory.rglob('*')
    for file_path in files:
        if not file_path.is_file():
            continue
            
        # Skip files in subdirectories if we're at the root and not recursive
        if not recursive and file_path.parent != directory:
            continue
            
        try:
            # Get file size in MB
            size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # Determine category
            category = None
            for cat_name, (min_size, max_size) in categories.items():
                if min_size <= size_mb < max_size:
                    category = cat_name
                    break
            
            if category:
                # Create target directory if it doesn't exist
                target_dir = directory / category
                
                # Record the planned move
                target_path = target_dir / file_path.name
                result["moves"].append({
                    "source": str(file_path),
                    "destination": str(target_path),
                    "size": size_mb,
                    "category": category
                })
                
                # Execute the move if not a dry run
                if not dry_run:
                    try:
                        if not target_dir.exists():
                            target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Handle name conflicts
                        if target_path.exists():
                            base = target_path.stem
                            ext = target_path.suffix
                            counter = 1
                            while target_path.exists():
                                new_name = f"{base}_{counter}{ext}"
                                target_path = target_dir / new_name
                                counter += 1
                        
                        # Move the file
                        shutil.move(str(file_path), str(target_path))
                    except Exception as e:
                        result["errors"].append(f"Error moving {file_path}: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Error processing {file_path}: {str(e)}")
    
    return result

def _organize_smart(directory: Path, dry_run: bool, recursive: bool) -> Dict[str, Any]:
    """Helper function for content-aware organization."""
    result = {"moves": [], "errors": []}
    
    # Try to get directory summary for content-aware organization
    try:
        from cleanupx.utils.directory_summary import get_directory_summary, suggest_reorganization
        from cleanupx.utils.hidden_summary import get_reorganization_suggestions
        
        # First try to get detailed suggestions from hidden summary
        suggestions = get_reorganization_suggestions(directory)
        
        # If no hidden summary, fall back to basic summary suggestions
        if not suggestions:
            summary = get_directory_summary(directory)
            if summary:
                suggestions = suggest_reorganization(directory, summary)
        
        if suggestions:
            for suggestion in suggestions:
                if suggestion.get("type") == "create_subdirectory":
                    subdir_name = suggestion.get("name", "")
                    if subdir_name:
                        subdir_path = directory / subdir_name
                        patterns = suggestion.get("file_patterns", [])
                        
                        # Find matching files
                        for pattern in patterns:
                            for file_path in directory.glob(pattern):
                                if file_path.is_file():
                                    # Create target directory if needed
                                    target_path = subdir_path / file_path.name
                                    
                                    # Record the planned move
                                    result["moves"].append({
                                        "source": str(file_path),
                                        "destination": str(target_path),
                                        "suggestion": suggestion.get("reason", "Content-based organization")
                                    })
                                    
                                    # Execute the move if not a dry run
                                    if not dry_run:
                                        try:
                                            if not subdir_path.exists():
                                                subdir_path.mkdir(parents=True, exist_ok=True)
                                            
                                            # Handle name conflicts
                                            if target_path.exists():
                                                base = target_path.stem
                                                ext = target_path.suffix
                                                counter = 1
                                                while target_path.exists():
                                                    new_name = f"{base}_{counter}{ext}"
                                                    target_path = subdir_path / new_name
                                                    counter += 1
                                            
                                            # Move the file
                                            shutil.move(str(file_path), str(target_path))
                                        except Exception as e:
                                            result["errors"].append(f"Error moving {file_path}: {str(e)}")
        else:
            # Fall back to type-based organization if no suggestions
            logger.info("No content-based suggestions found, falling back to type-based organization")
            type_result = _organize_by_type(directory, dry_run, recursive)
            result["moves"].extend(type_result["moves"])
            result["errors"].extend(type_result["errors"])
            result["fallback"] = "type_based"
    except Exception as e:
        logger.error(f"Error in smart organization: {e}")
        result["errors"].append(f"Smart organization failed: {str(e)}")
        
        # Fall back to type-based organization on error
        logger.info("Error in smart organization, falling back to type-based organization")
        type_result = _organize_by_type(directory, dry_run, recursive)
        result["moves"].extend(type_result["moves"])
        result["errors"].extend(type_result["errors"])
        result["fallback"] = "type_based"
    
    return result

def _determine_best_strategy(analysis: Dict[str, Any]) -> str:
    """Determine the best organization strategy based on directory analysis."""
    # Default strategy
    strategy = "by_type"
    
    # Check if we have enough files to make a decision
    if analysis.get("file_count", 0) < 5:
        return strategy
    
    # If many different file types, type-based organization makes sense
    file_types = analysis.get("file_types", {})
    if len(file_types) > 3:
        return "by_type"
    
    # If one dominant file type and it's a document or image,
    # content-based organization might be better
    dominant_type = None
    max_count = 0
    for ext, info in file_types.items():
        if info.get("count", 0) > max_count:
            max_count = info["count"]
            dominant_type = ext
    
    if dominant_type and max_count / analysis.get("file_count", 1) > 0.7:
        if dominant_type in DOCUMENT_EXTENSIONS or dominant_type in IMAGE_EXTENSIONS:
            return "smart"
    
    # If hidden summary has meaningful suggestions, use smart organization
    if "hidden_summary" in analysis and "suggestions" in analysis["hidden_summary"]:
        if len(analysis["hidden_summary"]["suggestions"]) > 0:
            return "smart"
    
    return strategy

def generate_dashboard(directory: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """
    Generate an HTML dashboard for the directory.
    
    Args:
        directory: Path to the directory to analyze
        output_path: Optional custom output path for the dashboard
        
    Returns:
        Path to the generated dashboard HTML file, or None if generation failed
    """
    try:
        from cleanupx.utils.dashboard_generator import generate_dashboard as generate_html_dashboard
        return generate_html_dashboard(directory, output_path)
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        return None

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
