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

# Configure logging
logger = logging.getLogger(__name__)

# Constants
HIDDEN_SUMMARY_FILE = ".cleanupx"

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
            "description": None
        },
        "organization": {
            "current_scheme": None,
            "suggestions": []
        },
        "history": []
    }
    
    # Get basic statistics about the directory
    try:
        files = []
        directories = []
        total_size = 0
        
        for item in directory.iterdir():
            if item.is_file():
                if not item.name.startswith('.'):  # Skip other hidden files
                    files.append(item)
                    total_size += item.stat().st_size
            elif item.is_dir():
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
            elif item.is_dir():
                subdir_file_count = sum(1 for _ in item.glob('*') if not Path(_).name.startswith('.'))
                file_tree[item.name] = {
                    "type": "directory",
                    "count": subdir_file_count
                }
        
        summary["file_tree"] = file_tree
        
    except Exception as e:
        logger.error(f"Error creating directory summary for {directory}: {e}")
    
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
        from cleanupx.config import XAI_MODEL_TEXT, DIRECTORY_ANALYSIS_SCHEMA
        from cleanupx.api import call_xai_api
        
        # Create a prompt for the AI to analyze the directory
        prompt = f"""
        You are analyzing a directory and its contents to provide insights and organization suggestions.
        
        Directory: {directory.name}
        File count: {summary.get('file_count', 0)}
        Directory count: {summary.get('directory_count', 0)}
        
        Categories:
        {json.dumps(summary.get('categories', {}), indent=2)}
        
        File tree:
        {json.dumps(summary.get('file_tree', {}), indent=2)}
        
        Keywords found in files:
        {', '.join(summary.get('content_analysis', {}).get('keywords', []))}
        
        Based on this information, provide a description of the directory contents, likely topics, and organization suggestions.
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
        except Exception as ai_error:
            logger.error(f"Error in AI analysis for {directory}: {ai_error}")
    
    except Exception as e:
        logger.error(f"Error updating AI analysis for {directory}: {e}")
    
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
    summary_file = directory / HIDDEN_SUMMARY_FILE
    summary["updated"] = datetime.now().isoformat()
    
    try:
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
    summary_file = directory / HIDDEN_SUMMARY_FILE
    
    # If the summary file exists, load it
    if summary_file.exists():
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            return summary
        except Exception as e:
            logger.error(f"Error reading hidden summary file {summary_file}: {e}")
    
    # If it doesn't exist, create a new one
    summary = create_hidden_summary(directory)
    summary = analyze_directory_content(directory, summary)
    summary = update_with_ai_analysis(summary, directory)
    save_hidden_summary(directory, summary)
    
    return summary

def update_hidden_summary(directory: Path, full_analysis: bool = False) -> Dict[str, Any]:
    """
    Update the hidden summary for a directory.
    
    Args:
        directory: Directory path to update the summary for
        full_analysis: Whether to perform a full analysis with AI
        
    Returns:
        Updated summary dictionary
    """
    directory = Path(directory)  # Ensure it's a Path object
    summary_file = directory / HIDDEN_SUMMARY_FILE
    
    # Start with a new summary or load existing one
    if summary_file.exists():
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
                
            # Archive the current state in history
            if "history" not in summary:
                summary["history"] = []
            
            # Only keep the 5 most recent history entries
            summary["history"] = summary["history"][-4:] if len(summary["history"]) > 4 else summary["history"]
            
            # Add current state to history
            history_entry = {
                "timestamp": summary.get("updated"),
                "file_count": summary.get("file_count"),
                "directory_count": summary.get("directory_count"),
                "categories": summary.get("categories"),
                "organization_scheme": summary.get("organization", {}).get("current_scheme")
            }
            summary["history"].append(history_entry)
            
        except Exception as e:
            logger.error(f"Error reading hidden summary file {summary_file}: {e}")
            summary = create_hidden_summary(directory)
    else:
        summary = create_hidden_summary(directory)
    
    # Update the basic statistics
    new_summary = create_hidden_summary(directory)
    summary["file_count"] = new_summary["file_count"]
    summary["directory_count"] = new_summary["directory_count"]
    summary["total_size_bytes"] = new_summary["total_size_bytes"]
    summary["categories"] = new_summary["categories"]
    summary["file_tree"] = new_summary["file_tree"]
    summary["updated"] = datetime.now().isoformat()
    
    # Perform content analysis if requested
    if full_analysis:
        summary = analyze_directory_content(directory, summary)
        summary = update_with_ai_analysis(summary, directory)
    
    # Save the updated summary
    save_hidden_summary(directory, summary)
    
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
                    target = new_dir / file_name
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