#!/usr/bin/env python3
"""
Smart Document Merging processor for CleanupX.

This module provides functionality to intelligently merge similar documents,
deduplicate content, and create definitive versions of snippets.
"""

import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union, Any
import hashlib
import difflib

from cleanupx.config import TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file, strip_media_suffixes, clean_filename
from cleanupx.utils.cache import save_cache, load_cache, get_cache_path
from cleanupx.api import call_xai_api
from cleanupx.processors.document import extract_text_from_pdf, extract_text_from_docx

# Configure logging
logger = logging.getLogger(__name__)

# Similarity threshold for considering documents similar enough to merge
DEFAULT_SIMILARITY_THRESHOLD = 0.75

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity ratio between two text documents.
    
    Args:
        text1: First text content
        text2: Second text content
        
    Returns:
        Similarity ratio between 0 and 1
    """
    # Normalize text by removing extra whitespace, making lowercase
    def normalize(text):
        return re.sub(r'\s+', ' ', text.lower()).strip()
    
    norm_text1 = normalize(text1)
    norm_text2 = normalize(text2)
    
    # Use difflib sequence matcher to calculate similarity
    matcher = difflib.SequenceMatcher(None, norm_text1, norm_text2)
    return matcher.ratio()

def extract_document_text(file_path: Path) -> str:
    """
    Extract text content from a document file.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Extracted text content
    """
    suffix = file_path.suffix.lower()
    text = ""
    
    try:
        # Handle different file types
        if suffix in ['.pdf']:
            text = extract_text_from_pdf(file_path)
        elif suffix in ['.docx', '.doc']:
            text = extract_text_from_docx(file_path)
        elif suffix in TEXT_EXTENSIONS:
            text = read_text_file(file_path)
        else:
            # Try to read as text for unknown formats
            text = read_text_file(file_path)
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        text = file_path.stem  # Fallback to filename
    
    return text

def find_similar_documents(directory: Path, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD, 
                          recursive: bool = False) -> Dict[str, List[Tuple[Path, str]]]:
    """
    Find groups of similar documents in a directory.
    
    Args:
        directory: Directory to scan for similar documents
        similarity_threshold: Threshold for considering documents similar (0-1)
        recursive: Whether to scan subdirectories
        
    Returns:
        Dictionary mapping group IDs to lists of (path, text) tuples
    """
    # Get all document files
    all_files = []
    if recursive:
        for ext in TEXT_EXTENSIONS + DOCUMENT_EXTENSIONS:
            all_files.extend(directory.glob(f"**/*{ext}"))
    else:
        for ext in TEXT_EXTENSIONS + DOCUMENT_EXTENSIONS:
            all_files.extend(directory.glob(f"*{ext}"))
    
    logger.info(f"Found {len(all_files)} documents to analyze in {directory}")
    
    # Extract text and signatures
    file_data = []
    for file_path in all_files:
        try:
            logger.info(f"Extracting text from {file_path}")
            text = extract_document_text(file_path)
            # Only process if we got meaningful text
            if len(text.strip()) > 10:
                file_data.append((file_path, text))
            else:
                logger.warning(f"Skipping {file_path} due to insufficient text content")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    # Group similar documents
    similar_groups = {}
    processed_files = set()
    group_id = 0
    
    for i, (file_path1, text1) in enumerate(file_data):
        if file_path1 in processed_files:
            continue
            
        # Start a new group
        current_group = [(file_path1, text1)]
        processed_files.add(file_path1)
        
        # Find similar documents
        for j, (file_path2, text2) in enumerate(file_data):
            if i == j or file_path2 in processed_files:
                continue
                
            # Check similarity
            similarity = calculate_similarity(text1, text2)
            if similarity >= similarity_threshold:
                current_group.append((file_path2, text2))
                processed_files.add(file_path2)
        
        # Only add groups with multiple documents
        if len(current_group) > 1:
            similar_groups[f"group_{group_id}"] = current_group
            group_id += 1
    
    logger.info(f"Found {len(similar_groups)} groups of similar documents")
    return similar_groups

def merge_document_group(group: List[Tuple[Path, str]], output_dir: Path, 
                        group_name: str) -> Tuple[Path, List[Path]]:
    """
    Merge a group of similar documents into a definitive version.
    
    Args:
        group: List of (path, text) tuples for similar documents
        output_dir: Directory to save the merged document
        group_name: Name of the document group
        
    Returns:
        Tuple of (path to merged document, list of source document paths)
    """
    files = [p for p, _ in group]
    texts = [t for _, t in group]
    
    # Determine the best document to use as base
    best_idx = select_best_document(files, texts)
    best_file = files[best_idx]
    best_text = texts[best_idx]
    
    # Create a prompt for the language model to merge the documents
    prompt = f"""
I need to merge these {len(group)} similar documents into one definitive version. 
The files are different versions or snippets of the same content.

Here are the document contents:

{'-' * 40}
BASE DOCUMENT: {best_file.name}
{'-' * 40}
{best_text[:5000] if len(best_text) > 5000 else best_text}
{'-' * 40}

"""
    
    # Add other documents
    for i, (file_path, text) in enumerate(group):
        if i != best_idx:
            prompt += f"""
ALTERNATIVE VERSION: {file_path.name}
{'-' * 40}
{text[:5000] if len(text) > 5000 else text}
{'-' * 40}
"""
    
    prompt += """
Create a merged version that:
1. Keeps the most complete and accurate information
2. Removes redundancies
3. Combines unique information from each document
4. Maintains a coherent structure
5. Prioritizes newer information when there are conflicts

