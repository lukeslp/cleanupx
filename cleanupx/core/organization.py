"""
Directory Organizer

Handles directory structure organization and summary generation.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from ..processors import DocumentProcessor, ImageProcessor, ArchiveProcessor
from .config import (
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    TEXT_EXTENSIONS,
    MEDIA_EXTENSIONS,
    CODE_EXTENSIONS,
    PROTECTED_PATTERNS
)
from .utils import (
    get_file_metadata,
    is_protected_file,
    normalize_path,
    save_rename_log,
    add_error_to_log
)

logger = logging.getLogger(__name__)

class DirectoryOrganizer:
    """Manages directory organization and summary generation."""
    
    def __init__(self, base_dir: str):
        """Initialize the directory organizer with a base directory."""
        self.base_dir = Path(base_dir)
        self.summary_file = self.base_dir / '.cleanupx' / '.summary'
        self.processors = {
            'document': DocumentProcessor(),
            'image': ImageProcessor(),
            'archive': ArchiveProcessor()
        }
        self._load_summary()
        
    def _load_summary(self):
        """Load existing directory summary."""
        self.summary = {
            'structure': {},
            'content_overview': {},
            'recommendations': []
        }
        if self.summary_file.exists():
            try:
                with open(self.summary_file, 'r') as f:
                    self.summary = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupted summary file, starting fresh")
                
    def _save_summary(self):
        """Save directory summary to file."""
        with open(self.summary_file, 'w') as f:
            json.dump(self.summary, f, indent=2)
            
    def analyze_directory(self, recursive: bool = True) -> Dict:
        """
        Analyze directory structure and contents.
        
        Args:
            recursive: Whether to analyze subdirectories
            
        Returns:
            Analysis results
        """
        analysis = {
            'structure': self._analyze_structure(recursive),
            'content_overview': self._analyze_content(recursive),
            'recommendations': self._generate_recommendations()
        }
        
        self.summary = analysis
        self._save_summary()
        return analysis
        
    def _analyze_structure(self, recursive: bool) -> Dict:
        """Analyze directory structure."""
        structure = {}
        for root, dirs, files in os.walk(self.base_dir):
            if not recursive and Path(root) != self.base_dir:
                continue
                
            rel_path = Path(root).relative_to(self.base_dir)
            structure[str(rel_path)] = {
                'directories': dirs,
                'files': files
            }
            
        return structure
        
    def _analyze_content(self, recursive: bool) -> Dict:
        """Analyze directory contents."""
        content = {
            'file_types': {},
            'topics': {},
            'projects': {}
        }
        
        for root, _, files in os.walk(self.base_dir):
            if not recursive and Path(root) != self.base_dir:
                continue
                
            for file in files:
                file_path = Path(root) / file
                file_type = self._determine_file_type(file_path)
                
                # Update file type statistics
                content['file_types'][file_type] = content['file_types'].get(file_type, 0) + 1
                
                # Extract content information
                if file_type in self.processors:
                    try:
                        info = self.processors[file_type].analyze_content(file_path)
                        if info.get('topics'):
                            for topic in info['topics']:
                                content['topics'][topic] = content['topics'].get(topic, 0) + 1
                        if info.get('project'):
                            content['projects'][info['project']] = content['projects'].get(info['project'], 0) + 1
                    except Exception as e:
                        logger.error(f"Error analyzing {file_path}: {str(e)}")
                        
        return content
        
    def _generate_recommendations(self) -> List[str]:
        """Generate organization recommendations based on analysis."""
        recommendations = []
        
        # Analyze file types and suggest organization
        file_types = self.summary['content_overview']['file_types']
        if len(file_types) > 10:
            recommendations.append("Consider organizing files by type into subdirectories")
            
        # Analyze topics and suggest grouping
        topics = self.summary['content_overview']['topics']
        if len(topics) > 5:
            recommendations.append("Consider creating topic-based subdirectories")
            
        # Analyze projects and suggest structure
        projects = self.summary['content_overview']['projects']
        if len(projects) > 3:
            recommendations.append("Consider organizing by project structure")
            
        return recommendations
        
    def reorganize(self, strategy: str = 'auto') -> Dict:
        """
        Reorganize directory based on specified strategy.
        
        Args:
            strategy: Reorganization strategy ('auto', 'by_type', 'by_topic', 'by_project')
            
        Returns:
            Reorganization results
        """
        results = {
            'moved': [],
            'created': [],
            'failed': []
        }
        
        if strategy == 'auto':
            strategy = self._determine_best_strategy()
            
        try:
            if strategy == 'by_type':
                results.update(self._reorganize_by_type())
            elif strategy == 'by_topic':
                results.update(self._reorganize_by_topic())
            elif strategy == 'by_project':
                results.update(self._reorganize_by_project())
        except Exception as e:
            logger.error(f"Error during reorganization: {str(e)}")
            
        return results
        
    def _determine_best_strategy(self) -> str:
        """Determine the best reorganization strategy based on content analysis."""
        content = self.summary['content_overview']
        
        if len(content['projects']) > len(content['topics']):
            return 'by_project'
        elif len(content['topics']) > 5:
            return 'by_topic'
        else:
            return 'by_type'
            
    def _reorganize_by_type(self) -> Dict:
        """Reorganize files by type."""
        # Implementation for type-based reorganization
        pass
        
    def _reorganize_by_topic(self) -> Dict:
        """Reorganize files by topic."""
        # Implementation for topic-based reorganization
        pass
        
    def _reorganize_by_project(self) -> Dict:
        """Reorganize files by project."""
        # Implementation for project-based reorganization
        pass

def organize_files(
    directory: Union[str, Path],
    recursive: bool = False,
    create_dirs: bool = True,
    move_files: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Organize files in a directory by type.
    
    Args:
        directory: Directory to organize
        recursive: Whether to process subdirectories
        create_dirs: Whether to create type directories
        move_files: Whether to move files
        dry_run: Whether to simulate organization
        
    Returns:
        Organization results
    """
    try:
        directory = normalize_path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
            
        # Initialize results
        results = {
            'organized': [],
            'skipped': [],
            'errors': [],
            'stats': {
                'total_files': 0,
                'organized_files': 0,
                'skipped_files': 0,
                'error_files': 0
            }
        }
        
        # Create type directories if needed
        type_dirs = {
            'images': IMAGE_EXTENSIONS,
            'documents': DOCUMENT_EXTENSIONS,
            'archives': ARCHIVE_EXTENSIONS,
            'text': TEXT_EXTENSIONS,
            'media': MEDIA_EXTENSIONS,
            'code': CODE_EXTENSIONS,
            'other': set()
        }
        
        if create_dirs and not dry_run:
            for type_dir in type_dirs:
                (directory / type_dir).mkdir(exist_ok=True)
                
        # Process files
        for root, _, files in os.walk(directory):
            if not recursive and Path(root) != directory:
                continue
                
            for file in files:
                file_path = Path(root) / file
                results['stats']['total_files'] += 1
                
                try:
                    # Skip protected files
                    if is_protected_file(file_path, PROTECTED_PATTERNS):
                        logger.info(f"Skipping protected file: {file_path}")
                        results['skipped'].append(str(file_path))
                        results['stats']['skipped_files'] += 1
                        continue
                        
                    # Get file type
                    file_type = _get_file_type(file_path, type_dirs)
                    type_dir = directory / file_type
                    
                    # Create type directory if needed
                    if create_dirs and not dry_run:
                        type_dir.mkdir(exist_ok=True)
                        
                    # Move file
                    if move_files and not dry_run:
                        target_path = type_dir / file_path.name
                        counter = 1
                        
                        # Handle duplicates
                        while target_path.exists():
                            name = f"{file_path.stem}_{counter}{file_path.suffix}"
                            target_path = type_dir / name
                            counter += 1
                            
                        shutil.move(str(file_path), str(target_path))
                        logger.info(f"Moved {file_path} to {target_path}")
                        
                    results['organized'].append({
                        'file': str(file_path),
                        'type': file_type,
                        'target': str(type_dir / file_path.name)
                    })
                    results['stats']['organized_files'] += 1
                    
                except Exception as e:
                    logger.error(f"Error organizing {file_path}: {e}")
                    results['errors'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
                    results['stats']['error_files'] += 1
                    
            if not recursive:
                break
                
        # Save results
        if not dry_run:
            save_rename_log(results, directory)
            
        return results
        
    except Exception as e:
        logger.error(f"Error organizing directory {directory}: {e}")
        return {
            'organized': [],
            'skipped': [],
            'errors': [{'file': str(directory), 'error': str(e)}],
            'stats': {
                'total_files': 0,
                'organized_files': 0,
                'skipped_files': 0,
                'error_files': 1
            }
        }

def _get_file_type(file_path: Path, type_dirs: Dict[str, set]) -> str:
    """
    Get the type directory for a file.
    
    Args:
        file_path: Path to the file
        type_dirs: Dictionary of type directories and their extensions
        
    Returns:
        Type directory name
    """
    ext = file_path.suffix.lower()
    
    for type_dir, extensions in type_dirs.items():
        if ext in extensions:
            return type_dir
            
    return 'other' 