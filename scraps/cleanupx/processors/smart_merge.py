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
import ast

from cleanupx.config import TEXT_EXTENSIONS, DOCUMENT_EXTENSIONS, XAI_MODEL_TEXT
from cleanupx.utils.common import read_text_file, strip_media_suffixes, clean_filename
from cleanupx.utils.cache import save_cache, load_cache, get_cache_path, _CACHE_CONFIG
from cleanupx.api import call_xai_api
from cleanupx.processors.document import extract_text_from_pdf, extract_text_from_docx

# Configure logging
logger = logging.getLogger(__name__)

# Similarity threshold for considering documents similar enough to merge
DEFAULT_SIMILARITY_THRESHOLD = 0.75

# Maximum tokens per batch for LLM processing
MAX_BATCH_TOKENS = 4000

# Initialize in-memory text cache
_TEXT_CACHE = {}

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity ratio between two text strings.
    
    Args:
        text1: First text string
        text2: Second text string
        
    Returns:
        Similarity ratio between 0 and 1
    """
    # Use difflib's SequenceMatcher to calculate similarity
    matcher = difflib.SequenceMatcher(None, text1, text2)
    return matcher.ratio()

def is_meaningful_code(text: str) -> bool:
    """
    Determine if a code snippet is meaningful enough to keep.
    
    Args:
        text: Code snippet to analyze
        
    Returns:
        True if the snippet is meaningful, False if it's too simple or boilerplate
    """
    # Remove empty or whitespace-only snippets
    if not text.strip():
        return False
        
    # Try to parse as Python code
    try:
        tree = ast.parse(text)
        
        # Count meaningful nodes (excluding imports, simple assignments, etc.)
        meaningful_nodes = 0
        total_nodes = 0
        
        for node in ast.walk(tree):
            total_nodes += 1
            
            # Skip imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
                
            # Skip simple assignments (e.g., VERSION = "1.0.0")
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                if isinstance(node.value, (ast.Str, ast.Num, ast.NameConstant)):
                    continue
            
            # Skip empty __init__ files
            if isinstance(node, ast.Module) and len(node.body) <= 2:
                if all(isinstance(n, (ast.Import, ast.ImportFrom)) for n in node.body):
                    return False
            
            meaningful_nodes += 1
        
        # Require a minimum number of meaningful nodes
        if meaningful_nodes < 3:
            return False
            
        # Require a minimum ratio of meaningful to total nodes
        if meaningful_nodes / total_nodes < 0.3:
            return False
            
    except SyntaxError:
        # If it's not valid Python, check for other meaningful patterns
        lines = text.strip().split('\n')
        
        # Skip if too short
        if len(lines) < 3:
            return False
            
        # Skip if mostly imports or simple assignments
        meaningful_lines = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(('import ', 'from ')):
                continue
            if re.match(r'^[A-Z_]+\s*=\s*["\'].*["\']$', line):
                continue
            meaningful_lines += 1
        
        if meaningful_lines < 3:
            return False
    
    return True

def extract_code_snippets(file_path: Path) -> List[Tuple[str, str]]:
    """
    Extract meaningful code snippets from a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        List of (snippet_name, snippet_text) tuples
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []
    
    snippets = []
    
    # Try to parse as Python code
    try:
        tree = ast.parse(content)
        
        # Extract classes and functions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                snippet_text = ast.get_source_segment(content, node)
                if snippet_text and is_meaningful_code(snippet_text):
                    snippet_name = f"{node.name}"
                    snippets.append((snippet_name, snippet_text))
                    
    except SyntaxError:
        # If not valid Python, try to extract blocks based on indentation
        lines = content.split('\n')
        current_block = []
        current_indent = 0
        
        for line in lines:
            if not line.strip():
                continue
                
            indent = len(line) - len(line.lstrip())
            
            # Start of a new block
            if not current_block or indent > current_indent:
                current_block.append(line)
                current_indent = indent
            # End of current block
            elif indent < current_indent:
                block_text = '\n'.join(current_block)
                if is_meaningful_code(block_text):
                    # Try to extract a meaningful name from the first line
                    first_line = current_block[0].strip()
                    name_match = re.search(r'(?:def|class|function)\s+(\w+)', first_line)
                    name = name_match.group(1) if name_match else "snippet"
                    snippets.append((name, block_text))
                current_block = [line]
                current_indent = indent
            # Continue current block
            else:
                current_block.append(line)
    
    return snippets

