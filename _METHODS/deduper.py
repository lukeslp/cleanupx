#!/usr/bin/env python3
"""
dedupe_images.py

This script deduplicates images in a folder based on file size and resolution.
It also provides extended functionality to deduplicate general files and merge
similar text files into a single comprehensive document.

For images, for each image in the folder (filtered by common image extensions), it computes:
  - File size (in bytes)
  - Image resolution (width and height)

For general files, deduplication is based on file size and SHA-256 hash.
For text files, similarity is computed based on lines, paragraphs, and word overlap.

Usage:
    Run this script and follow the interactive prompts.
"""

import os
import sys
import logging
import hashlib
import re
import difflib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, Any, List, Union, Set, Tuple

from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define common image file extensions
IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}

def get_image_info(file_path: Path) -> Tuple[Optional[int], Optional[Tuple[int, int]]]:
    """
    Return the file size (in bytes) and resolution (width, height) for an image.

    Args:
        file_path (Path): Path to the image file.

    Returns:
        tuple: (file_size, (width, height)) if successful; otherwise (None, None).
    """
    try:
        file_size = file_path.stat().st_size
    except Exception as e:
        print(f"Error getting file size for {file_path}: {e}")
        return None, None

    try:
        with Image.open(file_path) as img:
            resolution = img.size  # (width, height)
    except Exception as e:
        print(f"Error opening image {file_path}: {e}")
        resolution = None

    return file_size, resolution

def dedupe_images(folder_path: str) -> None:
    """
    Scan the specified folder for duplicate images based on file size and resolution.
    For each set of duplicates, keep the first file and prompt to delete the others.

    Args:
        folder_path (str): Path to the image folder.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"{folder_path} is not a valid directory.")
        return

    # Collect all image files (non-recursively)
    images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    if not images:
        print("No images found in the folder.")
        return

    # Map (file_size, resolution) to list of files
    image_dict: Dict[Tuple[int, Tuple[int, int]], List[Path]] = {}
    for img in images:
        file_size, resolution = get_image_info(img)
        if file_size is None or resolution is None:
            continue
        key = (file_size, resolution)
        image_dict.setdefault(key, []).append(img)

    duplicates: List[Path] = []
    # Identify duplicate groups
    for key, file_list in image_dict.items():
        if len(file_list) > 1:
            original = file_list[0]
            dupes = file_list[1:]
            print(f"\nFound duplicates for '{original.name}' (size: {key[0]} bytes, resolution: {key[1][0]}x{key[1][1]}):")
            for dup in dupes:
                print(f"  - {dup.name}")
            duplicates.extend(dupes)

    # Confirm deletion
    if duplicates:
        confirm = input("\nDo you want to delete these duplicate files? [y/N]: ").strip().lower()
        if confirm == 'y':
            for dup in duplicates:
                try:
                    dup.unlink()
                    print(f"Deleted: {dup}")
                except Exception as e:
                    print(f"Error deleting {dup}: {e}")
        else:
            print("No files were deleted.")
    else:
        print("No duplicate images found based on size and resolution.")

# -----------------
# Utility Functions for File Deduplication
# -----------------
def get_file_hash(file_path: Path, block_size: int = 65536) -> Optional[str]:
    """
    Calculate the SHA-256 hash of a file.

    Args:
        file_path (Path): Path to the file.
        block_size (int): Block size for reading.

    Returns:
        Optional[str]: Hex digest of the file hash, or None if error.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                hasher.update(block)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None