Just provide the final merged content. Do not include explanations or document names in your response.
"""
    
    # Call the language model to merge the documents
    try:
        merged_text = call_xai_api(prompt, model=XAI_MODEL_TEXT, max_tokens=8000)
    except Exception as e:
        logger.error(f"Error calling language model API: {e}")
        # Fallback to best document if API call fails
        merged_text = best_text
        logger.info(f"Using best document as fallback due to API error")
    
    # Determine output file extension (use the extension of the best file)
    output_ext = best_file.suffix
    
    # Create a meaningful name for the merged file
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"merged_{group_name}_{timestamp}{output_ext}"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the merged content
    try:
        # For text-based files, we can write directly
        if output_ext in TEXT_EXTENSIONS:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(merged_text)
        else:
            # For binary formats, copy the best file and add a note about the merge
            shutil.copy2(best_file, output_file)
            
            # Create an accompanying text file with notes
            notes_file = output_file.with_suffix('.merge_notes.txt')
            with open(notes_file, 'w', encoding='utf-8') as f:
                f.write(f"MERGED DOCUMENT NOTES\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Base document: {best_file}\n\n")
                f.write(f"Merged from:\n")
                for file_path, _ in group:
                    f.write(f"- {file_path}\n")
                f.write("\nNote: For non-text formats, the base document was used with notes about the merge.")
    except Exception as e:
        logger.error(f"Error saving merged document: {e}")
        return None, files
    
    logger.info(f"Created merged document at {output_file}")
    return output_file, files

def select_best_document(files: List[Path], texts: List[str]) -> int:
    """
    Select the best document to use as a base for merging.
    
    Args:
        files: List of file paths
        texts: List of document texts
        
    Returns:
        Index of the best document
    """
    scores = []
    
    for i, (file_path, text) in enumerate(zip(files, texts)):
        score = 0
        
        # Prefer longer documents (more comprehensive)
        score += len(text) / 1000  # Length factor
        
        # Prefer newer files
        try:
            mtime = file_path.stat().st_mtime
            age_days = (datetime.now().timestamp() - mtime) / (60 * 60 * 24)
            score += 10 * (1 / (1 + age_days))  # Higher score for newer files
        except Exception:
            pass
        
        # Prefer more structured documents (with headings, sections)
        heading_patterns = [
            r'^#{1,6}\s+\w+',  # Markdown headings
            r'^[A-Z][A-Za-z\s]+:',  # Title-like lines
            r'^\d+\.\s+\w+',  # Numbered sections
        ]
        
        for pattern in heading_patterns:
            score += 5 * len(re.findall(pattern, text, re.MULTILINE))
        
        # Prefer documents with links, citations (more reference value)
        score += 2 * len(re.findall(r'\[.*?\]\(.*?\)', text))  # Markdown links
        score += 2 * len(re.findall(r'https?://\S+', text))  # Raw URLs
        
        scores.append(score)
    
    # Return index of document with highest score
    return scores.index(max(scores))

def archive_source_documents(files: List[Path], archive_dir: Path) -> bool:
    """
    Archive the source documents after merging.
    
    Args:
        files: List of file paths to archive
        archive_dir: Directory to move the files to
        
    Returns:
        True if successful, False if errors occurred
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    success = True
    
    for file_path in files:
        try:
            # Create a unique name in case of filename collisions
            dest_file = archive_dir / file_path.name
            if dest_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                dest_file = archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
            
            # Move the file
            shutil.move(str(file_path), str(dest_file))
            logger.info(f"Archived {file_path} to {dest_file}")
        except Exception as e:
            logger.error(f"Error archiving {file_path}: {e}")
            success = False
    
    return success

def smart_merge_documents(directory: Path, output_dir: Optional[Path] = None, 
                         similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
                         archive_dir: Optional[Path] = None,
                         recursive: bool = False) -> Dict[str, Any]:
    """
    Intelligently merge similar documents in a directory.
    
    Args:
        directory: Directory containing documents to merge
        output_dir: Directory to save merged documents (defaults to directory/merged)
        similarity_threshold: Threshold for considering documents similar (0-1)
        archive_dir: Directory to move source documents to after merging
        recursive: Whether to scan subdirectories
        
    Returns:
        Dictionary with merge results
    """
    directory = Path(directory)
    
    # Set default output directory if not specified
    if output_dir is None:
        output_dir = directory / "merged"
    else:
        output_dir = Path(output_dir)
    
    # Set default archive directory if not specified
    if archive_dir is None:
        archive_dir = directory / "archived"
    else:
        archive_dir = Path(archive_dir)
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        "merged_groups": 0,
        "merged_files": [],
        "archived_files": [],
        "total_files": 0,
        "error_files": []
    }
    
    try:
        # Find similar document groups
        similar_groups = find_similar_documents(directory, similarity_threshold, recursive)
        results["total_groups"] = len(similar_groups)
        
        # Process each group
        for group_id, group in similar_groups.items():
            try:
                logger.info(f"Processing group {group_id} with {len(group)} documents")
                
                # Merge the documents
                merged_file, source_files = merge_document_group(
                    group, 
                    output_dir, 
                    group_id
                )
                
                if merged_file:
                    results["merged_files"].append(str(merged_file))
                    results["merged_groups"] += 1
                    
                    # Archive source documents
                    if archive_source_documents(source_files, archive_dir):
                        results["archived_files"].extend([str(f) for f in source_files])
                    
                    results["total_files"] += len(source_files)
            except Exception as e:
                logger.error(f"Error processing group {group_id}: {e}")
                results["error_files"].extend([str(f) for f, _ in group])
    
    except Exception as e:
        logger.error(f"Error in smart_merge_documents: {e}")
    
    logger.info(f"Smart merge complete: {results['merged_groups']} groups merged, "
               f"{len(results['merged_files'])} merged files created")
    return results 