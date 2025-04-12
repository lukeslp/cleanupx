#!/usr/bin/env python3
"""
Hidden directory summary utilities for CleanupX.

This module provides functionality to create and maintain hidden .cleanupx files
in directories that provide summaries of contents, project information,
and organizational recommendations.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import shutil

from cleanupx.config import IGNORE_PATTERNS
from cleanupx.utils.common import count_by_extension, is_ignored_file
from cleanupx.utils.cache import ensure_metadata_dir, HIDDEN_SUMMARY_FILE

# Configure logging
logger = logging.getLogger(__name__)

# Constants
HIDDEN_SUMMARY_FILE = ".cleanupx"

# Global in-memory storage for directory summaries
_MEMORY_SUMMARIES = {}

def create_hidden_summary(directory: Path) -> Dict[str, Any]:
    """
    Create a new hidden summary file for a directory.
    
    Args:
        directory: Directory path to create the summary for
        
    Returns:
        Dictionary containing the summary data
    """
    summary = {
        "directory": str(directory),
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "file_count": 0,
        "directory_count": 0,
        "total_size_bytes": 0,
        "categories": {},
        "file_tree": {},
        "content_analysis": {
            "themes": [],
            "keywords": [],
            "topics": []
        },
        "project_info": {
            "name": directory.name,
            "type": None,
            "description": None,
            "from_project_plan": False
        },
        "organization": {
            "current_scheme": None,
            "suggestions": []
        },
        "history": [],
        "ongoing_summary": ""
    }
    
    # Get basic statistics about the directory
    try:
        files = []
        directories = []
        total_size = 0
        
        for item in directory.iterdir():
            if item.is_file():
                if not item.name.startswith('.'):  # Skip hidden files
                    files.append(item)
                    total_size += item.stat().st_size
            elif item.is_dir():
                if not item.name.startswith('.'):  # Skip hidden directories
                    directories.append(item)
        
        summary["file_count"] = len(files)
        summary["directory_count"] = len(directories)
        summary["total_size_bytes"] = total_size
        
        # Categorize files by extension
        categories = {}
        for file in files:
            ext = file.suffix.lower()
            if ext not in categories:
                categories[ext] = 0
            categories[ext] += 1
        
        summary["categories"] = categories
        
        # Create a simplified file tree (just the first level)
        file_tree = {}
        for item in directory.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                file_tree[item.name] = {
                    "type": "file",
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
            elif item.is_dir() and not item.name.startswith('.'):
                subdir_file_count = sum(1 for _ in item.glob('*') if not Path(_).name.startswith('.'))
                file_tree[item.name] = {
                    "type": "directory",
                    "count": subdir_file_count
                }
        
        summary["file_tree"] = file_tree
        
        # Check for PROJECT_PLAN.md
        project_plan_path = directory / "PROJECT_PLAN.md"
        if project_plan_path.exists():
            try:
                from cleanupx.utils.directory_summary import parse_project_plan
                project_info = parse_project_plan(project_plan_path)
                if project_info:
                    summary["project_info"] = {
                        "name": project_info.get("title") or directory.name,
                        "type": "project",
                        "description": project_info.get("description"),
                        "from_project_plan": True
                    }
            except Exception as e:
                logger.error(f"Error parsing PROJECT_PLAN.md: {e}")
        
    except Exception as e:
        logger.error(f"Error creating directory summary for {directory}: {e}")
    
    # Store summary in memory
    directory_key = str(directory.resolve())
    _MEMORY_SUMMARIES[directory_key] = summary
    logger.info(f"Created in-memory summary for {directory}")
    
    return summary

def analyze_directory_content(directory: Path, summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the content of a directory and update the summary with content insights.
    
    Args:
        directory: Directory path to analyze
        summary: Existing summary dictionary to update
        
    Returns:
        Updated summary dictionary
    """
    # Import necessary functions from directory_summary
    from cleanupx.utils.directory_summary import analyze_directory_content as existing_analysis
    from cleanupx.utils.directory_summary import parse_project_plan
    
    # Use existing analysis function
    content_analysis = existing_analysis(directory)
    
    # Update the summary
    summary["content_analysis"] = {
        "themes": content_analysis.get("themes", []),
        "keywords": content_analysis.get("keywords", []),
        "topics": []  # Will be populated by AI analysis
    }
    
    # Check for PROJECT_PLAN.md
    project_plan_path = directory / "PROJECT_PLAN.md"
    if project_plan_path.exists():
        project_info = parse_project_plan(project_plan_path)
        if project_info:
            summary["project_info"] = {
                "name": project_info.get("title") or directory.name,
                "type": "project",
                "description": project_info.get("description"),
                "from_project_plan": True
            }
    
    return summary

