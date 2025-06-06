"""
CleanupX Configuration Module

Centralizes configuration settings and output path management to prevent
scattered file creation and ensure organized output structure.

MIT License by Luke Steuber, lukesteuber.com, assisted.site
luke@lukesteuber.com; bluesky @lukesteuber.com
linkedin https://www.linkedin.com/in/lukesteuber/
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

# Default configurations
DEFAULT_EXTENSIONS = {'.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.yaml', '.yml'}
PROTECTED_PATTERNS = ['.git', '__pycache__', 'node_modules', '.cleanupx', '.xsnippet']
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}

# Output directory structure
DEFAULT_OUTPUT_STRUCTURE = {
    'root': 'cleanupx_output',
    'deduplicated': 'deduplicated',
    'organized': 'organized', 
    'images': 'images_processed',
    'snippets': 'snippets',
    'metadata': '.cleanupx',
    'cache': 'cache',
    'logs': 'logs',
    'reports': 'reports'
}

class OutputManager:
    """
    Manages output directory structure and prevents scattered file creation.
    """
    
    def __init__(self, base_directory: Path, output_name: str = "cleanupx_output"):
        """
        Initialize output manager.
        
        Args:
            base_directory: Base directory where processing is happening
            output_name: Name of the main output directory
        """
        self.base_directory = Path(base_directory).resolve()
        self.output_root = self.base_directory / output_name
        self.structure = DEFAULT_OUTPUT_STRUCTURE.copy()
        self._created_dirs = set()
    
    def get_output_path(self, category: str, filename: Optional[str] = None) -> Path:
        """
        Get standardized output path for a category of files.
        
        Args:
            category: Category of output (deduplicated, images, etc.)
            filename: Optional filename to append
            
        Returns:
            Path object for the output location
        """
        if category not in self.structure:
            category = 'reports'  # Default fallback
        
        category_dir = self.output_root / self.structure[category]
        
        # Ensure directory exists
        if category_dir not in self._created_dirs:
            category_dir.mkdir(parents=True, exist_ok=True)
            self._created_dirs.add(category_dir)
        
        if filename:
            return category_dir / filename
        return category_dir
    
    def get_metadata_path(self, filename: str) -> Path:
        """Get path for metadata files."""
        return self.get_output_path('metadata', filename)
    
    def get_cache_path(self, filename: str) -> Path:
        """Get path for cache files."""
        return self.get_output_path('cache', filename)
    
    def get_log_path(self, filename: str) -> Path:
        """Get path for log files."""
        return self.get_output_path('logs', filename)
    
    def get_report_path(self, filename: str) -> Path:
        """Get path for report files."""
        return self.get_output_path('reports', filename)
    
    def cleanup_empty_dirs(self):
        """Remove empty directories from the output structure."""
        for dir_path in self._created_dirs:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except:
                pass  # Ignore errors when cleaning up
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of output structure and files created."""
        summary = {
            'output_root': str(self.output_root),
            'base_directory': str(self.base_directory),
            'categories': {},
            'total_files': 0
        }
        
        for category, subdir in self.structure.items():
            category_path = self.output_root / subdir
            if category_path.exists():
                files = list(category_path.rglob('*'))
                file_count = len([f for f in files if f.is_file()])
                summary['categories'][category] = {
                    'path': str(category_path),
                    'file_count': file_count,
                    'exists': True
                }
                summary['total_files'] += file_count
            else:
                summary['categories'][category] = {
                    'path': str(category_path),
                    'file_count': 0,
                    'exists': False
                }
        
        return summary

def get_default_output_manager(directory: Path) -> OutputManager:
    """Get a default output manager for a directory."""
    return OutputManager(directory)

def ensure_output_structure(directory: Path, custom_structure: Optional[Dict] = None) -> OutputManager:
    """
    Ensure proper output directory structure exists.
    
    Args:
        directory: Base directory for processing
        custom_structure: Optional custom directory structure
        
    Returns:
        OutputManager instance
    """
    manager = OutputManager(directory)
    
    if custom_structure:
        manager.structure.update(custom_structure)
    
    # Pre-create common directories
    manager.get_output_path('metadata')
    manager.get_output_path('reports')
    manager.get_output_path('cache')
    
    return manager

# Environment variable configuration
def get_config_from_env() -> Dict[str, Any]:
    """Get configuration from environment variables."""
    return {
        'xai_api_key': os.getenv('XAI_API_KEY'),
        'max_file_size_mb': int(os.getenv('CLEANUPX_MAX_FILE_SIZE', '20')),
        'cache_dir': os.getenv('CLEANUPX_CACHE_DIR', './cache'),
        'log_level': os.getenv('CLEANUPX_LOG_LEVEL', 'INFO'),
        'output_dir': os.getenv('CLEANUPX_OUTPUT_DIR', 'cleanupx_output')
    }

# Utility functions for common file operations
def is_protected_file(file_path: Path) -> bool:
    """Check if a file should be protected from processing."""
    path_str = str(file_path)
    return any(pattern in path_str for pattern in PROTECTED_PATTERNS)

def normalize_path(path) -> Path:
    """Normalize a path to a Path object."""
    return Path(path).resolve()

def get_file_metadata(file_path: Path) -> Dict[str, Any]:
    """Get basic metadata for a file."""
    try:
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'extension': file_path.suffix.lower(),
            'stem': file_path.stem
        }
    except Exception as e:
        return {'error': str(e)}

def ensure_metadata_dir(directory: Path) -> Path:
    """Ensure metadata directory exists and return its path."""
    metadata_dir = directory / '.cleanupx'
    metadata_dir.mkdir(exist_ok=True)
    return metadata_dir 