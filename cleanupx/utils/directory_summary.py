#!/usr/bin/env python3
"""
Directory summary utilities for CleanupX.

This module provides functionality to generate and maintain hidden summary files
in directories that describe the contents, organization, and potential improvements.
"""

import os
import json
import logging
import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
import hashlib

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    logging.warning("Inquirer not installed. Interactive prompts will use basic input.")

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SUMMARY_FILENAME = ".dir_summary.json"
MAX_SAMPLE_FILES = 20
CONTENT_ANALYSIS_SAMPLE = 5
PROJECT_PLAN_FILE = "PROJECT_PLAN.md"

def get_file_categories(files: List[Path]) -> Dict[str, List[str]]:
    """
    Categorize files by extension and type.
    
    Args:
        files (List[Path]): List of file paths
        
    Returns:
        Dict: Dictionary mapping categories to lists of filenames
    """
    categories = {
        "images": [],
        "videos": [],
        "audio": [],
        "documents": [],
        "archives": [],
        "code": [],
        "data": [],
        "other": []
    }
    
    # Extension mappings
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
    video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v'}
    audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}
    document_exts = {'.pdf', '.doc', '.docx', '.txt', '.md', '.rtf', '.odt', '.ppt', '.pptx'}
    archive_exts = {'.zip', '.tar', '.gz', '.rar', '.7z', '.bz2'}
    code_exts = {'.py', '.js', '.html', '.css', '.c', '.cpp', '.java', '.php', '.rb', '.go', '.rs', '.ts', '.jsx', '.tsx'}
    data_exts = {'.json', '.xml', '.csv', '.xlsx', '.db', '.sql', '.yaml', '.yml'}
    
    for file in files:
        ext = file.suffix.lower()
        name = file.name
        
        if ext in image_exts:
            categories["images"].append(name)
        elif ext in video_exts:
            categories["videos"].append(name)
        elif ext in audio_exts:
            categories["audio"].append(name)
        elif ext in document_exts:
            categories["documents"].append(name)
        elif ext in archive_exts:
            categories["archives"].append(name)
        elif ext in code_exts:
            categories["code"].append(name)
        elif ext in data_exts:
            categories["data"].append(name)
        else:
            categories["other"].append(name)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}

def get_directory_tree(directory: Path, max_depth: int = 2) -> Dict:
    """
    Generate a tree representation of the directory structure.
    
    Args:
        directory (Path): Directory to scan
        max_depth (int): Maximum depth to traverse
        
    Returns:
        Dict: Tree representation of the directory structure
    """
    def _get_tree(path: Path, current_depth: int) -> Dict:
        if current_depth > max_depth:
            return {"type": "directory", "children": "..."}
        
        if path.is_file():
            return {"type": "file", "name": path.name}
        
        result = {"type": "directory", "name": path.name, "children": []}
        try:
            for item in path.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files/directories
                result["children"].append(_get_tree(item, current_depth + 1))
        except PermissionError:
            result["children"] = "permission denied"
        except Exception as e:
            result["children"] = f"error: {str(e)}"
            
        return result
    
    return _get_tree(directory, 0)

def parse_project_plan(file_path: Path) -> Dict[str, Any]:
    """
    Parse a PROJECT_PLAN.md file to extract information about the project's structure and organization.
    
    Args:
        file_path (Path): Path to the PROJECT_PLAN.md file
        
    Returns:
        Dict: Extracted organization information from the project plan
    """
    if not file_path.exists():
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Extract key information from PROJECT_PLAN.md
        project_info = {
            "title": None,
            "description": None,
            "structure": [],
            "categories": [],
            "naming_conventions": [],
            "keywords": []
        }
        
        # Try to extract project title (usually the first heading)
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if title_match:
            project_info["title"] = title_match.group(1).strip()
        
        # Try to extract description (text following the title heading)
        desc_match = re.search(r'^#\s+.+?\n\n(.*?)(?=\n#|\Z)', content, re.MULTILINE | re.DOTALL)
        if desc_match:
            project_info["description"] = desc_match.group(1).strip()
        
        # Look for structure information (often in a "Structure" or "Organization" section)
        structure_section = re.search(r'## (?:Project )?(?:Structure|Organization).*?\n(.*?)(?=\n##|\Z)', 
                                     content, re.MULTILINE | re.DOTALL)
        if structure_section:
            # Look for potential directory listings
            dir_items = re.findall(r'[-*]\s+`?([^`\n]+)`?', structure_section.group(1))
            project_info["structure"] = [item.strip() for item in dir_items]
        
        # Look for category information
        categories_section = re.search(r'## (?:Categories|File Types|Content).*?\n(.*?)(?=\n##|\Z)', 
                                      content, re.MULTILINE | re.DOTALL)
        if categories_section:
            category_items = re.findall(r'[-*]\s+`?([^`\n]+)`?', categories_section.group(1))
            project_info["categories"] = [item.strip() for item in category_items]
        
        # Look for naming conventions
        naming_section = re.search(r'## (?:Naming|Naming Conventions|File Naming).*?\n(.*?)(?=\n##|\Z)',
                                 content, re.MULTILINE | re.DOTALL)
        if naming_section:
            naming_items = re.findall(r'[-*]\s+(.+)', naming_section.group(1))
            project_info["naming_conventions"] = [item.strip() for item in naming_items]
        
        # Extract potential keywords from the entire document
        keywords = set()
        # Find words in headings (likely important concepts)
        for heading in re.findall(r'##?\s+(.+)$', content, re.MULTILINE):
            words = re.findall(r'\b\w{4,}\b', heading.lower())
            keywords.update(words)
        
        project_info["keywords"] = list(keywords)
        
        return project_info
    
    except Exception as e:
        logger.error(f"Error parsing PROJECT_PLAN.md: {e}")
        return {}