def find_similar_snippets(directory: Path, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> Dict[str, List[Tuple[str, str, Path]]]:
    """
    Find groups of similar code snippets in a directory.
    
    Args:
        directory: Directory to scan for snippets
        similarity_threshold: Threshold for considering snippets similar
        
    Returns:
        Dictionary mapping group IDs to lists of (name, text, source_file) tuples
    """
    # Get all Python and text files
    all_files = []
    for ext in ['.py', '.python', '.txt']:
        all_files.extend(directory.glob(f"**/*{ext}"))
    
    logger.info(f"Found {len(all_files)} files to analyze in {directory}")
    
    # Extract snippets from all files
    all_snippets = []
    for file_path in all_files:
        try:
            snippets = extract_code_snippets(file_path)
            for name, text in snippets:
                all_snippets.append((name, text, file_path))
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    logger.info(f"Extracted {len(all_snippets)} meaningful code snippets")
    
    # Group similar snippets
    similar_groups = {}
    processed_snippets = set()
    group_id = 0
    
    for i, (name1, text1, file1) in enumerate(all_snippets):
        if i in processed_snippets:
            continue
            
        # Start a new group
        current_group = [(name1, text1, file1)]
        processed_snippets.add(i)
        
        # Find similar snippets
        for j, (name2, text2, file2) in enumerate(all_snippets):
            if i == j or j in processed_snippets:
                continue
                
            # Check similarity
            similarity = calculate_similarity(text1, text2)
            if similarity >= similarity_threshold:
                current_group.append((name2, text2, file2))
                processed_snippets.add(j)
        
        # Only add groups with multiple snippets
        if len(current_group) > 1:
            similar_groups[f"group_{group_id}"] = current_group
            group_id += 1
    
    logger.info(f"Found {len(similar_groups)} groups of similar snippets")
    return similar_groups

def merge_snippet_group(group: List[Tuple[str, str, Path]], output_dir: Path, 
                       group_name: str) -> Tuple[Path, List[Path]]:
    """
    Merge a group of similar code snippets into a definitive version.
    
    Args:
        group: List of (name, text, source_file) tuples for similar snippets
        output_dir: Directory to save the merged snippet
        group_name: Name of the snippet group
        
    Returns:
        Tuple of (path to merged snippet, list of source files)
    """
    names = [n for n, _, _ in group]
    texts = [t for _, t, _ in group]
    files = [f for _, _, f in group]
    
    # Determine the best snippet to use as base
    best_idx = select_best_snippet(names, texts)
    best_name = names[best_idx]
    best_text = texts[best_idx]
    
    # Create a prompt for the language model to merge the snippets
    prompt = f"""
I need to merge these {len(group)} similar code snippets into one optimized version.
The snippets are different implementations or variations of similar functionality.

Here are the snippets:

{'-' * 40}
BASE SNIPPET: {best_name}
{'-' * 40}
{best_text}
{'-' * 40}

"""
    
    # Add other snippets
    for i, (name, text, _) in enumerate(group):
        if i != best_idx:
            prompt += f"""
ALTERNATIVE VERSION: {name}
{'-' * 40}
{text}
{'-' * 40}
"""
    
    prompt += """
Create a merged version that:
1. Combines the best aspects of each implementation
2. Uses modern and efficient coding practices
3. Includes comprehensive error handling
4. Has clear documentation and type hints
5. Maintains compatibility with all use cases
6. Removes any redundant or unnecessary code

Return ONLY the final merged code. Do not include explanations or snippet names.
"""
    
    # Call the language model to merge the snippets
    try:
        # Create a basic function schema for text generation
        merge_function_schema = {
            "name": "merge_snippets",
            "description": "Merge multiple code snippets into one optimized version",
            "parameters": {
                "type": "object",
                "properties": {
                    "merged_code": {
                        "type": "string",
                        "description": "The merged and optimized code combining the best parts of all snippets"
                    }
                },
                "required": ["merged_code"]
            }
        }
        
        # Call the API
        result = call_xai_api(model=XAI_MODEL_TEXT, prompt=prompt, function_schema=merge_function_schema)
        merged_text = result.get("merged_code", best_text)
    except Exception as e:
        logger.error(f"Error calling language model API: {e}")
        merged_text = best_text
        logger.info(f"Using best snippet as fallback due to API error")
    
    # Create a meaningful name for the merged file
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = output_dir / f"snippet_{clean_filename(best_name)}_{timestamp}.py"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the merged content
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(merged_text)
            
        # Create an accompanying metadata file
        meta_file = output_file.with_suffix('.meta.json')
        import json
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump({
                "name": best_name,
                "group_id": group_name,
                "source_files": [str(f) for f in files],
                "timestamp": datetime.now().isoformat(),
                "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD
            }, f, indent=2)
            
        logger.info(f"Created merged snippet at {output_file}")
    except Exception as e:
        logger.error(f"Error saving merged snippet: {e}")
        return None, files
    
    return output_file, files

def select_best_snippet(names: List[str], texts: List[str]) -> int:
    """
    Select the best snippet to use as a base for merging.
    
    Args:
        names: List of snippet names
        texts: List of snippet texts
        
    Returns:
        Index of the best snippet
    """
    scores = []
    
    for i, (name, text) in enumerate(zip(names, texts)):
        score = 0
        
        # Prefer longer snippets (more comprehensive)
        score += len(text) / 100  # Length factor
        
        # Prefer snippets with docstrings
        if '"""' in text or "'''" in text:
            score += 10
        
        # Prefer snippets with type hints
        if re.search(r':\s*[A-Z][A-Za-z]*[\[\],\s]*', text):
            score += 5
        
        # Prefer snippets with error handling
        if 'try:' in text:
            score += 5
        
        # Prefer snippets with comments
        score += 2 * len(re.findall(r'#.*$', text, re.MULTILINE))
        
        # Prefer descriptive names
        score += len(name.split('_'))
        
        scores.append(score)
    
    # Return index of snippet with highest score
    return scores.index(max(scores))

def merge_code_snippets(
    directory: Path,
    output_dir: Optional[Path] = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    archive_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Find and merge similar code snippets in a directory.
    
    Args:
        directory: Directory containing snippets to merge
        output_dir: Directory to save merged snippets
        similarity_threshold: Threshold for considering snippets similar
        archive_dir: Directory to move source files to after merging
        
    Returns:
        Dictionary with merge results
    """
    directory = Path(directory)
    
    # Set default output directory if not specified
    if output_dir is None:
        output_dir = directory / "merged_snippets"
    else:
        output_dir = Path(output_dir)
    
    # Set default archive directory if not specified
    if archive_dir is None:
        archive_dir = directory / "archived_snippets"
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
        # Find similar snippet groups
        similar_groups = find_similar_snippets(directory, similarity_threshold)
        results["total_groups"] = len(similar_groups)
        
        # Process each group
        for group_id, group in similar_groups.items():
            try:
                logger.info(f"Processing group {group_id} with {len(group)} snippets")
                
                # Merge the snippets
                merged_file, source_files = merge_snippet_group(
                    group, 
                    output_dir, 
                    group_id
                )
                
                if merged_file:
                    results["merged_files"].append(str(merged_file))
                    results["merged_groups"] += 1
                    
                    # Archive source files
                    for file_path in source_files:
                        try:
                            # Create a unique name in case of filename collisions
                            dest_file = archive_dir / file_path.name
                            if dest_file.exists():
                                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                                dest_file = archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
                            
                            # Move the file
                            shutil.move(str(file_path), str(dest_file))
                            results["archived_files"].append(str(dest_file))
                            logger.info(f"Archived {file_path} to {dest_file}")
                        except Exception as e:
                            logger.error(f"Error archiving {file_path}: {e}")
                            results["error_files"].append(str(file_path))
                    
                    results["total_files"] += len(source_files)
            except Exception as e:
                logger.error(f"Error processing group {group_id}: {e}")
                results["error_files"].extend([str(f) for _, _, f in group])
    
    except Exception as e:
        logger.error(f"Error in merge_code_snippets: {e}")
    
    logger.info(f"Code snippet merge complete: {results['merged_groups']} groups merged, "
               f"{len(results['merged_files'])} merged files created")
    return results 