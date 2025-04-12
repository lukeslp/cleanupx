"""
Report Utilities for CleanupX

This module provides utilities for generating HTML and other reports
from directory content.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

def generate_html_report(
    directory: Union[str, Path], 
    include_images: bool = True,
    include_descriptions: bool = True,
    include_statistics: bool = True,
    theme: str = "light"
) -> str:
    """
    Generate an HTML report for a directory.
    
    Args:
        directory: Directory to generate report for
        include_images: Whether to include image previews
        include_descriptions: Whether to include file descriptions
        include_statistics: Whether to include file statistics
        theme: Theme for the report (light, dark, colorful, minimal)
        
    Returns:
        Path to the generated HTML file
    """
    # Ensure directory is a Path
    if not isinstance(directory, Path):
        directory = Path(directory)
    
    # Generate HTML report
    report_path = directory / "directory_report.html"
    
    # Create a basic HTML report
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Report - {directory.name}</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 0;
            padding: 20px;
            background-color: {_get_theme_color(theme, 'background')};
            color: {_get_theme_color(theme, 'text')};
        }}
        h1, h2, h3 {{ 
            color: {_get_theme_color(theme, 'heading')}; 
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .file-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .file-card {{
            border: 1px solid {_get_theme_color(theme, 'border')};
            border-radius: 5px;
            padding: 15px;
            background-color: {_get_theme_color(theme, 'card')};
        }}
        .file-name {{
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .stats-table th, .stats-table td {{
            border: 1px solid {_get_theme_color(theme, 'border')};
            padding: 8px;
            text-align: left;
        }}
        .stats-table th {{
            background-color: {_get_theme_color(theme, 'tableHeader')};
        }}
        img.preview {{
            max-width: 100%;
            max-height: 150px;
            display: block;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Directory Report - {directory.name}</h1>
        <p>Generated on {Path.ctime(Path.stat(directory))}</p>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total files: {len([f for f in directory.iterdir() if f.is_file()])}</p>
            <p>Total directories: {len([f for f in directory.iterdir() if f.is_dir()])}</p>
        </div>
        
        <div class="file-list">
            <!-- Files will be listed here -->
            {_generate_file_cards(directory, include_images, include_descriptions, include_statistics)}
        </div>
    </div>
</body>
</html>
"""
    
    # Write the report to a file
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return str(report_path)

def _get_theme_color(theme: str, element: str) -> str:
    """Get color for a theme element."""
    themes = {
        'light': {
            'background': '#f5f5f5',
            'text': '#333333',
            'heading': '#2c3e50',
            'border': '#dddddd',
            'card': '#ffffff',
            'tableHeader': '#e7e7e7'
        },
        'dark': {
            'background': '#2c3e50',
            'text': '#ecf0f1',
            'heading': '#3498db',
            'border': '#34495e',
            'card': '#34495e',
            'tableHeader': '#1a252f'
        },
        'colorful': {
            'background': '#f9f9f9',
            'text': '#333333',
            'heading': '#e74c3c',
            'border': '#bdc3c7',
            'card': '#ffffff',
            'tableHeader': '#3498db'
        },
        'minimal': {
            'background': '#ffffff',
            'text': '#333333',
            'heading': '#333333',
            'border': '#eeeeee',
            'card': '#fafafa',
            'tableHeader': '#f5f5f5'
        }
    }
    
    return themes.get(theme, themes['light']).get(element, '#000000')

def _generate_file_cards(directory: Path, include_images: bool, include_descriptions: bool, include_statistics: bool) -> str:
    """Generate HTML for file cards."""
    html = ""
    
    for file_path in directory.iterdir():
        if file_path.is_file():
            html += f"""
            <div class="file-card">
                <div class="file-name">{file_path.name}</div>
            """
            
            # Add image preview if requested and file is an image
            if include_images and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                html += f'<img class="preview" src="file://{file_path}" alt="{file_path.name}" />'
            
            # Add file statistics
            if include_statistics:
                size_kb = file_path.stat().st_size / 1024
                modified = Path.ctime(file_path)
                html += f"""
                <div class="file-stats">
                    <p>Size: {size_kb:.2f} KB</p>
                    <p>Modified: {modified}</p>
                </div>
                """
            
            # Add description if requested
            if include_descriptions:
                # Check for .cleanupx description file
                desc_file = directory / ".cleanupx" / f"{file_path.name}.json"
                description = "No description available"
                
                if desc_file.exists():
                    try:
                        with open(desc_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            description = data.get('description', description)
                    except:
                        pass
                
                html += f"""
                <div class="file-description">
                    <p><strong>Description:</strong> {description}</p>
                </div>
                """
            
            html += "</div>"
    
    return html
