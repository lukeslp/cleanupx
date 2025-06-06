#!/usr/bin/env python3
"""
File Purpose: Main entry point for cleanupx - Comprehensive File Processing Tool
Primary Functions/Classes: 
- main(): Command-line interface and argument parsing
- deduplicate_directory(): Legacy duplicate detection
- extract_snippets(): Legacy snippet extraction  
- organize_directory(): Legacy file organization
- process_all(): Legacy comprehensive processing
- process_comprehensive(): New comprehensive processing with all features

Inputs and Outputs (I/O):
- Input: Command-line arguments, directory paths, processing options
- Output: Processed files, reports, metadata, organized directories

cleanupx - Comprehensive File Organization and Processing Tool

This script integrates multiple utilities to help organize, deduplicate, and
extract important snippets from code repositories and snippet collections.

Features:
- Find and process duplicate files using X.AI API
- Extract important code snippets for documentation
- Organize and rename files based on content analysis
- Generate alt text for images using AI vision
- Scramble filenames for privacy
- AI-powered code analysis and consolidation
- Generate summaries and documentation

Usage:
  python cleanupx.py deduplicate --dir <directory> [--output <output_dir>]
  python cleanupx.py extract --dir <directory> [--output <output_file>]
  python cleanupx.py organize --dir <directory>
  python cleanupx.py images --dir <directory> [--force] [--rename]
  python cleanupx.py scramble --dir <directory>
  python cleanupx.py all --dir <directory> [--output <output_dir>]
  python cleanupx.py comprehensive --dir <directory> [--all-features]

MIT License by Luke Steuber, lukesteuber.com, assisted.site
luke@lukesteuber.com; bluesky @lukesteuber.com
linkedin https://www.linkedin.com/in/lukesteuber/
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import the new comprehensive cleanup functionality
try:
    from cleanupx_core import (
        cleanup_directory,
        CleanupProcessor,
        XAIIntegration,
        ImageProcessor,
        FilenameScrambler,
        INTEGRATED_AVAILABLE
    )
    COMPREHENSIVE_AVAILABLE = INTEGRATED_AVAILABLE
except ImportError as e:
    logging.warning(f"Comprehensive cleanup module not available: {e}")
    COMPREHENSIVE_AVAILABLE = False

# Convenience functions for the new structure
def process_images_directory(directory, recursive=False, force=False, rename=False, api_key=None):
    """Process all images in a directory for alt text generation."""
    if not COMPREHENSIVE_AVAILABLE:
        return {"error": "Comprehensive cleanup module not available"}
    
    processor = CleanupProcessor(api_key)
    file_scan = processor.scan_directory(directory, recursive)
    return processor.process_images(file_scan['images'], force, rename)

def scramble_directory_filenames(directory, interactive=True):
    """Scramble filenames in a directory."""
    if not COMPREHENSIVE_AVAILABLE:
        return {"error": "Comprehensive cleanup module not available"}
    
    scrambler = FilenameScrambler()
    return scrambler.scramble_directory(directory, interactive)

# Import our unified X.AI API for legacy support
try:
    from cleanupx_core.api import xai_unified
    XAI_AVAILABLE = True
except ImportError:
    try:
        import cleanupx_core.api.xai_unified as xai_unified
        XAI_AVAILABLE = True
    except ImportError:
        XAI_AVAILABLE = False
        logging.warning("X.AI unified API not available. Install requirements or check path.")

# Import functionality from legacy processors for backward compatibility
try:
    from cleanupx_core.processors.legacy.deduper import (
        DedupeProcessor, TextDedupeProcessor, detect_duplicates
    )
    DEDUPER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import from deduplication modules: {e}")
    DEDUPER_AVAILABLE = False

try:
    from cleanupx_core.processors.legacy.xsnipper import (
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
# New Comprehensive Processing Functions
# =============================================================================

def process_comprehensive(
    dir_path: Path, 
    output_dir: Optional[Path] = None,
    process_images: bool = True,
    scramble_filenames: bool = False,
    ai_analysis: bool = True,
    extract_citations: bool = True,
    extract_snippets: bool = True,
    organize: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Run comprehensive processing with all integrated features.
    
    Args:
        dir_path: Directory to process
        output_dir: Output directory for results
        process_images: Whether to generate alt text for images
        scramble_filenames: Whether to scramble filenames for privacy
        ai_analysis: Whether to use AI for code analysis
        extract_citations: Whether to extract citations
        extract_snippets: Whether to extract code snippets
        organize: Whether to organize files by type
        dry_run: Whether to simulate processing
        
    Returns:
        Dictionary with comprehensive processing results
    """
    if not COMPREHENSIVE_AVAILABLE:
        logger.error("Comprehensive cleanup module not available. Falling back to legacy processing.")
        return process_all(dir_path, output_dir)
    
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    # Set default output directory if not provided
    if output_dir is None:
        output_dir = dir_path / "cleanupx_comprehensive_output"
    
    logger.info(f"Starting comprehensive processing of directory: {dir_path}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Features enabled - Images: {process_images}, Scramble: {scramble_filenames}, AI: {ai_analysis}")
    
    try:
        # Use the new comprehensive cleanup function
        results = cleanup_directory(
            directory=dir_path,
            recursive=True,
            extract_citations=extract_citations,
            extract_snippets=extract_snippets,
            organize=organize,
            process_images=process_images,
            scramble_filenames=scramble_filenames,
            ai_analysis=ai_analysis,
            dry_run=dry_run
        )
        
        logger.info("Comprehensive processing completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive processing: {e}")
        return {"error": f"Comprehensive processing failed: {e}"}

