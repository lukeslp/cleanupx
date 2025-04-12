"""
Organization Utilities for CleanupX

This module provides utilities for organizing files based on content analysis,
including topic, project, date, and other categorization methods.
"""

import os
import shutil
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

# Configure logging
logger = logging.getLogger(__name__)

def organize_files_by_topic(
    directory: Union[str, Path],
    destination: Union[str, Path],
    cache: Dict[str, Any],
    min_files_per_folder: int = 3,
    recursive: bool = False
) -> Tuple[int, List[str]]:
    """
    Organize files by topic based on content analysis.
    
    Args:
        directory: Source directory containing files to organize
        destination: Destination directory to organize files into
        cache: Content analysis cache with file analysis data
        min_files_per_folder: Minimum number of files required to create a topic folder
        recursive: Whether to process subdirectories
        
    Returns:
        Tuple of (number of files organized, list of folders created)
    """
    # Ensure directories are Path objects
    directory = Path(directory) if not isinstance(directory, Path) else directory
    destination = Path(destination) if not isinstance(destination, Path) else destination
    
    # Ensure destination directory exists
    destination.mkdir(parents=True, exist_ok=True)
    
    # Find files to organize
    files_to_organize = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files_to_organize.append(Path(root) / filename)
    else:
        files_to_organize = [f for f in directory.iterdir() if f.is_file()]
    
    # Group files by topic
    topic_groups = {}
    for file_path in files_to_organize:
        # Get topics from cache if available
        file_key = str(file_path)
        if file_key in cache and 'topics' in cache[file_key]:
            topics = cache[file_key]['topics']
            
            # Add file to each topic group
            for topic in topics:
                if topic not in topic_groups:
                    topic_groups[topic] = []
                topic_groups[topic].append(file_path)
    
    # Filter out topics with too few files
    valid_topics = {topic: files for topic, files in topic_groups.items() 
                   if len(files) >= min_files_per_folder}
    
    # Create topic folders and move files
    created_folders = []
    file_count = 0
    
    for topic, files in valid_topics.items():
        # Create sanitized folder name
        topic_folder_name = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in topic)
        topic_folder_name = topic_folder_name.strip().replace(' ', '_')
        topic_folder = destination / topic_folder_name
        
        # Create folder if it doesn't exist
        topic_folder.mkdir(exist_ok=True)
        created_folders.append(str(topic_folder))
        
        # Move files to topic folder
        for file_path in files:
            target_path = topic_folder / file_path.name
            
            # Handle filename collisions
            if target_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                
                while target_path.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    target_path = topic_folder / new_name
                    counter += 1
            
            try:
                shutil.copy2(file_path, target_path)
                file_count += 1
                logger.info(f"Copied {file_path} to {target_path}")
            except Exception as e:
                logger.error(f"Error copying {file_path} to {target_path}: {e}")
    
    return file_count, created_folders

def organize_files_by_project(
    directory: Union[str, Path],
    destination: Union[str, Path],
    cache: Dict[str, Any],
    min_files_per_folder: int = 3,
    recursive: bool = False
) -> Tuple[int, List[str]]:
    """
    Organize files by project based on content analysis.
    
    Args:
        directory: Source directory containing files to organize
        destination: Destination directory to organize files into
        cache: Content analysis cache with file analysis data
        min_files_per_folder: Minimum number of files required to create a project folder
        recursive: Whether to process subdirectories
        
    Returns:
        Tuple of (number of files organized, list of folders created)
    """
    # Implementation is similar to organize_files_by_topic
    # For now, we'll use the same logic with a slight variation
    directory = Path(directory) if not isinstance(directory, Path) else directory
    destination = Path(destination) if not isinstance(destination, Path) else destination
    
    # Ensure destination directory exists
    destination.mkdir(parents=True, exist_ok=True)
    
    # Find files to organize
    files_to_organize = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files_to_organize.append(Path(root) / filename)
    else:
        files_to_organize = [f for f in directory.iterdir() if f.is_file()]
    
    # Group files by project
    project_groups = {}
    for file_path in files_to_organize:
        # Get projects from cache if available
        file_key = str(file_path)
        if file_key in cache and 'projects' in cache[file_key]:
            projects = cache[file_key]['projects']
            
            # Add file to each project group
            for project in projects:
                if project not in project_groups:
                    project_groups[project] = []
                project_groups[project].append(file_path)
    
    # Filter out projects with too few files
    valid_projects = {project: files for project, files in project_groups.items() 
                     if len(files) >= min_files_per_folder}
    
    # Create project folders and move files
    created_folders = []
    file_count = 0
    
    for project, files in valid_projects.items():
        # Create sanitized folder name
        project_folder_name = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in project)
        project_folder_name = project_folder_name.strip().replace(' ', '_')
        project_folder = destination / project_folder_name
        
        # Create folder if it doesn't exist
        project_folder.mkdir(exist_ok=True)
        created_folders.append(str(project_folder))
        
        # Move files to project folder
        for file_path in files:
            target_path = project_folder / file_path.name
            
            # Handle filename collisions
            if target_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                
                while target_path.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    target_path = project_folder / new_name
                    counter += 1
            
            try:
                shutil.copy2(file_path, target_path)
                file_count += 1
                logger.info(f"Copied {file_path} to {target_path}")
            except Exception as e:
                logger.error(f"Error copying {file_path} to {target_path}: {e}")
    
    return file_count, created_folders

