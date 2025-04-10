#!/usr/bin/env python3
"""
Snippet Deduplication Workflow.

This script provides a streamlined workflow to:
1. Find potential duplicate snippets using a low similarity threshold
2. Generate batch prompts for LLM analysis
3. Process these batches with an LLM to identify actual duplicates
4. Generate consolidated files and document the process
"""

import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_executable(script_path: Path) -> bool:
    """Ensure a script is executable."""
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return False
    
    # Make executable if not already
    if not os.access(script_path, os.X_OK):
        try:
            script_path.chmod(script_path.stat().st_mode | 0o111)
            logger.info(f"Made script executable: {script_path}")
        except Exception as e:
            logger.error(f"Could not make script executable: {e}")
            return False
    
    return True

def run_script(script_path: Path, args: list) -> bool:
    """Run a script with the given arguments."""
    try:
        cmd = [str(script_path)] + args
        logger.info(f"Running: {' '.join(cmd)}")
        
        # Run the script
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True
        )
        
        # Log output
        for line in result.stdout.splitlines():
            logger.info(f"OUTPUT: {line}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Script failed with exit code {e.returncode}")
        for line in e.stderr.splitlines():
            logger.error(f"ERROR: {line}")
        return False
    except Exception as e:
        logger.error(f"Error running script: {e}")
        return False

def main():
    """Main entry point for the workflow."""
    parser = argparse.ArgumentParser(
        description="Run the complete snippet deduplication workflow"
    )
    parser.add_argument(
        "snippets_dir",
        help="Directory containing snippets to deduplicate"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Base directory for all outputs (default: snippets_dir/deduplication_TIMESTAMP)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.25,
        help="Similarity threshold (0.0-1.0, default: 0.25)"
    )
    parser.add_argument(
        "--skip-processing", "-s",
        action="store_true",
        help="Skip LLM processing of batches (only generate batch files)"
    )
    
    args = parser.parse_args()
    
    # Set up directories
    snippets_dir = Path(args.snippets_dir)
    if not snippets_dir.is_dir():
        logger.error(f"Snippets directory not found: {snippets_dir}")
        sys.exit(1)
    
    # Create timestamp for output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = snippets_dir / f"deduplication_{timestamp}"
    
    # Create subdirectories
    batches_dir = output_dir / "batches"
    consolidated_dir = output_dir / "consolidated"
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    batches_dir.mkdir(parents=True, exist_ok=True)
    consolidated_dir.mkdir(parents=True, exist_ok=True)
    
    # Get script paths
    current_dir = Path(__file__).resolve().parent
    find_script = current_dir / "find_duplicates.py"
    process_script = current_dir / "process_duplicates.py"
    
    # Ensure scripts are executable
    if not ensure_executable(find_script) or not ensure_executable(process_script):
        sys.exit(1)
    
    # Step 1: Find potential duplicates and generate batches
    logger.info("Step 1: Finding potential duplicates and generating batches")
    find_args = [
        str(snippets_dir),
        str(batches_dir)
    ]
    
    if not run_script(find_script, find_args):
        logger.error("Failed to generate batches. Workflow stopped.")
        sys.exit(1)
    
    # If skipping processing, stop here
    if args.skip_processing:
        logger.info("Skipping LLM processing as requested. Batch files are ready in:")
        logger.info(f"  {batches_dir}")
        logger.info("To process these batches later, run:")
        logger.info(f"  {process_script} {batches_dir} --output-dir {consolidated_dir}")
        sys.exit(0)
    
    # Step 2: Process batches with LLM
    logger.info("Step 2: Processing batches with LLM")
    process_args = [
        str(batches_dir),
        "--output-dir", str(consolidated_dir)
    ]
    
    if not run_script(process_script, process_args):
        logger.error("Failed to process batches. Workflow stopped.")
        sys.exit(1)
    
    logger.info("Deduplication workflow complete!")
    logger.info(f"Results available in: {output_dir}")
    logger.info(f"Consolidated files: {consolidated_dir}")
    logger.info(f"Analysis data: {batches_dir}")

if __name__ == "__main__":
    main() 