def process_images_only(dir_path: Path, force: bool = False, rename: bool = False) -> Dict[str, Any]:
    """
    Process only images in a directory for alt text generation.
    
    Args:
        dir_path: Directory containing images
        force: Force regeneration of alt text even if cached
        rename: Rename image files based on content
        
    Returns:
        Dictionary with image processing results
    """
    if not COMPREHENSIVE_AVAILABLE:
        logger.error("Comprehensive cleanup module not available for image processing.")
        return {"error": "Image processing module not available"}
    
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    logger.info(f"Processing images in directory: {dir_path}")
    logger.info(f"Force regeneration: {force}, Rename files: {rename}")
    
    try:
        results = process_images_directory(
            directory=dir_path,
            recursive=True,
            force=force,
            rename=rename
        )
        
        logger.info("Image processing completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"Error in image processing: {e}")
        return {"error": f"Image processing failed: {e}"}

def scramble_filenames_only(dir_path: Path) -> Dict[str, Any]:
    """
    Scramble filenames in a directory for privacy.
    
    Args:
        dir_path: Directory containing files to scramble
        
    Returns:
        Dictionary with scrambling results
    """
    if not COMPREHENSIVE_AVAILABLE:
        logger.error("Comprehensive cleanup module not available for filename scrambling.")
        return {"error": "Filename scrambling module not available"}
    
    if not dir_path.is_dir():
        logger.error(f"Invalid directory: {dir_path}")
        return {"error": f"Invalid directory: {dir_path}"}
    
    logger.info(f"Scrambling filenames in directory: {dir_path}")
    
    try:
        results = scramble_directory_filenames(
            directory=dir_path,
            interactive=False
        )
        
        logger.info("Filename scrambling completed successfully!")
        return results
        
    except Exception as e:
        logger.error(f"Error in filename scrambling: {e}")
        return {"error": f"Filename scrambling failed: {e}"}

# =============================================================================
# Legacy Fallback functions for when modules are not available
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
# Legacy Deduplication functionality
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
# Legacy Snippet extraction functionality
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
# Legacy File organization functionality
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
# Legacy Combined processing
# =============================================================================

def process_all(dir_path: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run all processing steps on a directory (legacy version).
    
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
        description="cleanupx - Comprehensive File Organization and Processing Tool"
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Comprehensive command (new)
    comp_parser = subparsers.add_parser("comprehensive", help="Run comprehensive processing with all features")
    comp_parser.add_argument("--dir", required=True, help="Directory to process")
    comp_parser.add_argument("--output", help="Output directory (default: <dir>/cleanupx_comprehensive_output)")
    comp_parser.add_argument("--no-images", action="store_true", help="Skip image processing")
    comp_parser.add_argument("--scramble", action="store_true", help="Scramble filenames for privacy")
    comp_parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis")
    comp_parser.add_argument("--no-citations", action="store_true", help="Skip citation extraction")
    comp_parser.add_argument("--no-snippets", action="store_true", help="Skip snippet extraction")
    comp_parser.add_argument("--no-organize", action="store_true", help="Skip file organization")
    comp_parser.add_argument("--dry-run", action="store_true", help="Simulate processing without making changes")
    
    # Images command (new)
    images_parser = subparsers.add_parser("images", help="Process images for alt text generation")
    images_parser.add_argument("--dir", required=True, help="Directory containing images")
    images_parser.add_argument("--force", action="store_true", help="Force regeneration of alt text")
    images_parser.add_argument("--rename", action="store_true", help="Rename image files based on content")
    
    # Scramble command (new)
    scramble_parser = subparsers.add_parser("scramble", help="Scramble filenames for privacy")
    scramble_parser.add_argument("--dir", required=True, help="Directory to scramble")
    
    # Legacy commands
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
    
    # Process all command (legacy)
    all_parser = subparsers.add_parser("all", help="Run all processing steps (legacy)")
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
    if args.command == "comprehensive":
        output_dir = Path(args.output) if args.output else None
        result = process_comprehensive(
            dir_path=dir_path,
            output_dir=output_dir,
            process_images=not args.no_images,
            scramble_filenames=args.scramble,
            ai_analysis=not args.no_ai,
            extract_citations=not args.no_citations,
            extract_snippets=not args.no_snippets,
            organize=not args.no_organize,
            dry_run=args.dry_run
        )
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    elif args.command == "images":
        result = process_images_only(dir_path, args.force, args.rename)
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    elif args.command == "scramble":
        result = scramble_filenames_only(dir_path)
        if result.get("error"):
            logger.error(result["error"])
            return 1
    
    elif args.command == "deduplicate":
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