#!/usr/bin/env python3
"""
Text file deduplication utility for CleanupX.

This module provides functionality to deduplicate and merge
similar text files into a single comprehensive document.
"""

import os
import re
import logging
import difflib
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict
from datetime import datetime

from cleanupx.utils.common import read_text_file, is_ignored_file

# Configure logging
logger = logging.getLogger(__name__)

# Constants
TEXT_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.rst', '.log', '.csv', '.json', '.xml', 
    '.yml', '.yaml', '.html', '.htm', '.css', '.conf', '.ini', '.cfg'
}

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
        """Normalize content for comparison by removing whitespace and common formatting."""
        # Remove all whitespace
        content = re.sub(r'\s+', ' ', self.content)
        # Convert to lowercase
        content = content.lower()
        # Remove common markdown formatting
        content = re.sub(r'[#*_`\[\]\(\)\{\}]', '', content)
        return content.strip()
    
    def _split_into_paragraphs(self) -> List[str]:
        """Split content into paragraphs for better comparison."""
        # Split by double newline (common paragraph separator)
        raw_paragraphs = re.split(r'\n\s*\n', self.content)
        # Filter out empty paragraphs and trim whitespace
        return [p.strip() for p in raw_paragraphs if p.strip()]

class TextDeduper:
    """Utility to find and merge duplicate text files."""
    
    def __init__(self, directory: Path, output_dir: Optional[Path] = None):
        """
        Initialize the TextDeduper.
        
        Args:
            directory: Directory containing text files to deduplicate
            output_dir: Directory to save merged files (defaults to directory/merged_docs)
        """
        self.directory = Path(directory)
        self.output_dir = output_dir or (self.directory / "merged_docs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store all loaded text files
        self.files: List[TextFile] = []
        
        # Maps for clustering similar files
        self.exact_duplicates: Dict[str, List[TextFile]] = defaultdict(list)  # Hash -> files
        self.similar_groups: List[List[TextFile]] = []  # Groups of similar files
    
    def load_files(self, recursive: bool = True, extensions: Optional[Set[str]] = None) -> int:
        """
        Load text files from the directory.
        
        Args:
            recursive: Whether to scan subdirectories recursively
            extensions: Set of file extensions to include (defaults to TEXT_EXTENSIONS)
            
        Returns:
            Number of files loaded
        """
        logger.info(f"Scanning directory: {self.directory}")
        self.files = []
        
        # Use default extensions if none provided
        if extensions is None:
            extensions = TEXT_EXTENSIONS
        
        # Function to process a file
        def process_file(file_path: Path) -> None:
            if is_ignored_file(file_path):
                return
                
            # Check if the file is a text file with acceptable extension
            if file_path.suffix.lower() in extensions:
                text_file = TextFile(file_path)
                if text_file.load():
                    self.files.append(text_file)
                    # Add to exact duplicates map
                    self.exact_duplicates[text_file.hash].append(text_file)
        
        # Walk the directory structure
        if recursive:
            for root, dirs, files in os.walk(self.directory):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if not is_ignored_file(Path(root) / d)]
                
                # Process each file
                for file in files:
                    process_file(Path(root) / file)
        else:
            # Only process files in the root directory
            for item in self.directory.iterdir():
                if item.is_file():
                    process_file(item)
        
        logger.info(f"Loaded {len(self.files)} text files.")
        return len(self.files)
    
    def find_exact_duplicates(self) -> Dict[str, List[TextFile]]:
        """
        Find files with exactly the same content.
        
        Returns:
            Dictionary mapping content hashes to lists of duplicate files
        """
        # Filter out unique files
        duplicates = {h: files for h, files in self.exact_duplicates.items() if len(files) > 1}
        
        logger.info(f"Found {len(duplicates)} sets of exact duplicates.")
        return duplicates
    
    def find_similar_files(self, similarity_threshold: float = 0.7) -> List[List[TextFile]]:
        """
        Find files with similar content.
        
        Args:
            similarity_threshold: Threshold for considering files similar (0.0 to 1.0)
            
        Returns:
            List of lists, each containing similar files
        """
        # Reset similar groups
        self.similar_groups = []
        
        # Sort files by name for consistent results
        sorted_files = sorted(self.files, key=lambda f: str(f.path))
        
        # Track which files have been grouped
        processed_files = set()
        
        for i, file1 in enumerate(sorted_files):
            if str(file1.path) in processed_files:
                continue
                
            # Start a new group with this file
            current_group = [file1]
            processed_files.add(str(file1.path))
            
            # Compare with all other files
            for j, file2 in enumerate(sorted_files):
                if i == j or str(file2.path) in processed_files:
                    continue
                    
                # Check similarity
                similarity = self._calculate_similarity(file1, file2)
                if similarity >= similarity_threshold:
                    current_group.append(file2)
                    processed_files.add(str(file2.path))
            
            # Only add groups with multiple files
            if len(current_group) > 1:
                self.similar_groups.append(current_group)
        
        logger.info(f"Found {len(self.similar_groups)} groups of similar files.")
        return self.similar_groups
    
    def _calculate_similarity(self, file1: TextFile, file2: TextFile) -> float:
        """
        Calculate similarity between two text files.
        
        Uses a combination of:
        1. Line-based difflib similarity
        2. Paragraph matching
        3. Word overlap
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # If they're exact duplicates, return 1.0
        if file1.hash == file2.hash:
            return 1.0
            
        # Use difflib for line-based similarity
        matcher = difflib.SequenceMatcher(None, file1.lines, file2.lines)
        line_similarity = matcher.ratio()
        
        # Calculate paragraph similarity
        paragraph_matches = 0
        for p1 in file1.paragraphs:
            for p2 in file2.paragraphs:
                # Use sequence matcher for paragraph comparison
                para_matcher = difflib.SequenceMatcher(None, p1, p2)
                if para_matcher.ratio() > 0.8:  # High threshold for paragraph matching
                    paragraph_matches += 1
                    break
        
        max_paragraphs = max(len(file1.paragraphs), len(file2.paragraphs))
        paragraph_similarity = paragraph_matches / max_paragraphs if max_paragraphs > 0 else 0
        
        # Calculate word overlap
        words1 = set(re.findall(r'\b\w+\b', file1.content.lower()))
        words2 = set(re.findall(r'\b\w+\b', file2.content.lower()))
        
        if not words1 or not words2:
            word_similarity = 0
        else:
            intersection = words1.intersection(words2)
            word_similarity = len(intersection) / max(len(words1), len(words2))
        
        # Combine the similarities with weights
        combined_similarity = (line_similarity * 0.5) + (paragraph_similarity * 0.3) + (word_similarity * 0.2)
        
        return combined_similarity
    
    def merge_duplicates(self, output_path: Optional[Path] = None) -> Dict[str, Path]:
        """
        Merge exact duplicate files.
        
        Args:
            output_path: Custom output path (uses output_dir if None)
            
        Returns:
            Dictionary mapping content hashes to paths of merged files
        """
        merged_files = {}
        
        for content_hash, duplicate_files in self.exact_duplicates.items():
            if len(duplicate_files) <= 1:
                continue
                
            # Sort files by modified time (newest first)
            sorted_files = sorted(duplicate_files, key=lambda f: f.modified_time, reverse=True)
            
            # Use the newest file's content
            newest_file = sorted_files[0]
            
            # Create a name for the merged file
            base_names = [f.path.stem for f in sorted_files]
            merged_name = f"merged_{'_'.join(base_names[:3])}"
            if len(base_names) > 3:
                merged_name += f"_and_{len(base_names) - 3}_more"
            
            # Use the same extension as the newest file
            merged_name += newest_file.ext
            
            # Create path for the merged file
            merged_path = output_path or (self.output_dir / merged_name)
            
            # Create the merged content with a header
            merged_content = f"# Merged from {len(duplicate_files)} duplicate files\n\n"
            merged_content += "## Source Files\n\n"
            for file in sorted_files:
                rel_path = os.path.relpath(file.path, self.directory)
                merged_content += f"* {rel_path} (Last modified: {file.modified_time.strftime('%Y-%m-%d %H:%M:%S')})\n"
            
            merged_content += "\n---\n\n"
            merged_content += newest_file.content
            
            # Write the merged file
            with open(merged_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
                
            # Add to the result dict
            merged_files[content_hash] = merged_path
            
            logger.info(f"Merged {len(duplicate_files)} exact duplicates into {merged_path}")
        
        return merged_files
    
    def merge_similar_files(self, similarity_threshold: float = 0.7, output_path: Optional[Path] = None) -> List[Path]:
        """
        Find and merge similar files.
        
        Args:
            similarity_threshold: Threshold for considering files similar (0.0 to 1.0)
            output_path: Custom output path (uses output_dir if None)
            
        Returns:
            List of paths to merged files
        """
        # First find similar files if not already done
        if not self.similar_groups:
            self.find_similar_files(similarity_threshold)
            
        merged_paths = []
        
        for group_index, group in enumerate(self.similar_groups):
            # Create a name for the merged file
            base_names = [f.path.stem for f in group]
            merged_name = f"similar_{'_'.join(base_names[:3])}"
            if len(base_names) > 3:
                merged_name += f"_and_{len(base_names) - 3}_more"
            
            # Use .md extension for the merged file to support markdown formatting
            merged_path = output_path or (self.output_dir / f"{merged_name}.md")
            
            # Merge the content using a diff-based approach
            merged_content = self._generate_merged_content(group)
            
            # Write the merged file
            with open(merged_path, 'w', encoding='utf-8') as f:
                f.write(merged_content)
                
            merged_paths.append(merged_path)
            logger.info(f"Merged {len(group)} similar files into {merged_path}")
        
        return merged_paths
    
    def _generate_merged_content(self, files: List[TextFile]) -> str:
        """
        Generate merged content from a group of similar files.
        
        The merged content will include:
        1. Metadata about the source files
        2. Common content across all files
        3. Unique content from each file, clearly marked
        
        Args:
            files: List of similar TextFile objects
            
        Returns:
            Merged content as a string
        """
        # Start with metadata header
        content = f"# Merged content from {len(files)} similar files\n\n"
        content += "## Source Files\n\n"
        
        # Sort files by modified time (newest first)
        sorted_files = sorted(files, key=lambda f: f.modified_time, reverse=True)
        
        for file in sorted_files:
            rel_path = os.path.relpath(file.path, self.directory)
            content += f"* {rel_path} (Last modified: {file.modified_time.strftime('%Y-%m-%d %H:%M:%S')})\n"
        
        content += "\n---\n\n"
        
        # Find common paragraphs across all files
        common_paragraphs = self._find_common_paragraphs(sorted_files)
        
        content += "## Common Content\n\n"
        if common_paragraphs:
            content += "\n".join(common_paragraphs)
        else:
            content += "*No significant common content was found.*\n"
        
        content += "\n---\n\n"
        
        # Add unique content from each file
        content += "## Unique Content\n\n"
        
        for file in sorted_files:
            rel_path = os.path.relpath(file.path, self.directory)
            content += f"### From {rel_path}\n\n"
            
            unique_paragraphs = self._find_unique_paragraphs(file, common_paragraphs)
            if unique_paragraphs:
                content += "\n\n".join(unique_paragraphs)
            else:
                content += "*No unique content in this file.*\n"
                
            content += "\n---\n\n"
        
        return content
    
    def _find_common_paragraphs(self, files: List[TextFile]) -> List[str]:
        """Find paragraphs that are common across all files."""
        if not files:
            return []
            
        # Start with all paragraphs from the first file
        reference_file = files[0]
        common_paragraphs = []
        
        for paragraph in reference_file.paragraphs:
            # Check if this paragraph exists in all other files
            is_common = True
            for other_file in files[1:]:
                paragraph_found = False
                for other_paragraph in other_file.paragraphs:
                    # Use sequence matcher for fuzzy matching
                    matcher = difflib.SequenceMatcher(None, paragraph, other_paragraph)
                    if matcher.ratio() > 0.8:  # High threshold for paragraph matching
                        paragraph_found = True
                        break
                        
                if not paragraph_found:
                    is_common = False
                    break
                    
            if is_common and len(paragraph.split()) > 5:  # Only include substantial paragraphs
                common_paragraphs.append(paragraph)
        
        return common_paragraphs
    
    def _find_unique_paragraphs(self, file: TextFile, common_paragraphs: List[str]) -> List[str]:
        """Find paragraphs in a file that are not in the common paragraphs list."""
        unique_paragraphs = []
        
        for paragraph in file.paragraphs:
            is_unique = True
            
            for common_paragraph in common_paragraphs:
                # Use sequence matcher for fuzzy matching
                matcher = difflib.SequenceMatcher(None, paragraph, common_paragraph)
                if matcher.ratio() > 0.8:  # High threshold for paragraph matching
                    is_unique = False
                    break
                    
            if is_unique and len(paragraph.split()) > 5:  # Only include substantial paragraphs
                unique_paragraphs.append(paragraph)
        
        return unique_paragraphs
    
    def generate_report(self) -> Tuple[Path, Dict[str, Any]]:
        """
        Generate a report about duplicate and similar files.
        
        Returns:
            Tuple of (report file path, report data)
        """
        # Create the report data
        report = {
            "scan_time": datetime.now().isoformat(),
            "directory": str(self.directory),
            "total_files": len(self.files),
            "exact_duplicates": [],
            "similar_groups": []
        }
        
        # Add exact duplicates
        for content_hash, duplicate_files in self.exact_duplicates.items():
            if len(duplicate_files) <= 1:
                continue
                
            duplicate_group = {
                "hash": content_hash,
                "count": len(duplicate_files),
                "files": [str(os.path.relpath(f.path, self.directory)) for f in duplicate_files],
                "oldest": min(f.modified_time for f in duplicate_files).isoformat(),
                "newest": max(f.modified_time for f in duplicate_files).isoformat(),
                "size_bytes": duplicate_files[0].size
            }
            
            report["exact_duplicates"].append(duplicate_group)
        
        # Add similar groups
        for group in self.similar_groups:
            similar_group = {
                "count": len(group),
                "files": [str(os.path.relpath(f.path, self.directory)) for f in group],
                "oldest": min(f.modified_time for f in group).isoformat(),
                "newest": max(f.modified_time for f in group).isoformat()
            }
            
            report["similar_groups"].append(similar_group)
        
        # Write the report to a markdown file
        report_path = self.output_dir / "deduplication_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Text File Deduplication Report\n\n")
            f.write(f"**Directory:** {self.directory}\n")
            f.write(f"**Scan Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Files Scanned:** {len(self.files)}\n\n")
            
            # Write duplicate file information
            exact_dupes = [g for g in report["exact_duplicates"] if g["count"] > 1]
            f.write(f"## Exact Duplicates: {len(exact_dupes)} groups\n\n")
            
            if exact_dupes:
                for i, group in enumerate(exact_dupes, 1):
                    f.write(f"### Group {i}: {group['count']} files\n\n")
                    f.write(f"* Size: {self._format_size(group['size_bytes'])}\n")
                    f.write(f"* Newest: {datetime.fromisoformat(group['newest']).strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"* Oldest: {datetime.fromisoformat(group['oldest']).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    f.write("**Files:**\n\n")
                    for file_path in group["files"]:
                        f.write(f"* {file_path}\n")
                    f.write("\n")
            else:
                f.write("*No exact duplicates found.*\n\n")
            
            # Write similar file information
            f.write(f"## Similar Files: {len(report['similar_groups'])} groups\n\n")
            
            if report["similar_groups"]:
                for i, group in enumerate(report["similar_groups"], 1):
                    f.write(f"### Group {i}: {group['count']} files\n\n")
                    f.write(f"* Newest: {datetime.fromisoformat(group['newest']).strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"* Oldest: {datetime.fromisoformat(group['oldest']).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    
                    f.write("**Files:**\n\n")
                    for file_path in group["files"]:
                        f.write(f"* {file_path}\n")
                    f.write("\n")
            else:
                f.write("*No similar file groups found.*\n\n")
        
        return report_path, report
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

def dedupe_text_files(directory: Path, output_dir: Optional[Path] = None) -> Tuple[List[Path], Path]:
    """
    Find and merge duplicate/similar text files in a directory.
    
    Args:
        directory: Directory containing text files
        output_dir: Directory to save merged files (defaults to directory/merged_docs)
        
    Returns:
        Tuple of (list of merged file paths, report file path)
    """
    deduper = TextDeduper(directory, output_dir)
    deduper.load_files(recursive=True)
    
    # Process exact duplicates
    deduper.find_exact_duplicates()
    merged_exact = deduper.merge_duplicates()
    
    # Process similar files
    deduper.find_similar_files()
    merged_similar = deduper.merge_similar_files()
    
    # Generate report
    report_path, _ = deduper.generate_report()
    
    # Combine all merged file paths
    all_merged = list(merged_exact.values()) + merged_similar
    
    return all_merged, report_path 