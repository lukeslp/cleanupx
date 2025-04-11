"""
Citations module for CleanupX.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from .config import TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS, PROTECTED_PATTERNS
from .utils import (
    get_file_metadata,
    is_protected_file,
    normalize_path,
    read_text_file,
    ensure_metadata_dir
)

logger = logging.getLogger(__name__)

def process_citations(
    directory: Union[str, Path],
    recursive: bool = False,
    styles: Optional[List[str]] = None,
    save_results: bool = True
) -> Dict[str, Any]:
    """
    Process citations in text and document files.
    
    Args:
        directory: Directory to process
        recursive: Whether to process subdirectories
        styles: List of citation styles to extract
        save_results: Whether to save results to file
        
    Returns:
        Processing results
    """
    try:
        directory = normalize_path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
            
        # Set default citation styles
        if not styles:
            styles = ['apa', 'mla', 'chicago', 'ieee', 'vancouver']
            
        # Initialize results
        results = {
            'processed': [],
            'skipped': [],
            'errors': [],
            'stats': {
                'total_files': 0,
                'processed_files': 0,
                'skipped_files': 0,
                'error_files': 0,
                'total_citations': 0
            }
        }
        
        # Process files
        for root, _, files in os.walk(directory):
            if not recursive and Path(root) != directory:
                continue
                
            for file in files:
                file_path = Path(root) / file
                results['stats']['total_files'] += 1
                
                try:
                    # Skip non-text/document and protected files
                    if not _is_processable_file(file_path) or is_protected_file(file_path, PROTECTED_PATTERNS):
                        logger.info(f"Skipping file: {file_path}")
                        results['skipped'].append(str(file_path))
                        results['stats']['skipped_files'] += 1
                        continue
                        
                    # Extract citations
                    citations = _extract_citations(file_path, styles)
                    
                    if citations:
                        results['processed'].append({
                            'file': str(file_path),
                            'citations': citations
                        })
                        results['stats']['processed_files'] += 1
                        results['stats']['total_citations'] += len(citations)
                    else:
                        results['skipped'].append(str(file_path))
                        results['stats']['skipped_files'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    results['errors'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
                    results['stats']['error_files'] += 1
                    
            if not recursive:
                break
                
        # Save results if requested
        if save_results:
            _save_citations(results, directory)
            
        return results
        
    except Exception as e:
        logger.error(f"Error processing directory {directory}: {e}")
        return {
            'processed': [],
            'skipped': [],
            'errors': [{'file': str(directory), 'error': str(e)}],
            'stats': {
                'total_files': 0,
                'processed_files': 0,
                'skipped_files': 0,
                'error_files': 1,
                'total_citations': 0
            }
        }

def _is_processable_file(file_path: Path) -> bool:
    """
    Check if a file can be processed for citations.
    
    Args:
        file_path: Path to check
        
    Returns:
        Whether the file can be processed
    """
    ext = file_path.suffix.lower()
    return ext in TEXT_EXTENSIONS or ext in DOCUMENT_EXTENSIONS

def _extract_citations(file_path: Path, styles: List[str]) -> List[Dict[str, Any]]:
    """
    Extract citations from a file.
    
    Args:
        file_path: Path to the file
        styles: List of citation styles to extract
        
    Returns:
        List of extracted citations
    """
    try:
        # Read file content
        content = read_text_file(file_path)
        if not content:
            return []
            
        # Initialize citations
        citations = []
        
        # Extract citations for each style
        for style in styles:
            style_citations = _extract_style_citations(content, style)
            if style_citations:
                citations.extend([
                    {
                        'style': style,
                        'citation': citation,
                        'line': line
                    }
                    for citation, line in style_citations
                ])
                
        return citations
        
    except Exception as e:
        logger.error(f"Error extracting citations from {file_path}: {e}")
        return []

def _extract_style_citations(content: str, style: str) -> List[tuple]:
    """
    Extract citations for a specific style.
    
    Args:
        content: Text content to process
        style: Citation style to extract
        
    Returns:
        List of (citation, line_number) tuples
    """
    # Citation patterns for different styles
    patterns = {
        'apa': r'\((?:[A-Za-z\-]+(?:\s*&\s*[A-Za-z\-]+)*,\s*\d{4}[a-z]?(?:;\s*)?)+\)',
        'mla': r'\([A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Za-z\-]+)*\s+\d+(?:-\d+)?\)',
        'chicago': r'\([A-Za-z\-]+\s+\d{4},\s*\d+(?:-\d+)?\)',
        'ieee': r'\[\d+\]',
        'vancouver': r'\[\d+\]'
    }
    
    if style not in patterns:
        logger.warning(f"Unknown citation style: {style}")
        return []
        
    citations = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        matches = re.finditer(patterns[style], line)
        for match in matches:
            citations.append((match.group(), i))
            
    return citations

def _save_citations(results: Dict[str, Any], directory: Path) -> None:
    """
    Save citation results to file.
    
    Args:
        results: Citation results to save
        directory: Directory to save in
    """
    try:
        metadata_dir = ensure_metadata_dir(directory)
        citations_file = metadata_dir / '.cleanupx-citations'
        
        with open(citations_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Saved citation results to {citations_file}")
        
    except Exception as e:
        logger.error(f"Error saving citation results: {e}")

def format_citation(citation: str, style: str, target_style: str) -> Optional[str]:
    """
    Convert a citation from one style to another.
    
    Args:
        citation: Citation to convert
        style: Current citation style
        target_style: Target citation style
        
    Returns:
        Converted citation or None if conversion failed
    """
    # TODO: Implement citation style conversion
    logger.warning("Citation style conversion not yet implemented")
    return None 