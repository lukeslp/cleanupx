#!/usr/bin/env python3
"""
Snippet Duplicate Finder and Batch Processor

This script finds potential duplicate files using a low similarity threshold,
groups them into batches, and sends them to an LLM assistant to identify
actual duplicates and suggest replacements.
"""

import os
import re
import sys
import json
import difflib
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set a low similarity threshold to catch more potential duplicates
SIMILARITY_THRESHOLD = 0.25

# Maximum number of files to include in a single batch
MAX_BATCH_SIZE = 8  

# Maximum tokens to send in a single batch
MAX_BATCH_TOKENS = 12000

# File extensions to process
VALID_EXTENSIONS = {'.py', '.python', '.js', '.javascript', '.html', '.css', '.txt', '.md'}

def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing whitespace and making lowercase."""
    return re.sub(r'\s+', ' ', text.lower()).strip()

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two text documents."""
    norm_text1 = normalize_text(text1)
    norm_text2 = normalize_text(text2)
    
    # Use difflib sequence matcher to calculate similarity
    matcher = difflib.SequenceMatcher(None, norm_text1, norm_text2)
    return matcher.ratio()

def estimate_tokens(text: str) -> int:
    """Roughly estimate the number of tokens in a text."""
    # A very rough approximation: 4 characters ≈ 1 token
    return len(text) // 4

def read_file_content(file_path: Path) -> str:
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return ""

def find_potential_duplicates(directory: Path) -> Dict[str, List[Tuple[Path, str]]]:
    """
    Find groups of potentially duplicate files using a low similarity threshold.
    
    Args:
        directory: Directory containing files to check
        
    Returns:
        Dictionary mapping group IDs to lists of (path, content) tuples
    """
    # Get all valid files
    all_files = []
    for ext in VALID_EXTENSIONS:
        all_files.extend(directory.glob(f"*{ext}"))
    
    logger.info(f"Found {len(all_files)} files to analyze in {directory}")
    
    # Extract text from files
    file_data = []
    for file_path in all_files:
        try:
            content = read_file_content(file_path)
            if len(content.strip()) > 10:  # Skip empty files
                file_data.append((file_path, content))
            else:
                logger.warning(f"Skipping {file_path} due to insufficient content")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    # Group similar files
    similar_groups = {}
    processed_files = set()
    group_id = 0
    
    for i, (file_path1, content1) in enumerate(file_data):
        if file_path1 in processed_files:
            continue
            
        # Start a new group
        current_group = [(file_path1, content1)]
        processed_files.add(file_path1)
        
        # Find similar files
        for j, (file_path2, content2) in enumerate(file_data):
            if i == j or file_path2 in processed_files:
                continue
                
            # Check similarity
            similarity = calculate_similarity(content1, content2)
            if similarity >= SIMILARITY_THRESHOLD:
                current_group.append((file_path2, content2))
                processed_files.add(file_path2)
        
        # Only add groups with multiple files
        if len(current_group) > 1:
            similar_groups[f"group_{group_id}"] = current_group
            group_id += 1
    
    logger.info(f"Found {len(similar_groups)} groups of potentially similar files")
    return similar_groups

def create_batches(groups: Dict[str, List[Tuple[Path, str]]]) -> List[Dict[str, Any]]:
    """
    Create batches of file groups to send to the LLM assistant.
    
    Args:
        groups: Dictionary of similar file groups
        
    Returns:
        List of batch dictionaries containing file groups
    """
    batches = []
    current_batch = {"groups": {}, "total_tokens": 0, "files": 0}
    
    for group_id, group_files in groups.items():
        # Calculate tokens for this group
        group_content = "\n\n".join([content for _, content in group_files])
        group_tokens = estimate_tokens(group_content)
        group_size = len(group_files)
        
        # Check if we need to start a new batch
        if (current_batch["files"] + group_size > MAX_BATCH_SIZE or
            current_batch["total_tokens"] + group_tokens > MAX_BATCH_TOKENS):
            
            # Only add non-empty batches
            if current_batch["files"] > 0:
                batches.append(current_batch)
                current_batch = {"groups": {}, "total_tokens": 0, "files": 0}
        
        # Add group to current batch
        current_batch["groups"][group_id] = group_files
        current_batch["total_tokens"] += group_tokens
        current_batch["files"] += group_size
    
    # Add the last batch if not empty
    if current_batch["files"] > 0:
        batches.append(current_batch)
    
    logger.info(f"Created {len(batches)} batches of similar files")
    return batches

def process_batch(batch: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """
    Process a batch of similar files using an LLM assistant.
    
    Args:
        batch: Batch dictionary containing file groups
        output_dir: Directory to save output files
        
    Returns:
        Dictionary with processing results
    """
    # Create a prompt for the LLM assistant
    prompt = "I need to identify duplicate code snippets and create consolidated versions.\n\n"
    
    # Add file content to the prompt
    for group_id, group_files in batch["groups"].items():
        prompt += f"## Group {group_id}\n\n"
        
        for i, (file_path, content) in enumerate(group_files):
            content_preview = content[:1000] + "..." if len(content) > 1000 else content
            prompt += f"### File {i+1}: {file_path.name}\n```\n{content_preview}\n```\n\n"
    
    prompt += """
For each group, please:
1. Identify which files are duplicates or near-duplicates
2. Create a single consolidated version that contains the best parts of each file
3. Provide a meaningful name for the consolidated file
4. List which original files should be replaced by the consolidated version

Return your response in the following JSON format:
{
  "groups": [
    {
      "group_id": "group_X",
      "analysis": "Brief analysis of similarities and differences",
      "duplicates": ["file1.py", "file2.py"],
      "consolidated_file": {
        "name": "suggested_filename.py",
        "content": "// Full content of the consolidated file"
      }
    }
  ]
}
"""
    
    # TODO: Here we would call the LLM API
    # For now, we'll simulate by writing the prompt to a file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    prompt_file = output_dir / f"batch_{timestamp}.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    logger.info(f"Batch prompt written to {prompt_file}")
    logger.info(f"To process this batch, send its content to an LLM and parse the JSON response")
    
    # In a real implementation, we would:
    # 1. Call the LLM API
    # 2. Parse the response JSON
    # 3. Create the consolidated files
    # 4. Return results
    
    return {
        "prompt_file": str(prompt_file),
        "batch_size": batch["files"],
        "status": "prompt_generated"
    }

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <snippets_directory> [output_directory]")
        sys.exit(1)
    
    # Parse command line arguments
    snippets_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else snippets_dir / "deduplicated"
    
    # Ensure directories exist
    if not snippets_dir.is_dir():
        print(f"Error: {snippets_dir} is not a valid directory")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find potential duplicates
    similar_groups = find_potential_duplicates(snippets_dir)
    
    # Create batches
    batches = create_batches(similar_groups)
    
    # Process each batch
    results = []
    for i, batch in enumerate(batches):
        logger.info(f"Processing batch {i+1}/{len(batches)}")
        batch_result = process_batch(batch, output_dir)
        results.append(batch_result)
    
    # Save overall results
    results_file = output_dir / "deduplication_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_groups": len(similar_groups),
            "total_batches": len(batches),
            "batch_results": results
        }, f, indent=2)
    
    logger.info(f"Deduplication analysis complete. Results saved to {results_file}")
    logger.info(f"Generated {len(results)} batch prompts. Send these to an LLM for analysis.")

if __name__ == "__main__":
    main() 