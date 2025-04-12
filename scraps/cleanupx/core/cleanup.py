"""
Cleanup module for CleanupX.

Handles file cleanup operations including:
- File organization
- Metadata extraction
- Citation processing
- Snippet extraction
"""

import logging
from pathlib import Path
from typing import Dict, Any, Union, Optional
from .config import DEFAULT_EXTENSIONS, PROTECTED_PATTERNS
from .utils import (
    get_file_metadata,
    is_protected_file,
    normalize_path,
    ensure_metadata_dir
)
from .organization import organize_files
from .citations import process_citations
from .snippets import process_snippets

logger = logging.getLogger(__name__)

def cleanup_directory(
    directory: Union[str, Path],
    recursive: bool = False,
    max_size: Optional[int] = None,
    extract_citations: bool = True,
    extract_snippets: bool = True,
    organize: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Clean up and organize a directory.
    
    Args:
        directory: Directory to process
        recursive: Whether to process subdirectories
        max_size: Maximum file size in MB to process
        extract_citations: Whether to extract citations
        extract_snippets: Whether to extract code snippets
        organize: Whether to organize files by type
        dry_run: Whether to simulate cleanup
        
    Returns:
        Cleanup results
    """
    try:
        directory = normalize_path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
            
        # Initialize results
        results = {
            'processed': [],
            'skipped': [],
            'errors': [],
            'stats': {
                'total_files': 0,
                'processed_files': 0,
                'skipped_files': 0,
                'error_files': 0
            },
            'citations': {},
            'snippets': {},
            'organization': {}
        }
        
        # Process citations if requested
        if extract_citations:
            logger.info("Extracting citations...")
            citation_results = process_citations(
                directory,
                recursive=recursive,
                save_results=not dry_run
            )
            results['citations'] = citation_results
            results['stats']['total_citations'] = citation_results['stats']['total_citations']
            
        # Process snippets if requested
        if extract_snippets:
            logger.info("Extracting code snippets...")
            snippet_results = process_snippets(
                directory,
                recursive=recursive,
                extract_comments=True,
                include_metadata=True
            )
            results['snippets'] = snippet_results
            results['stats']['total_snippets'] = snippet_results['stats']['total_snippets']
            
        # Organize files if requested
        if organize:
            logger.info("Organizing files...")
            org_results = organize_files(
                directory,
                recursive=recursive,
                create_dirs=True,
                move_files=not dry_run,
                dry_run=dry_run
            )
            results['organization'] = org_results
            results['stats'].update(org_results['stats'])
            
        # Update overall statistics
        results['stats']['total_files'] = (
            results['stats'].get('total_files', 0) +
            results['citations'].get('stats', {}).get('total_files', 0) +
            results['snippets'].get('stats', {}).get('total_files', 0)
        )
        results['stats']['processed_files'] = (
            results['stats'].get('processed_files', 0) +
            results['citations'].get('stats', {}).get('processed_files', 0) +
            results['snippets'].get('stats', {}).get('processed_files', 0)
        )
        results['stats']['skipped_files'] = (
            results['stats'].get('skipped_files', 0) +
            results['citations'].get('stats', {}).get('skipped_files', 0) +
            results['snippets'].get('stats', {}).get('skipped_files', 0)
        )
        results['stats']['error_files'] = (
            results['stats'].get('error_files', 0) +
            results['citations'].get('stats', {}).get('error_files', 0) +
            results['snippets'].get('stats', {}).get('error_files', 0)
        )
        
        # Save metadata if not a dry run
        if not dry_run:
            metadata_dir = ensure_metadata_dir(directory)
            metadata_file = metadata_dir / '.cleanupx-metadata'
            with open(metadata_file, 'w') as f:
                import json
                json.dump(results, f, indent=2)
                
        return results
        
    except Exception as e:
        logger.error(f"Error cleaning up directory {directory}: {e}")
        return {
            'processed': [],
            'skipped': [],
            'errors': [{'file': str(directory), 'error': str(e)}],
            'stats': {
                'total_files': 0,
                'processed_files': 0,
                'skipped_files': 0,
                'error_files': 1,
                'total_citations': 0,
                'total_snippets': 0
            }
        } 