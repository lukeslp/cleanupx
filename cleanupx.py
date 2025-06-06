#!/usr/bin/env python3
"""
CleanupX - Unified Code Organization and Deduplication Tool

This script integrates multiple utilities to help organize, deduplicate, and
extract important snippets from code repositories and snippet collections.

Features:
- Find and process duplicate files using X.AI API
- Extract important code snippets for documentation
- Organize and rename files based on content analysis
- Generate summaries and documentation

Usage:
  python cleanupx.py deduplicate --dir <directory> [--output <output_dir>]
  python cleanupx.py extract --dir <directory> [--output <output_file>]
  python cleanupx.py organize --dir <directory>
  python cleanupx.py all --dir <directory> [--output <output_dir>]
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import our unified X.AI API
try:
    from storage import xai_unified
    XAI_AVAILABLE = True
except ImportError:
    try:
        import storage.xai_unified as xai_unified
        XAI_AVAILABLE = True
    except ImportError:
        XAI_AVAILABLE = False
        logging.warning("X.AI unified API not available. Install requirements or check path.")

# Import functionality from deduper module
try:
    from _METHODS.deduper import (
        DedupeProcessor, TextDedupeProcessor, detect_duplicates
    )
    DEDUPER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import from deduplication modules: {e}")
    DEDUPER_AVAILABLE = False

try:
    from _METHODS.xsnipper import (
        process_directory as process_snippets_directory,
        init_snipper_directory
    )
    SNIPPER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import from snippet extraction module: {e}")
    SNIPPER_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Fallback functions for when modules are not available
# =============================================================================

def fallback_find_potential_duplicates(dir_path: Path) -> List[Dict[str, List[Path]]]:
    """
    Fallback function to find potential duplicates using basic file size comparison.
    """
    if not DEDUPER_AVAILABLE:
        logger.warning("Using fallback duplicate detection (file size only)")
        size_groups = {}
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    if size not in size_groups:
                        size_groups[size] = []
                    size_groups[size].append(file_path)
                except Exception as e:
                    logger.warning(f"Could not get size for {file_path}: {e}")
        
        # Return groups with more than one file
        similar_groups = []
        for size, files in size_groups.items():
            if len(files) > 1:
                similar_groups.append({
                    'key': f"size_{size}",
                    'files': files,
                    'similarity_type': 'file_size'
                })
        
        return similar_groups
    else:
        # Use proper deduplication
        duplicate_groups = detect_duplicates(dir_path)
        similar_groups = []
        for key, files in duplicate_groups.items():
            similar_groups.append({
                'key': key,
                'files': files,
                'similarity_type': 'hash'
            })
        return similar_groups

def fallback_create_batches(similar_groups: List[Dict], max_batch_size: int = 5) -> List[List[Dict]]:
    """
    Create batches from similar groups for processing.
    """
    return [similar_groups[i:i+max_batch_size] for i in range(0, len(similar_groups), max_batch_size)]

def fallback_process_batch(batch: List[Dict], output_dir: Path) -> Dict[str, Any]:
    """
    Process a batch of similar files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    batch_results = {
        'status': 'processed',
        'groups_processed': len(batch),
        'files_processed': 0,
        'consolidated_files': []
    }
    
    for group in batch:
        files = group['files']
        batch_results['files_processed'] += len(files)
        
        # Create a simple consolidated file
        if len(files) > 1:
            # Keep the first file, note the duplicates
            original = files[0]
            duplicates = files[1:]
            
            consolidated_name = f"consolidated_{original.stem}_{int(time.time())}.md"
            consolidated_path = output_dir / consolidated_name
            
            with open(consolidated_path, 'w', encoding='utf-8') as f:
                f.write(f"# Consolidated File Report\n\n")
                f.write(f"## Original File: {original}\n\n")
                f.write(f"## Duplicate Files Found:\n")
                for dup in duplicates:
                    f.write(f"- {dup}\n")
                f.write(f"\n## Similarity Type: {group['similarity_type']}\n\n")
                
                # Copy original content if it's a text file
                try:
                    if original.suffix.lower() in ['.txt', '.py', '.md', '.js', '.html', '.css']:
                        with open(original, 'r', encoding='utf-8') as orig_file:
                            f.write(f"## Original Content:\n\n```\n{orig_file.read()}\n```\n")
                except Exception as e:
                    f.write(f"Could not read original file content: {e}\n")
            
            batch_results['consolidated_files'].append(str(consolidated_path))
    
    return batch_results

