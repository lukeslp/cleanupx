#!/usr/bin/env python3
"""
Command-line interface for CleanupX.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logging.error("Rich not installed. Install with: pip install rich")

try:
    import inquirer
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False
    logging.error("Inquirer not installed. Install with: pip install inquirer")

from cleanupx.ui.interactive import interactive_mode, scramble_directory
from cleanupx.utils.cache import load_rename_log
from cleanupx.ui.reporting import display_rename_report
from cleanupx.config import (
    IMAGE_EXTENSIONS, 
    TEXT_EXTENSIONS, 
    DOCUMENT_EXTENSIONS, 
    ARCHIVE_EXTENSIONS,
    CACHE_FILE
)

# Configure logging
logger = logging.getLogger(__name__)

def parse_args(args: List[str]) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: List of command-line arguments
        
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Process images, text files, and documents to generate descriptions and rename them."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Directory containing files to process",
        default="inbox"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Process subdirectories recursively"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Process all files, including previously renamed ones"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before processing"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--scramble", "-s",
        action="store_true",
        help="Scramble filenames with random strings instead of content-based renaming"
    )
    parser.add_argument(
        "--max-size",
        type=float,
        default=25.0,
        help="Skip files larger than this size in MB (default: 25MB)"
    )
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Process only image files"
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Process only text files"
    )
    parser.add_argument(
        "--documents-only",
        action="store_true",
        help="Process only document files"
    )
    parser.add_argument(
        "--archives-only",
        action="store_true",
        help="Process only archive files"
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip processing of image files"
    )
    parser.add_argument(
        "--skip-text",
        action="store_true",
        help="Skip processing of text files"
    )
    parser.add_argument(
        "--skip-documents",
        action="store_true",
        help="Skip processing of document files"
    )
    parser.add_argument(
        "--skip-archives",
        action="store_true",
        help="Skip processing of archive files"
    )
    
    return parser.parse_args(args)

def run_cli(args: Optional[List[str]] = None) -> int:
    """
    Run the command-line interface.
    
    Args:
        args: Optional list of command-line arguments (uses sys.argv if None)
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Use sys.argv if no args provided
    if args is None:
        args = sys.argv[1:]
    
    # Check if no arguments were provided
    if len(args) == 0:
        return interactive_mode()
    
    parsed_args = parse_args(args)
    
    # Interactive mode
    if parsed_args.interactive:
        return interactive_mode()
    
    # Ensure console is available for UI
    if not RICH_AVAILABLE:
        print("Rich library not available. Install with: pip install rich")
        return 1
        
    console = Console()
    
    directory = Path(parsed_args.directory)
    if not directory.is_dir():
        console.print(f"[bold red]Error: {directory} is not a valid directory[/bold red]")
        return 1
    
    # Scramble mode
    if parsed_args.scramble:
        if INQUIRER_AVAILABLE:
            confirm = inquirer.confirm(
                message=f"This will rename ALL files in {directory} with random names. Continue?",
                default=False
            )
            if not confirm:
                console.print("[yellow]Operation cancelled by user[/yellow]")
                return 1
        else:
            console.print("[yellow]Inquirer not installed. Proceeding without confirmation.[/yellow]")
        
        rename_log = load_rename_log()
        scrambled_count = scramble_directory(directory, rename_log)
        
        console.print(f"\n[bold green]Scrambling complete![/bold green]")
        console.print(f"[cyan]Total files scrambled:[/cyan] {scrambled_count}")
        
        # Display the comprehensive report
        display_rename_report(rename_log)
        
        return 0
    
    # Normal renaming mode
    if parsed_args.clear_cache and os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        console.print("[yellow]Cache cleared[/yellow]")
    
    # Configure file type filtering
    from cleanupx import config
    file_type_selection = []
    
    # "Only" flags have priority over "skip" flags
    if parsed_args.images_only or parsed_args.text_only or parsed_args.documents_only or parsed_args.archives_only:
        # If any "only" flag is set, first empty all extensions
        config.IMAGE_EXTENSIONS = set()
        config.TEXT_EXTENSIONS = set()
        config.DOCUMENT_EXTENSIONS = set()
        config.ARCHIVE_EXTENSIONS = set()
        
        # Then selectively restore based on flags
        if parsed_args.images_only:
            config.IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
            file_type_selection.append("images")
        if parsed_args.text_only:
            config.TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.text', '.log', '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.html', '.htm', '.py', '.zip'}
            file_type_selection.append("text")
        if parsed_args.documents_only:
            config.DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.doc', '.ppt', '.pptx'}
            file_type_selection.append("documents")
        if parsed_args.archives_only:
            config.ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.tgz', '.tar.gz', '.rar'}
            file_type_selection.append("archives")
    else:
        # Default is to process all types, then selectively skip
        file_type_selection = ["images", "text", "documents", "archives"]
        if parsed_args.skip_images:
            config.IMAGE_EXTENSIONS = set()
            file_type_selection.remove("images")
        if parsed_args.skip_text:
            config.TEXT_EXTENSIONS = set()
            file_type_selection.remove("text")
        if parsed_args.skip_documents:
            config.DOCUMENT_EXTENSIONS = set()
            file_type_selection.remove("documents")
        if parsed_args.skip_archives:
            config.ARCHIVE_EXTENSIONS = set()
            file_type_selection.remove("archives")
    
    console.print(Panel(
        f"[bold]Processing directory:[/bold] {directory}\n"
        f"[bold]Recursive:[/bold] {'Yes' if parsed_args.recursive else 'No'}\n"
        f"[bold]Skip renamed:[/bold] {'No' if parsed_args.force else 'Yes'}\n"
        f"[bold]File types:[/bold] {', '.join(file_type_selection) or 'None - no files will be processed'}",
        title="Processing Configuration",
        border_style="cyan"
    ))
    
    # Import process_directory here to avoid circular imports
    from cleanupx.main import process_directory
    
    with console.status("[bold green]Processing files...", spinner="dots") as status:
        stats = process_directory(directory, recursive=parsed_args.recursive, skip_renamed=not parsed_args.force, max_size_mb=parsed_args.max_size)
    
    console.print(Panel(
        f"[bold]Total files processed:[/bold] {stats['total']}\n"
        f"[bold]Images processed:[/bold] {stats['images']}\n"
        f"[bold]Text files processed:[/bold] {stats['text']}\n"
        f"[bold]Documents processed:[/bold] {stats['documents']}\n"
        f"[bold]Files skipped:[/bold] {stats['skipped']}\n"
        f"[bold]Files skipped (too large):[/bold] {stats.get('skipped_large', 0)}\n"
        f"[bold]Files failed:[/bold] {stats['failed']}",
        title="[bold green]Processing Complete![/bold green]",
        border_style="green"
    ))
    
    # Display comprehensive rename report
    rename_log = load_rename_log()
    display_rename_report(rename_log)
    
    return 0
