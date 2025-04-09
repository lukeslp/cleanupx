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
    
    # Add new options for deduplication
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Find and remove duplicate files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes (works with --dedupe)"
    )
    parser.add_argument(
        "--auto-delete",
        action="store_true",
        help="Automatically delete duplicates without confirmation (use with --dedupe)"
    )
    
    # Add options for directory summaries
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Generate or update a directory summary without processing files"
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Suggest organization improvements based on directory summary"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip generating directory summaries after processing"
    )
    
    # Add option for interactive organization preferences
    parser.add_argument(
        "--ask-preferences", "-p",
        action="store_true",
        help="Prompt for organization preferences before processing"
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
    
    # Summary-only mode
    if parsed_args.summary:
        from cleanupx.utils.directory_summary import update_directory_summary
        console.print(f"[bold cyan]Generating directory summary for {directory}[/bold cyan]")
        
        # Include user preferences if requested
        include_prefs = parsed_args.ask_preferences
        summary = update_directory_summary(directory, include_user_prefs=include_prefs)
        
        console.print("[bold green]Directory summary updated[/bold green]")
        return 0
    
    # Suggestion-only mode
    if parsed_args.suggest:
        from cleanupx.utils.directory_summary import get_directory_summary
        console.print(f"[bold cyan]Analyzing directory {directory} for organization suggestions[/bold cyan]")
        
        # Include user preferences if requested
        include_prefs = parsed_args.ask_preferences
        summary = get_directory_summary(directory, include_user_prefs=include_prefs)
        
        suggestions = summary.get("suggestions", [])
        if suggestions:
            console.print("[bold yellow]Organization suggestions:[/bold yellow]")
            
            # Sort suggestions by priority if available
            try:
                suggestions.sort(key=lambda x: {
                    "high": 0,
                    "medium": 1,
                    "normal": 2,
                    "low": 3
                }.get(x.get("priority", "normal"), 2))
            except:
                pass  # If sorting fails, just use original order
                
            for suggestion in suggestions:
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                
                # Add priority indication if available
                priority_str = ""
                if "priority" in suggestion:
                    priority_str = f"[{suggestion['priority']}] "
                
                # Add indicator if this was user-requested or from project plan
                source = ""
                if suggestion.get("user_requested", False):
                    source = "[User preference] "
                elif suggestion.get("project_plan", False):
                    source = "[From PROJECT_PLAN.md] "
                    
                console.print(f"[cyan]- {suggestion_type}:[/cyan] {priority_str}{source}{reason}")
        else:
            console.print("[green]No suggestions available - directory seems well organized[/green]")
        return 0
    
    # Deduplication mode
    if parsed_args.dedupe:
        from cleanupx.main import dedupe_files
        console.print(f"[bold cyan]Scanning for duplicates in {directory}[/bold cyan]")
        
        # Confirm if not in dry-run mode and auto-delete is enabled
        if parsed_args.auto_delete and not parsed_args.dry_run:
            if INQUIRER_AVAILABLE:
                confirm = inquirer.confirm(
                    message=f"This will automatically delete duplicate files in {directory}. Continue?",
                    default=False
                )
                if not confirm:
                    console.print("[yellow]Operation cancelled by user[/yellow]")
                    return 1
            else:
                confirm = input(f"This will automatically delete duplicate files in {directory}. Continue? (y/N): ").lower().strip() == 'y'
                if not confirm:
                    console.print("Operation cancelled by user")
                    return 1
                
        result = dedupe_files(
            directory=directory,
            recursive=parsed_args.recursive,
            auto_delete=parsed_args.auto_delete,
            dry_run=parsed_args.dry_run
        )
        
        console.print(f"\n[bold green]Deduplication complete![/bold green]")
        console.print(f"[cyan]Duplicate groups found:[/cyan] {result.get('duplicate_groups', 0)}")
        console.print(f"[cyan]Total duplicates:[/cyan] {result.get('total_duplicates', 0)}")
        
        if parsed_args.auto_delete and not parsed_args.dry_run:
            console.print(f"[cyan]Files deleted:[/cyan] {result.get('deleted', 0)}")
        elif parsed_args.dry_run:
            console.print(f"[cyan]Files that would be deleted:[/cyan] {result.get('total_duplicates', 0)}")
            console.print("[yellow]Dry run completed. Use --auto-delete without --dry-run to actually delete files.[/yellow]")
        else:
            console.print("[yellow]No files were deleted. Use --auto-delete to remove duplicates.[/yellow]")
            
        return 0
    
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
        f"[bold]Ask for preferences:[/bold] {'Yes' if parsed_args.ask_preferences else 'No'}\n"
        f"[bold]File types:[/bold] {', '.join(file_type_selection) or 'None - no files will be processed'}",
        title="Processing Configuration",
        border_style="cyan"
    ))
    
    # Import process_directory here to avoid circular imports
    from cleanupx.main import process_directory
    
    # Process the directory
    stats = process_directory(
        directory=directory,
        recursive=parsed_args.recursive,
        skip_renamed=not parsed_args.force,
        max_size_mb=parsed_args.max_size,
        update_summary=not parsed_args.no_summary,
        include_user_prefs=parsed_args.ask_preferences
    )
    
    console.print(f"\n[bold green]Processing complete![/bold green]")
    console.print(f"[cyan]Files processed:[/cyan] {stats.get('total', 0)}")
    console.print(f"[cyan]Images renamed:[/cyan] {stats.get('images', 0)}")
    console.print(f"[cyan]Text files renamed:[/cyan] {stats.get('text', 0)}")
    console.print(f"[cyan]Documents renamed:[/cyan] {stats.get('documents', 0)}")
    console.print(f"[cyan]Files skipped:[/cyan] {stats.get('skipped', 0)}")
    console.print(f"[cyan]Files failed:[/cyan] {stats.get('failed', 0)}")
    
    # Display the comprehensive report
    rename_log = load_rename_log()
    display_rename_report(rename_log)
    
    # Show organization suggestions if available and summaries were generated
    if not parsed_args.no_summary:
        from cleanupx.utils.directory_summary import get_directory_summary
        summary = get_directory_summary(directory, include_user_prefs=False)  # Don't prompt again if already asked
        
        suggestions = summary.get("suggestions", [])
        if suggestions:
            console.print("\n[bold yellow]Organization suggestions:[/bold yellow]")
            for suggestion in suggestions:
                suggestion_type = suggestion.get("type", "")
                reason = suggestion.get("reason", "")
                console.print(f"[cyan]- {suggestion_type}:[/cyan] {reason}")
            
            console.print("\nRun with --suggest to see detailed suggestions or --dedupe to find duplicates")
    
    return 0