# =============================================================================
# Deduplication functionality
# =============================================================================

def deduplicate_directory(dir_path: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Find and process duplicate files in a directory.
    
    Args:
        dir_path: Directory containing files to deduplicate
        output_dir: Directory to save consolidated files (default: dir_path/deduplicated)
        
    Returns:
        Dictionary with deduplication results
    """
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    # Set default output directory if not provided
    if output_dir is None:
        output_dir = dir_path / "deduplicated"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Log start of deduplication
    logger.info(f"Starting deduplication of directory: {dir_path}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"X.AI API available: {XAI_AVAILABLE}")
    logger.info(f"Deduper available: {DEDUPER_AVAILABLE}")
    
    # Find potential duplicates
    similar_groups = fallback_find_potential_duplicates(dir_path)
    
    if not similar_groups:
        logger.info("No potential duplicates found.")
        return {"status": "success", "duplicates_found": False}
    
    # Create batches
    batches = fallback_create_batches(similar_groups)
    
    # Process each batch
    results = []
    for i, batch in enumerate(batches):
        logger.info(f"Processing batch {i+1}/{len(batches)}")
        batch_result = fallback_process_batch(batch, output_dir)
        results.append(batch_result)
    
    # Save overall results
    results_file = output_dir / "deduplication_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_groups": len(similar_groups),
            "total_batches": len(batches),
            "batch_results": results
        }, f, indent=2)
    
    logger.info(f"Deduplication complete. Results saved to {results_file}")
    
    return {
        "status": "success",
        "duplicates_found": True,
        "total_groups": len(similar_groups),
        "total_batches": len(batches),
        "results_file": str(results_file)
    }

# =============================================================================
# Snippet extraction functionality
# =============================================================================

def extract_snippets(dir_path: Path, output_file: Optional[str] = None, mode: str = "code") -> Dict[str, Any]:
    """
    Extract important code snippets from files in a directory.
    
    Args:
        dir_path: Directory containing files to process
        output_file: Output file for combined snippets (default: dir_path/final_combined.md)
        mode: Processing mode - 'code' or 'snippet'
        
    Returns:
        Dictionary with extraction results
    """
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    # Set default output file if not provided
    if output_file is None:
        output_file = str(dir_path / "final_combined.md")
    
    # Log start of extraction
    logger.info(f"Starting snippet extraction from directory: {dir_path}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Mode: {mode}")
    logger.info(f"X.AI API available: {XAI_AVAILABLE}")
    logger.info(f"Snipper available: {SNIPPER_AVAILABLE}")
    
    if SNIPPER_AVAILABLE:
        # Process the directory using xsnipper
        try:
            process_snippets_directory(str(dir_path), mode, verbose=True, output_file=output_file)
            
            # Get the snipper paths
            snipper_paths = init_snipper_directory(str(dir_path))
            
            return {
                "status": "success",
                "output_file": output_file,
                "summary_file": snipper_paths["summary"],
                "snippets_file": snipper_paths["snippets"],
                "log_file": snipper_paths["log"]
            }
        except Exception as e:
            logger.error(f"Error in snippet extraction: {e}")
            return {"error": f"Snippet extraction failed: {e}"}
    else:
        # Fallback: simple file listing
        logger.warning("Using fallback snippet extraction (simple file listing)")
        
        try:
            files_found = []
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    files_found.append(str(file_path))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Simple File Listing for {dir_path}\n\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"Total files found: {len(files_found)}\n\n")
                
                for file_path in sorted(files_found):
                    f.write(f"- {file_path}\n")
            
            return {
                "status": "success",
                "output_file": output_file,
                "summary_file": None,
                "snippets_file": None,
                "log_file": None,
                "note": "Fallback mode used - install dependencies for full functionality"
            }
        except Exception as e:
            logger.error(f"Error in fallback snippet extraction: {e}")
            return {"error": f"Fallback snippet extraction failed: {e}"}

# =============================================================================
# File organization functionality
# =============================================================================

def organize_directory(dir_path: Path) -> Dict[str, Any]:
    """
    Organize and rename files in a directory based on content analysis.
    
    Args:
        dir_path: Directory containing files to organize
        
    Returns:
        Dictionary with organization results
    """
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    # Log start of organization
    logger.info(f"Starting organization of directory: {dir_path}")
    
    # For now, this is a placeholder that could be expanded
    # to include actual organization logic
    try:
        # Simple organization: create subdirectories by file type
        extensions_found = {}
        
        for file_path in dir_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                ext = file_path.suffix.lower() or 'no_extension'
                if ext not in extensions_found:
                    extensions_found[ext] = []
                extensions_found[ext].append(file_path)
        
        # Create organization report
        report_file = dir_path / "organization_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Organization Report for {dir_path}\n\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for ext, files in sorted(extensions_found.items()):
                f.write(f"## {ext.upper()} Files ({len(files)} found)\n\n")
                for file_path in sorted(files):
                    f.write(f"- {file_path.name}\n")
                f.write("\n")
        
        return {
            "status": "success",
            "message": f"Directory {dir_path} analyzed",
            "report_file": str(report_file),
            "extensions_found": {ext: len(files) for ext, files in extensions_found.items()}
        }
    except Exception as e:
        logger.error(f"Error organizing directory: {e}")
        return {
            "status": "error",
            "error": f"Organization failed: {e}"
        }

# =============================================================================
# Combined processing
# =============================================================================

def process_all(dir_path: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run all processing steps on a directory.
    
    Args:
        dir_path: Directory to process
        output_dir: Output directory for results
        
    Returns:
        Dictionary with processing results
    """
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    # Set default output directory if not provided
    if output_dir is None:
        output_dir = dir_path / "cleanupx_output"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Log start of processing
    logger.info(f"Starting complete processing of directory: {dir_path}")
    logger.info(f"Output directory: {output_dir}")
    
    results = {}
    
    # Step 1: Deduplicate
    logger.info("=== Step 1: Deduplication ===")
    dedup_results = deduplicate_directory(dir_path, output_dir / "deduplicated")
    results["deduplication"] = dedup_results
    
    # Step 2: Extract snippets
    logger.info("=== Step 2: Snippet Extraction ===")
    extract_results = extract_snippets(dir_path, str(output_dir / "final_combined.md"))
    results["extraction"] = extract_results
    
    # Step 3: Organize (if available)
    logger.info("=== Step 3: Organization ===")
    organize_results = organize_directory(dir_path)
    results["organization"] = organize_results
    
    # Save overall results
    results_file = output_dir / "processing_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "directory": str(dir_path),
            "results": results
        }, f, indent=2)
    
    logger.info(f"Complete processing finished. Results saved to {results_file}")
    
    return {
        "status": "success",
        "results_file": str(results_file),
        "results": results
    }