def detect_duplicates(directory: Path, file_types: Optional[Set[str]] = None, recursive: bool = False) -> Dict[str, List[Path]]:
    """
    Detect duplicate files in a directory based on size and hash.

    Args:
        directory (Path): Directory to scan.
        file_types (Optional[Set[str]]): Supported file extensions (if provided).
        recursive (bool): Whether to process subdirectories.

    Returns:
        Dict[str, List[Path]]: Mapping from a key (size_hash) to list of files.
    """
    if not directory.is_dir():
        logger.error(f"{directory} is not a valid directory.")
        return {}
    
    files: List[Path] = []
    if recursive:
        for path in directory.rglob('*'):
            if path.is_file() and (file_types is None or path.suffix.lower() in file_types):
                files.append(path)
    else:
        for path in directory.iterdir():
            if path.is_file() and (file_types is None or path.suffix.lower() in file_types):
                files.append(path)
    
    if not files:
        logger.info(f"No matching files found in {directory}")
        return {}
    
    size_groups: Dict[int, List[Path]] = {}
    for file_path in files:
        try:
            size = file_path.stat().st_size
            size_groups.setdefault(size, []).append(file_path)
        except Exception as e:
            logger.error(f"Error getting size for {file_path}: {e}")
    
    duplicate_groups: Dict[str, List[Path]] = {}
    for size, group in size_groups.items():
        if len(group) < 2:
            continue  # Need at least 2 files
        hash_dict: Dict[str, List[Path]] = {}
        for file_path in group:
            file_hash = get_file_hash(file_path)
            if file_hash:
                key = f"{size}_{file_hash}"
                hash_dict.setdefault(key, []).append(file_path)
        for key, paths in hash_dict.items():
            if len(paths) > 1:
                duplicate_groups[key] = paths
    
    return duplicate_groups

# -----------------
# Base Processor Classes
# -----------------
class BaseProcessor:
    """
    Minimal base processor class.
    """
    def __init__(self):
        pass

