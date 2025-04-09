#!/usr/bin/env python3
"""
Reporting utilities for CleanupX.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logging.error("Rich not installed. Install with: pip install rich")

# Configure logging
logger = logging.getLogger(__name__)

def display_rename_report(rename_log: Dict) -> None:
    """
    Display a comprehensive report of file renaming operations.
    
    Args:
        rename_log: Dictionary containing rename log information
    """
    if not RICH_AVAILABLE:
        logger.warning("Rich library not available. Cannot display formatted report.")
        return
    
    console = Console()
    
    console.print("\n[bold green]===== File Renaming Report =====[/bold green]")
    
    # Display summary statistics
    stats = rename_log.get("stats", {})
    
    stats_table = Table(title="Processing Statistics", show_header=True, header_style="bold cyan")
    stats_table.add_column("Metric", style="dim")
    stats_table.add_column("Count", justify="right")
    
    stats_table.add_row("Total Files Processed", str(stats.get("total_files", 0)))
    stats_table.add_row("Successfully Renamed", str(stats.get("successful_renames", 0)))
    stats_table.add_row("Failed Operations", str(stats.get("failed_renames", 0)))
    stats_table.add_row("Skipped Files", str(stats.get("skipped_files", 0)))
    stats_table.add_row("Images Processed", str(stats.get("images_processed", 0)))
    stats_table.add_row("Text Files Processed", str(stats.get("text_processed", 0)))
    stats_table.add_row("Documents Processed", str(stats.get("documents_processed", 0)))
    
    console.print(stats_table)
    
    # Display successful renames
    if rename_log.get("renames", []):
        console.print("\n[bold cyan]Successful Rename Operations:[/bold cyan]")
        
        rename_table = Table(show_header=True, header_style="bold cyan", show_lines=True)
        rename_table.add_column("Original Filename", style="dim")
        rename_table.add_column("New Filename", style="green")
        rename_table.add_column("File Type", style="yellow")
        
        for entry in rename_log.get("renames", []):
            orig_path = Path(entry.get("original_path", ""))
            new_path = Path(entry.get("new_path", ""))
            
            file_type = orig_path.suffix.lower() if orig_path.suffix else "unknown"
            
            rename_table.add_row(
                orig_path.name,
                new_path.name,
                file_type
            )
        
        console.print(rename_table)
    
    # Display errors if any
    if rename_log.get("errors", []):
        console.print("\n[bold red]Failed Operations:[/bold red]")
        
        error_table = Table(show_header=True, header_style="bold red", show_lines=True)
        error_table.add_column("Filename", style="dim")
        error_table.add_column("Error Type", style="yellow")
        error_table.add_column("Error Details", style="red")
        
        for entry in rename_log.get("errors", []):
            file_path = Path(entry.get("file_path", ""))
            error_type = entry.get("error_type", "unknown")
            error_msg = entry.get("error", "No details available")
            
            error_table.add_row(
                file_path.name,
                error_type,
                error_msg
            )
        
        console.print(error_table)
    
    # Display log file location
    from cleanupx.config import RENAME_LOG_FILE
    console.print(f"\n[dim]Full rename log saved to: {RENAME_LOG_FILE}[/dim]")