# =============================================================================
# Main entry point
# =============================================================================

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="CleanupX - Unified Code Organization and Deduplication Tool"
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Deduplicate command
    dedup_parser = subparsers.add_parser("deduplicate", help="Find and process duplicate files")
    dedup_parser.add_argument("--dir", required=True, help="Directory to process")
    dedup_parser.add_argument("--output", help="Output directory (default: <dir>/deduplicated)")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract important code snippets")
    extract_parser.add_argument("--dir", required=True, help="Directory to process")
    extract_parser.add_argument("--output", help="Output file (default: <dir>/final_combined.md)")
    extract_parser.add_argument("--mode", choices=["code", "snippet"], default="code",
                              help="Processing mode - 'code' or 'snippet' (default: code)")
    
    # Organize command
    organize_parser = subparsers.add_parser("organize", help="Organize and rename files")
    organize_parser.add_argument("--dir", required=True, help="Directory to process")
    
    # Process all command
    all_parser = subparsers.add_parser("all", help="Run all processing steps")
    all_parser.add_argument("--dir", required=True, help="Directory to process")
    all_parser.add_argument("--output", help="Output directory (default: <dir>/cleanupx_output)")
    
    args = parser.parse_args()
    
    # Check if a command was provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Parse arguments
    dir_path = Path(args.dir)
    
    # Execute the requested command
    if args.command == "deduplicate":
        output_dir = Path(args.output) if args.output else None
        result = deduplicate_directory(dir_path, output_dir)
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    elif args.command == "extract":
        output_file = args.output
        mode = args.mode
        result = extract_snippets(dir_path, output_file, mode)
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    elif args.command == "organize":
        result = organize_directory(dir_path)
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    elif args.command == "all":
        output_dir = Path(args.output) if args.output else None
        result = process_all(dir_path, output_dir)
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 