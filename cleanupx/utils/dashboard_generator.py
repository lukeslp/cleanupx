#!/usr/bin/env python3
"""
Dashboard generator for CleanupX.

This module provides functionality to generate an HTML dashboard
that displays information about the files processed by CleanupX.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from cleanupx.utils.cache import load_rename_log, load_cache
from cleanupx.utils.hidden_summary import get_hidden_summary, update_hidden_summary
from cleanupx.config import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, MEDIA_EXTENSIONS

# Configure logging
logger = logging.getLogger(__name__)

def generate_dashboard(directory: Path, output_path: Optional[Path] = None) -> Optional[Path]:
    """
    Generate an HTML dashboard for the specified directory.
    
    Args:
        directory: Directory to generate dashboard for
        output_path: Optional custom path to save the dashboard HTML file
                     (defaults to directory/cleanupx_dashboard.html)
                     
    Returns:
        Path to the generated dashboard HTML file or None if generation failed
    """
    try:
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            logger.error(f"Invalid directory: {directory}")
            return None
            
        # Determine output path
        if output_path is None:
            output_path = directory / "cleanupx_dashboard.html"
            
        # Load data from rename log
        rename_log = load_rename_log(directory)
        cache = load_cache()
        
        # Get or update hidden summary
        try:
            summary = get_hidden_summary(directory)
        except Exception as e:
            logger.error(f"Error getting hidden summary: {e}")
            summary = {}
            
        # Generate HTML content
        html_content = generate_dashboard_html(directory, rename_log, cache, summary)
        
        # Save HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"Dashboard generated at: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        return None

def generate_dashboard_html(directory: Path, rename_log: Dict[str, Any], 
                          cache: Dict[str, Any], summary: Dict[str, Any]) -> str:
    """
    Generate HTML content for the dashboard.
    
    Args:
        directory: Directory path
        rename_log: Rename log data
        cache: Cache data
        summary: Directory summary data
        
    Returns:
        HTML content as a string
    """
    # Calculate statistics
    stats = calculate_statistics(rename_log)
    
    # Get folder name for display
    folder_name = directory.name
    folder_path = str(directory)
    
    # Format timestamp
    timestamp = rename_log.get("timestamp", datetime.now().isoformat())
    if isinstance(timestamp, str):
        try:
            timestamp_date = datetime.fromisoformat(timestamp).strftime("%B %d, %Y at %I:%M %p")
        except ValueError:
            timestamp_date = timestamp
    else:
        timestamp_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    # Get file types breakdown
    file_types = get_file_type_breakdown(summary)
    
    # Get recent renames
    renames = get_recent_renames(rename_log)
    
    # Get errors
    errors = get_errors(rename_log)
    
    # Get file descriptions
    descriptions = get_file_descriptions(rename_log, cache)
    
    # Get organization suggestions
    suggestions = get_organization_suggestions(summary)
    
    # Get narrative summary
    narrative_summary = get_narrative_summary(summary)
    
    # Generate JavaScript data
    js_data = {
        "folderPath": folder_path,
        "folderName": folder_name,
        "lastProcessed": timestamp_date,
        "generationDate": datetime.now().strftime("%B %d, %Y"),
        "stats": stats,
        "fileTypes": file_types,
        "renames": renames,
        "errors": errors,
        "descriptions": descriptions,
        "suggestions": suggestions,
        "narrativeSummary": narrative_summary
    }
    
    # Serialize JSON data
    js_data_json = json.dumps(js_data)
    
    # Generate HTML - starting portion
    html_content_start = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CleanupX Dashboard - {folder_name}</title>
    <style>
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --light-bg: #f8f9fa;
            --dark-text: #343a40;
            --light-text: #f8f9fa;
            --border-color: #dee2e6;
            --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: var(--dark-text);
            background-color: var(--light-bg);
            margin: 0;
            padding: 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            background-color: var(--primary-color);
            color: var(--light-text);
            padding: 1.5rem 0;
            margin-bottom: 2rem;
            text-align: center;
        }}
        
        h1, h2, h3, h4 {{
            margin-top: 0;
        }}
        
        .card {{
            background-color: white;
            border-radius: 8px;
            box-shadow: var(--card-shadow);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .summary-section {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
        }}
        
        .stat-card {{
            flex: 1;
            min-width: 200px;
            background-color: white;
            border-radius: 8px;
            box-shadow: var(--card-shadow);
            padding: 1.5rem;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: var(--secondary-color);
            margin: 0.5rem 0;
        }}
        
        .stat-label {{
            font-size: 1rem;
            color: var(--dark-text);
            opacity: 0.8;
        }}
        
        .file-list {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background-color: var(--primary-color);
            color: var(--light-text);
            position: sticky;
            top: 0;
        }}
        
        tr:nth-child(even) {{
            background-color: var(--light-bg);
        }}
        
        .success {{
            color: #28a745;
        }}
        
        .error {{
            color: var(--accent-color);
        }}
        
        .tag {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            background-color: var(--secondary-color);
            color: white;
            border-radius: 4px;
            font-size: 0.85rem;
            margin-right: 0.5rem;
        }}
        
        .footer {{
            text-align: center;
            padding: 1rem 0;
            margin-top: 2rem;
            color: var(--dark-text);
            opacity: 0.7;
            font-size: 0.9rem;
        }}
        
        .error-card {{
            background-color: #fff8f8;
            border-left: 4px solid var(--accent-color);
        }}
        
        .suggestion-item {{
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .suggestion-item:last-child {{
            border-bottom: none;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .summary-section {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>CleanupX Dashboard</h1>
        </div>
    </header>
    
    <div class="container">
        <!-- Folder Overview Section -->
        <section>
            <h2>Folder Overview</h2>
            <div class="card">
                <h3>Folder Information</h3>
                <p><strong>Location:</strong> <span id="folder-path"></span></p>
                <p><strong>Last Processed:</strong> <span id="last-processed"></span></p>
                
                <div class="summary-section">
                    <div class="stat-card">
                        <div class="stat-value" id="total-files"></div>
                        <div class="stat-label">Total Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="processed-files"></div>
                        <div class="stat-label">Processed Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="renamed-files"></div>
                        <div class="stat-label">Renamed Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="errors"></div>
                        <div class="stat-label">Errors</div>
                    </div>
                </div>
            </div>
            
            <!-- Narrative Summary -->
            <div class="card">
                <h3>Folder Summary</h3>
                <div id="folder-summary"></div>
            </div>
            
            <!-- File Type Breakdown -->
            <div class="card">
                <h3>File Type Breakdown</h3>
                <div id="file-types">
                    <p>The folder contains the following file types:</p>
                    <ul id="file-type-list"></ul>
                </div>
            </div>
        </section>
        
        <!-- Organization Suggestions -->
        <section>
            <h2>Organization Suggestions</h2>
            <div class="card">
                <div id="suggestions-list"></div>
            </div>
        </section>
        
        <!-- Recently Processed Files -->
        <section>
            <h2>Recently Processed Files</h2>
            <div class="card">
                <div class="file-list">
                    <table>
                        <thead>
                            <tr>
                                <th>Original Filename</th>
                                <th>New Filename</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="processed-files-list"></tbody>
                    </table>
                </div>
            </div>
        </section>
        
        <!-- Errors and Issues -->
        <section id="errors-section">
            <h2>Errors and Issues</h2>
            <div class="card error-card">
                <div class="file-list">
                    <table>
                        <thead>
                            <tr>
                                <th>File</th>
                                <th>Error Type</th>
                                <th>Error Message</th>
                            </tr>
                        </thead>
                        <tbody id="error-files-list"></tbody>
                    </table>
                </div>
            </div>
        </section>
        
        <!-- File Descriptions -->
        <section id="descriptions-section">
            <h2>Generated File Descriptions</h2>
            <div class="card">
                <div class="file-list">
                    <table>
                        <thead>
                            <tr>
                                <th>Filename</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody id="file-descriptions-list"></tbody>
                    </table>
                </div>
            </div>
        </section>
    </div>
    
    <footer class="footer">
        <div class="container">
            <p>CleanupX Dashboard | Generated on <span id="generation-date"></span></p>
        </div>
    </footer>
    
    <script>
        // Data from the Python generator
"""

    # Middle portion - adding the JavaScript data
    html_content_middle = f"const dashboardData = {js_data_json};\n"
    
    # End portion
    html_content_end = """
        document.addEventListener('DOMContentLoaded', function() {
            // Update folder information
            document.getElementById('folder-path').textContent = dashboardData.folderPath;
            document.getElementById('last-processed').textContent = dashboardData.lastProcessed;
            document.getElementById('generation-date').textContent = dashboardData.generationDate;
            
            // Update statistics
            document.getElementById('total-files').textContent = dashboardData.stats.totalFiles;
            document.getElementById('processed-files').textContent = dashboardData.stats.processedFiles;
            document.getElementById('renamed-files').textContent = dashboardData.stats.renamedFiles;
            document.getElementById('errors').textContent = dashboardData.stats.errorCount;
            
            // Populate narrative summary
            document.getElementById('folder-summary').innerHTML = dashboardData.narrativeSummary;
            
            // Populate file types
            const fileTypeList = document.getElementById('file-type-list');
            dashboardData.fileTypes.forEach(type => {
                const li = document.createElement('li');
                li.textContent = `${type.ext} files: ${type.count}`;
                fileTypeList.appendChild(li);
            });
            
            // Populate processed files
            const processedFilesList = document.getElementById('processed-files-list');
            dashboardData.renames.forEach(file => {
                const tr = document.createElement('tr');
                
                const tdOriginal = document.createElement('td');
                tdOriginal.textContent = file.original;
                
                const tdNew = document.createElement('td');
                tdNew.textContent = file.new;
                
                const tdStatus = document.createElement('td');
                tdStatus.textContent = file.status;
                tdStatus.className = file.status.includes('Skipped') || file.status.includes('Error') ? 'error' : 'success';
                
                tr.appendChild(tdOriginal);
                tr.appendChild(tdNew);
                tr.appendChild(tdStatus);
                
                processedFilesList.appendChild(tr);
            });
            
            // Populate error files
            const errorFilesList = document.getElementById('error-files-list');
            const errorsSection = document.getElementById('errors-section');
            
            if (dashboardData.errors.length === 0) {
                errorsSection.style.display = 'none';
            } else {
                dashboardData.errors.forEach(file => {
                    const tr = document.createElement('tr');
                    
                    const tdFile = document.createElement('td');
                    tdFile.textContent = file.file;
                    
                    const tdType = document.createElement('td');
                    tdType.textContent = file.type;
                    
                    const tdMessage = document.createElement('td');
                    tdMessage.textContent = file.message;
                    
                    tr.appendChild(tdFile);
                    tr.appendChild(tdType);
                    tr.appendChild(tdMessage);
                    
                    errorFilesList.appendChild(tr);
                });
            }
            
            // Populate file descriptions
            const fileDescriptionsList = document.getElementById('file-descriptions-list');
            const descriptionsSection = document.getElementById('descriptions-section');
            
            if (dashboardData.descriptions.length === 0) {
                descriptionsSection.style.display = 'none';
            } else {
                dashboardData.descriptions.forEach(file => {
                    const tr = document.createElement('tr');
                    
                    const tdFile = document.createElement('td');
                    tdFile.textContent = file.file;
                    
                    const tdDescription = document.createElement('td');
                    tdDescription.textContent = file.description;
                    
                    tr.appendChild(tdFile);
                    tr.appendChild(tdDescription);
                    
                    fileDescriptionsList.appendChild(tr);
                });
            }
            
            // Populate organization suggestions
            const suggestionsList = document.getElementById('suggestions-list');
            dashboardData.suggestions.forEach(suggestion => {
                const div = document.createElement('div');
                div.className = 'suggestion-item';
                
                const h4 = document.createElement('h4');
                h4.textContent = suggestion.title;
                
                const p = document.createElement('p');
                p.textContent = suggestion.description;
                
                div.appendChild(h4);
                div.appendChild(p);
                
                suggestionsList.appendChild(div);
            });
        });
    </script>
</body>
</html>"""

    # Combine all parts of the HTML content
    html_content = html_content_start + html_content_middle + html_content_end
    
    return html_content