def update_with_ai_analysis(summary: Dict[str, Any], directory: Path) -> Dict[str, Any]:
    """
    Update the summary with AI-generated insights about the directory.
    
    Args:
        summary: Existing summary dictionary to update
        directory: Directory path being analyzed
        
    Returns:
        Updated summary dictionary
    """
    try:
        # Import safely - if this fails, we'll still return a basic summary
        try:
            from cleanupx.config import XAI_MODEL_TEXT, DIRECTORY_ANALYSIS_SCHEMA
            from cleanupx.api import call_xai_api
        except ImportError as e:
            logger.warning(f"Could not import AI modules: {e}. Skipping AI analysis.")
            return summary
        
        # Create a simple directory content description if AI fails
        if summary.get("file_count", 0) == 0:
            default_description = f"Empty directory named '{directory.name}'."
            summary["project_info"]["description"] = default_description
            summary["content_analysis"]["topics"] = ["empty directory"]
            logger.info(f"Directory {directory} is empty, using default description")
            return summary
            
        # Create a prompt for the AI to analyze the directory
        file_types = [ext for ext, count in summary.get('categories', {}).items() if count > 0]
        file_type_str = ", ".join(file_types) if file_types else "no recognized file types"
        
        # Simplify the prompt to reduce processing
        prompt = f"""
        Analyze directory: {directory.name}
        File count: {summary.get('file_count', 0)}
        Directory count: {summary.get('directory_count', 0)}
        File types: {file_type_str}
        
        Based on this information, provide a description of the directory, likely topics, and organization suggestions.
        """
        
        # Call the AI API and parse the result
        try:
            result = call_xai_api(XAI_MODEL_TEXT, prompt, DIRECTORY_ANALYSIS_SCHEMA)
            
            if result and isinstance(result, dict):
                # Update the summary with AI insights
                summary["content_analysis"]["topics"] = result.get("topics", [])
                summary["project_info"]["description"] = result.get("description", summary["project_info"]["description"])
                summary["organization"]["current_scheme"] = result.get("current_organization_scheme")
                summary["organization"]["suggestions"] = result.get("organization_suggestions", [])
                
                logger.info(f"Updated directory summary for {directory} with AI analysis")
            else:
                # Fallback to basic description if AI fails
                fallback_description = f"Directory '{directory.name}' containing {summary.get('file_count', 0)} files and {summary.get('directory_count', 0)} subdirectories."
                summary["project_info"]["description"] = fallback_description
                logger.warning(f"AI analysis didn't return valid results for {directory}. Using fallback description.")
        except Exception as ai_error:
            logger.error(f"Error in AI analysis for {directory}: {ai_error}")
            # Create fallback content if AI fails
            fallback_description = f"Directory '{directory.name}' containing {summary.get('file_count', 0)} files and {summary.get('directory_count', 0)} subdirectories."
            summary["project_info"]["description"] = fallback_description
    
    except Exception as e:
        logger.error(f"Error updating AI analysis for {directory}: {e}")
        # Ensure we have at least a basic description
        fallback_description = f"Directory '{directory.name}' containing {summary.get('file_count', 0)} files and {summary.get('directory_count', 0)} subdirectories."
        if "project_info" in summary:
            summary["project_info"]["description"] = fallback_description
    
    return summary