def organize_files_by_person(
    directory: Union[str, Path],
    destination: Union[str, Path],
    cache: Dict[str, Any],
    min_files_per_folder: int = 3,
    recursive: bool = False
) -> Tuple[int, List[str]]:
    """
    Organize files by person/author based on content analysis.
    
    Args:
        directory: Source directory containing files to organize
        destination: Destination directory to organize files into
        cache: Content analysis cache with file analysis data
        min_files_per_folder: Minimum number of files required to create a person folder
        recursive: Whether to process subdirectories
        
    Returns:
        Tuple of (number of files organized, list of folders created)
    """
    # Similar implementation to the above functions, focusing on person/author data
    directory = Path(directory) if not isinstance(directory, Path) else directory
    destination = Path(destination) if not isinstance(destination, Path) else destination
    
    # Ensure destination directory exists
    destination.mkdir(parents=True, exist_ok=True)
    
    # Find files to organize
    files_to_organize = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files_to_organize.append(Path(root) / filename)
    else:
        files_to_organize = [f for f in directory.iterdir() if f.is_file()]
    
    # Group files by person
    person_groups = {}
    for file_path in files_to_organize:
        # Get authors/people from cache if available
        file_key = str(file_path)
        if file_key in cache and 'people' in cache[file_key]:
            people = cache[file_key]['people']
            
            # Add file to each person group
            for person in people:
                if person not in person_groups:
                    person_groups[person] = []
                person_groups[person].append(file_path)
    
    # Filter out persons with too few files
    valid_persons = {person: files for person, files in person_groups.items() 
                    if len(files) >= min_files_per_folder}
    
    # Create person folders and move files
    created_folders = []
    file_count = 0
    
    for person, files in valid_persons.items():
        # Create sanitized folder name
        person_folder_name = "".join(c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in person)
        person_folder_name = person_folder_name.strip().replace(' ', '_')
        person_folder = destination / person_folder_name
        
        # Create folder if it doesn't exist
        person_folder.mkdir(exist_ok=True)
        created_folders.append(str(person_folder))
        
        # Move files to person folder
        for file_path in files:
            target_path = person_folder / file_path.name
            
            # Handle filename collisions
            if target_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                
                while target_path.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    target_path = person_folder / new_name
                    counter += 1
            
            try:
                shutil.copy2(file_path, target_path)
                file_count += 1
                logger.info(f"Copied {file_path} to {target_path}")
            except Exception as e:
                logger.error(f"Error copying {file_path} to {target_path}: {e}")
    
    return file_count, created_folders