def calculate_statistics(rename_log: Dict[str, Any]) -> Dict[str, int]:
    """Calculate statistics from the rename log."""
    stats = rename_log.get("stats", {})
    return {
        "totalFiles": stats.get("total_files", 0),
        "processedFiles": stats.get("total_processed", stats.get("successful_renames", 0) + stats.get("skipped_files", 0)),
        "renamedFiles": stats.get("successful_renames", 0),
        "errorCount": stats.get("failed_renames", 0) + len(rename_log.get("errors", []))
    }

def get_file_type_breakdown(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get file type breakdown from the directory summary."""
    categories = summary.get("categories", {})
    return [{"ext": ext, "count": count} for ext, count in categories.items()]

def get_recent_renames(rename_log: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get recent renames from the rename log."""
    renames = rename_log.get("renames", [])
    result = []
    
    # Take the most recent 20 renames
    for rename in renames[-20:]:
        original_path = rename.get("original_path", "")
        new_path = rename.get("new_path", "")
        
        original_name = Path(original_path).name if original_path else ""
        new_name = Path(new_path).name if new_path else ""
        
        result.append({
            "original": original_name,
            "new": new_name,
            "status": rename.get("status", "Unknown")
        })
    
    return result

def get_errors(rename_log: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get errors from the rename log."""
    errors = rename_log.get("errors", [])
    result = []
    
    for error in errors:
        file_path = error.get("file_path", "")
        file_name = Path(file_path).name if file_path else ""
        
        result.append({
            "file": file_name,
            "type": error.get("error_type", "Unknown"),
            "message": error.get("error", "Unknown error")
        })
    
    return result

def get_file_descriptions(rename_log: Dict[str, Any], cache: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get file descriptions from the cache."""
    renames = rename_log.get("renames", [])
    result = []
    
    # Process only the most recent 20 renames
    for rename in renames[-20:]:
        new_path = rename.get("new_path", "")
        
        if new_path and new_path in cache:
            description_data = cache[new_path]
            
            # Extract relevant description based on file type
            description = ""
            if isinstance(description_data, dict):
                if "description" in description_data:
                    description = description_data["description"]
                elif "alt_text" in description_data:
                    description = description_data["alt_text"]
                elif "content_summary" in description_data:
                    description = description_data["content_summary"]
                elif "title" in description_data:
                    description = description_data["title"]
            
            if description:
                result.append({
                    "file": Path(new_path).name,
                    "description": description
                })
    
    return result

def get_organization_suggestions(summary: Dict[str, Any]) -> List[Dict[str, str]]:
    """Get organization suggestions from the directory summary."""
    organization = summary.get("organization", {})
    suggestions = organization.get("suggestions", [])
    result = []
    
    # If no specific suggestions are found, add some generic ones
    if not suggestions:
        return [
            {
                "title": "Create Subdirectories by Type",
                "description": "Group files into subdirectories based on their type (images, documents, etc.) to improve organization."
            },
            {
                "title": "Standardize Naming Convention",
                "description": "Rename files to follow a consistent pattern based on content type and creation date."
            },
            {
                "title": "Archive Older Content",
                "description": "Move older files to an archive directory to keep the main folder focused on current materials."
            }
        ]
    
    # Process actual suggestions
    for suggestion in suggestions:
        suggestion_type = suggestion.get("type", "")
        
        if suggestion_type == "create_subdirectory":
            result.append({
                "title": f"Create '{suggestion.get('name', '')}' Subdirectory",
                "description": f"Group {len(suggestion.get('files_to_move', []))} related files into a new subdirectory."
            })
        elif suggestion_type == "categorize_by_extension":
            result.append({
                "title": "Categorize by File Type",
                "description": "Create subdirectories for each file type to better organize your content."
            })
        elif suggestion_type == "group_by_date":
            result.append({
                "title": "Group Files by Date",
                "description": "Organize files into directories based on their creation or modification date."
            })
        elif suggestion_type == "separate_by_size":
            result.append({
                "title": "Separate Large Files",
                "description": "Move large files to a separate directory to make the main folder more manageable."
            })
    
    return result

def get_narrative_summary(summary: Dict[str, Any]) -> str:
    """Generate a narrative summary from the directory summary."""
    # If there's already an ongoing summary in the data, use it
    if "ongoing_summary" in summary and summary["ongoing_summary"]:
        return f"<p>{summary['ongoing_summary']}</p>"
    
    # Otherwise, generate one based on available data
    parts = []
    
    # Get basic folder information
    file_count = summary.get("file_count", 0)
    directory_count = summary.get("directory_count", 0)
    
    parts.append(f"This folder contains {file_count} files and {directory_count} subdirectories.")
    
    # Get file type information
    categories = summary.get("categories", {})
    if categories:
        file_types = []
        for ext, count in categories.items():
            if ext in IMAGE_EXTENSIONS:
                file_types.append(f"{count} image files")
            elif ext in DOCUMENT_EXTENSIONS:
                file_types.append(f"{count} document files")
            elif ext in MEDIA_EXTENSIONS:
                file_types.append(f"{count} media files")
        
        if file_types:
            parts.append(f"It includes {', '.join(file_types)}.")
    
    # Get project information
    project_info = summary.get("project_info", {})
    if project_info:
        if project_info.get("name"):
            parts.append(f"The folder appears to be related to the project '{project_info.get('name')}'.")
        if project_info.get("description"):
            parts.append(f"{project_info.get('description')}")
    
    # Get organization status
    organization = summary.get("organization", {})
    if organization:
        org_status = organization.get("status")
        if org_status == "needs_improvement":
            parts.append("The folder structure could benefit from better organization.")
        elif org_status == "well_organized":
            parts.append("The folder is currently well-organized.")
    
    return "<p>" + " ".join(parts) + "</p>" 