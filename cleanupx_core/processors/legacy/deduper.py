#!/usr/bin/env python3
"""
File Purpose: Legacy deduplication processor for cleanupx
Primary Functions/Classes: 
- DedupeProcessor: Main file deduplication processor
- TextDedupeProcessor: Text file similarity and merging processor
- detect_duplicates(): Find duplicate files by hash and size
- dedupe_images(): Image-specific deduplication

Inputs and Outputs (I/O):
- Input: Directory paths, file paths, configuration options
- Output: Duplicate file reports, processed file metadata, deletion/merge results

This script deduplicates images in a folder based on file size and resolution and extends functionality 
to deduplicate general files and merge similar text files. The deduplication strategies are:
  - Images: Uses file size and resolution.
  - General files: Uses file size and SHA-256 hashing.
  - Text files: Uses content similarity (lines, paragraphs, and word overlap) and merges similar files.
  
It provides an interactive CLI for selecting the deduplication operation, enabling deletion
and merging of duplicate files. The tool leverages robust logging and error handling practices 
to ensure reliable operation.

Usage:
    Run the script and follow the interactive prompts.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}

def get_image_info(file_path: Path) -> Tuple[Optional[int], Optional[Tuple[int, int]]]:
    try:
        file_size = file_path.stat().st_size
    except Exception as e:
        print(f"Error getting file size for {file_path}: {e}")
        return None, None
    try:
        with Image.open(file_path) as img:
            resolution = img.size
    except Exception as e:
        print(f"Error opening image {file_path}: {e}")
        resolution = None
    return file_size, resolution

def dedupe_images(folder_path: str) -> None:
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"{folder_path} is not a valid directory.")
        return
    images = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    if not images:
        print("No images found in the folder.")
        return
    image_dict: Dict[Tuple[int, Tuple[int, int]], List[Path]] = {}
    for img in images:
        file_size, resolution = get_image_info(img)
        if file_size is None or resolution is None:
            continue
        key = (file_size, resolution)
        image_dict.setdefault(key, []).append(img)
    duplicates: List[Path] = []
    for key, file_list in image_dict.items():
        if len(file_list) > 1:
            original = file_list[0]
            dupes = file_list[1:]
            print(f"\nFound duplicates for '{original.name}' (size: {key[0]} bytes, resolution: {key[1][0]}x{key[1][1]}):")
            for dup in dupes:
                print(f"  - {dup.name}")
            duplicates.extend(dupes)
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

def get_file_hash(file_path: Path, block_size: int = 65536) -> Optional[str]:
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
            continue
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

class BaseProcessor:
    def __init__(self):
        pass

class DedupeProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.supported_extensions: Set[str] = set()
        self.max_size_mb: float = 1000.0

    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict[str, Any]:
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
    TEXT_EXTENSIONS: Set[str] = {
        '.txt', '.md', '.markdown', '.rst', '.log', '.csv', '.json', '.xml',
        '.yml', '.yaml', '.html', '.htm', '.css', '.conf', '.ini', '.cfg'
    }
    def __init__(self):
        super().__init__()
        self.supported_extensions: Set[str] = self.TEXT_EXTENSIONS
        self.max_size_mb: float = 10.0
        self.similarity_threshold: float = 0.7
        self.exact_duplicates: Dict[str, List[Any]] = defaultdict(list)
        self.similar_groups: List[List[Any]] = []

    def process(self, file_path: Union[str, Path], cache: Dict[str, Any], rename_log: Optional[Dict] = None) -> Dict[str, Any]:
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
            return result
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
            result['error'] = str(e)
            return result

    def process_directory(self, directory: Union[str, Path], recursive: bool = False) -> Dict[str, Any]:
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
        unique_paragraphs = []
        for paragraph in file['paragraphs']:
            if not any(difflib.SequenceMatcher(None, paragraph, common).ratio() > 0.8 for common in common_paragraphs):
                if len(paragraph.split()) > 5:
                    unique_paragraphs.append(paragraph)
        return unique_paragraphs

    def _split_into_paragraphs(self, text: str) -> List[str]:
        raw_paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in raw_paragraphs if p.strip()]

    def _calculate_hash(self, text: str) -> str:
        normalized = re.sub(r'\s+', ' ', text.lower())
        normalized = re.sub(r'[#*_`\[\]\(\)\{\}]', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def main() -> None:
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