def organize_files_by_date(
    directory: Union[str, Path],
    destination: Union[str, Path],
    recursive: bool = False
) -> Tuple[int, List[str]]:
    """
    Organize files by their creation or modification date.
    
    Args:
        directory: Source directory containing files to organize
        destination: Destination directory to organize files into
        recursive: Whether to process subdirectories
        
    Returns:
        Tuple of (number of files organized, list of folders created)
    """
    directory = Path(directory) if not isinstance(directory, Path) else directory
    destination = Path(destination) if not isinstance(destination, Path) else destination
    
    # Ensure destination directory exists
    destination.mkdir(parents=True, exist_ok=True)
    
    # Find files to organize
    files_to_organize = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files_to_organize.append(Path(root) / filename)
    else:
        files_to_organize = [f for f in directory.iterdir() if f.is_file()]
    
    # Organize files by date
    created_folders = []
    file_count = 0
    
    for file_path in files_to_organize:
        try:
            # Get file modification time
            mod_time = file_path.stat().st_mtime
            date_str = os.path.getmtime(file_path)
            
            # Format date folder names (YYYY-MM)
            import time
            date_obj = time.localtime(date_str)
            year_month = time.strftime("%Y-%m", date_obj)
            
            # Create date folder
            date_folder = destination / year_month
            date_folder.mkdir(exist_ok=True)
            
            if str(date_folder) not in created_folders:
                created_folders.append(str(date_folder))
            
            # Copy file to date folder
            target_path = date_folder / file_path.name
            
            # Handle filename collisions
            if target_path.exists():
                base_name = file_path.stem
                extension = file_path.suffix
                counter = 1
                
                while target_path.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    target_path = date_folder / new_name
                    counter += 1
            
            shutil.copy2(file_path, target_path)
            file_count += 1
            logger.info(f"Copied {file_path} to {target_path}")
            
        except Exception as e:
            logger.error(f"Error organizing {file_path}: {e}")
    
    return file_count, created_folders

def create_bibliography(directory: Union[str, Path], format: str = "apa") -> Optional[str]:
    """
    Create a bibliography from citations found in the directory.
    
    Args:
        directory: Directory to scan for citations
        format: Citation format (apa, mla, chicago, etc.)
        
    Returns:
        Formatted bibliography string or None if no citations found
    """
    try:
        directory = Path(directory)
        citations = []
        
        # Scan markdown files for citations
        for file_path in directory.rglob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                citations.extend(extract_citations(content))
        
        if not citations:
            return None
            
        # Format citations based on style
        if format.lower() == "apa":
            return format_apa_citations(citations)
        elif format.lower() == "mla":
            return format_mla_citations(citations)
        elif format.lower() == "chicago":
            return format_chicago_citations(citations)
        else:
            return format_apa_citations(citations)  # Default to APA
            
    except Exception as e:
        logger.error(f"Error creating bibliography: {e}")
        return None

def extract_citations(content: str) -> List[Dict[str, str]]:
    """
    Extract citations from text content.
    
    Args:
        content: Text content to scan
        
    Returns:
        List of citation dictionaries
    """
    citations = []
    
    # Match formal citations like [Author, Year] or (Author, Year)
    citation_pattern = r'[\[\(]([^,\]\)]+),\s*(\d{4})[\]\)](?:\s*\(([^\)]+)\))?'
    matches = re.finditer(citation_pattern, content)
    
    for match in matches:
        author = match.group(1).strip()
        year = match.group(2)
        title = match.group(3) if match.group(3) else ""
        
        # Look for associated URL
        url_pattern = rf'\[{re.escape(author)},\s*{year}\].*?\(([^\)]+)\)'
        url_match = re.search(url_pattern, content)
        url = url_match.group(1) if url_match else ""
        
        citations.append({
            "author": author,
            "year": year,
            "title": title,
            "url": url
        })
    
    return citations

def format_apa_citations(citations: List[Dict[str, str]]) -> str:
    """Format citations in APA style."""
    formatted = []
    
    for cite in sorted(citations, key=lambda x: (x["author"].split()[-1], x["year"])):
        entry = f"{cite['author']} ({cite['year']})"
        if cite["title"]:
            entry += f". {cite['title']}"
            if not cite["title"].endswith("."):
                entry += "."
        if cite["url"]:
            entry += f" Retrieved from {cite['url']}"
        formatted.append(entry)
    
    return "\n\n".join(formatted)

def format_mla_citations(citations: List[Dict[str, str]]) -> str:
    """Format citations in MLA style."""
    formatted = []
    
    for cite in sorted(citations, key=lambda x: x["author"].split()[-1]):
        entry = cite["author"]
        if cite["title"]:
            entry += f". \"{cite['title']}\""
        entry += f", {cite['year']}"
        if cite["url"]:
            entry += f". Web. {cite['url']}"
        formatted.append(entry)
    
    return "\n\n".join(formatted)

def format_chicago_citations(citations: List[Dict[str, str]]) -> str:
    """Format citations in Chicago style."""
    formatted = []
    
    for cite in sorted(citations, key=lambda x: x["author"].split()[-1]):
        entry = f"{cite['author']}. "
        if cite["title"]:
            entry += f"\"{cite['title']}.\" "
        entry += f"({cite['year']})"
        if cite["url"]:
            entry += f". {cite['url']}"
        formatted.append(entry)
    
    return "\n\n".join(formatted)