def analyze_directory_content(directory: Path) -> Dict:
    """
    Analyze the content of files in a directory to identify common themes.
    
    Args:
        directory (Path): Directory to analyze
        
    Returns:
        Dict: Analysis results
    """
    files = [f for f in directory.iterdir() if f.is_file() and not f.name.startswith('.')]
    
    if not files:
        return {"themes": [], "patterns": [], "keywords": []}
    
    # Sample files for content analysis
    sample_files = files[:min(CONTENT_ANALYSIS_SAMPLE, len(files))]
    
    # Extract text content from sample files (if possible)
    content_samples = []
    for file in sample_files:
        ext = file.suffix.lower()
        if ext in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.py', '.js', '.css'}:
            try:
                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read(8192)  # Read only the first 8KB
                    content_samples.append((file.name, content))
            except Exception as e:
                logger.warning(f"Could not read {file}: {e}")
    
    # For now, just return a basic analysis based on filenames
    # In a more advanced version, this could use NLP to extract themes
    keywords = set()
    for file in files:
        words = file.stem.replace('_', ' ').replace('-', ' ').lower().split()
        keywords.update(w for w in words if len(w) > 3)
    
    # Check for PROJECT_PLAN.md and incorporate its keywords if available
    project_plan_path = directory / PROJECT_PLAN_FILE
    project_info = {}
    if project_plan_path.exists():
        project_info = parse_project_plan(project_plan_path)
        if project_info:
            # Add any keywords from the project plan
            keywords.update(project_info.get("keywords", []))
    
    return {
        "themes": [],  # Would require more advanced analysis
        "patterns": [],  # Would require more advanced analysis
        "keywords": sorted(list(keywords)[:20])  # Limit to top 20 keywords
    }

def prompt_for_organization_preferences(directory: Path) -> Dict[str, Any]:
    """
    Prompt the user for their organization preferences for this directory.
    
    Args:
        directory (Path): Directory to organize
        
    Returns:
        Dict: User's organization preferences
    """
    print(f"\n--- Organization Preferences for {directory} ---")
    print("Please provide information to help organize this directory better.")
    
    preferences = {}
    
    if INQUIRER_AVAILABLE:
        # Use inquirer for a more user-friendly experience
        questions = [
            inquirer.Text('purpose', message="What is the main purpose of this directory?"),
            inquirer.Checkbox('categories',
                             message="Which categories of files do you expect in this directory?",
                             choices=['images', 'videos', 'audio', 'documents', 'code', 'data', 'archives', 'other']),
            inquirer.Text('naming', message="Do you have a preferred naming convention for files?"),
            inquirer.Confirm('create_subdirs', 
                           message="Should similar files be organized into subdirectories?",
                           default=True),
            inquirer.Confirm('deduplicate',
                           message="Do you want to find and remove duplicate files?",
                           default=True)
        ]
        
        answers = inquirer.prompt(questions)
        preferences.update(answers)
        
    else:
        # Fallback to basic input
        preferences['purpose'] = input("What is the main purpose of this directory? ")
        
        print("\nWhich categories of files do you expect in this directory?")
        categories = []
        for cat in ['images', 'videos', 'audio', 'documents', 'code', 'data', 'archives', 'other']:
            if input(f"Include {cat}? (y/n): ").lower().startswith('y'):
                categories.append(cat)
        preferences['categories'] = categories
        
        preferences['naming'] = input("Do you have a preferred naming convention for files? ")
        
        preferences['create_subdirs'] = input("Should similar files be organized into subdirectories? (y/n): ").lower().startswith('y')
        preferences['deduplicate'] = input("Do you want to find and remove duplicate files? (y/n): ").lower().startswith('y')
    
    # Ask for additional custom categories if the user selected 'other'
    if 'other' in preferences.get('categories', []):
        custom_categories = input("Please specify any custom categories (comma separated): ")
        preferences['custom_categories'] = [c.strip() for c in custom_categories.split(',') if c.strip()]
    
    print("Thank you for providing your organization preferences!")
    return preferences

