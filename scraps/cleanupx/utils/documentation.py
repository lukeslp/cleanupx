#!/usr/bin/env python3
"""
Documentation utilities for CleanupX.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

logger = logging.getLogger(__name__)

class DocumentationManager:
    """Manages documentation for directories, including summaries and citations."""
    
    def __init__(self, directory: Path):
        """
        Initialize the DocumentationManager for a directory.
        
        Args:
            directory: Path to the directory to document
        """
        self.directory = Path(directory)
        self.console = Console()
        self.summary_file = self.directory / ".cleanupx"
        self.readme_file = self.directory / "README.md"
        self.citations_file = self.directory / "CITATIONS.md"
    
    def generate_directory_summary(self) -> Dict[str, Any]:
        """
        Generates a summary of the directory contents.
        
        Returns:
            Dictionary containing the summary data
        """
        files = list(self.directory.glob("*"))
        
        # Count files by type
        file_types: Dict[str, int] = {}
        file_count = 0
        dir_count = 0
        
        # Track earliest and latest modification times
        earliest_mod_time = None
        latest_mod_time = None
        
        total_size = 0
        
        for item in files:
            if item.is_file():
                # Skip hidden files
                if item.name.startswith("."):
                    continue
                
                file_count += 1
                ext = item.suffix.lower() or "no_extension"
                file_types[ext] = file_types.get(ext, 0) + 1
                
                # Update file size
                size = item.stat().st_size
                total_size += size
                
                # Update modification times
                mod_time = datetime.fromtimestamp(item.stat().st_mtime)
                if earliest_mod_time is None or mod_time < earliest_mod_time:
                    earliest_mod_time = mod_time
                if latest_mod_time is None or mod_time > latest_mod_time:
                    latest_mod_time = mod_time
            
            elif item.is_dir():
                dir_count += 1
        
        # Generate summary
        summary = {
            "directory": str(self.directory),
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "file_count": file_count,
                "directory_count": dir_count,
                "file_types": file_types,
                "total_size_bytes": total_size,
                "earliest_modified": earliest_mod_time.isoformat() if earliest_mod_time else None,
                "latest_modified": latest_mod_time.isoformat() if latest_mod_time else None,
                "suggestions": []
            }
        }
        
        # Generate suggestions based on analysis
        suggestions = []
        if file_count > 50:
            suggestions.append("Consider organizing files into subdirectories for better management.")
        
        if any(count > 10 for ext, count in file_types.items()):
            suggestions.append("Some file types have high counts. Consider grouping them by type.")
        
        summary["analysis"]["suggestions"] = suggestions
        
        return summary
    
    def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a file to return its metadata."""
        stats = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path),
            "size": stats.st_size,
            "extension": file_path.suffix.lower(),
            "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
        }
    
    def _analyze_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Analyze a directory to return its metadata."""
        stats = dir_path.stat()
        file_count = len(list(dir_path.glob("*")))
        return {
            "name": dir_path.name,
            "path": str(dir_path),
            "file_count": file_count,
            "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
        }
    
    def _categorize_file(self, file_path: Path) -> str:
        """Categorize a file based on its extension."""
        ext = file_path.suffix.lower()
        
        # Basic categorization - expand as needed
        document_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        archive_extensions = {'.zip', '.rar', '.tar', '.gz', '.7z'}
        
        if ext in document_extensions:
            return "document"
        elif ext in image_extensions:
            return "image"
        elif ext in archive_extensions:
            return "archive"
        else:
            return "other"
    
    def update_hidden_summary(self) -> None:
        """Update the hidden summary file with the current state of the directory."""
        summary = self.generate_directory_summary()
        
        with open(self.summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        logger.info(f"Updated hidden summary at {self.summary_file}")
    
    def generate_readme(self) -> None:
        """Create a README.md file summarizing the directory contents."""
        if not self.summary_file.exists():
            self.update_hidden_summary()
            
        with open(self.summary_file) as f:
            summary = json.load(f)
        
        # Create markdown content
        md_content = f"# {self.directory.name} Directory\n\n"
        md_content += f"*Last updated: {summary['timestamp']}*\n\n"
        
        md_content += "## Overview\n\n"
        md_content += f"- **Files:** {summary['analysis']['file_count']}\n"
        md_content += f"- **Directories:** {summary['analysis']['directory_count']}\n"
        md_content += f"- **Total Size:** {summary['analysis']['total_size_bytes'] / (1024*1024):.2f} MB\n"
        
        if summary['analysis']['earliest_modified']:
            md_content += f"- **Date Range:** {summary['analysis']['earliest_modified'].split('T')[0]} to {summary['analysis']['latest_modified'].split('T')[0]}\n"
        
        md_content += "\n## File Types\n\n"
        md_content += "| Type | Count |\n"
        md_content += "|------|-------|\n"
        
        for ext, count in summary['analysis']['file_types'].items():
            md_content += f"| {ext} | {count} |\n"
        
        if summary['analysis']['suggestions']:
            md_content += "\n## Suggestions\n\n"
            for suggestion in summary['analysis']['suggestions']:
                md_content += f"- {suggestion}\n"
                
        # Project plan detection
        project_plan = self.directory / "PROJECT_PLAN.md"
        if project_plan.exists():
            md_content += "\n## Project Information\n\n"
            md_content += "This directory contains a project plan. See PROJECT_PLAN.md for details.\n"
        
        # Write to README
        with open(self.readme_file, 'w') as f:
            f.write(md_content)
            
        logger.info(f"Generated README at {self.readme_file}")
    
    def display_summary(self) -> None:
        """Display a summary of the directory in a formatted way."""
        if not self.summary_file.exists():
            self.update_hidden_summary()
            
        with open(self.summary_file) as f:
            summary = json.load(f)
            
        self.console.print("\n[bold]Directory Summary[/bold]")
        self.console.print(f"Location: {summary['directory']}")
        self.console.print(f"Last Updated: {summary['timestamp']}")
        
        # Display file type statistics
        table = Table(title="File Types")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="magenta")
        
        for ext, count in summary['analysis']['file_types'].items():
            table.add_row(ext, str(count))
            
        self.console.print(table)
        
        # Display suggestions
        if summary['analysis']['suggestions']:
            self.console.print("\n[bold]Suggestions:[/bold]")
            for suggestion in summary['analysis']['suggestions']:
                self.console.print(f"- {suggestion}")
    
    def update_citations(self) -> None:
        """Update the citations file with references from documents."""
        # TODO: Implement citation extraction from documents
        pass
    
    def display_citations(self) -> None:
        """Display citations in a formatted way."""
        if not self.citations_file.exists():
            self.console.print("[yellow]No citations file found.[/yellow]")
            return
            
        with open(self.citations_file) as f:
            citations_md = f.read()
            
        self.console.print(Markdown(citations_md)) 