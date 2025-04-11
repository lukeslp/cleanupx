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
    import xai_unified
    XAI_AVAILABLE = True
except ImportError:
    XAI_AVAILABLE = False
    logging.warning("X.AI unified API not available. Install requirements or check path.")

# Import functionality from other scripts
try:
    from find_duplicates import (
        find_potential_duplicates, create_batches, process_batch,
        SIMILARITY_THRESHOLD, MAX_BATCH_SIZE, MAX_BATCH_TOKENS
    )
    from process_duplicates import process_batches as process_duplicate_batches
except ImportError as e:
    logging.warning(f"Could not import from duplicate processing modules: {e}")
    # We'll define fallback functions if needed

try:
    from _METHODS.xsnipper import (
        process_directory as process_snippets_directory,
        init_xcleaner_directory
    )
except ImportError as e:
    logging.warning(f"Could not import from snippet extraction module: {e}")
    # We'll define fallback functions if needed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    # Find potential duplicates
    similar_groups = find_potential_duplicates(dir_path)
    
    if not similar_groups:
        logger.info("No potential duplicates found.")
        return {"status": "success", "duplicates_found": False}
    
    # Create batches
    batches = create_batches(similar_groups)
    
    # Process each batch
    results = []
    for i, batch in enumerate(batches):
        logger.info(f"Processing batch {i+1}/{len(batches)}")
        batch_result = process_batch(batch, output_dir)
        results.append(batch_result)
    
    # Process batch prompts that were generated (if X.AI API wasn't available earlier)
    prompt_files = [r["prompt_file"] for r in results if r.get("status") == "prompt_generated" and "prompt_file" in r]
    if prompt_files:
        if XAI_AVAILABLE:
            logger.info(f"Processing {len(prompt_files)} batch prompts with X.AI API")
            process_duplicate_batches(output_dir, output_dir / "consolidated")
        else:
            logger.warning("X.AI API not available. Batch prompts were generated but not processed.")
    
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
    
    # Process the directory
    process_snippets_directory(str(dir_path), mode, verbose=True, output_file=output_file)
    
    # Get the xcleaner paths
    xcleaner_paths = init_xcleaner_directory()
    
    return {
        "status": "success",
        "output_file": output_file,
        "summary_file": xcleaner_paths["summary"],
        "snippets_file": xcleaner_paths["snippets"],
        "log_file": xcleaner_paths["log"]
    }

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
    
    # Import organize function dynamically
    try:
        from cleanupx.ui.cli import run_cli
        
        # Call the CLI with the directory path
        original_args = sys.argv.copy()
        sys.argv = [sys.argv[0], str(dir_path)]
        run_cli()
        sys.argv = original_args
        
        return {
            "status": "success",
            "message": f"Directory {dir_path} organized"
        }
    except ImportError:
        logger.error("Could not import organization module from cleanupx")
        return {
            "status": "error",
            "error": "Organization module not available"
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
        deduplicate_directory(dir_path, output_dir)
    
    elif args.command == "extract":
        output_file = args.output
        mode = args.mode
        extract_snippets(dir_path, output_file, mode)
    
    elif args.command == "organize":
        organize_directory(dir_path)
    
    elif args.command == "all":
        output_dir = Path(args.output) if args.output else None
        process_all(dir_path, output_dir)

if __name__ == "__main__":
    sys.exit(main() or 0) 