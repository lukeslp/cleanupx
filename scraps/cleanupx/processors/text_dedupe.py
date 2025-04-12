#!/usr/bin/env python3
"""
Text deduplication processor for CleanupX.

This module provides functionality to deduplicate and merge
similar text files into a single comprehensive document.
"""

import os
import re
import logging
import difflib
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any, Union
from collections import defaultdict
from datetime import datetime

from cleanupx.processors.base import BaseProcessor
from cleanupx.utils.common import read_text_file, is_ignored_file
from cleanupx.utils.cache import save_cache, ensure_metadata_dir, get_description_path

# Configure logging
logger = logging.getLogger(__name__)

# Constants
TEXT_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.rst', '.log', '.csv', '.json', '.xml', 
    '.yml', '.yaml', '.html', '.htm', '.css', '.conf', '.ini', '.cfg'
}

class TextDedupeProcessor(BaseProcessor):
    """Processor for deduplicating and merging similar text files."""
    
    def __init__(self):
        """Initialize the text dedupe processor."""
        super().__init__()
        self.supported_extensions = TEXT_EXTENSIONS
        self.max_size_mb = 10.0  # Text files are typically smaller
        self.similarity_threshold = 0.7
        self.exact_duplicates = defaultdict(list)  # Hash -> files
        self.similar_groups = []  # Groups of similar files
        
    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict:
        """
        Process a text file for deduplication.
        
        Args:
            file_path: Path to the text file
            cache: Cache dictionary for storing/retrieving text content
            rename_log: Optional log for tracking renames
            
        Returns:
            Dictionary with processing results
        """
        file_path = Path(file_path)
        result = {
            'original_path': str(file_path),
            'new_path': None,
            'content': None,
            'paragraphs': [],
            'hash': None,
            'error': None
        }
        
        try:
            # Check if we can process this file
            if not self.can_process(file_path):
                result['error'] = f"Unsupported file type: {file_path.suffix}"
                return result
                
            # Check file size
            if not self.check_file_size(file_path):
                result['error'] = f"File size exceeds maximum ({self.max_size_mb}MB)"
                return result
                
            # Load and process content
            content = read_text_file(file_path)
            if not content:
                result['error'] = "Failed to read file content"
                return result
                
            # Store content and metadata
            result['content'] = content
            result['paragraphs'] = self._split_into_paragraphs(content)
            result['hash'] = self._calculate_hash(content)
            
            # Cache the result
            if cache is not None:
                cache_key = str(file_path)
                cache[cache_key] = {
                    'hash': result['hash'],
                    'paragraphs': len(result['paragraphs'])
                }
                save_cache(cache)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            result['error'] = str(e)
            return result
            
    def process_directory(self, directory: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
        """
        Process a directory to find and merge similar text files.
        
        Args:
            directory: Directory to process
            recursive: Whether to process subdirectories
            
        Returns:
            Dictionary with deduplication results
        """
        directory = Path(directory)
        # Reset tracking collections
        self.exact_duplicates = defaultdict(list)
        self.similar_groups = []
        
        result = {
            'directory': str(directory),
            'exact_duplicates': [],
            'similar_groups': [],
            'total_duplicates': 0,
            'total_similar': 0,
            'error': None
        }
        
        try:
            # Load all text files
            files = self._load_text_files(directory, recursive)
            
            # Find exact duplicates
            for file in files:
                self.exact_duplicates[file.hash].append(file)
                
            # Process duplicates for the result
            for hash_value, duplicate_files in self.exact_duplicates.items():
                if len(duplicate_files) > 1:
                    group = {
                        'hash': hash_value,
                        'files': [str(f.path) for f in duplicate_files],
                        'count': len(duplicate_files)
                    }
                    result['exact_duplicates'].append(group)
                    result['total_duplicates'] += len(duplicate_files) - 1
            
            # Find similar files
            self.similar_groups = self._find_similar_files(files)
            
            # Process similar groups for the result
            for group in self.similar_groups:
                if len(group) > 1:
                    group_info = {
                        'files': [str(f.path) for f in group],
                        'count': len(group)
                    }
                    result['similar_groups'].append(group_info)
                    result['total_similar'] += len(group) - 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
            result['error'] = str(e)
            return result
            
    def merge_duplicates(self, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Merge duplicate and similar text files.
        
        Args:
            output_dir: Directory to save merged files
            
        Returns:
            Dictionary with merge results
        """
        result = {
            'merged_files': [],
            'errors': [],
            'total_merged': 0
        }
        
        try:
            # Create output directory if needed
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process exact duplicates
            for hash_value, duplicate_files in self.exact_duplicates.items():
                if len(duplicate_files) > 1:
                    try:
                        merged_path = self._merge_exact_duplicates(duplicate_files, output_dir)
                        if merged_path:
                            result['merged_files'].append(str(merged_path))
                            result['total_merged'] += 1
                    except Exception as e:
                        error = {'files': [str(f.path) for f in duplicate_files], 'error': str(e)}
                        result['errors'].append(error)
                        logger.error(f"Error merging exact duplicates: {e}")
            
            # Process similar files
            for similar_group in self.similar_groups:
                if len(similar_group) > 1:
                    try:
                        merged_path = self._merge_similar_files(similar_group, output_dir)
                        if merged_path:
                            result['merged_files'].append(str(merged_path))
                            result['total_merged'] += 1
                    except Exception as e:
                        error = {'files': [str(f.path) for f in similar_group], 'error': str(e)}
                        result['errors'].append(error)
                        logger.error(f"Error merging similar files: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error merging files: {e}")
            result['error'] = str(e)
            return result
            
    def _load_text_files(self, directory: Path, recursive: bool = True) -> List['TextFile']:
        """Load all text files from the directory."""
        files = []
        
        def process_file(file_path: Path) -> None:
            if is_ignored_file(file_path):
                return
                
            if file_path.suffix.lower() in self.supported_extensions:
                text_file = TextFile(file_path)
                if text_file.load():
                    files.append(text_file)
        
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if not is_ignored_file(Path(root) / d)]
                
                for filename in filenames:
                    process_file(Path(root) / filename)
        else:
            for item in directory.iterdir():
                if item.is_file():
                    process_file(item)
        
        return files
        
    def _find_exact_duplicates(self, files: List['TextFile']) -> Dict[str, List['TextFile']]:
        """Find files with exactly the same content."""
        duplicates = defaultdict(list)
        for file in files:
            duplicates[file.hash].append(file)
        return {h: files for h, files in duplicates.items() if len(files) > 1}
        
    def _find_similar_files(self, files: List['TextFile']) -> List[List['TextFile']]:
        """Find files with similar content."""
        similar_groups = []
        processed = set()
        
        for i, file1 in enumerate(files):
            if str(file1.path) in processed:
                continue
                
            current_group = [file1]
            processed.add(str(file1.path))
            
            for j, file2 in enumerate(files):
                if i == j or str(file2.path) in processed:
                    continue
                    
                similarity = self._calculate_similarity(file1, file2)
                if similarity >= self.similarity_threshold:
                    current_group.append(file2)
                    processed.add(str(file2.path))
            
            if len(current_group) > 1:
                similar_groups.append(current_group)
        
        return similar_groups
        
    def _calculate_similarity(self, file1: 'TextFile', file2: 'TextFile') -> float:
        """Calculate similarity between two text files."""
        if file1.hash == file2.hash:
            return 1.0
            
        # Line-based similarity
        matcher = difflib.SequenceMatcher(None, file1.lines, file2.lines)
        line_similarity = matcher.ratio()
        
        # Paragraph similarity
        paragraph_matches = 0
        for p1 in file1.paragraphs:
            for p2 in file2.paragraphs:
                para_matcher = difflib.SequenceMatcher(None, p1, p2)
                if para_matcher.ratio() > 0.8:
                    paragraph_matches += 1
                    break
        
        max_paragraphs = max(len(file1.paragraphs), len(file2.paragraphs))
        paragraph_similarity = paragraph_matches / max_paragraphs if max_paragraphs > 0 else 0
        
        # Word overlap
        words1 = set(re.findall(r'\b\w+\b', file1.content.lower()))
        words2 = set(re.findall(r'\b\w+\b', file2.content.lower()))
        
        if not words1 or not words2:
            word_similarity = 0
        else:
            intersection = words1.intersection(words2)
            word_similarity = len(intersection) / max(len(words1), len(words2))
        
        # Combine similarities with weights
        return (line_similarity * 0.5) + (paragraph_similarity * 0.3) + (word_similarity * 0.2)
        
    def _merge_exact_duplicates(self, files: List['TextFile'], output_dir: Optional[Path] = None) -> Optional[Path]:
        """Merge exact duplicate files."""
        if not files or len(files) < 2:
            return None
            
        try:
            # Use the newest file's content
            sorted_files = sorted(files, key=lambda f: f.modified_time, reverse=True)
            newest_file = sorted_files[0]
            
            # Create merged filename
            base_names = [f.path.stem for f in sorted_files]
            merged_name = f"merged_{'_'.join(base_names[:3])}"
            if len(base_names) > 3:
                merged_name += f"_and_{len(base_names) - 3}_more"
            merged_name += newest_file.path.suffix
            
            # Create output path
            output_path = output_dir / merged_name if output_dir else newest_file.path.parent / merged_name
            
            # Create merged content
            content = [
                f"# Merged from {len(files)} duplicate files\n",
                "\n## Source Files\n"
            ]
            
            for file in sorted_files:
                rel_path = os.path.relpath(file.path, files[0].path.parent)
                modified_time = file.modified_time.strftime('%Y-%m-%d %H:%M:%S')
                content.append(f"* {rel_path} (Last modified: {modified_time})")
            
            content.extend(["\n---\n", newest_file.content])
            
            # Write merged file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error merging exact duplicates: {e}")
            return None
            
    def _merge_similar_files(self, files: List['TextFile'], output_dir: Optional[Path] = None) -> Optional[Path]:
        """Merge similar files."""
        if not files or len(files) < 2:
            return None
            
        try:
            # Create merged filename
            base_names = [f.path.stem for f in files]
            merged_name = f"similar_{'_'.join(base_names[:3])}"
            if len(base_names) > 3:
                merged_name += f"_and_{len(base_names) - 3}_more"
            merged_name += ".md"  # Use markdown for merged file
            
            # Create output path
            output_path = output_dir / merged_name if output_dir else files[0].path.parent / merged_name
            
            # Generate merged content
            content = self._generate_merged_content(files)
            
            # Write merged file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error merging similar files: {e}")
            return None
            
    def _generate_merged_content(self, files: List['TextFile']) -> str:
        """Generate merged content from similar files."""
        content = [
            f"# Merged content from {len(files)} similar files\n",
            "## Source Files\n"
        ]
        
        # Add file information
        for file in sorted(files, key=lambda f: f.modified_time, reverse=True):
            content.append(f"* {file.path.name} (Last modified: {file.modified_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        content.append("\n---\n")
        
        # Find common paragraphs
        common_paragraphs = self._find_common_paragraphs(files)
        
        content.extend([
            "## Common Content\n",
            "\n".join(common_paragraphs) if common_paragraphs else "*No significant common content was found.*"
        ])
        
        content.append("\n---\n")
        
        # Add unique content from each file
        content.append("## Unique Content\n")
        
        for file in files:
            content.extend([
                f"### From {file.path.name}\n",
                "\n".join(self._find_unique_paragraphs(file, common_paragraphs)) or "*No unique content in this file.*",
                "\n---\n"
            ])
        
        return "\n".join(content)
        
    def _find_common_paragraphs(self, files: List['TextFile']) -> List[str]:
        """Find paragraphs that are common across all files."""
        if not files:
            return []
            
        reference_file = files[0]
        common_paragraphs = []
        
        for paragraph in reference_file.paragraphs:
            is_common = True
            for other_file in files[1:]:
                paragraph_found = False
                for other_paragraph in other_file.paragraphs:
                    matcher = difflib.SequenceMatcher(None, paragraph, other_paragraph)
                    if matcher.ratio() > 0.8:
                        paragraph_found = True
                        break
                        
                if not paragraph_found:
                    is_common = False
                    break
                    
            if is_common and len(paragraph.split()) > 5:
                common_paragraphs.append(paragraph)
        
        return common_paragraphs
        
    def _find_unique_paragraphs(self, file: 'TextFile', common_paragraphs: List[str]) -> List[str]:
        """Find paragraphs in a file that are not in the common paragraphs list."""
        unique_paragraphs = []
        
        for paragraph in file.paragraphs:
            is_unique = True
            
            for common_paragraph in common_paragraphs:
                matcher = difflib.SequenceMatcher(None, paragraph, common_paragraph)
                if matcher.ratio() > 0.8:
                    is_unique = False
                    break
                    
            if is_unique and len(paragraph.split()) > 5:
                unique_paragraphs.append(paragraph)
        
        return unique_paragraphs
        
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        raw_paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in raw_paragraphs if p.strip()]
        
    def _calculate_hash(self, text: str) -> str:
        """Calculate hash of normalized text content."""
        normalized = re.sub(r'\s+', ' ', text.lower())
        normalized = re.sub(r'[#*_`\[\]\(\)\{\}]', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

class TextFile:
    """Represents a text file with content and metadata."""
    
    def __init__(self, path: Path):
        """Initialize a TextFile object."""
        self.path = path
        self.name = path.name
        self.content = ""
        self.size = 0
        self.lines: List[str] = []
        self.hash = ""
        self.paragraphs: List[str] = []
        self.modified_time = datetime.fromtimestamp(0)
        self.ext = path.suffix.lower()
        self.is_loaded = False
    
    def load(self) -> bool:
        """Load file content and metadata."""
        try:
            self.content = read_text_file(self.path)
            self.size = self.path.stat().st_size
            self.lines = self.content.splitlines()
            self.hash = self._calculate_hash()
            self.paragraphs = self._split_into_paragraphs()
            self.modified_time = datetime.fromtimestamp(self.path.stat().st_mtime)
            self.is_loaded = True
            return True
        except Exception as e:
            logger.error(f"Error loading {self.path}: {e}")
            return False
    
    def _calculate_hash(self) -> str:
        """Calculate a hash of the file content."""
        normalized_content = self._normalize_content()
        return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()
    
    def _normalize_content(self) -> str:
        """Normalize content for comparison."""
        content = re.sub(r'\s+', ' ', self.content)
        content = content.lower()
        content = re.sub(r'[#*_`\[\]\(\)\{\}]', '', content)
        return content.strip()
    
    def _split_into_paragraphs(self) -> List[str]:
        """Split content into paragraphs."""
        raw_paragraphs = re.split(r'\n\s*\n', self.content)
        return [p.strip() for p in raw_paragraphs if p.strip()] 