def suggest_organization(directory: Path, summary: Dict, project_info: Dict = None, user_prefs: Dict = None) -> List[Dict]:
    """
    Suggest ways to improve the organization of files in the directory.
    
    Args:
        directory (Path): Directory to analyze
        summary (Dict): Existing directory summary
        project_info (Dict): Information extracted from PROJECT_PLAN.md
        user_prefs (Dict): User's organization preferences
        
    Returns:
        List[Dict]: List of organization suggestions
    """
    suggestions = []
    
    # Count files by category
    categories = summary.get("categories", {})
    category_counts = {k: len(v) for k, v in categories.items()}
    
    # Incorporate user preferences if available
    preferred_categories = []
    create_subdirs = True  # Default behavior
    if user_prefs:
        preferred_categories = user_prefs.get("categories", [])
        create_subdirs = user_prefs.get("create_subdirs", True)
        
        # Suggest deduplication if user wants it
        if user_prefs.get("deduplicate", False):
            suggestions.append({
                "type": "deduplicate",
                "reason": "User preference: Find and remove duplicate files",
                "user_requested": True
            })
    
    # Only suggest creating subdirectories if user prefers it
    if create_subdirs:
        # Prioritize categories that match user preferences
        for category, count in category_counts.items():
            should_suggest = (count >= 5)
            
            # If we have user preferences, prioritize those categories
            if preferred_categories and category in preferred_categories:
                priority = "high"
            else:
                priority = "normal"
                
            if should_suggest:
                suggestions.append({
                    "type": "create_subdirectory",
                    "category": category,
                    "priority": priority,
                    "reason": f"Found {count} {category} files that could be organized into a subdirectory",
                    "user_requested": category in preferred_categories if preferred_categories else False
                })
    
    # Incorporate project structure from PROJECT_PLAN.md if available
    if project_info and "structure" in project_info and project_info["structure"]:
        for item in project_info["structure"]:
            # Check if it looks like a directory name
            if '/' not in item and '.' not in item and len(item.strip()) > 0:
                # Check if this directory already exists
                if not (directory / item).exists():
                    suggestions.append({
                        "type": "create_directory",
                        "name": item,
                        "priority": "high",
                        "reason": f"Directory '{item}' specified in PROJECT_PLAN.md but not found",
                        "project_plan": True
                    })
    
    # Suggest naming conventions from PROJECT_PLAN.md or user preferences
    naming_convention = None
    if project_info and "naming_conventions" in project_info and project_info["naming_conventions"]:
        naming_convention = "; ".join(project_info["naming_conventions"])
    elif user_prefs and "naming" in user_prefs and user_prefs["naming"]:
        naming_convention = user_prefs["naming"]
    
    if naming_convention:
        suggestions.append({
            "type": "naming_convention",
            "convention": naming_convention,
            "priority": "high",
            "reason": "Apply consistent naming convention based on user/project preferences",
            "project_plan": bool(project_info and project_info.get("naming_conventions"))
        })
    
    # Suggest fixing inconsistent naming patterns (if no specific convention provided)
    if not naming_convention:
        for category, files in categories.items():
            if len(files) < 2:
                continue
                
            # Check if files have inconsistent naming patterns
            patterns = set()
            for filename in files:
                # Extract prefix pattern (e.g., "IMG_", "DSC_", etc.)
                prefix = ""
                for i, char in enumerate(filename):
                    if char.isalpha() or char == '_':
                        prefix += char
                    else:
                        break
                if prefix and len(prefix) >= 2:
                    patterns.add(prefix)
            
            if len(patterns) > 1:
                suggestions.append({
                    "type": "standardize_naming",
                    "category": category,
                    "patterns": list(patterns),
                    "priority": "medium",
                    "reason": f"Files in {category} have inconsistent naming patterns"
                })
    
    # Suggest deduplication if the same summary file has been regenerated multiple times
    # (but only if user didn't already specify a preference)
    if not user_prefs or not "deduplicate" in user_prefs:
        if summary.get("generation_count", 0) > 3:
            suggestions.append({
                "type": "deduplicate",
                "priority": "medium",
                "reason": "This directory has been scanned multiple times, consider running deduplication"
            })
    
    return suggestions

