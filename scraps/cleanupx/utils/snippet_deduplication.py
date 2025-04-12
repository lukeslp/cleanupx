#!/usr/bin/env python3
"""
Snippet Deduplication Utility

This module provides functions to find and consolidate duplicate code snippets
using text similarity detection and LLM-powered analysis.
"""

import sys
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_scripts() -> Dict[str, Path]:
    """Find the deduplication scripts in various possible locations."""
    scripts = {
        'deduplicate': 'deduplicate_snippets.py',
        'find': 'find_duplicates.py',
        'process': 'process_duplicates.py'
    }
    
    # Possible script locations in order of preference
    search_paths = [
        # Project root
        Path.cwd(),
        # Package parent directory
        Path(__file__).resolve().parent.parent.parent,
        # Utils directory
        Path(__file__).resolve().parent,
        # Utils/scripts subdirectory
        Path(__file__).resolve().parent / 'scripts'
    ]
    
    found_scripts = {}
    
    for script_key, script_name in scripts.items():
        for search_path in search_paths:
            script_path = search_path / script_name
            if script_path.exists():
                found_scripts[script_key] = script_path
                break
    
    return found_scripts

def import_script_module(script_path: Path, module_name: Optional[str] = None) -> Any:
    """Dynamically import a script as a module."""
    if module_name is None:
        module_name = script_path.stem
        
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return module

def deduplicate_snippets(
    directory: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    threshold: float = 0.25,
    skip_processing: bool = False
) -> Dict[str, Any]:
    """
    Find and consolidate duplicate snippets in a directory.
    
    Args:
        directory: Directory containing snippets to deduplicate
        output_dir: Output directory for results
        threshold: Similarity threshold (0.0-1.0)
        skip_processing: Skip LLM processing step
        
    Returns:
        Dictionary with results of the operation
    """
    # Ensure directory is a Path object
    directory = Path(directory)
    
    # Import the code merger
    try:
        from cleanupx.processors.code_merge import merge_code_snippets
    except ImportError:
        logger.error("Could not import code_merge module. Please ensure it is installed correctly.")
        return {
            "success": False,
            "error_message": "Code merge module not found",
            "output": [],
            "errors": ["Could not import code_merge module"]
        }
    
    # Capture stdout/stderr for clean output handling
    import io
    import sys
    
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    results = {
        "success": True,
        "output": [],
        "errors": [],
        "directory": str(directory),
        "output_dir": str(output_dir) if output_dir else None,
        "threshold": threshold,
        "skip_processing": skip_processing
    }
    
    try:
        # Redirect output
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        # Call the code merger
        merge_results = merge_code_snippets(
            directory=directory,
            output_dir=output_dir,
            similarity_threshold=threshold,
            archive_dir=None if skip_processing else directory / "archived_snippets"
        )
        
        # Process results
        results["output"].extend([
            f"Found {merge_results.get('total_groups', 0)} groups of similar snippets",
            f"Successfully merged {merge_results.get('merged_groups', 0)} groups",
            f"Created {len(merge_results.get('merged_files', []))} merged files",
            f"Processed {merge_results.get('total_files', 0)} total files"
        ])
        
        if merge_results.get('error_files'):
            results["errors"].extend([
                f"Errors occurred with {len(merge_results['error_files'])} files:",
                *[f"- {f}" for f in merge_results['error_files']]
            ])
        
        # Add paths to results
        results["output_dir"] = str(output_dir) if output_dir else str(directory / "merged_snippets")
        results["merged_files"] = merge_results.get('merged_files', [])
        results["archived_files"] = merge_results.get('archived_files', [])
        
        # Process captured output
        results["output"].extend(stdout_capture.getvalue().splitlines())
        results["errors"].extend(stderr_capture.getvalue().splitlines())
        results["exit_code"] = 0
        
    except Exception as e:
        import traceback
        results["success"] = False
        results["error_message"] = str(e)
        results["traceback"] = traceback.format_exc()
        results["exit_code"] = 1
    finally:
        # Restore stdout/stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
    return results

def process_batch_files(
    batch_dir: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Process batch files generated by find_duplicates.py.
    
    Args:
        batch_dir: Directory containing batch files
        output_dir: Output directory for consolidated files
        
    Returns:
        Dictionary with results of the operation
    """
    # This functionality is now handled by the code merger
    logger.warning("process_batch_files is deprecated. Use deduplicate_snippets instead.")
    
    return {
        "success": False,
        "error_message": "This function is deprecated. Use deduplicate_snippets instead.",
        "output": [],
        "errors": ["Function deprecated"]
    } 