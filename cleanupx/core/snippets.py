"""
Snippet Manager

Handles extraction and management of code snippets from processed documents.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from ..processors.document import DocumentProcessor
from .config import CODE_EXTENSIONS, PROTECTED_PATTERNS
from .utils import (
    get_file_metadata,
    is_protected_file,
    normalize_path,
    read_text_file
)

logger = logging.getLogger(__name__)

class SnippetManager:
    """Manages code snippets extracted from processed documents."""
    
    def __init__(self, base_dir: str):
        """Initialize the snippet manager with a base directory."""
        self.base_dir = Path(base_dir)
        self.snippets_file = self.base_dir / '.cleanupx' / '.snippets'
        self.document_processor = DocumentProcessor()
        self._load_snippets()
        
    def _load_snippets(self):
        """Load existing snippets from the snippets file."""
        self.snippets = {
            'python': [],
            'html': [],
            'css': [],
            'javascript': [],
            'other': []
        }
        if self.snippets_file.exists():
            try:
                with open(self.snippets_file, 'r') as f:
                    self.snippets = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupted snippets file, starting fresh")
                
    def _save_snippets(self):
        """Save snippets to the snippets file."""
        with open(self.snippets_file, 'w') as f:
            json.dump(self.snippets, f, indent=2)
            
    def extract_snippets(self, file_path: Path) -> Dict[str, List[Dict]]:
        """
        Extract code snippets from a document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary of extracted snippets by language
        """
        try:
            new_snippets = self.document_processor.extract_snippets(file_path)
            for lang, snippets in new_snippets.items():
                for snippet in snippets:
                    if snippet not in self.snippets[lang]:
                        self.snippets[lang].append(snippet)
            self._save_snippets()
            return new_snippets
        except Exception as e:
            logger.error(f"Error extracting snippets from {file_path}: {str(e)}")
            return {}
            
    def get_snippets(self, language: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Get stored snippets, optionally filtered by language.
        
        Args:
            language: Optional language to filter by
            
        Returns:
            Dictionary of snippets by language
        """
        if language:
            return {language: self.snippets.get(language, [])}
        return self.snippets
        
    def search_snippets(self, query: str, language: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Search snippets by query, optionally filtered by language.
        
        Args:
            query: Search query string
            language: Optional language to filter by
            
        Returns:
            Dictionary of matching snippets by language
        """
        results = {}
        languages = [language] if language else self.snippets.keys()
        
        for lang in languages:
            results[lang] = [
                snippet for snippet in self.snippets[lang]
                if query.lower() in str(snippet).lower()
            ]
            
        return results
        
    def export_snippets(self, format: str = 'markdown') -> str:
        """
        Export snippets in the specified format.
        
        Args:
            format: Export format (markdown, html, etc.)
            
        Returns:
            Exported snippets as string
        """
        # Implementation for different export formats
        pass 

def process_snippets(
    directory: Union[str, Path],
    recursive: bool = False,
    extract_comments: bool = True,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Process code snippets in a directory.
    
    Args:
        directory: Directory to process
        recursive: Whether to process subdirectories
        extract_comments: Whether to extract code comments
        include_metadata: Whether to include file metadata
        
    Returns:
        Processing results
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
                'error_files': 0,
                'total_snippets': 0
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
                    # Skip non-code and protected files
                    if not _is_code_file(file_path) or is_protected_file(file_path, PROTECTED_PATTERNS):
                        logger.info(f"Skipping file: {file_path}")
                        results['skipped'].append(str(file_path))
                        results['stats']['skipped_files'] += 1
                        continue
                        
                    # Process file
                    snippets = _extract_snippets(
                        file_path,
                        extract_comments=extract_comments,
                        include_metadata=include_metadata
                    )
                    
                    if snippets:
                        results['processed'].append({
                            'file': str(file_path),
                            'snippets': snippets
                        })
                        results['stats']['processed_files'] += 1
                        results['stats']['total_snippets'] += len(snippets)
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
                'total_snippets': 0
            }
        }

def _is_code_file(file_path: Path) -> bool:
    """
    Check if a file is a code file.
    
    Args:
        file_path: Path to check
        
    Returns:
        Whether the file is a code file
    """
    return file_path.suffix.lower() in CODE_EXTENSIONS

def _extract_snippets(
    file_path: Path,
    extract_comments: bool = True,
    include_metadata: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract code snippets from a file.
    
    Args:
        file_path: Path to the file
        extract_comments: Whether to extract comments
        include_metadata: Whether to include metadata
        
    Returns:
        List of extracted snippets
    """
    try:
        # Read file content
        content = read_text_file(file_path)
        if not content:
            return []
            
        # Split into lines
        lines = content.splitlines()
        
        # Initialize snippets
        snippets = []
        current_snippet = []
        in_comment_block = False
        comment_block = []
        
        # Language-specific comment markers
        ext = file_path.suffix.lower()
        comment_markers = _get_comment_markers(ext)
        
        if not comment_markers:
            logger.warning(f"Unknown file type for comments: {ext}")
            return []
            
        # Process lines
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Handle comment blocks
            if extract_comments:
                if comment_markers['block_start'] and line.startswith(comment_markers['block_start']):
                    in_comment_block = True
                    comment_block = [line]
                    continue
                    
                if in_comment_block:
                    comment_block.append(line)
                    if comment_markers['block_end'] and line.endswith(comment_markers['block_end']):
                        in_comment_block = False
                        if len(comment_block) > 1:
                            snippets.append({
                                'type': 'comment_block',
                                'content': '\n'.join(comment_block),
                                'line_start': i - len(comment_block) + 1,
                                'line_end': i
                            })
                        comment_block = []
                    continue
                    
                # Handle single-line comments
                if comment_markers['line'] and line.startswith(comment_markers['line']):
                    snippets.append({
                        'type': 'comment',
                        'content': line,
                        'line': i
                    })
                    continue
                    
            # Handle code blocks
            if line:
                current_snippet.append(line)
            elif current_snippet:
                snippets.append({
                    'type': 'code',
                    'content': '\n'.join(current_snippet),
                    'line_start': i - len(current_snippet),
                    'line_end': i - 1
                })
                current_snippet = []
                
        # Add final snippet if any
        if current_snippet:
            snippets.append({
                'type': 'code',
                'content': '\n'.join(current_snippet),
                'line_start': len(lines) - len(current_snippet) + 1,
                'line_end': len(lines)
            })
            
        # Add metadata if requested
        if include_metadata:
            metadata = get_file_metadata(file_path)
            for snippet in snippets:
                snippet['metadata'] = metadata
                
        return snippets
        
    except Exception as e:
        logger.error(f"Error extracting snippets from {file_path}: {e}")
        return []

def _get_comment_markers(extension: str) -> Dict[str, Optional[str]]:
    """
    Get comment markers for a file type.
    
    Args:
        extension: File extension
        
    Returns:
        Dictionary with comment markers
    """
    markers = {
        '.py': {'line': '#', 'block_start': '"""', 'block_end': '"""'},
        '.js': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.jsx': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.ts': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.tsx': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.java': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.c': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.cpp': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.cs': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.go': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.rb': {'line': '#', 'block_start': '=begin', 'block_end': '=end'},
        '.php': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.swift': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.kt': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.rs': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.html': {'line': None, 'block_start': '<!--', 'block_end': '-->'},
        '.css': {'line': None, 'block_start': '/*', 'block_end': '*/'},
        '.scss': {'line': '//', 'block_start': '/*', 'block_end': '*/'},
        '.sql': {'line': '--', 'block_start': '/*', 'block_end': '*/'},
        '.sh': {'line': '#', 'block_start': None, 'block_end': None},
        '.bash': {'line': '#', 'block_start': None, 'block_end': None},
        '.zsh': {'line': '#', 'block_start': None, 'block_end': None},
        '.fish': {'line': '#', 'block_start': None, 'block_end': None}
    }
    
    return markers.get(extension, {'line': None, 'block_start': None, 'block_end': None}) 