def generate_directory_summary(directory: Path, include_user_prefs: bool = False) -> Dict:
    """
    Generate a comprehensive summary of the directory contents.
    
    Args:
        directory (Path): Directory to analyze
        include_user_prefs (bool): Whether to prompt for user preferences
        
    Returns:
        Dict: Summary data
    """
    directory = Path(directory)
    if not directory.is_dir():
        logger.error(f"{directory} is not a valid directory.")
        return {}
    
    try:
        # Get all files in the directory (non-recursive)
        files = [f for f in directory.iterdir() if f.is_file() and not f.name.startswith('.')]
        subdirs = [d for d in directory.iterdir() if d.is_dir()]
        
        # Get summary file if it exists
        summary_path = directory / SUMMARY_FILENAME
        existing_summary = {}
        if summary_path.exists():
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    existing_summary = json.load(f)
            except Exception as e:
                logger.error(f"Error reading existing summary file: {e}")
        
        # Update generation count
        generation_count = existing_summary.get("generation_count", 0) + 1
        
        # Limit files to a reasonable sample size for the summary
        file_sample = files[:min(MAX_SAMPLE_FILES, len(files))]
        
        # Check for PROJECT_PLAN.md
        project_plan_path = directory / PROJECT_PLAN_FILE
        project_info = {}
        if project_plan_path.exists():
            project_info = parse_project_plan(project_plan_path)
            logger.info(f"Found PROJECT_PLAN.md in {directory}")
        
        # Get user preferences if requested
        user_prefs = {}
        if include_user_prefs:
            user_prefs = prompt_for_organization_preferences(directory)
            logger.info("Collected user organization preferences")
        
        # Build the summary
        summary = {
            "directory": str(directory),
            "last_updated": datetime.datetime.now().isoformat(),
            "generation_count": generation_count,
            "previous_update": existing_summary.get("last_updated"),
            "file_count": len(files),
            "subdir_count": len(subdirs),
            "categories": get_file_categories(files),
            "directory_tree": get_directory_tree(directory),
            "content_analysis": analyze_directory_content(directory),
            "previous_suggestions": existing_summary.get("suggestions", []),
            "has_project_plan": project_plan_path.exists(),
            "project_info": project_info,
            "user_preferences": user_prefs if user_prefs else existing_summary.get("user_preferences", {})
        }
        
        # Generate new suggestions
        summary["suggestions"] = suggest_organization(
            directory, 
            summary, 
            project_info=project_info,
            user_prefs=user_prefs or existing_summary.get("user_preferences")
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating directory summary: {e}")
        return {
            "directory": str(directory),
            "error": str(e),
            "last_updated": datetime.datetime.now().isoformat()
        }

def update_directory_summary(directory: Path, include_user_prefs: bool = False) -> Dict:
    """
    Generate or update a hidden summary file in the directory.
    
    Args:
        directory (Path): Directory to analyze
        include_user_prefs (bool): Whether to prompt for user preferences
        
    Returns:
        Dict: Generated summary
    """
    directory = Path(directory)
    summary = generate_directory_summary(directory, include_user_prefs)
    
    if not summary:
        return {}
    
    # Save the summary to a hidden file in the directory
    summary_path = directory / SUMMARY_FILENAME
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Updated directory summary at {summary_path}")
    except Exception as e:
        logger.error(f"Error writing summary file: {e}")
    
    return summary

def get_directory_summary(directory: Path, include_user_prefs: bool = False) -> Dict:
    """
    Get the existing directory summary if available, or generate a new one.
    
    Args:
        directory (Path): Directory to get summary for
        include_user_prefs (bool): Whether to prompt for user preferences if generating a new summary
        
    Returns:
        Dict: Directory summary
    """
    directory = Path(directory)
    summary_path = directory / SUMMARY_FILENAME
    
    if summary_path.exists():
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                existing_summary = json.load(f)
                
                # If we need user preferences and there are none in the existing summary,
                # regenerate with user preferences
                if include_user_prefs and not existing_summary.get("user_preferences"):
                    return update_directory_summary(directory, include_user_prefs=True)
                
                return existing_summary
        except Exception as e:
            logger.error(f"Error reading summary file: {e}")
    
    # Generate a new summary if none exists or if there was an error
    return update_directory_summary(directory, include_user_prefs=include_user_prefs)

def suggest_reorganization(directory: Path, include_user_prefs: bool = False) -> List[Dict]:
    """
    Suggest ways to reorganize the files in a directory based on the summary.
    
    Args:
        directory (Path): Directory to analyze
        include_user_prefs (bool): Whether to prompt for user preferences
        
    Returns:
        List[Dict]: List of reorganization suggestions
    """
    summary = get_directory_summary(directory, include_user_prefs)
    
    if not summary:
        return []
    
    return summary.get("suggestions", []) 