class DedupeProcessor(BaseProcessor):
    """
    Processor for deduplicating files.
    Supports deduplication based on file size, hash, and for images, resolution.
    """
    def __init__(self):
        super().__init__()
        self.supported_extensions: Set[str] = set()  # All file types supported
        self.max_size_mb: float = 1000.0  # Maximum size in MB

    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a file for deduplication.

        Args:
            file_path (Union[str, Path]): Path of the file.
            cache (Dict[str, Any]): Cache for storing file hash.
            rename_log (Optional[Dict]): Optional log for renames.

        Returns:
            Dict[str, Any]: Processing result with metadata.
        """
        file_path = Path(file_path)
        result: Dict[str, Any] = {
            'original_path': str(file_path),
            'new_path': None,
            'hash': None,
            'size': None,
            'resolution': None,
            'is_duplicate': False,
            'error': None
        }
        try:
            file_size = file_path.stat().st_size
            result['size'] = file_size

            cache_key = str(file_path)
            if cache.get(cache_key) and 'hash' in cache[cache_key]:
                result['hash'] = cache[cache_key]['hash']

            if not result['hash']:
                result['hash'] = get_file_hash(file_path)
                if result['hash']:
                    cache[cache_key] = {'hash': result['hash']}
                    # Assume save_cache(cache) is handled externally
                    
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                try:
                    with Image.open(file_path) as img:
                        result['resolution'] = img.size
                except Exception as e:
                    logger.error(f"Error getting image resolution for {file_path}: {e}")

            return result
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            result['error'] = str(e)
            return result

    def process_directory(self, directory: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
        """
        Process a directory to find duplicate files.

        Args:
            directory (Union[str, Path]): Directory to scan.
            recursive (bool): Whether to process subdirectories.

        Returns:
            Dict[str, Any]: Aggregated deduplication results.
        """
        directory = Path(directory)
        result: Dict[str, Any] = {
            'directory': str(directory),
            'duplicate_groups': [],
            'total_duplicates': 0,
            'total_size_saved': 0,
            'error': None
        }
        try:
            duplicate_groups = detect_duplicates(directory, recursive=recursive)
            for key, files in duplicate_groups.items():
                if len(files) > 1:
                    group_info = {
                        'key': key,
                        'files': [str(f) for f in files],
                        'size': files[0].stat().st_size,
                        'count': len(files)
                    }
                    result['duplicate_groups'].append(group_info)
                    result['total_duplicates'] += (len(files) - 1)
                    result['total_size_saved'] += (len(files) - 1) * files[0].stat().st_size
            return result
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
            result['error'] = str(e)
            return result

    def delete_duplicates(self, duplicate_groups: Dict[str, List[Path]], keep_first: bool = True) -> Dict[str, Any]:
        """
        Delete duplicate files from the groups.

        Args:
            duplicate_groups (Dict[str, List[Path]]): Mapping of group keys to lists of duplicate files.
            keep_first (bool): If True, retain the first file in each group.

        Returns:
            Dict[str, Any]: Deletion statistics.
        """
        result: Dict[str, Any] = {
            'deleted_files': [],
            'errors': [],
            'total_deleted': 0,
            'total_size_saved': 0
        }
        for key, files in duplicate_groups.items():
            if len(files) <= 1:
                continue
            files_to_delete = files[1:] if keep_first else files
            for file_path in files_to_delete:
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    result['deleted_files'].append(str(file_path))
                    result['total_deleted'] += 1
                    result['total_size_saved'] += size
                except Exception as e:
                    error = {'file': str(file_path), 'error': str(e)}
                    result['errors'].append(error)
                    logger.error(f"Error deleting {file_path}: {e}")
        return result

class TextDedupeProcessor(BaseProcessor):
    """
    Processor for deduplicating and merging similar text files.
    """
    TEXT_EXTENSIONS: Set[str] = {
        '.txt', '.md', '.markdown', '.rst', '.log', '.csv', '.json', '.xml',
        '.yml', '.yaml', '.html', '.htm', '.css', '.conf', '.ini', '.cfg'
    }
    def __init__(self):
        super().__init__()
        self.supported_extensions: Set[str] = self.TEXT_EXTENSIONS
        self.max_size_mb: float = 10.0  # Typical text file sizes are small
        self.similarity_threshold: float = 0.7
        self.exact_duplicates: Dict[str, List[Any]] = defaultdict(list)
        self.similar_groups: List[List[Any]] = []

    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process a text file for deduplication.

        Args:
            file_path (Union[str, Path]): Path to the text file.
            cache (Dict[str, Any]): Cache for storing file metrics.
            rename_log (Optional[Dict]): Log for renames.

        Returns:
            Dict[str, Any]: Processing result containing file content and metadata.
        """
        file_path = Path(file_path)
        result: Dict[str, Any] = {
            'original_path': str(file_path),
            'new_path': None,
            'content': None,
            'paragraphs': [],
            'hash': None,
            'error': None
        }
        try:
            if file_path.suffix.lower() not in self.supported_extensions:
                result['error'] = f"Unsupported file type: {file_path.suffix}"
                return result

            if file_path.stat().st_size > self.max_size_mb * 1024 * 1024:
                result['error'] = f"File size exceeds maximum ({self.max_size_mb}MB)"
                return result

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content:
                result['error'] = "Failed to read file content"
                return result

            result['content'] = content
            result['paragraphs'] = self._split_into_paragraphs(content)
            result['hash'] = self._calculate_hash(content)

            if cache is not None:
                cache_key = str(file_path)
                cache[cache_key] = {
                    'hash': result['hash'],
                    'paragraphs': len(result['paragraphs'])
                }
                # Assume save_cache(cache) is performed externally
            return result
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            result['error'] = str(e)
            return result

    def process_directory(self, directory: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
        """
        Process a directory to find and group duplicate text files.

        Args:
            directory (Union[str, Path]): Directory to scan.
            recursive (bool): Whether to process subdirectories.

        Returns:
            Dict[str, Any]: Aggregated deduplication results.
        """
        directory = Path(directory)
        self.exact_duplicates = defaultdict(list)
        self.similar_groups = []
        result: Dict[str, Any] = {
            'directory': str(directory),
            'exact_duplicates': [],
            'similar_groups': [],
            'total_duplicates': 0,
            'total_similar': 0,
            'error': None
        }
        try:
            files = self._load_text_files(directory, recursive)
            for file in files:
                self.exact_duplicates[file['hash']].append(file)
            for hash_value, duplicate_files in self.exact_duplicates.items():
                if len(duplicate_files) > 1:
                    group = {
                        'hash': hash_value,
                        'files': [f['original_path'] for f in duplicate_files],
                        'count': len(duplicate_files)
                    }
                    result['exact_duplicates'].append(group)
                    result['total_duplicates'] += (len(duplicate_files) - 1)
            self.similar_groups = self._find_similar_files(files)
            for group in self.similar_groups:
                if len(group) > 1:
                    group_info = {
                        'files': [f['original_path'] for f in group],
                        'count': len(group)
                    }
                    result['similar_groups'].append(group_info)
                    result['total_similar'] += (len(group) - 1)
            return result
        except Exception as e:
            logger.error(f"Error processing directory {directory}: {e}")
            result['error'] = str(e)
            return result

    def merge_duplicates(self, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Merge duplicate and similar text files.

        Args:
            output_dir (Optional[Path]): Directory to save merged files.

        Returns:
            Dict[str, Any]: Merge results.
        """
        result: Dict[str, Any] = {
            'merged_files': [],
            'errors': [],
            'total_merged': 0
        }
        try:
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            for hash_value, duplicate_files in self.exact_duplicates.items():
                if len(duplicate_files) > 1:
                    try:
                        merged_path = self._merge_exact_duplicates(duplicate_files, output_dir)
                        if merged_path:
                            result['merged_files'].append(str(merged_path))
                            result['total_merged'] += 1
                    except Exception as e:
                        error = {'files': [f['original_path'] for f in duplicate_files], 'error': str(e)}
                        result['errors'].append(error)
                        logger.error(f"Error merging exact duplicates: {e}")
            for similar_group in self.similar_groups:
                if len(similar_group) > 1:
                    try:
                        merged_path = self._merge_similar_files(similar_group, output_dir)
                        if merged_path:
                            result['merged_files'].append(str(merged_path))
                            result['total_merged'] += 1
                    except Exception as e:
                        error = {'files': [f['original_path'] for f in similar_group], 'error': str(e)}
                        result['errors'].append(error)
                        logger.error(f"Error merging similar files: {e}")
            return result
        except Exception as e:
            logger.error(f"Error merging files: {e}")
            result['error'] = str(e)
            return result

    def _load_text_files(self, directory: Path, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Load all text files from a directory.

        Args:
            directory (Path): Directory to scan.
            recursive (bool): Whether to scan subdirectories.

        Returns:
            List[Dict[str, Any]]: List of processed text file results.
        """
        files: List[Dict[str, Any]] = []
        def process_file(file_path: Path) -> None:
            if file_path.suffix.lower() in self.supported_extensions:
                file_result = self.process(file_path, cache={})
                if file_result and not file_result.get('error'):
                    files.append(file_result)
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for filename in filenames:
                    process_file(Path(root) / filename)
        else:
            for item in directory.iterdir():
                if item.is_file():
                    process_file(item)
        return files

    def _find_similar_files(self, files: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Find groups of files with similar text content.

        Args:
            files (List[Dict[str, Any]]): List of processed text files.

        Returns:
            List[List[Dict[str, Any]]]: Groups of similar files.
        """
        similar_groups: List[List[Dict[str, Any]]] = []
        processed = set()
        for i, file1 in enumerate(files):
            if file1['original_path'] in processed:
                continue
            current_group = [file1]
            processed.add(file1['original_path'])
            for j, file2 in enumerate(files):
                if i == j or file2['original_path'] in processed:
                    continue
                similarity = self._calculate_similarity(file1, file2)
                if similarity >= self.similarity_threshold:
                    current_group.append(file2)
                    processed.add(file2['original_path'])
            if len(current_group) > 1:
                similar_groups.append(current_group)
        return similar_groups

    def _calculate_similarity(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two text files based on lines, paragraphs, and words.

        Args:
            file1 (Dict[str, Any]): Processed result for file 1.
            file2 (Dict[str, Any]): Processed result for file 2.

        Returns:
            float: Similarity ratio.
        """
        if file1['hash'] == file2['hash']:
            return 1.0
        lines1 = file1['content'].splitlines()
        lines2 = file2['content'].splitlines()
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        line_similarity = matcher.ratio()
        paragraph_matches = 0
        for p1 in file1['paragraphs']:
            for p2 in file2['paragraphs']:
                para_matcher = difflib.SequenceMatcher(None, p1, p2)
                if para_matcher.ratio() > 0.8:
                    paragraph_matches += 1
                    break
        max_paragraphs = max(len(file1['paragraphs']), len(file2['paragraphs']))
        paragraph_similarity = paragraph_matches / max_paragraphs if max_paragraphs > 0 else 0
        words1 = set(re.findall(r'\b\w+\b', file1['content'].lower()))
        words2 = set(re.findall(r'\b\w+\b', file2['content'].lower()))
        word_similarity = len(words1.intersection(words2)) / max(len(words1), len(words2)) if words1 and words2 else 0
        return (line_similarity * 0.5) + (paragraph_similarity * 0.3) + (word_similarity * 0.2)

    def _merge_exact_duplicates(self, files: List[Dict[str, Any]], output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Merge exact duplicate text files into a single file.

        Args:
            files (List[Dict[str, Any]]): List of duplicate file results.
            output_dir (Optional[Path]): Directory where merged file will be saved.

        Returns:
            Optional[Path]: Path to the merged file.
        """
        if not files or len(files) < 2:
            return None
        try:
            sorted_files = sorted(files, key=lambda f: os.path.getmtime(f['original_path']), reverse=True)
            newest_file = sorted_files[0]
            base_names = [Path(f['original_path']).stem for f in sorted_files]
            merged_name = f"merged_{'_'.join(base_names[:3])}"
            if len(base_names) > 3:
                merged_name += f"_and_{len(base_names)-3}_more"
            merged_name += Path(newest_file['original_path']).suffix
            output_path = output_dir / merged_name if output_dir else Path(newest_file['original_path']).parent / merged_name
            content_lines = [
                f"# Merged from {len(files)} duplicate files\n",
                "## Source Files\n"
            ]
            for file in sorted_files:
                rel_path = os.path.relpath(file['original_path'], Path(sorted_files[0]['original_path']).parent)
                modified_time = datetime.fromtimestamp(os.path.getmtime(file['original_path'])).strftime('%Y-%m-%d %H:%M:%S')
                content_lines.append(f"* {rel_path} (Last modified: {modified_time})")
            content_lines.extend(["\n---\n", newest_file['content']])
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(content_lines))
            return output_path
        except Exception as e:
            logger.error(f"Error merging exact duplicates: {e}")
            return None

    def _merge_similar_files(self, files: List[Dict[str, Any]], output_dir: Optional[Path] = None) -> Optional[Path]:
        """
        Merge similar text files into a single markdown file.

        Args:
            files (List[Dict[str, Any]]): List of similar file results.
            output_dir (Optional[Path]): Directory where merged file will be saved.

        Returns:
            Optional[Path]: Path to the merged file.
        """
        if not files or len(files) < 2:
            return None
        try:
            base_names = [Path(f['original_path']).stem for f in files]
            merged_name = f"similar_{'_'.join(base_names[:3])}"
            if len(base_names) > 3:
                merged_name += f"_and_{len(base_names)-3}_more"
            merged_name += ".md"
            output_path = output_dir / merged_name if output_dir else Path(files[0]['original_path']).parent / merged_name
            content = self._generate_merged_content(files)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return output_path
        except Exception as e:
            logger.error(f"Error merging similar files: {e}")
            return None

    def _generate_merged_content(self, files: List[Dict[str, Any]]) -> str:
        """
        Generate merged content from similar text files.

        Args:
            files (List[Dict[str, Any]]): List of file results.

        Returns:
            str: Merged file content.
        """
        content = [
            f"# Merged content from {len(files)} similar files\n",
            "## Source Files\n"
        ]
        for file in sorted(files, key=lambda f: os.path.getmtime(f['original_path']), reverse=True):
            modified_time = datetime.fromtimestamp(os.path.getmtime(file['original_path'])).strftime('%Y-%m-%d %H:%M:%S')
            content.append(f"* {Path(file['original_path']).name} (Last modified: {modified_time})")
        content.append("\n---\n")
        common_paragraphs = self._find_common_paragraphs(files)
        content.extend([
            "## Common Content\n",
            "\n".join(common_paragraphs) if common_paragraphs else "*No significant common content was found.*"
        ])
        content.append("\n---\n")
        content.append("## Unique Content\n")
        for file in files:
            unique_content = "\n".join(self._find_unique_paragraphs(file, common_paragraphs))
            content.append(f"### From {Path(file['original_path']).name}\n{unique_content or '*No unique content in this file.*'}\n---\n")
        return "\n".join(content)

    def _find_common_paragraphs(self, files: List[Dict[str, Any]]) -> List[str]:
        """
        Find paragraphs that are common across all files.

        Args:
            files (List[Dict[str, Any]]): List of file results.

        Returns:
            List[str]: List of common paragraphs.
        """
        if not files:
            return []
        reference_file = files[0]
        common_paragraphs = []
        for paragraph in reference_file['paragraphs']:
            is_common = True
            for other in files[1:]:
                if not any(difflib.SequenceMatcher(None, paragraph, p).ratio() > 0.8 for p in other['paragraphs']):
                    is_common = False
                    break
            if is_common and len(paragraph.split()) > 5:
                common_paragraphs.append(paragraph)
        return common_paragraphs

    def _find_unique_paragraphs(self, file: Dict[str, Any], common_paragraphs: List[str]) -> List[str]:
        """
        Find paragraphs in a file that are not common.

        Args:
            file (Dict[str, Any]): File result.
            common_paragraphs (List[str]): List of common paragraphs.

        Returns:
            List[str]: Unique paragraphs.
        """
        unique_paragraphs = []
        for paragraph in file['paragraphs']:
            if not any(difflib.SequenceMatcher(None, paragraph, common).ratio() > 0.8 for common in common_paragraphs):
                if len(paragraph.split()) > 5:
                    unique_paragraphs.append(paragraph)
        return unique_paragraphs

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Args:
            text (str): The text to split.

        Returns:
            List[str]: A list of paragraphs.
        """
        raw_paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in raw_paragraphs if p.strip()]

    def _calculate_hash(self, text: str) -> str:
        """
        Calculate hash for normalized text content.

        Args:
            text (str): Text content.

        Returns:
            str: MD5 hash of normalized text.
        """
        normalized = re.sub(r'\s+', ' ', text.lower())
        normalized = re.sub(r'[#*_`\[\]\(\)\{\}]', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def main() -> None:
    # Interactive CLI to select deduplication mode and folder
    while True:
        print("\n=== Deduplication CLI ===")
        print("Select the operation to perform:")
        print("1. Deduplicate Images")
        print("2. Deduplicate General Files")
        print("3. Deduplicate and Merge Text Files")
        print("4. Exit")
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '4':
            print("Exiting. Goodbye!")
            break
        
        folder = input("Enter the path to the folder: ").strip()
        if not folder:
            print("Folder path cannot be empty. Please try again.")
            continue
        folder_path = Path(folder)
        if not folder_path.is_dir():
            print(f"Invalid directory: {folder}")
            continue

        if choice == '1':
            dedupe_images(folder)
        elif choice == '2':
            processor = DedupeProcessor()
            cache: Dict[str, Any] = {}
            result = processor.process_directory(folder, recursive=False)
            print("\n=== File Deduplication Result ===")
            print(result)
            if result.get("duplicate_groups"):
                confirm = input("\nDo you want to delete these duplicate files? [y/N]: ").strip().lower()
                if confirm == 'y':
                    duplicates = {group['key']: [Path(f) for f in group['files']] for group in result["duplicate_groups"]}
                    deletion_result = processor.delete_duplicates(duplicates)
                    print("\nDeletion Result:")
                    print(deletion_result)
                else:
                    print("No files were deleted.")
            else:
                print("No duplicate general files found.")
        elif choice == '3':
            processor = TextDedupeProcessor()
            cache: Dict[str, Any] = {}
            result = processor.process_directory(folder, recursive=True)
            print("\n=== Text Deduplication Result ===")
            print(result)
            merge_confirm = input("\nDo you want to merge duplicates? [y/N]: ").strip().lower()
            if merge_confirm == 'y':
                output_dir = input("Enter output directory for merged files (leave blank for default): ").strip()
                output_path = Path(output_dir) if output_dir else None
                merge_result = processor.merge_duplicates(output_path)
                print("\nMerge Result:")
                print(merge_result)
            else:
                print("No files were merged.")
        else:
            print("Invalid selection. Please choose a valid option.")

if __name__ == "__main__":
    main()