def save_hidden_summary(directory: Path, summary: Dict[str, Any]) -> Path:
    """
    Save the hidden summary file to the directory.
    
    Args:
        directory: Directory path where the summary should be saved
        summary: Summary dictionary to save
        
    Returns:
        Path to the saved summary file
    """
    summary_file = HIDDEN_SUMMARY_FILE(directory)
    summary["updated"] = datetime.now().isoformat()
    
    try:
        # Ensure .cleanupx directory exists
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved hidden summary file to {summary_file}")
        
        return summary_file
    except Exception as e:
        logger.error(f"Error saving hidden summary file to {summary_file}: {e}")
        raise e

def get_hidden_summary(directory: Path) -> Dict[str, Any]:
    """
    Get the hidden summary for a directory, creating it if it doesn't exist.
    
    Args:
        directory: Directory path to get the summary for
        
    Returns:
        Dictionary containing the summary data
    """
    directory_key = str(directory.resolve())
    if directory_key not in _MEMORY_SUMMARIES:
        return None
    
    return _MEMORY_SUMMARIES[directory_key]

def update_hidden_summary(directory: Path, changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing hidden summary file with new information.
    
    Args:
        directory: Directory path to update
        changes: Dictionary containing changes to apply
        
    Returns:
        Updated summary dictionary
    """
    directory_key = str(directory.resolve())
    summary = _MEMORY_SUMMARIES.get(directory_key)
    
    if not summary:
        return create_hidden_summary(directory)
    
    # Update timestamp
    summary["updated"] = datetime.now().isoformat()
    
    # Track changes in history
    change_entry = {
        "timestamp": datetime.now().isoformat(),
        "changes": changes
    }
    summary["history"].append(change_entry)
    
    # Apply changes
    for key, value in changes.items():
        if key in summary:
            if isinstance(summary[key], dict) and isinstance(value, dict):
                summary[key].update(value)
            else:
                summary[key] = value
    
    # Recalculate statistics if needed
    if any(key in changes for key in ["file_count", "directory_count", "total_size_bytes"]):
        try:
            files = []
            directories = []
            total_size = 0
            
            for item in directory.iterdir():
                if item.is_file():
                    if not item.name.startswith('.'):  # Skip hidden files
                        files.append(item)
                        total_size += item.stat().st_size
                elif item.is_dir():
                    if not item.name.startswith('.'):  # Skip hidden directories
                        directories.append(item)
            
            summary["file_count"] = len(files)
            summary["directory_count"] = len(directories)
            summary["total_size_bytes"] = total_size
            
            # Update categories
            categories = {}
            for file in files:
                ext = file.suffix.lower()
                if ext not in categories:
                    categories[ext] = 0
                categories[ext] += 1
            
            summary["categories"] = categories
            
            # Update file tree
            file_tree = {}
            for item in directory.iterdir():
                if item.is_file() and not item.name.startswith('.'):
                    file_tree[item.name] = {
                        "type": "file",
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    }
                elif item.is_dir() and not item.name.startswith('.'):
                    subdir_file_count = sum(1 for _ in item.glob('*') if not Path(_).name.startswith('.'))
                    file_tree[item.name] = {
                        "type": "directory",
                        "count": subdir_file_count
                    }
            
            summary["file_tree"] = file_tree
            
        except Exception as e:
            logger.error(f"Error recalculating directory statistics: {e}")
    
    try:
        summary["ongoing_summary"] = generate_ongoing_summary(summary)
    except Exception as e:
        logger.error(f"Error generating ongoing summary: {e}")
    
    # Update in-memory storage
    _MEMORY_SUMMARIES[directory_key] = summary
    logger.info(f"Updated in-memory summary for {directory}")
    
    return summary

def get_reorganization_suggestions(directory: Path) -> List[Dict[str, Any]]:
    """
    Get suggestions for reorganizing a directory based on its hidden summary.
    
    Args:
        directory: Directory path to get suggestions for
        
    Returns:
        List of reorganization suggestions
    """
    # Make sure the summary exists and is up-to-date
    summary = update_hidden_summary(directory, full_analysis=True)
    
    # Return the organization suggestions
    return summary.get("organization", {}).get("suggestions", [])

def create_suggested_structure(directory: Path, suggestion: Dict[str, Any]) -> bool:
    """
    Create a suggested directory structure based on a reorganization suggestion.
    
    Args:
        directory: Base directory path
        suggestion: Reorganization suggestion to implement
        
    Returns:
        True if the structure was created successfully, False otherwise
    """
    suggestion_type = suggestion.get("type", "")
    
    try:
        if suggestion_type == "create_subdirectory":
            subdir_name = suggestion.get("name")
            if not subdir_name:
                return False
            
            new_dir = directory / subdir_name
            if not new_dir.exists():
                new_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {new_dir}")
            
            # If files to move are specified, move them
            files_to_move = suggestion.get("files_to_move", [])
            for file_name in files_to_move:
                source = directory / file_name
                if source.exists() and source.is_file():
                    new_file_name = file_name
                    if file_name.startswith('.') and file_name not in [".cleanupx", ".cleanupx-citations"]:
                        new_file_name = file_name.lstrip('.')
                    target = new_dir / new_file_name
                    source.rename(target)
                    logger.info(f"Moved {source} to {target}")
            
            return True
            
        elif suggestion_type == "categorize_by_extension":
            # Get directory summary to find categories
            summary = get_hidden_summary(directory)
            
            # Create directories for each category
            categories = summary.get("categories", {})
            for ext, count in categories.items():
                if count < 2:  # Skip extensions with only one file
                    continue
                    
                category_name = ext.strip('.').upper()
                category_dir = directory / category_name
                if not category_dir.exists():
                    category_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory for {ext} files: {category_dir}")
                
                # Move files with this extension
                for file in directory.glob(f"*{ext}"):
                    if file.is_file():
                        target = category_dir / file.name
                        file.rename(target)
                        logger.info(f"Moved {file} to {target}")
            
            return True
            
        elif suggestion_type == "categorize_by_topic":
            topics = suggestion.get("topics", {})
            for topic, files in topics.items():
                topic_dir = directory / topic
                if not topic_dir.exists():
                    topic_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory for topic {topic}: {topic_dir}")
                
                for file_name in files:
                    source = directory / file_name
                    if source.exists() and source.is_file():
                        target = topic_dir / file_name
                        source.rename(target)
                        logger.info(f"Moved {source} to {target}")
            
            return True
            
        return False
    
    except Exception as e:
        logger.error(f"Error creating suggested structure: {e}")
        return False

def generate_ongoing_summary(summary: Dict[str, Any]) -> str:
    """Generate a human-readable ongoing summary based on the directory's summary data."""
    parts = []
    project_info = summary.get("project_info", {})
    if project_info.get("name"):
        parts.append(f"Project Name: {project_info.get('name')}")
    if project_info.get("description"):
        parts.append(f"Description: {project_info.get('description')}")
    parts.append(f"Files: {summary.get('file_count', 0)}")
    parts.append(f"Directories: {summary.get('directory_count', 0)}")
    categories = summary.get("categories", {})
    if categories:
        cat_summary = ", ".join([f"{ext}: {count}" for ext, count in categories.items()])
        parts.append(f"File types: {cat_summary}")
    org = summary.get("organization", {})
    suggestions = org.get("suggestions", [])
    if suggestions:
        parts.append(f"Organization suggestions: {', '.join(map(str, suggestions))}")
    return " | ".join(parts) 